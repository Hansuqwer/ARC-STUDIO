"""Pydantic AI adapter for ARC Studio.

Phase 29: Detection, export, and live streaming for Pydantic AI agents.
"""

from __future__ import annotations

__all__ = ["detect_pydantic_ai", "PydanticAIDetectionResult"]

from .detect import PydanticAIDetectionResult, detect_pydantic_ai
