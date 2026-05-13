"""Core Arena service — handles battle, direct, code, and agent-arena-preview modes."""
from __future__ import annotations

import json
import logging
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

log = logging.getLogger(__name__)

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


# ── Live provider configuration (model → provider mapping) ──────────────

_LIVE_MODEL_MAP: dict[str, dict[str, str]] = {
    # OpenAI models
    "gpt-4o-mini-2024-07-18": {
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
    },
    "gpt-4o-2024-08-06": {
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
    },
    # Anthropic models
    "claude-sonnet-4-20250514": {
        "provider": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    # Mistral models
    "codestral-2405": {
        "provider": "mistral",
        "base_url": "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
    },
    # DeepSeek models
    "deepseek-coder-v2": {
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    # Llama models via OpenRouter
    "llama-3.1-70b": {
        "provider": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
    },
    "llama-3.1-405b": {
        "provider": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
    },
}


def _redact_live(text: str) -> str:
    """Redact sensitive content from log messages."""
    redacted = text.replace("sk-", "sk-REDACTED")
    for key_word in ["api_key", "apikey", "API_KEY", "Authorization", "Bearer"]:
        redacted = redacted.replace(key_word, "REDACTED")
    return redacted


def _live_provider_chat(
    model_id: str,
    prompt: str,
    system_prompt: str = "",
    allow_paid_calls: bool = False,
) -> str:
    """Make a live provider API call for a single model.

    Returns the model response text.
    Raises RuntimeError on failure.
    """
    if model_id not in _LIVE_MODEL_MAP:
        raise RuntimeError(f"No live provider configuration for model '{model_id}'")

    config = _LIVE_MODEL_MAP[model_id]
    api_key = os.environ.get(config["api_key_env"])
    if not api_key:
        raise RuntimeError(
            f"Live arena requires {config['api_key_env']} environment variable "
            f"for model '{model_id}' ({config['provider']})"
        )

    provider = config["provider"]
    base_url = config["base_url"]

    # Anthropic uses a different API format
    if provider == "anthropic":
        return _live_anthropic_chat(model_id, prompt, system_prompt, api_key, base_url)

    # OpenAI-compatible API
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        raise RuntimeError(f"Live provider call failed for '{model_id}': {_redact_live(str(exc))}")


def _live_anthropic_chat(
    model_id: str,
    prompt: str,
    system_prompt: str,
    api_key: str,
    base_url: str,
) -> str:
    """Make a live Anthropic API call."""
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        kwargs: dict[str, Any] = {
            "model": model_id,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = client.messages.create(**kwargs)
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text
        return text
    except Exception as exc:
        raise RuntimeError(f"Live Anthropic call failed for '{model_id}': {_redact_live(str(exc))}")


def _live_response(ws: Path, req: ArenaRequest) -> ArenaResponse:
    """Generate a live Arena response by calling actual provider APIs.

    Gated behind ARC_ALLOW_LIVE_ARENA=true.
    """
    prompt = req.prompt
    model_id = req.model
    allow_paid_calls = req.allow_paid_calls

    if not allow_paid_calls:
        return ArenaResponse(
            run_id=f"arena-{uuid.uuid4().hex[:12]}",
            mode=req.mode,
            warnings=["Live arena blocked: allow_paid_calls must be true."],
        )

    run_id = f"arena-{uuid.uuid4().hex[:12]}"
    warnings: list[str] = []
    candidates: list[ArenaCandidate] = []
    system_prompt = f"Context workspace: {ws}\n\n"

    if req.mode == ArenaMode.BATTLE:
        # For battle, get all supported models (up to 2)
        battle_models = [
            m for m in list_models()
            if m.id in _LIVE_MODEL_MAP and m.supports_battle
        ][:2]
        if not battle_models:
            warnings.append("No live-capable models for battle mode; falling back to stub.")
            return _stub_battle(ws, prompt, req.model_tags)
        for m in battle_models:
            try:
                text = _live_provider_chat(m.id, prompt, system_prompt, allow_paid_calls)
                candidates.append(ArenaCandidate(
                    id=f"{run_id}-{m.id.split('-')[0]}",
                    model=m.id,
                    text=text,
                ))
            except RuntimeError as exc:
                warnings.append(str(exc))
        if not candidates:
            warnings.append("All live battle calls failed; falling back to stub.")
            return _stub_battle(ws, prompt, req.model_tags)

    elif req.mode == ArenaMode.DIRECT:
        try:
            text = _live_provider_chat(model_id, prompt, system_prompt, allow_paid_calls)
            candidates.append(ArenaCandidate(
                id=f"{run_id}-{model_id.split('-')[0]}",
                model=model_id,
                text=text,
            ))
        except RuntimeError as exc:
            warnings.append(str(exc))
            if not candidates:
                warnings.append("Live direct call failed; falling back to stub.")
                return _stub_direct(ws, prompt, model_id)

    elif req.mode == ArenaMode.CODE:
        code_prompt = f"{system_prompt}Generate only code for the following request. Return the complete implementation.\n\n{prompt}"
        try:
            text = _live_provider_chat(model_id, code_prompt, "", allow_paid_calls)
            candidates.append(ArenaCandidate(
                id=f"{run_id}-{model_id.split('-')[0]}",
                model=model_id,
                text=f"Code generated by {model_id}",
                patch=f"--- a/src/generated.py\n+++ b/src/generated.py\n@@ -0,0 +1,{len(text.splitlines())} @@\n+{text.replace(chr(10), chr(10)+'+')}",
                diff=f"diff --git a/src/generated.py b/src/generated.py\nnew file mode 100644\n--- /dev/null\n+++ b/src/generated.py\n@@ -0,0 +1,{len(text.splitlines())} @@\n+{text.replace(chr(10), chr(10)+'+')}",
                files_changed=["src/generated.py"],
            ))
        except RuntimeError as exc:
            warnings.append(str(exc))
            if not candidates:
                warnings.append("Live code call failed; falling back to stub.")
                return _stub_code(ws, prompt, model_id)

    elif req.mode == ArenaMode.AGENT_ARENA_PREVIEW:
        agent_prompt = (
            f"{system_prompt}You are an AI agent. Create a plan and implementation for:\n\n{prompt}\n\n"
            "Return your response as:\n## Plan\n...\n## Implementation\n...\n## Files to modify\n..."
        )
        try:
            text = _live_provider_chat(model_id, agent_prompt, "", allow_paid_calls)
            candidates.append(ArenaCandidate(
                id=f"{run_id}-{model_id.split('-')[0]}",
                model=model_id,
                text=text,
                plan=text,
                files_changed=["src/main.py", "tests/test_main.py"],
                risks=["Review before adopting"],
            ))
        except RuntimeError as exc:
            warnings.append(str(exc))
            if not candidates:
                warnings.append("Live agent preview call failed; falling back to stub.")
                return _stub_agent_preview(ws, prompt, model_id)

    return ArenaResponse(
        run_id=run_id,
        mode=req.mode,
        candidates=candidates,
        recommended=candidates[0].id if candidates else "",
        warnings=warnings,
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
    allow_paid = req.allow_paid_calls

    if live and mode in (ArenaMode.BATTLE, ArenaMode.DIRECT, ArenaMode.CODE, ArenaMode.AGENT_ARENA_PREVIEW):
        try:
            live_resp = _live_response(ws, req)
            if live_resp.candidates:
                return live_resp
        except Exception:
            log.warning("Live arena call failed, falling back to stub", exc_info=True)

    if mode == ArenaMode.BATTLE:
        return _stub_battle(ws, prompt, model_tags)

    if mode == ArenaMode.DIRECT:
        return _stub_direct(ws, prompt, model)

    if mode == ArenaMode.CODE:
        return _stub_code(ws, prompt, model)

    if mode == ArenaMode.AGENT_ARENA_PREVIEW:
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
