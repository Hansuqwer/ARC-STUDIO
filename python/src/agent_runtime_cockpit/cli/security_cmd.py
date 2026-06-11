"""Security CLI commands."""

from __future__ import annotations

import json

import typer

from ..protocol.event_envelope import ok
from ..security.prompt_guard import highest_severity, scan, scan_batch
from ._helpers import JSON_FLAG, _out
from ._subapps import security_app


@security_app.command("scan-prompt")
def security_scan_prompt(
    prompt: str = typer.Argument(..., help="Prompt text to scan deterministically"),
    batch_json: str = typer.Option("", "--batch-json", help="JSON array of prompts to scan"),
    as_json: bool = JSON_FLAG,
) -> None:
    """Scan prompt text for deterministic prompt-injection patterns."""
    prompts = [prompt]
    if batch_json:
        parsed = json.loads(batch_json)
        if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
            prompts = parsed
    results = scan_batch(prompts) if len(prompts) > 1 else [scan(prompts[0])]
    payload = {
        "state": "success",
        "count": len(results),
        "highest_severity": highest_severity(results),
        "results": [result.to_dict() for result in results],
    }
    _out(ok(payload), as_json)


__all__ = ["security_app"]
