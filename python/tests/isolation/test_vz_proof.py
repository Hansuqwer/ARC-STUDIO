from __future__ import annotations

import os
import platform

import pytest

from agent_runtime_cockpit.isolation.vz_provider import VZNoNetworkProof


def test_vz_preflight_reports_status(monkeypatch):
    monkeypatch.delenv("ARC_VZ_PROOF", raising=False)
    status = VZNoNetworkProof().preflight()
    assert status["provider"] == "vz_no_nic"
    assert status["network_devices_configured"] == 0
    assert status["networkDevices"] == []
    assert status["status"] in {"ready", "blocked", "unavailable"}


@pytest.mark.skipif(
    os.environ.get("ARC_VZ_PROOF") != "1" or platform.system() != "Darwin",
    reason="requires ARC_VZ_PROOF=1 on macOS with VZ runner/kernel/initrd",
)
@pytest.mark.asyncio
async def test_vz_no_nic_boot_and_proof(tmp_path):
    proof = VZNoNetworkProof()
    status = proof.preflight()
    if status["status"] != "ready":
        pytest.skip(str(status["blockers"]))
    result = await proof.run_proof(tmp_path, ["ip", "link"])
    assert result.no_nic_configured is True
    assert result.network_devices_configured == 0
    assert result.proof == "proven"
