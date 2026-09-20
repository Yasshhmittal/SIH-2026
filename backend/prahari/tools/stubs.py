"""Tools whose subsystems are not yet built (phases P4-P5), plus kb.search.

The remaining stubs are deliberately *honest*: every observation is tagged
`stub: true` and the summary is prefixed `[STUB]`, so a stubbed run is never
mistaken for a working one — in the UI, in the audit log, or in a demo.

`kb.search` is no longer a stub; it lives here because the tool definitions are
registered together. Its interface did not change when the real implementation
landed, which is the point of having defined it properly up front.
"""

from __future__ import annotations

from ..agent.schemas import Observation
from .base import (
    CAP_EXEC_SANDBOX,
    CAP_KB_READ,
    CAP_VISION,
    ToolContext,
    ToolSpec,
    registry,
)


def _stub(summary: str, **data) -> Observation:
    return Observation(
        ok=True,
        summary=f"[STUB] {summary}",
        data={"stub": True, **data},
    )


def kb_search(ctx: ToolContext, *, query: str, k: int = 6) -> Observation:
    """Real hybrid retrieval over the organisation's indexed documents.

    No longer a stub. Scoped by `ctx.org_id`, so one organisation's chunks are
    structurally unreachable from another's.
    """
    from ..knowledge.search import search_knowledge

    return search_knowledge(query, org_id=ctx.org_id, k=k)


def ocr_page(ctx: ToolContext, *, document: str, page: int = 1) -> Observation:
    return _stub(
        f"would OCR page {page} of {document}",
        document=document, page=page, text="", confidence=None,
        note="OCR cascade lands in P3 (pdfplumber -> RapidOCR -> VL escalation).",
    )


def vision_ask(ctx: ToolContext, *, image: str, question: str) -> Observation:
    return _stub(
        f"would ask a vision model about {image}",
        image=image, question=question, answer="",
        note="Vision lands in P5 (moondream / qwen2.5vl via the router).",
    )


def code_run(ctx: ToolContext, *, code: str, tests: str | None = None) -> Observation:
    return _stub(
        "would execute code in a network-isolated container",
        code_chars=len(code), has_tests=bool(tests),
        stdout="", stderr="", exit_code=None,
        note="Sandbox lands in P4 (docker --network none, caps dropped).",
    )


_STUBS = [
    ToolSpec(
        name="kb.search",
        description="Search the organisation's indexed documents. Returns cited chunks.",
        args_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look for"},
                "k": {"type": "integer", "description": "How many chunks to return"},
            },
            "required": ["query"],
        },
        capabilities=frozenset({CAP_KB_READ}),
        handler=kb_search,
        returns="list of chunks with doc, page and bbox for citation",
    ),
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
    ),
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
    ),
    ToolSpec(
        name="code.run",
        description="Run Python in an isolated sandbox with no network. Returns output.",
        args_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python source to execute"},
                "tests": {"type": "string", "description": "Optional pytest source"},
            },
            "required": ["code"],
        },
        capabilities=frozenset({CAP_EXEC_SANDBOX}),
        handler=code_run,
        returns="stdout, stderr, exit code",
    ),
]

for _spec in _STUBS:
    registry.register(_spec)
