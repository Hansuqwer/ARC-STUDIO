"""Core Arena service — handles battle, direct, code, and agent-arena-preview modes."""
from __future__ import annotations

import json
import os
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..gating import GatingError, require_dual_gate
from ..protocol.envelope import ArcEnvelope, ok, err
from ..protocol.errors import ArcErrorCode
from ..protocol.schemas import RunEvent, RunRecord, RunStatus
from ..security.profiles import enforce_profile, resolve_profile
from ..storage.jsonl import JsonlTraceStore
from .models import (
    ArenaAdoptRequest,
    ArenaAdoptResult,
    ArenaCandidate,
    ArenaMode,
    ArenaModelInfo,
    ArenaRequest,
    ArenaResponse,
    ArenaVote,
    PrivacyLevel,
)

# ── Known Arena models (mirrors Copilot Arena model config) ──────────────

DEFAULT_MODELS: list[ArenaModelInfo] = [
    ArenaModelInfo(id="gpt-4o-mini-2024-07-18", name="GPT-4o Mini", provider="openai",
                   tags=["fast", "edit"], supports_battle=True, supports_direct=True,
                   supports_code=True, input_cost=0.15, output_cost=0.6),
    ArenaModelInfo(id="gpt-4o-2024-08-06", name="GPT-4o", provider="openai",
                   tags=["best", "edit"], supports_battle=True, supports_direct=True,
                   supports_code=True, input_cost=2.5, output_cost=10.0),
    ArenaModelInfo(id="codestral-2405", name="Codestral", provider="mistral",
                   tags=["fast", "code"], supports_battle=True, supports_direct=True,
                   supports_code=True, supports_agent_preview=False),
    ArenaModelInfo(id="llama-3.1-70b", name="Llama 3.1 70B", provider="meta",
                   tags=["open", "code"], supports_battle=True, supports_direct=True,
                   supports_code=True),
    ArenaModelInfo(id="llama-3.1-405b", name="Llama 3.1 405B", provider="meta",
                   tags=["best", "open"], supports_battle=True, supports_direct=True,
                   supports_code=True, input_cost=2.0, output_cost=6.0),
    ArenaModelInfo(id="claude-sonnet-4-20250514", name="Claude Sonnet 4", provider="anthropic",
                   tags=["best", "code", "agent"], supports_battle=True, supports_direct=True,
                   supports_code=True, supports_agent_preview=True),
    ArenaModelInfo(id="deepseek-coder-v2", name="DeepSeek Coder V2", provider="deepseek",
                   tags=["code", "open"], supports_battle=True, supports_direct=True,
                   supports_code=True),
]

# ── Model tags for filtering ─────────────────────────────────────────────

MODEL_TAGS: dict[str, str] = {
    "fast": "Fast models (low latency)",
    "best": "Best quality models",
    "code": "Code-optimized models",
    "edit": "Editing/infill models",
    "open": "Open-weight models",
    "agent": "Agent-capable models",
}


def list_models(tags: list[str] | None = None) -> list[ArenaModelInfo]:
    """List available Arena models, optionally filtered by tags."""
    if not tags:
        return DEFAULT_MODELS
    return [m for m in DEFAULT_MODELS if any(t in m.tags for t in tags)]


def list_tags() -> dict[str, str]:
    """List available model tags with descriptions."""
    return dict(MODEL_TAGS)


# ── Stub response generators (for offline/testing, no real API calls) ───

def _stub_battle(ws: Path, prompt: str, model_tags: list[str]) -> ArenaResponse:
    """Generate stub battle responses for offline testing."""
    models = list_models(model_tags) if model_tags else [DEFAULT_MODELS[0], DEFAULT_MODELS[1]]
    run_id = f"arena-battle-{uuid.uuid4().hex[:12]}"
    candidates = []
    for m in models[:2]:
        candidates.append(ArenaCandidate(
            id=f"{run_id}-{m.id.split('-')[0]}",
            model=m.id,
            text=f"# Response from {m.name}\n\n**Prompt:** {prompt}\n\nThis is a stub response from {m.name}. "
                 f"In production, this would contain the model's actual output.\n\n```python\ndef hello():\n    "
                 f'print("Hello from {m.name}")\n```',
            patch="",
            diff="",
        ))
    return ArenaResponse(
        run_id=run_id,
        mode=ArenaMode.BATTLE,
        candidates=candidates,
        recommended=candidates[0].id if random.random() > 0.5 else "",
        warnings=["Stub mode: no real API calls. Set ARC_ALLOW_LIVE_ARENA=true for live responses."],
    )


def _stub_direct(ws: Path, prompt: str, model: str) -> ArenaResponse:
    """Generate a stub direct response."""
    models = list_models()
    m = next((x for x in models if x.id == model), models[0])
    run_id = f"arena-direct-{uuid.uuid4().hex[:12]}"
    return ArenaResponse(
        run_id=run_id,
        mode=ArenaMode.DIRECT,
        candidates=[ArenaCandidate(
            id=f"{run_id}-{m.id.split('-')[0]}",
            model=m.id,
            text=f"# Response from {m.name}\n\n**Prompt:** {prompt}\n\nThis is a stub direct response from {m.name}.\n\n"
                 f"```python\ndef solution():\n    return '{m.name} response for: {prompt}'\n```",
        )],
        warnings=["Stub mode: no real API calls."],
    )


def _stub_code(ws: Path, prompt: str, model: str) -> ArenaResponse:
    """Generate a stub code/patch response."""
    models = list_models()
    m = next((x for x in models if x.id == model), models[0])
    run_id = f"arena-code-{uuid.uuid4().hex[:12]}"
    return ArenaResponse(
        run_id=run_id,
        mode=ArenaMode.CODE,
        candidates=[ArenaCandidate(
            id=f"{run_id}-{m.id.split('-')[0]}",
            model=m.id,
            text=f"Code generated by {m.name}",
            patch=f"--- a/src/example.py\n+++ b/src/example.py\n@@ -0,0 +1,10 @@\n+# Generated by {m.name}\n+def generated_function():\n+    \"\"\"Generated from: {prompt}\"\"\"\n+    return 'implemented'\n+",
            diff=f"diff --git a/src/example.py b/src/example.py\nnew file mode 100644\n"
                 f"--- /dev/null\n+++ b/src/example.py\n@@ -0,0 +1,10 @@\n+# Generated by {m.name}\n+def generated_function():\n+    \"\"\"Generated from: {prompt}\"\"\"\n+    return 'implemented'\n+",
            files_changed=["src/example.py"],
        )],
        warnings=["Stub mode: no real API calls."],
    )


def _stub_agent_preview(ws: Path, prompt: str, model: str) -> ArenaResponse:
    """Generate a stub agent-arena-preview response with plan + patch."""
    models = list_models()
    m = next((x for x in models if x.id == model), models[0])
    run_id = f"arena-agent-{uuid.uuid4().hex[:12]}"
    return ArenaResponse(
        run_id=run_id,
        mode=ArenaMode.AGENT_ARENA_PREVIEW,
        candidates=[ArenaCandidate(
            id=f"{run_id}-{m.id.split('-')[0]}",
            model=m.id,
            text=f"# Agent Plan by {m.name}\n\n## Plan\n1. Analyze requirements\n2. Design solution\n3. Implement changes\n4. Add tests\n\n## Implementation\n```python\ndef solution():\n    pass\n```",
            plan=f"## Agent Plan\n\n**Objective:** {prompt}\n\n### Steps:\n1. Parse requirements from prompt\n2. Design architecture\n3. Generate implementation\n4. Create tests\n5. Verify correctness\n\n### Files to modify:\n- `src/main.py`\n- `tests/test_main.py`",
            patch="--- a/src/main.py\n+++ b/src/main.py\n@@ -0,0 +1,20 @@\n+def agent_generated():\n+    pass\n+",
            diff="diff --git a/src/main.py b/src/main.py\nnew file mode 100644\n...",
            files_changed=["src/main.py", "tests/test_main.py"],
            risks=["Stub response — review before adopting"],
            metadata={"agent_steps": 5, "estimated_effort": "medium"},
        )],
        warnings=["Stub mode: no real API calls."],
    )


# ── Public API ───────────────────────────────────────────────────────────


def arena_request(ws: Path, req: ArenaRequest) -> ArenaResponse:
    """Process an Arena request in the specified mode.

    In stub mode (default), generates mock responses.
    Set ARC_ALLOW_LIVE_ARENA=true + configure provider API keys for real calls.
    """
    mode = req.mode
    prompt = req.prompt
    model = req.model
    model_tags = req.model_tags

    live = os.environ.get("ARC_ALLOW_LIVE_ARENA", "").lower() in {"true", "1"}

    if mode == ArenaMode.BATTLE:
        if live:
            # TODO: Implement live battle via provider API
            pass
        return _stub_battle(ws, prompt, model_tags)

    if mode == ArenaMode.DIRECT:
        if live:
            # TODO: Implement live direct via provider API
            pass
        return _stub_direct(ws, prompt, model)

    if mode == ArenaMode.CODE:
        if live:
            # TODO: Implement live code generation
            pass
        return _stub_code(ws, prompt, model)

    if mode == ArenaMode.AGENT_ARENA_PREVIEW:
        if live:
            # TODO: Implement live agent preview
            pass
        return _stub_agent_preview(ws, prompt, model)

    return ArenaResponse(
        mode=mode, warnings=[f"Unknown mode: {mode}"],
    )


def store_arena_run(store: JsonlTraceStore, response: ArenaResponse, req: ArenaRequest) -> RunRecord:
    """Store an Arena response as an ARC run record for traceability."""
    run = RunRecord(
        id=response.run_id,
        workflow_id=f"arena-{req.mode.value}",
        runtime="lmarena",
        status=RunStatus.COMPLETED,
        started_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        ended_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        events=[
            RunEvent(
                type="LMARENA_REQUESTED",
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                run_id=response.run_id,
                sequence=0,
                data={
                    "mode": req.mode.value,
                    "prompt": req.prompt,
                    "model": req.model,
                    "model_tags": req.model_tags,
                    "privacy": req.privacy.value,
                },
            ),
            RunEvent(
                type="LMARENA_CANDIDATES_RECEIVED",
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                run_id=response.run_id,
                sequence=1,
                data={
                    "candidate_count": len(response.candidates),
                    "candidate_models": [c.model for c in response.candidates],
                    "recommended": response.recommended,
                },
            ),
        ],
        metadata={
            "mode": req.mode.value,
            "models": [c.model for c in response.candidates],
            "privacy": req.privacy.value,
            "profile_id": req.profile_id,
            "allow_paid_calls": req.allow_paid_calls,
            "warnings": response.warnings,
        },
    )
    store.save(run)
    return run


def adopt_candidate(ws: Path, req: ArenaAdoptRequest) -> ArenaAdoptResult:
    """Adopt a candidate's code patch into the workspace."""
    # In stub mode, just return success
    return ArenaAdoptResult(
        applied=True,
        file_changed=req.target_file or "src/generated.py",
        patch_lines=5,
        message="Patch adopted (stub mode). In production, this would apply the diff to the workspace.",
    )
