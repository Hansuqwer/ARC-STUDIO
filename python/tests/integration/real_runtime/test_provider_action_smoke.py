"""Opt-in live provider-action smoke for one narrow 9router MiniMax action.

Skipped by default. This file must not run in normal CI/offline gates.

Required gates:
- ``ARC_PROVIDER_ACTION_SMOKE=1``: explicit smoke-test approval env.
- ``ARC_ALLOW_LIVE_PROVIDER_TESTS=true``: existing live-provider gate.
- ``NINEROUTER_API_KEY``: env reference only; never logged or stored here.
- CLI flags below: ``--live``, ``--allow-paid-calls``, exact confirmation.

This is only a narrow ``arc providers action`` smoke path. It is not provider-backed
adoption, not SwarmGraph/provider wiring, and not a broad real-provider claim.
"""

from __future__ import annotations

import json
import os
import subprocess

import pytest

pytestmark = pytest.mark.real_runtime


PROVIDER = "9router"
MODEL = "nvidia/minimaxai/minimax-m2.7"
CONFIRMATION = f"RUN_PROVIDER_ACTION:{PROVIDER}:{MODEL}"


def _requires_provider_action_smoke() -> None:
    if os.environ.get("ARC_PROVIDER_ACTION_SMOKE") != "1":
        pytest.skip("set ARC_PROVIDER_ACTION_SMOKE=1 for one narrow provider-action smoke")
    if os.environ.get("ARC_ALLOW_LIVE_PROVIDER_TESTS") != "true":
        pytest.skip("set ARC_ALLOW_LIVE_PROVIDER_TESTS=true to permit live provider tests")
    if not os.environ.get("NINEROUTER_API_KEY"):
        pytest.skip("set NINEROUTER_API_KEY env ref; raw key is never logged/stored")


def test_9router_minimax_provider_action_smoke_requires_explicit_gates(tmp_path) -> None:
    """Manual-only live smoke: one paid-gated provider action, no adoption wiring."""
    _requires_provider_action_smoke()
    routing_path = tmp_path / "provider-routing.json"
    routing_path.write_text(
        json.dumps(
            {
                "mode": "manual",
                "default_provider": "9router",
                "default_model": MODEL,
                "dry_run": False,
                "allow_paid_calls": True,
                "max_retries": 1,
                "timeout_ms": 900000,
            }
        ),
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "ARC_PROVIDER_ROUTING": str(routing_path),
        "ARC_PROVIDER_QUOTA": str(tmp_path / "provider-quota.json"),
    }

    result = subprocess.run(
        [
            "arc",
            "providers",
            "action",
            "--provider",
            PROVIDER,
            "--model",
            MODEL,
            "--prompt",
            "Return exactly: ARC_PROVIDER_ACTION_SMOKE_OK",
            "--live",
            "--allow-paid-calls",
            "--confirm",
            CONFIRMATION,
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=950,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    data = payload["data"]
    assert data["real_provider_call"] is True
    assert data["network_call_attempted"] is True
    assert data["provider"] == PROVIDER
    assert data["model"] == MODEL
    assert data["metadata"]["choice_count"] >= 1
