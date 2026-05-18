"""Opt-in live provider-action smoke for one narrow 9router/Qwen action.

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

import os
import subprocess

import pytest


pytestmark = pytest.mark.real_runtime


PROVIDER = "9router"
MODEL = "qwen/qwen3-235b-a22b-thinking-2507"
CONFIRMATION = f"RUN_PROVIDER_ACTION:{PROVIDER}:{MODEL}"


def _requires_provider_action_smoke() -> None:
    if os.environ.get("ARC_PROVIDER_ACTION_SMOKE") != "1":
        pytest.skip("set ARC_PROVIDER_ACTION_SMOKE=1 for one narrow provider-action smoke")
    if os.environ.get("ARC_ALLOW_LIVE_PROVIDER_TESTS") != "true":
        pytest.skip("set ARC_ALLOW_LIVE_PROVIDER_TESTS=true to permit live provider tests")
    if not os.environ.get("NINEROUTER_API_KEY"):
        pytest.skip("set NINEROUTER_API_KEY env ref; raw key is never logged/stored")


def test_9router_qwen_provider_action_smoke_requires_explicit_gates(tmp_path) -> None:
    """Manual-only live smoke: one paid-gated provider action, no adoption wiring."""
    _requires_provider_action_smoke()

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
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "ARC_PROVIDER_ACTION_SMOKE_OK" in result.stdout
