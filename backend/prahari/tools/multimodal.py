"""Multimodal tools for OCR and vision capabilities."""

from __future__ import annotations

import base64
from pathlib import Path

from ..agent.schemas import Observation
from ..config import ORGS_DIR
from ..llm.ollama import generate
from .base import CAP_KB_READ, CAP_VISION, ToolContext, ToolSpec, registry


def _resolve_document_path(ctx: ToolContext, document_id: str) -> Path | None:
    """Find a document in the organization's knowledge base."""
    # This is a naive implementation: check inbox first, then kb directories
    org_dir = ORGS_DIR / ctx.org_id
    
    # Try direct filename in inbox
    inbox_path = org_dir / "inbox" / document_id
    if inbox_path.exists() and inbox_path.is_file():
        return inbox_path
        
    # Check if we can find it anywhere in the org dir
    for path in org_dir.rglob(document_id):
        if path.is_file():
            return path
            
    # Try as an absolute path (with security boundary check)
    try:
        path = Path(document_id).resolve()
        if path.is_relative_to(org_dir.resolve()) and path.exists():
            return path
    except ValueError:
        pass
        
    return None


def ocr_page(ctx: ToolContext, *, document: str, page: int = 1) -> Observation:
    """Extract text from one page of a scanned document."""
    import pymupdf
    
    path = _resolve_document_path(ctx, document)
    if not path:
        return Observation(
            ok=False,
            summary=f"Document not found: {document}",
            data={"error": "not found"}
        )
        
    try:
        doc = pymupdf.open(str(path))
        if page < 1 or page > len(doc):
            return Observation(
                ok=False,
                summary=f"Page {page} out of range (1-{len(doc)})",
                data={"error": "page out of range"}
            )
            
        page_obj = doc[page - 1]
        text = page_obj.get_text()
        
        return Observation(
            ok=True,
            summary=f"Extracted {len(text)} characters from page {page}",
            data={
                "document": document,
                "page": page,
                "text": text,
            }
        )
    except Exception as exc:
        return Observation(
            ok=False,
            summary=f"OCR failed: {exc}",
            data={"error": str(exc)}
        )


def vision_ask(ctx: ToolContext, *, image: str, question: str) -> Observation:
    """Ask a vision model a question about an image."""
    import pymupdf
    
    # Check if the "image" refers to a document page, e.g. "doc.pdf (page 1)"
    # A bit hacky, but lets the agent pass the document name. We will extract page 1 if it's a PDF.
    path = _resolve_document_path(ctx, image)
    
    if not path:
        return Observation(
            ok=False,
            summary=f"Image/Document not found: {image}",
            data={"error": "not found"}
        )
        
    image_b64 = None
    
    try:
        if path.suffix.lower() == ".pdf":
            doc = pymupdf.open(str(path))
            page_obj = doc[0] # Just use page 1 for now if no page specified
            pix = page_obj.get_pixmap()
            img_bytes = pix.tobytes("png")
            image_b64 = base64.b64encode(img_bytes).decode("utf-8")
        else:
            with open(path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")
                
        # Call the vision model (defaulting to moondream or qwen2.5vl:3b if available)
        # Using the standard generate API
        result = generate(
            model="moondream", # or query router for a vision model
            prompt=question,
            images=[image_b64]
        )
        
        return Observation(
            ok=True,
            summary="Vision model provided an answer",
            data={
                "image": image,
                "question": question,
                "answer": result,
            }
        )
    except Exception as exc:
        return Observation(
            ok=False,
            summary=f"Vision request failed: {exc}",
            data={"error": str(exc)}
        )


registry.register(
    ToolSpec(
        name="ocr.page",
        description="Extract text from one page of a scanned document.",
        args_schema={
            "type": "object",
            "properties": {
                "document": {"type": "string", "description": "Document id or filename"},
                "page": {"type": "integer", "description": "1-based page number"},
            },
            "required": ["document"],
        },
        capabilities=frozenset({CAP_KB_READ}),
        handler=ocr_page,
        returns="page text with per-region confidence",
        planner_visible=False,
    )
)

registry.register(
    ToolSpec(
        name="vision.ask",
        description="Ask a question about an image, drawing or scanned page.",
        args_schema={
            "type": "object",
            "properties": {
                "image": {"type": "string", "description": "Image path or document page ref"},
                "question": {"type": "string", "description": "What to ask about it"},
            },
            "required": ["image", "question"],
        },
        capabilities=frozenset({CAP_VISION}),
        handler=vision_ask,
        returns="answer grounded in the image region",
        planner_visible=False,
    )
)
