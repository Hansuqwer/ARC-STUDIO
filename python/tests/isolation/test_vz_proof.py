from __future__ import annotations

import os
import platform
from types import SimpleNamespace

import pytest

import agent_runtime_cockpit.isolation.vz_provider as vz_provider
from agent_runtime_cockpit.isolation.vz_provider import (
    VZNoNetworkProof,
    parse_vz_guest_command_result,
    parse_vz_guest_proof,
)


def _ready_proof(tmp_path, monkeypatch) -> VZNoNetworkProof:
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
    return VZNoNetworkProof(kernel_path=kernel, initrd_path=initrd, runner_path=runner)


def _successful_guest_output() -> str:
    return "\n".join(
        [
            "ARC_VZ_PROOF booted=1",
            "ARC_VZ_PROOF no-guest-ethernet=1",
            "ARC_VZ_PROOF no-default-route=1",
            "ARC_VZ_PROOF wget-available=1",
            "ARC_VZ_PROOF network-failure=1",
            "ARC_VZ_PROOF workspace-mount=1",
            "ARC_VZ_PROOF sentinel-read=1",
            "ARC_VZ_PROOF symlink-escape-blocked=1",
            "ARC_VZ_RESULT exit_code=0",
            "ARC_VZ_RESULT stdout=arc-vz-proof-ok",
            "ARC_VZ_RESULT stderr=",
            "ARC_VZ_TEARDOWN_ATTEMPTED=1",
            "ARC_VZ_TEARDOWN_OK=1",
        ]
    )


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


def test_vz_guest_marker_parsers_success():
    output = _successful_guest_output()

    proof = parse_vz_guest_proof(output)
    result = parse_vz_guest_command_result(output)

    assert proof.marker_seen is True
    assert proof.network_proof_passed is True
    assert proof.workspace_proof_passed is True
    assert result.marker_seen is True
    assert result.exit_code == 0
    assert result.stdout == "arc-vz-proof-ok"


def test_vz_guest_marker_parsers_failure():
    proof = parse_vz_guest_proof(
        "\n".join(
            [
                "ARC_VZ_PROOF booted=1",
                "ARC_VZ_PROOF symlink-escape-blocked=0",
            ]
        )
    )
    result = parse_vz_guest_command_result("ARC_VZ_RESULT exit_code=not-int")

    assert proof.marker_seen is True
    assert proof.network_proof_passed is False
    assert proof.workspace_proof_passed is False
    assert proof.symlink_escape_blocked is False
    assert result.exit_code == -1


@pytest.mark.asyncio
async def test_vz_run_proof_requires_teardown_marker(tmp_path, monkeypatch):
    proof = _ready_proof(tmp_path, monkeypatch)

    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout=_successful_guest_output().replace(
                "ARC_VZ_TEARDOWN_ATTEMPTED=1\nARC_VZ_TEARDOWN_OK=1", ""
            ),
            stderr="",
        )

    monkeypatch.setattr(vz_provider.subprocess, "run", fake_run)

    result = await proof.run_proof(tmp_path, ["ip", "link"])

    assert result.proof == "failed"
    assert result.teardown_attempted is False
    assert "teardown marker missing" in str(result.blocker)


@pytest.mark.asyncio
async def test_vz_run_proof_requires_and_cleans_sentinel_symlink(tmp_path, monkeypatch):
    proof = _ready_proof(tmp_path, monkeypatch)
    seen: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        sentinel = tmp_path / ".arc-vz-sentinel"
        escape = tmp_path / ".arc-vz-escape"
        target = escape.resolve(strict=True)
        seen["target"] = target
        assert sentinel.read_text(encoding="utf-8") == "arc-vz-proof\n"
        assert escape.is_symlink()
        assert not target.is_relative_to(tmp_path.resolve())
        assert target.read_text(encoding="utf-8") == "arc-vz-host-secret\n"
        return SimpleNamespace(returncode=0, stdout=_successful_guest_output(), stderr="")

    monkeypatch.setattr(vz_provider.subprocess, "run", fake_run)

    result = await proof.run_proof(tmp_path, ["ip", "link"])

    assert result.proof == "proven"
    assert not (tmp_path / ".arc-vz-sentinel").exists()
    assert not (tmp_path / ".arc-vz-escape").exists()
    assert not seen["target"].exists()


@pytest.mark.asyncio
async def test_vz_run_proof_refuses_existing_marker(tmp_path, monkeypatch):
    proof = _ready_proof(tmp_path, monkeypatch)
    (tmp_path / ".arc-vz-sentinel").write_text("user data\n", encoding="utf-8")

    result = await proof.run_proof(tmp_path, ["ip", "link"])

    assert result.proof == "not_run"
    assert "refusing to overwrite user files" in str(result.blocker)


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
