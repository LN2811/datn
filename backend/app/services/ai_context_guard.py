from typing import Any


CONTEXT_SELECTION_SIGNATURE = "context-selector-v1"


def require_context_selection(context_selection: Any) -> None:
    if getattr(context_selection, "_selector_signature", None) != CONTEXT_SELECTION_SIGNATURE:
        raise RuntimeError("AI request rejected: ContextSelector metadata is required")
    if getattr(context_selection, "_validated", False) is not True:
        raise RuntimeError("AI request rejected: ContextSelector metadata was not validated")

    context_chars = getattr(context_selection, "context_chars", None)
    text = getattr(context_selection, "text", None)
    if not isinstance(context_chars, int) or not isinstance(text, str):
        raise RuntimeError("AI request rejected: invalid ContextSelector metadata")
    if context_chars != len(text):
        raise RuntimeError("AI request rejected: stale ContextSelector metadata")
