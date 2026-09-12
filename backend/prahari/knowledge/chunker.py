"""Layout-aware chunking.

Chunks are the unit of citation, so the boundaries matter. Two rules do most
of the work:

1. **Never split a table row.** An inspection table row is a single fact
   ("E-14 | 5.9 mm | 6.4 mm | critical"); half a row cites nothing useful.
2. **Keep the section heading with the body.** A chunk reading "shall be
   6.4 mm" is useless without "4.2 Retirement thickness" attached.

Sizes are in characters rather than tokens deliberately — an exact token count
would need the model's tokeniser loaded at ingest time, and the precision buys
nothing here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

TARGET_CHARS = 1400
OVERLAP_CHARS = 200
MIN_CHUNK_CHARS = 80

# A heading is a short line that is numbered, all-caps, or title-case without
# terminal punctuation. Deliberately conservative: a false positive splits a
# paragraph, which is worse than missing a heading.
_HEADING = re.compile(
    r"^\s*(?:"
    r"\d+(?:\.\d+)*\.?\s+\S.{0,70}"          # 4.2 Retirement thickness
    r"|[A-Z][A-Z0-9 \-/&(),.]{3,70}"          # SECTION HEADINGS
    r"|(?:[A-Z][a-z]+\s+){1,7}[A-Z][a-z]+"    # Title Case Heading
    r")\s*$"
)


@dataclass
class Chunk:
    text: str
    page: int
    section: str = ""
    index: int = 0
    meta: dict[str, Any] = field(default_factory=dict)

    def citation_label(self, document: str) -> str:
        bits = [document, f"p. {self.page}"]
        if self.section:
            bits.append(self.section)
        return " · ".join(bits)


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not (3 < len(stripped) <= 80):
        return False
    if stripped.endswith((".", ":", ";", ",")) and not re.match(r"^\d", stripped):
        return False
    if "|" in stripped:          # a table row, not a heading
        return False
    return bool(_HEADING.match(stripped))


def _is_table_row(line: str) -> bool:
    return line.count("|") >= 2


def _split_paragraphs(text: str) -> list[str]:
    """Split into blocks, keeping runs of table rows together."""
    lines = text.splitlines()
    blocks: list[str] = []
    buffer: list[str] = []
    in_table = False

    def flush() -> None:
        if buffer:
            joined = "\n".join(buffer).strip()
            if joined:
                blocks.append(joined)
            buffer.clear()

    for line in lines:
        row = _is_table_row(line)

        # A table boundary is a block boundary either way.
        if row != in_table:
            flush()
            in_table = row

        if not line.strip() and not in_table:
            flush()
            continue

        buffer.append(line)

    flush()
    return blocks


def chunk_pages(pages: list[Any], document: str = "") -> list[Chunk]:
    """Turn `Page` records into citable chunks.

    Accepts anything with `.number` and `.text` so readers stay decoupled.
    """
    chunks: list[Chunk] = []
    counter = 0

    for page in pages:
        text = (page.text or "").strip()
        if not text:
            continue

        section = ""
        current: list[str] = []
        current_len = 0

        def emit(section_label: str) -> None:
            nonlocal counter, current, current_len
            body = "\n".join(current).strip()
            if len(body) < MIN_CHUNK_CHARS and chunks and chunks[-1].page == page.number:
                # Too small to cite on its own — fold it into the previous chunk.
                chunks[-1].text += "\n" + body
                current, current_len = [], 0
                return
            if body:
                counter += 1
                chunks.append(Chunk(
                    text=(f"[{section_label}]\n{body}" if section_label else body),
                    page=page.number,
                    section=section_label,
                    index=counter,
                    meta={"document": document, "method": getattr(page, "method", "")},
                ))
            current, current_len = [], 0

        for block in _split_paragraphs(text):
            first_line = block.splitlines()[0] if block else ""

            # A heading closes the previous chunk and labels the next.
            if _is_heading(first_line) and len(block.splitlines()) == 1:
                if current:
                    emit(section)
                section = first_line.strip()
                continue

            # A block that alone exceeds the target is hard-split, on line
            # boundaries so table rows survive.
            if len(block) > TARGET_CHARS * 1.6:
                if current:
                    emit(section)
                for piece in _hard_split(block):
                    current = [piece]
                    current_len = len(piece)
                    emit(section)
                continue

            if current_len + len(block) > TARGET_CHARS and current:
                tail = "\n".join(current)[-OVERLAP_CHARS:]
                emit(section)
                if tail.strip():
                    current, current_len = [tail], len(tail)

            current.append(block)
            current_len += len(block) + 1

        if current:
            emit(section)

    return chunks


def _hard_split(block: str) -> list[str]:
    """Split an oversized block on line boundaries."""
    pieces: list[str] = []
    buffer: list[str] = []
    size = 0
    for line in block.splitlines():
        if size + len(line) > TARGET_CHARS and buffer:
            pieces.append("\n".join(buffer))
            buffer, size = [], 0
        buffer.append(line)
        size += len(line) + 1
    if buffer:
        pieces.append("\n".join(buffer))
    return pieces
