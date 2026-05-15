"""Workspace-local HITL pending approval persistence with expiry and single-use tokens."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional
from uuid import uuid4

from .hitl import HitlDecision, HitlPrompt, HitlResponse


DEFAULT_EXPIRY_SECONDS = 3600


def _pending_dir(workspace: Path) -> Path:
    path = workspace / ".arc" / "hitl" / "pending"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _responded_dir(workspace: Path) -> Path:
    path = workspace / ".arc" / "hitl" / "responded"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_prompt(
    workspace: Path,
    prompt: HitlPrompt,
    expiry_seconds: int = DEFAULT_EXPIRY_SECONDS,
) -> Path:
    """Save a HITL prompt with expiry and single-use token."""
    payload = prompt.model_dump()
    payload["_token"] = uuid4().hex
    payload["_expires_at"] = time.time() + expiry_seconds
    payload["_responded"] = False
    path = _pending_dir(workspace) / f"{prompt.hitl_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def list_prompts(workspace: Path, include_expired: bool = False) -> list[HitlPrompt]:
    """List pending HITL prompts, excluding expired ones by default."""
    prompts: list[HitlPrompt] = []
    now = time.time()
    for path in sorted(_pending_dir(workspace).glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("_responded"):
                continue
            expires_at = data.get("_expires_at", 0)
            if not include_expired and now > expires_at:
                continue
            prompt_data = {k: v for k, v in data.items() if not k.startswith("_")}
            prompts.append(HitlPrompt.model_validate(prompt_data))
        except Exception:
            continue
    return prompts


def _load_pending(workspace: Path, hitl_id: str) -> Optional[dict]:
    """Load a pending prompt's raw data, returning None if not found/expired/responded."""
    path = _pending_dir(workspace) / f"{hitl_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if data.get("_responded"):
        return None
    if time.time() > data.get("_expires_at", 0):
        return None
    return data


def respond(
    workspace: Path,
    hitl_id: str,
    decision: HitlDecision,
    token: str,
    notes: str = "",
) -> HitlResponse | None:
    """Respond to a HITL prompt with single-use token validation.

    Returns None if prompt not found, expired, already responded, or token mismatch.
    """
    data = _load_pending(workspace, hitl_id)
    if data is None:
        return None
    stored_token = data.get("_token", "")
    if not token or token != stored_token:
        return None
    prompt_data = {k: v for k, v in data.items() if not k.startswith("_")}
    prompt = HitlPrompt.model_validate(prompt_data)
    data["_responded"] = True
    data["_responded_at"] = time.time()
    data["_decision"] = decision.value
    pending_path = _pending_dir(workspace) / f"{hitl_id}.json"
    responded_path = _responded_dir(workspace) / f"{hitl_id}.json"
    responded_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    pending_path.unlink(missing_ok=True)
    return HitlResponse(hitl_id=hitl_id, run_id=prompt.run_id, decision=decision, notes=notes)


def get_token(workspace: Path, hitl_id: str) -> Optional[str]:
    """Return the single-use token for a pending prompt. None if not found/expired."""
    data = _load_pending(workspace, hitl_id)
    if data is None:
        return None
    return data.get("_token")


def prune_expired(workspace: Path) -> int:
    """Remove expired pending prompts. Returns count pruned."""
    now = time.time()
    pruned = 0
    for path in _pending_dir(workspace).glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("_responded") or now > data.get("_expires_at", 0):
                path.unlink()
                pruned += 1
        except Exception:
            continue
    return pruned
