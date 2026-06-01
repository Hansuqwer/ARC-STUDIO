from __future__ import annotations

import os
import platform
import hashlib
import io
import json
import subprocess
import signal
import threading
from types import SimpleNamespace

import pytest

import agent_runtime_cockpit.isolation.vz_provider as vz_provider
from agent_runtime_cockpit.isolation.vz_provider import (
    VZNoNetworkProof,
    VZPublicExecutionRunner,
    generate_vz_exec_init_artifacts,
    generate_vz_proof_artifacts,
    parse_vz_guest_command_result,
    parse_vz_guest_proof,
    validate_vz_exec_init_manifest,
    validate_vz_artifact_manifest,
    vz_public_exec_gates,
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


def _with_command_hash(output: str, command: list[str]) -> str:
    digest = hashlib.sha256(
        json.dumps(command, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return output + f"\nARC_VZ_RESULT command_sha256={digest}"


def _valid_public_manifest(tmp_path):
    kernel = tmp_path / "kernel"
    initrd = tmp_path / "initrd.gz"
    output = tmp_path / "artifacts"
    kernel.write_bytes(b"kernel")
    initrd.write_bytes(b"initrd")
    report = generate_vz_proof_artifacts(output, kernel_path=kernel, initrd_path=initrd)
    runner = output / "arc-vz-runner"
    runner.write_text("#!/bin/sh\n", encoding="utf-8")
    runner.chmod(0o755)
    runner_sha = hashlib.sha256(runner.read_bytes()).hexdigest()
    manifest = report.manifest.model_copy(
        update={
            "runner_path": str(runner),
            "runner_sha256": runner_sha,
            "runner_built": True,
            "runner_signed": True,
            "blockers": [],
            "build_status": "runner_inputs_pinned",
        }
    )
    manifest_path = output / "vz-artifacts-manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return manifest_path


def _host_vz_public_ready() -> bool:
    return (
        os.environ.get("ARC_MICROVM_EXEC_ENABLED") == "1"
        and os.environ.get("ARC_MICROVM_INTEGRATION") == "1"
        and os.environ.get("ARC_VZ_REAL_EXEC") == "1"
        and bool(os.environ.get("ARC_VZ_ARTIFACT_MANIFEST"))
        and platform.system() == "Darwin"
    )


def _env_argv(name: str, default: list[str] | None = None) -> list[str]:
    value = os.environ.get(name)
    if not value:
        if default is None:
            pytest.skip(f"{name} required")
        return default
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        pytest.skip(f"{name} must be a JSON string array")
    return parsed


class _FakePopen:
    def __init__(self, stdout: str, stderr: str = "", returncode: int = 0, timeout: bool = False):
        self.stdout = io.BytesIO(stdout.encode("utf-8"))
        self.stderr = io.BytesIO(stderr.encode("utf-8"))
        self.returncode = None
        self.pid = 12345
        self._final_returncode = returncode
        self._timeout = timeout
        self.killed = False

    def wait(self, timeout=None):
        if self._timeout and not self.killed:
            raise subprocess.TimeoutExpired(["arc-vz-runner"], timeout)
        self.returncode = self._final_returncode
        return self.returncode

    def poll(self):
        return self.returncode


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


def test_vz_artifact_generator_writes_manifest_without_boot(tmp_path, monkeypatch):
    monkeypatch.delenv("ARC_VZ_KERNEL", raising=False)
    monkeypatch.delenv("ARC_VZ_INITRD", raising=False)

    report = generate_vz_proof_artifacts(tmp_path)

    assert report.runner_built is False
    assert report.runner_signed is False
    assert "--build-runner not set" in "; ".join(report.blockers)
    assert "ARC_VZ_KERNEL missing/not provided" in report.blockers
    assert "ARC_VZ_INITRD missing/not provided" in report.blockers
    assert (tmp_path / "arc-vz-runner.swift").exists()
    assert (tmp_path / "arc-vz-runner.entitlements").exists()
    manifest = validate_vz_artifact_manifest(tmp_path / "vz-artifacts-manifest.json")
    assert manifest.artifact == "arc-vz-proof"
    assert manifest.public_execution_enabled is False
    assert manifest.proof_only is True
    assert manifest.no_downloads is True
    assert manifest.network_devices_configured == 0
    assert manifest.networkDevices == []
    assert "symlink_escape_blocked" in manifest.markers


def test_vz_artifact_generator_copies_kernel_initrd_and_hashes(tmp_path):
    kernel = tmp_path / "kernel"
    initrd = tmp_path / "initrd.gz"
    output = tmp_path / "artifacts"
    kernel.write_bytes(b"kernel")
    initrd.write_bytes(b"initrd")

    report = generate_vz_proof_artifacts(output, kernel_path=kernel, initrd_path=initrd)
    manifest = validate_vz_artifact_manifest(output / "vz-artifacts-manifest.json")

    assert report.kernel_path == str(output / "arc-vz-kernel")
    assert report.initrd_path == str(output / "arc-vz-initrd.gz")
    assert manifest.kernel_sha256
    assert manifest.initrd_sha256
    assert not report.runner_built


def test_vz_artifact_validator_rejects_network_device_source(tmp_path):
    report = generate_vz_proof_artifacts(tmp_path)
    source = tmp_path / "arc-vz-runner.swift"
    source.write_text(
        source.read_text(encoding="utf-8") + "\nlet _ = VZVirtioNetworkDeviceConfiguration()\n",
        encoding="utf-8",
    )
    manifest = report.manifest.model_copy(
        update={"source_sha256": __import__("hashlib").sha256(source.read_bytes()).hexdigest()}
    )
    manifest_path = tmp_path / "vz-artifacts-manifest.json"
    manifest_path.write_text(manifest.model_dump_json(), encoding="utf-8")

    with pytest.raises(ValueError, match="network device type"):
        validate_vz_artifact_manifest(manifest_path)


def test_vz_artifact_build_runner_failure_is_blocker(tmp_path, monkeypatch):
    kernel = tmp_path / "kernel"
    initrd = tmp_path / "initrd.gz"
    output = tmp_path / "artifacts"
    kernel.write_bytes(b"kernel")
    initrd.write_bytes(b"initrd")
    monkeypatch.setattr(vz_provider.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(vz_provider.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="compile failed")

    monkeypatch.setattr(vz_provider.subprocess, "run", fake_run)

    report = generate_vz_proof_artifacts(
        output, kernel_path=kernel, initrd_path=initrd, build_runner=True
    )

    assert report.runner_built is False
    assert any("swiftc failed" in blocker for blocker in report.blockers)


def test_vz_exec_init_artifacts_are_reviewable_and_no_download(tmp_path):
    report = generate_vz_exec_init_artifacts(tmp_path)
    manifest = validate_vz_exec_init_manifest(tmp_path / "vz-exec-init-manifest.json")
    init_text = (tmp_path / "arc-vz-exec-init.sh").read_text(encoding="utf-8")

    assert report.blockers == []
    assert manifest.no_downloads is True
    assert manifest.shell_string_execution is False
    assert manifest.python_runtime_included is False
    assert manifest.packed_initrd is False
    assert manifest.initrd_path is None
    assert "ARC_VZ_COMMAND_ARGV_B64CSV" in init_text
    assert "ARC_VZ_RESULT command_sha256" in init_text
    assert '"$@" >/tmp/arc-vz-cmd.out' in init_text
    assert "sh -c" not in init_text
    assert "requested argv binary/runtime present inside the guest" in manifest.guest_requirements


def test_vz_exec_init_pack_initrd_uses_local_busybox_and_cpio(tmp_path, monkeypatch):
    busybox = tmp_path / "busybox"
    busybox.write_bytes(b"busybox")
    busybox.chmod(0o755)
    cpio = tmp_path / "cpio"
    cpio.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(
        vz_provider.shutil, "which", lambda name: str(cpio) if name == "cpio" else None
    )

    def fake_run(*args, **kwargs):
        assert kwargs["cwd"] == tmp_path / "arc-vz-exec-initrd-root"
        assert b"init" in kwargs["input"]
        assert b"usr/bin/busybox" in kwargs["input"]
        return SimpleNamespace(returncode=0, stdout=b"newc-archive", stderr=b"")

    monkeypatch.setattr(vz_provider.subprocess, "run", fake_run)

    report = generate_vz_exec_init_artifacts(tmp_path, pack_initrd=True, busybox_path=busybox)
    manifest = validate_vz_exec_init_manifest(tmp_path / "vz-exec-init-manifest.json")

    assert report.packed_initrd is True
    assert report.blockers == []
    assert manifest.packed_initrd is True
    assert manifest.initrd_path == str(tmp_path / "arc-vz-exec-initrd.gz")
    assert manifest.busybox_sha256 == hashlib.sha256(busybox.read_bytes()).hexdigest()
    assert manifest.busybox_static is True
    assert (tmp_path / "arc-vz-exec-initrd-root" / "init").exists()
    assert (tmp_path / "arc-vz-exec-initrd-root" / "usr" / "bin" / "pwd").is_symlink()
    assert (tmp_path / "arc-vz-exec-initrd-root" / "usr" / "bin" / "sleep").is_symlink()


def test_vz_exec_init_pack_initrd_missing_busybox_is_blocker(tmp_path, monkeypatch):
    monkeypatch.setattr(vz_provider.shutil, "which", lambda name: "/usr/bin/cpio")

    report = generate_vz_exec_init_artifacts(tmp_path, pack_initrd=True)
    manifest = validate_vz_exec_init_manifest(tmp_path / "vz-exec-init-manifest.json")

    assert report.packed_initrd is False
    assert "ARC_VZ_BUSYBOX missing/not provided" in report.blockers
    assert manifest.packed_initrd is False
    assert manifest.initrd_path is None


def test_vz_exec_init_pack_initrd_rejects_dynamic_busybox(tmp_path, monkeypatch):
    busybox = tmp_path / "busybox"
    busybox.write_bytes(b"ELF.../lib/ld-linux-aarch64.so.1")
    busybox.chmod(0o755)
    monkeypatch.setattr(vz_provider.shutil, "which", lambda name: "/usr/bin/cpio")

    report = generate_vz_exec_init_artifacts(tmp_path, pack_initrd=True, busybox_path=busybox)
    manifest = validate_vz_exec_init_manifest(tmp_path / "vz-exec-init-manifest.json")

    assert report.packed_initrd is False
    assert "ARC_VZ_BUSYBOX must be a static Linux BusyBox binary" in report.blockers
    assert manifest.busybox_static is False
    assert manifest.initrd_path is None


def test_vz_exec_init_validator_rejects_shell_string_execution(tmp_path):
    report = generate_vz_exec_init_artifacts(tmp_path)
    init_path = tmp_path / "arc-vz-exec-init.sh"
    init_path.write_text(init_path.read_text(encoding="utf-8") + "\nsh -c 'echo unsafe'\n")
    manifest = report.manifest.model_copy(
        update={"init_sha256": hashlib.sha256(init_path.read_bytes()).hexdigest()}
    )
    manifest_path = tmp_path / "vz-exec-init-manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="forbidden shell execution"):
        validate_vz_exec_init_manifest(manifest_path)


def test_vz_public_exec_gates_require_all_env(tmp_path, monkeypatch):
    manifest = _valid_public_manifest(tmp_path)
    monkeypatch.setattr(vz_provider.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(vz_provider, "_codesign_verify", lambda _path: True)

    gates = vz_public_exec_gates(manifest)

    assert gates["ready"] is False
    assert "ARC_MICROVM_EXEC_ENABLED=1 required" in gates["blockers"]


def test_vz_public_exec_gates_reject_manifest_hash_mismatch(tmp_path, monkeypatch):
    manifest = _valid_public_manifest(tmp_path)
    (manifest.parent / "arc-vz-kernel").write_bytes(b"tampered")
    monkeypatch.setenv("ARC_MICROVM_EXEC_ENABLED", "1")
    monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
    monkeypatch.setenv("ARC_VZ_REAL_EXEC", "1")
    monkeypatch.setenv("ARC_VZ_ARTIFACT_MANIFEST", str(manifest))
    monkeypatch.setattr(vz_provider.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(vz_provider, "_codesign_verify", lambda _path: True)

    gates = vz_public_exec_gates()

    assert gates["ready"] is False
    assert any("sha256 mismatch" in blocker for blocker in gates["blockers"])


@pytest.mark.asyncio
async def test_vz_public_runner_allows_valid_fake_run(tmp_path, monkeypatch):
    manifest = _valid_public_manifest(tmp_path)
    monkeypatch.setenv("ARC_MICROVM_EXEC_ENABLED", "1")
    monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
    monkeypatch.setenv("ARC_VZ_REAL_EXEC", "1")
    monkeypatch.setenv("ARC_VZ_ARTIFACT_MANIFEST", str(manifest))
    monkeypatch.setattr(vz_provider.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(vz_provider, "_codesign_verify", lambda _path: True)
    command = ["python", "-c", "print('hello')"]
    seen: dict[str, object] = {}

    def fake_popen(args, *_args, **_kwargs):
        seen["args"] = args
        return _FakePopen(
            _with_command_hash(
                _successful_guest_output().replace("arc-vz-proof-ok", "hello-vz"), command
            )
        )

    monkeypatch.setattr(
        vz_provider.subprocess,
        "Popen",
        fake_popen,
    )

    result = VZPublicExecutionRunner(workspace_root=tmp_path).run(command)

    assert result.exit_code == 0
    assert result.stdout == "hello-vz"
    assert result.metadata["microvm_provider"] == "vz"
    assert result.metadata["network_proof_passed"] is True
    assert result.metadata["workspace_proof_passed"] is True
    assert result.metadata["teardown_ok"] is True
    assert "--command-sha256" in seen["args"]


def test_vz_public_runner_proof_failure_fails_result(tmp_path, monkeypatch):
    manifest = _valid_public_manifest(tmp_path)
    monkeypatch.setenv("ARC_MICROVM_EXEC_ENABLED", "1")
    monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
    monkeypatch.setenv("ARC_VZ_REAL_EXEC", "1")
    monkeypatch.setenv("ARC_VZ_ARTIFACT_MANIFEST", str(manifest))
    monkeypatch.setattr(vz_provider.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(vz_provider, "_codesign_verify", lambda _path: True)
    command = ["pwd"]
    monkeypatch.setattr(
        vz_provider.subprocess,
        "Popen",
        lambda *args, **kwargs: _FakePopen(
            _with_command_hash(
                _successful_guest_output().replace(
                    "ARC_VZ_PROOF no-default-route=1", "ARC_VZ_PROOF no-default-route=0"
                ),
                command,
            )
        ),
    )

    result = VZPublicExecutionRunner(workspace_root=tmp_path).run(command)

    assert result.exit_code == -1
    assert "network proof failed" in result.stderr
    assert result.metadata["network_proof_passed"] is False


def test_vz_public_runner_teardown_failure_fails_result(tmp_path, monkeypatch):
    manifest = _valid_public_manifest(tmp_path)
    monkeypatch.setenv("ARC_MICROVM_EXEC_ENABLED", "1")
    monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
    monkeypatch.setenv("ARC_VZ_REAL_EXEC", "1")
    monkeypatch.setenv("ARC_VZ_ARTIFACT_MANIFEST", str(manifest))
    monkeypatch.setattr(vz_provider.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(vz_provider, "_codesign_verify", lambda _path: True)
    command = ["pwd"]
    monkeypatch.setattr(
        vz_provider.subprocess,
        "Popen",
        lambda *args, **kwargs: _FakePopen(
            _with_command_hash(
                _successful_guest_output().replace("ARC_VZ_TEARDOWN_OK=1", "ARC_VZ_TEARDOWN_OK=0"),
                command,
            )
        ),
    )

    result = VZPublicExecutionRunner(workspace_root=tmp_path).run(command)

    assert result.exit_code == -1
    assert "teardown did not report ok" in result.stderr
    assert result.metadata["teardown_ok"] is False


def test_vz_public_runner_timeout_caps_output_and_marks_failure(tmp_path, monkeypatch):
    manifest = _valid_public_manifest(tmp_path)
    fake = _FakePopen("x" * 1000, timeout=True)
    monkeypatch.setenv("ARC_MICROVM_EXEC_ENABLED", "1")
    monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
    monkeypatch.setenv("ARC_VZ_REAL_EXEC", "1")
    monkeypatch.setenv("ARC_VZ_ARTIFACT_MANIFEST", str(manifest))
    monkeypatch.setattr(vz_provider.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(vz_provider, "_codesign_verify", lambda _path: True)
    monkeypatch.setattr(vz_provider.subprocess, "Popen", lambda *args, **kwargs: fake)
    monkeypatch.setattr(
        vz_provider.os, "killpg", lambda *args, **kwargs: setattr(fake, "killed", True)
    )

    result = VZPublicExecutionRunner(workspace_root=tmp_path, max_bytes=32).run(
        ["pwd"], timeout_seconds=1
    )

    assert result.exit_code == -1
    assert result.killed is True
    assert result.kill_reason == "timeout"
    assert result.stdout_truncated is True
    assert result.metadata["teardown_ok"] is False


def test_vz_public_runner_missing_command_hash_fails_result(tmp_path, monkeypatch):
    manifest = _valid_public_manifest(tmp_path)
    monkeypatch.setenv("ARC_MICROVM_EXEC_ENABLED", "1")
    monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
    monkeypatch.setenv("ARC_VZ_REAL_EXEC", "1")
    monkeypatch.setenv("ARC_VZ_ARTIFACT_MANIFEST", str(manifest))
    monkeypatch.setattr(vz_provider.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(vz_provider, "_codesign_verify", lambda _path: True)
    monkeypatch.setattr(
        vz_provider.subprocess,
        "Popen",
        lambda *args, **kwargs: _FakePopen(_successful_guest_output()),
    )

    result = VZPublicExecutionRunner(workspace_root=tmp_path).run(["pwd"])

    assert result.exit_code == -1
    assert "guest command result did not prove requested argv hash" in result.stderr


def test_vz_public_runner_interrupt_kills_group_and_fails_result(tmp_path, monkeypatch):
    manifest = _valid_public_manifest(tmp_path)
    fake = _FakePopen(_successful_guest_output())

    def interrupt_once(timeout=None):
        if not fake.killed:
            raise KeyboardInterrupt
        fake.returncode = -2
        return fake.returncode

    fake.wait = interrupt_once
    monkeypatch.setenv("ARC_MICROVM_EXEC_ENABLED", "1")
    monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
    monkeypatch.setenv("ARC_VZ_REAL_EXEC", "1")
    monkeypatch.setenv("ARC_VZ_ARTIFACT_MANIFEST", str(manifest))
    monkeypatch.setattr(vz_provider.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(vz_provider, "_codesign_verify", lambda _path: True)
    monkeypatch.setattr(vz_provider.subprocess, "Popen", lambda *args, **kwargs: fake)
    monkeypatch.setattr(
        vz_provider.os, "killpg", lambda *args, **kwargs: setattr(fake, "killed", True)
    )

    result = VZPublicExecutionRunner(workspace_root=tmp_path).run(["pwd"])

    assert result.exit_code == -1
    assert result.killed is True
    assert result.kill_reason == "signal"
    assert "interrupted" in "; ".join(result.metadata["lifecycle_errors"])


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


@pytest.mark.skipif(
    not _host_vz_public_ready(),
    reason="requires explicit macOS VZ public exec gates and local artifact manifest",
)
def test_vz_public_real_host_pwd(tmp_path):
    result = VZPublicExecutionRunner(workspace_root=tmp_path).run(["pwd"])

    assert result.provider == "microvm"
    assert result.exit_code == 0
    assert result.stdout == "/workspace"
    assert result.metadata["network_proof_passed"] is True
    assert result.metadata["workspace_proof_passed"] is True
    assert result.metadata["teardown_ok"] is True


@pytest.mark.skipif(
    not _host_vz_public_ready() or os.environ.get("ARC_VZ_REAL_FAILURE_TESTS") != "1",
    reason="requires explicit macOS VZ public exec gates and ARC_VZ_REAL_FAILURE_TESTS=1",
)
def test_vz_public_real_host_command_failure(tmp_path):
    command = _env_argv("ARC_VZ_REAL_FAILURE_ARGV", ["/definitely-missing-arc-command"])

    result = VZPublicExecutionRunner(workspace_root=tmp_path).run(command, timeout_seconds=45)

    assert result.provider == "microvm"
    assert result.exit_code == -1
    assert result.metadata["network_proof_passed"] is True
    assert result.metadata["workspace_proof_passed"] is True
    assert result.metadata["teardown_ok"] is True
    assert result.metadata["guest_exit_code"] not in (None, 0)
    assert result.metadata["command_result_seen"] is True


@pytest.mark.skipif(
    not _host_vz_public_ready() or os.environ.get("ARC_VZ_REAL_FAILURE_TESTS") != "1",
    reason="requires explicit macOS VZ public exec gates and ARC_VZ_REAL_FAILURE_TESTS=1",
)
def test_vz_public_real_host_timeout(tmp_path):
    command = _env_argv("ARC_VZ_REAL_TIMEOUT_ARGV")

    result = VZPublicExecutionRunner(workspace_root=tmp_path).run(command, timeout_seconds=1)

    assert result.provider == "microvm"
    assert result.exit_code == -1
    assert result.killed is True
    assert result.kill_reason == "timeout"
    assert any("timed out" in item for item in result.metadata["lifecycle_errors"])


@pytest.mark.skipif(
    not _host_vz_public_ready() or os.environ.get("ARC_VZ_REAL_FAILURE_TESTS") != "1",
    reason="requires explicit macOS VZ public exec gates and ARC_VZ_REAL_FAILURE_TESTS=1",
)
def test_vz_public_real_host_sigint(tmp_path):
    command = _env_argv("ARC_VZ_REAL_SIGINT_ARGV")
    runner = VZPublicExecutionRunner(workspace_root=tmp_path)
    done = threading.Event()

    def interrupt() -> None:
        if not done.wait(timeout=3):
            os.kill(os.getpid(), signal.SIGINT)

    timer = threading.Thread(target=interrupt)
    timer.start()
    try:
        result = runner.run(command, timeout_seconds=45)
    finally:
        done.set()
        timer.join(timeout=5)

    assert result.provider == "microvm"
    assert result.exit_code == -1
    assert result.killed is True
    assert result.kill_reason == "signal"
    assert any("interrupted" in item for item in result.metadata["lifecycle_errors"])
