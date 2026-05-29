"""MicroVM public-execution truth guard tests.

Truth constraints:
- Default execution remains blocked.
- macOS Lima remains blocked for strict no-network.
- Linux Firecracker execution is allowed only behind all explicit gates.
"""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.isolation.microvm import MicroVMIsolationProvider


class TestMicroVMExecuteGates:
    """execute() is blocked by default and Linux-only when gated."""

    def test_microvm_execute_always_raises(self, tmp_path):
        """execute() raises NotImplementedError without explicit gates."""
        provider = MicroVMIsolationProvider()
        with pytest.raises(NotImplementedError, match="microVM execution blocked|macOS microVM"):
            import asyncio

            asyncio.run(provider.execute(["uname", "-a"], cwd=tmp_path))

    def test_microvm_execute_raises_with_arc_microvm_exec_enabled_set(self, monkeypatch, tmp_path):
        """execute() still raises if only the public exec gate is set."""
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm.platform.system", lambda: "Linux"
        )
        monkeypatch.setenv("ARC_MICROVM_EXEC_ENABLED", "1")
        provider = MicroVMIsolationProvider()
        with pytest.raises(NotImplementedError, match="ARC_MICROVM_INTEGRATION"):
            import asyncio

            asyncio.run(provider.execute(["uname", "-a"], cwd=tmp_path))

    def test_microvm_execute_runs_linux_firecracker_when_all_gates_pass(
        self, monkeypatch, tmp_path
    ):
        """All gates delegate to real Firecracker runner; subprocess call is faked only here."""
        kernel = tmp_path / "vmlinux"
        rootfs = tmp_path / "rootfs.ext4"
        kernel.write_text("kernel", encoding="utf-8")
        rootfs.write_text("rootfs", encoding="utf-8")
        monkeypatch.setenv("ARC_MICROVM_EXEC_ENABLED", "1")
        monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
        monkeypatch.setenv("ARC_FC_REAL_EXEC", "1")
        monkeypatch.setenv("ARC_FIRECRACKER_KERNEL", str(kernel))
        monkeypatch.setenv("ARC_FIRECRACKER_ROOTFS", str(rootfs))
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm.platform.system", lambda: "Linux"
        )
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm._firecracker_binary",
            lambda: "/usr/bin/firecracker",
        )
        original_exists = __import__("pathlib", fromlist=["Path"]).Path.exists
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm.Path.exists",
            lambda self: True if str(self) == "/dev/kvm" else original_exists(self),
        )
        monkeypatch.setattr("agent_runtime_cockpit.isolation.microvm.os.access", lambda *_: True)
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm.shutil.which",
            lambda name: (
                f"/usr/bin/{name}" if name in {"firecracker", "mkfs.ext4", "truncate"} else None
            ),
        )
        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm._copy_workspace_to_ext4",
            lambda _workspace, image, size_mib=64: image.write_text("workspace", encoding="utf-8"),
        )

        def fake_run(argv, *, timeout_seconds, max_bytes):
            assert "--config-file" in argv
            from agent_runtime_cockpit.isolation.base import IsolationResult

            return (
                IsolationResult(
                    exit_code=0,
                    stdout=(
                        "ARC_FC_PROOF no-default-route=1\n"
                        "ARC_FC_PROOF curl-available=1\n"
                        "ARC_FC_PROOF network-failure=1\n"
                        "ARC_FC_PROOF sentinel-read=1\n"
                        "ARC_FC_PROOF workspace-mount-proven=1\n"
                        "ARC_FC_PROOF symlink-escape-blocked=1\n"
                        "ARC_FC_RESULT exit-code=0\n"
                        "ARC_FC_RESULT stdout-b64=aGVsbG8K\n"
                        "ARC_FC_RESULT stderr-b64=\n"
                    ),
                    provider="microvm",
                ),
                None,
            )

        monkeypatch.setattr(
            "agent_runtime_cockpit.isolation.microvm._run_firecracker_process", fake_run
        )
        provider = MicroVMIsolationProvider()
        import asyncio

        result = asyncio.run(provider.execute(["printf", "hello"], cwd=tmp_path))
        assert result.exit_code == 0
        assert result.stdout == "hello\n"
        assert result.provider == "microvm"

    def test_microvm_execute_error_message_references_adr(self, tmp_path):
        """execute() error message must reference ADR-024."""
        provider = MicroVMIsolationProvider()
        with pytest.raises(NotImplementedError) as exc_info:
            import asyncio

            asyncio.run(provider.execute(["pwd"], cwd=tmp_path))
        assert "ADR-024" in str(exc_info.value)


class TestMicroVMStatus:
    """status() must always report available=False with correct contract reference."""

    def test_microvm_status_available_false(self):
        """status()['available'] is false by default."""
        provider = MicroVMIsolationProvider()
        assert provider.status()["available"] is False

    def test_microvm_status_contains_contract_ref(self):
        """status()['contract_doc'] references ADR-024."""
        provider = MicroVMIsolationProvider()
        doc = provider.status()["contract_doc"]
        assert isinstance(doc, str)
        assert len(doc) > 0
        assert "ADR-024" in doc

    def test_microvm_status_harness_fields_present(self):
        """status() contains lima_harness and firecracker_harness keys."""
        provider = MicroVMIsolationProvider()
        s = provider.status()
        assert "lima_harness" in s
        assert "firecracker_harness" in s

    def test_microvm_status_reason_gate_blocked(self):
        """status()['reason'] explains unsatisfied execution gates."""
        provider = MicroVMIsolationProvider()
        assert provider.status()["reason"] == "firecracker_exec_gates_not_satisfied"

    def test_microvm_status_unblock_gate_present(self):
        """status()['unblock_gate'] describes the honored gate."""
        provider = MicroVMIsolationProvider()
        gate = provider.status()["unblock_gate"]
        assert "ARC_MICROVM_EXEC_ENABLED" in gate

    def test_microvm_status_marks_strict_network_isolation_unavailable(self):
        provider = MicroVMIsolationProvider()
        status = provider.status()
        assert status["strict_network_isolation"] is False
        assert status["lima_security_posture"] == "low_security_network_present"

    def test_microvm_execute_still_blocked_after_firecracker_design_proof(self, tmp_path):
        provider = MicroVMIsolationProvider()
        with pytest.raises(NotImplementedError, match="ADR-024"):
            import asyncio

            asyncio.run(provider.execute(["curl", "https://example.com"], cwd=tmp_path))

    def test_microvm_name_property(self):
        """name property returns 'microvm'."""
        provider = MicroVMIsolationProvider()
        assert provider.name == "microvm"
