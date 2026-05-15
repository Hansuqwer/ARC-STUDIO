"""Workspace-local HITL pending approval persistence."""
from __future__ import annotations

import json
from pathlib import Path

from .hitl import HitlDecision, HitlPrompt, HitlResponse


def _pending_dir(workspace: Path) -> Path:
    path = workspace / ".arc" / "hitl" / "pending"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_prompt(workspace: Path, prompt: HitlPrompt) -> Path:
    path = _pending_dir(workspace) / f"{prompt.hitl_id}.json"
    path.write_text(prompt.model_dump_json(indent=2), encoding="utf-8")
    return path


def list_prompts(workspace: Path) -> list[HitlPrompt]:
    prompts: list[HitlPrompt] = []
    for path in sorted(_pending_dir(workspace).glob("*.json")):
        try:
            prompts.append(HitlPrompt.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        except Exception:
            continue
    return prompts


def respond(workspace: Path, hitl_id: str, decision: HitlDecision, notes: str = "") -> HitlResponse | None:
    path = _pending_dir(workspace) / f"{hitl_id}.json"
    if not path.exists():
        return None
    prompt = HitlPrompt.model_validate(json.loads(path.read_text(encoding="utf-8")))
    path.unlink()
    return HitlResponse(hitl_id=hitl_id, run_id=prompt.run_id, decision=decision, notes=notes)
