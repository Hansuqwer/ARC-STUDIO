from __future__ import annotations

import os
import platform

import pytest

import agent_runtime_cockpit.isolation.vz_provider as vz_provider
from agent_runtime_cockpit.isolation.vz_provider import VZNoNetworkProof


def test_vz_preflight_reports_status(monkeypatch):
    monkeypatch.delenv("ARC_VZ_PROOF", raising=False)
    status = VZNoNetworkProof().preflight()
    assert status["provider"] == "vz_no_nic"
    assert status["network_devices_configured"] == 0
    assert status["networkDevices"] == []
    assert status["status"] in {"ready", "blocked", "unavailable"}
    assert status["strict_no_network_proof"] == "not_proven"


def test_vz_preflight_requires_executable_runner_even_with_pyobjc(tmp_path, monkeypatch):
    kernel = tmp_path / "vmlinuz"
    initrd = tmp_path / "initrd.img"
    runner = tmp_path / "arc-vz-runner"
    kernel.write_bytes(b"kernel")
    initrd.write_bytes(b"initrd")
    runner.write_text("#!/bin/sh\n", encoding="utf-8")
    runner.chmod(0o644)
    monkeypatch.setenv("ARC_VZ_PROOF", "1")
    monkeypatch.setattr(vz_provider.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(vz_provider.platform, "mac_ver", lambda: ("14.0", ("", "", ""), ""))
    monkeypatch.setattr(vz_provider, "_pyobjc_available", lambda: True)

    status = VZNoNetworkProof(
        kernel_path=kernel,
        initrd_path=initrd,
        runner_path=runner,
    ).preflight()

    assert status["status"] == "blocked"
    assert status["runner_exists"] is True
    assert status["runner_executable"] is False
    assert status["pyobjc_runner_implemented"] is False
    assert "ARC_VZ_RUNNER missing/not executable" in status["blockers"]


def test_vz_preflight_ready_to_attempt_is_not_proof(tmp_path, monkeypatch):
    kernel = tmp_path / "vmlinuz"
    initrd = tmp_path / "initrd.img"
    runner = tmp_path / "arc-vz-runner"
    kernel.write_bytes(b"kernel")
    initrd.write_bytes(b"initrd")
    runner.write_text("#!/bin/sh\n", encoding="utf-8")
    runner.chmod(0o755)
    monkeypatch.setenv("ARC_VZ_PROOF", "1")
    monkeypatch.setattr(vz_provider.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(vz_provider.platform, "mac_ver", lambda: ("14.0", ("", "", ""), ""))
    monkeypatch.setattr(vz_provider, "_pyobjc_available", lambda: False)

    status = VZNoNetworkProof(
        kernel_path=kernel,
        initrd_path=initrd,
        runner_path=runner,
    ).preflight()

    assert status["status"] == "ready"
    assert status["preflight_ready"] is True
    assert status["proof_status"] == "ready_to_attempt"
    assert status["strict_no_network_proof"] == "not_proven"


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
