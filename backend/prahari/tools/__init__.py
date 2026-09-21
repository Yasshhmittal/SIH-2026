"""Tool package. Importing it registers every built-in tool.

Import order is the registration order; the registry rejects duplicates, so a
double import is a loud failure rather than a silent override.
"""

from . import calc, code_sandbox, deliverables, files, llm, multimodal, stubs  # noqa: F401  (import for side effects)
from .base import (
    DEFAULT_GRANTS,
    PolicyViolation,
    ToolContext,
    ToolError,
    ToolRegistry,
    ToolSpec,
    registry,
)

__all__ = [
    "registry", "ToolRegistry", "ToolSpec", "ToolContext",
    "ToolError", "PolicyViolation", "DEFAULT_GRANTS",
]
