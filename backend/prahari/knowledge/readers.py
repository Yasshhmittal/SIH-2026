"""Document readers — text and page structure out of real files.

Everything here is local and pip-installable: no system binaries, no OCR
service, no cloud API. That matters for the deployment story as much as for the
sovereignty one — an air-gapped site cannot run an installer that reaches out.

Each reader returns `Page` records carrying a page number, so a citation can
point at "SOP-INS-07, page 12" rather than at a whole document.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SUPPORTED_SUFFIXES = {
    ".pdf", ".docx", ".xlsx", ".xlsm", ".pptx",
    ".txt", ".md", ".csv", ".log",
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff",
}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


@dataclass
class Page:
    number: int
    text: str
    # How the text was obtained, surfaced in the UI so a judge can tell
    # extracted text from OCR'd text from a vision-model transcription.
    method: str = "text"
    needs_ocr: bool = False
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReadResult:
    pages: list[Page]
    kind: str
    error: str | None = None

    @property
    def text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text.strip())

    @property
    def char_count(self) -> int:
        return sum(len(p.text) for p in self.pages)


# ------------------------------------------------------------------- pdf ---

def _read_pdf(path: Path) -> ReadResult:
    """Born-digital PDFs give exact text. Scanned ones give nothing.

    A page yielding almost no characters is a scan, so it is flagged
    `needs_ocr` rather than silently indexed as empty — an empty chunk that
    looks successful is worse than a missing one.
    """
    try:
        import fitz  # pymupdf
    except ImportError:
        return ReadResult([], "pdf", error="pymupdf not installed")

    pages: list[Page] = []
    try:
        with fitz.open(path) as doc:
            for index, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                sparse = len(text.strip()) < 40
                pages.append(Page(
                    number=index,
                    text=text,
                    method="pdf-text" if not sparse else "pdf-empty",
                    needs_ocr=sparse,
                    meta={"width": page.rect.width, "height": page.rect.height},
                ))
    except Exception as exc:
        return ReadResult(pages, "pdf", error=f"{type(exc).__name__}: {exc}")

    return ReadResult(pages, "pdf")


# ------------------------------------------------------------------ docx ---

def _read_docx(path: Path) -> ReadResult:
    try:
        from docx import Document
    except ImportError:
        return ReadResult([], "docx", error="python-docx not installed")

    try:
        doc = Document(path)
    except Exception as exc:
        return ReadResult([], "docx", error=f"{type(exc).__name__}: {exc}")

    blocks: list[str] = [p.text for p in doc.paragraphs if p.text.strip()]

    # Tables carry most of the numbers in an inspection report, so they are
    # flattened into pipe-delimited rows rather than dropped.
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                blocks.append(" | ".join(cells))

    # Word has no page concept without rendering; treat it as one page.
    return ReadResult([Page(1, "\n".join(blocks), method="docx")], "docx")


# ------------------------------------------------------------------ xlsx ---

def _read_xlsx(path: Path) -> ReadResult:
    try:
        from openpyxl import load_workbook
    except ImportError:
        return ReadResult([], "xlsx", error="openpyxl not installed")

    try:
        book = load_workbook(path, data_only=True, read_only=True)
    except Exception as exc:
        return ReadResult([], "xlsx", error=f"{type(exc).__name__}: {exc}")

    pages: list[Page] = []
    for index, sheet in enumerate(book.worksheets, start=1):
        rows: list[str] = []
        for row in sheet.iter_rows(values_only=True):
            cells = ["" if v is None else str(v) for v in row]
            if any(c.strip() for c in cells):
                rows.append(" | ".join(cells))
        if rows:
            pages.append(Page(
                number=index,
                text=f"[sheet: {sheet.title}]\n" + "\n".join(rows),
                method="xlsx",
                meta={"sheet": sheet.title},
            ))
    book.close()
    return ReadResult(pages, "xlsx")


# ------------------------------------------------------------------ pptx ---

def _read_pptx(path: Path) -> ReadResult:
    try:
        from pptx import Presentation
    except ImportError:
        return ReadResult([], "pptx", error="python-pptx not installed")

    try:
        deck = Presentation(path)
    except Exception as exc:
        return ReadResult([], "pptx", error=f"{type(exc).__name__}: {exc}")

    pages: list[Page] = []
    for index, slide in enumerate(deck.slides, start=1):
        parts: list[str] = []
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame.text.strip():
                parts.append(shape.text_frame.text)
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    cells = [c.text.strip() for c in row.cells]
                    if any(cells):
                        parts.append(" | ".join(cells))
        if parts:
            pages.append(Page(index, "\n".join(parts), method="pptx"))
    return ReadResult(pages, "pptx")


# ------------------------------------------------------------- plain text ---

def _read_text(path: Path) -> ReadResult:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return ReadResult([], "text", error=f"{type(exc).__name__}: {exc}")
    return ReadResult([Page(1, raw, method="text")], "text")


def _read_csv(path: Path) -> ReadResult:
    """CSV as pipe-delimited rows, with the header repeated for context.

    Large files are truncated: a 30-year stock history indexed row by row
    would swamp retrieval for every other document in the corpus.
    """
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return ReadResult([], "csv", error=f"{type(exc).__name__}: {exc}")

    try:
        rows = list(csv.reader(io.StringIO(raw)))
    except Exception:
        return _read_text(path)

    if not rows:
        return ReadResult([], "csv", error="empty csv")

    header, body = rows[0], rows[1:]
    limit = 500
    truncated = len(body) > limit

    lines = [" | ".join(header)]
    lines += [" | ".join(r) for r in body[:limit]]
    if truncated:
        lines.append(f"[... {len(body) - limit} further rows not indexed]")

    return ReadResult(
        [Page(1, "\n".join(lines), method="csv",
              meta={"rows": len(body), "truncated": truncated})],
        "csv",
    )


# ---------------------------------------------------------------- images ---

def _read_image(path: Path) -> ReadResult:
    """Images hold no extractable text — they need OCR or a vision model.

    An empty page flagged `needs_ocr` is returned so the caller can route it,
    instead of pretending the file was read.
    """
    return ReadResult(
        [Page(1, "", method="image-pending-ocr", needs_ocr=True,
              meta={"filename": path.name})],
        "image",
    )


_READERS = {
    ".pdf": _read_pdf,
    ".docx": _read_docx,
    ".xlsx": _read_xlsx, ".xlsm": _read_xlsx,
    ".pptx": _read_pptx,
    ".txt": _read_text, ".md": _read_text, ".log": _read_text,
    ".csv": _read_csv,
}


def read_document(path: Path) -> ReadResult:
    """Read any supported file into pages of text."""
    path = Path(path)
    if not path.exists():
        return ReadResult([], "unknown", error=f"no such file: {path}")

    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return _read_image(path)

    reader = _READERS.get(suffix)
    if reader is None:
        return ReadResult([], "unsupported",
                          error=f"unsupported file type '{suffix}'. "
                                f"Supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}")
    return reader(path)
