"""Intelligent drafting and synthesis tools."""

from __future__ import annotations

from ..agent.schemas import Observation
from .base import CAP_COMPUTE, ToolContext, ToolSpec, registry


def llm_write(
    ctx: ToolContext, *, prompt: str, context: list[str]
) -> Observation:
    """Uses the `write` model role to draft prose from retrieved contexts."""
    # Deferred import to avoid circular dependency with agent.loop
    from ..agent.loop import get_runner, routing_request_for

    runner = get_runner()
    
    model = runner._route(
        ctx.run_id,
        routing_request_for("write"),
        label="draft document content",
    )
    if not model:
        return Observation(
            ok=False,
            summary="no model available for write role",
            error="no model available for write role",
        )

    context_text = "\n\n".join(context)
    system = (
        "You are an expert industrial technical writer. Your task is to draft a report, "
        "summary, or note based ONLY on the provided context passages. "
        "Do not hallucinate external facts. Write clearly and professionally."
    )
    user_prompt = f"Context:\n{context_text}\n\nTask: {prompt}\n\nWrite the content now."

    gen = runner._client.chat(
        model,
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
    )
    
    # We update the run state token count so the budget is respected
    state = runner.get(ctx.run_id)
    if state:
        state.tokens += gen.prompt_tokens + gen.output_tokens

    return Observation(
        ok=True,
        summary=f"drafted {len(gen.text.split())} words using {model}",
        data={
            "drafted_text": gen.text,
            "prompt_tokens": gen.prompt_tokens,
            "output_tokens": gen.output_tokens,
        },
    )


registry.register(
    ToolSpec(
        name="llm.write",
        description="Draft a report, summary, or response using retrieved context.",
        args_schema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "What to write about"},
                "context": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Source text to base the writing on",
                },
            },
            "required": ["prompt", "context"],
        },
        capabilities=frozenset({CAP_COMPUTE}),
        handler=llm_write,
        returns="the generated prose",
    )
)
