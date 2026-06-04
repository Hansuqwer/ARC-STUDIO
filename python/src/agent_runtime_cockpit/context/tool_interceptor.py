"""QW-4 tool-output virtualization interceptor.

Transforms a ProviderRequest: any tool message with content > threshold
bytes is stored as a handle and replaced with a resource_link summary.

No LLM in this path (CoSAI). Decision is a byte-size comparison only.
"""

from __future__ import annotations

from typing import Callable

from ..events import get_bus
from ..events.types import ToolOutputVirtualized
from ..providers.base import ProviderMessage, ProviderRequest
from .handles import VIRTUALIZE_THRESHOLD, HandleStore


def virtualize_tool_outputs(
    request: ProviderRequest,
    handle_store: HandleStore,
    threshold: int = VIRTUALIZE_THRESHOLD,
    redactor: Callable[[bytes], bytes] | None = None,
) -> ProviderRequest:
    """Return a new ProviderRequest with oversized tool messages replaced by handles.

    If no messages are over the threshold, returns the same request object unchanged.
    """
    new_messages: list[ProviderMessage] = []
    changed = False

    for msg in request.messages:
        if msg.role == "tool":
            raw = msg.content.encode() if isinstance(msg.content, str) else msg.content
            if len(raw) > threshold:
                meta = handle_store.store(raw, mime_type="text/plain")
                resource_link = (
                    f"[tool output too large to inline — {meta.size_bytes} bytes, "
                    f"~{meta.estimated_tokens} tokens]\n"
                    f"Handle: {meta.uri}\n"
                    f"Preview (head): {meta.preview_head[:200]}\n"
                    f"Preview (tail): {meta.preview_tail[:200] if meta.preview_tail else ''}\n"
                    f"To expand: /expand {meta.sha256_hex[:8]}"
                )
                new_messages.append(msg.model_copy(update={"content": resource_link}))
                changed = True

                get_bus().publish(
                    ToolOutputVirtualized(
                        tool_name="tool",
                        original_size_bytes=meta.size_bytes,
                        handle_uri=meta.uri,
                        estimated_tokens_saved=meta.estimated_tokens,
                    )
                )
                continue
        new_messages.append(msg)

    if not changed:
        return request
    return request.model_copy(update={"messages": new_messages})
