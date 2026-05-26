"""MicroVM public-execution truth guard tests (Phase 37 Slice 37.17).

These tests verify that MicroVMIsolationProvider.execute() ALWAYS raises
NotImplementedError and that status() returns the correct blocked posture.

Truth constraints:
- execute() must raise even when ARC_MICROVM_EXEC_ENABLED=1 is set (gate not yet honored).
- status()["available"] must always be False.
- status()["contract_doc"] must reference ADR-024.
- status() must include lima_harness and firecracker_harness keys.
"""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.isolation.microvm import MicroVMIsolationProvider


class TestMicroVMExecuteAlwaysRaises:
    """execute() must always raise NotImplementedError regardless of env vars."""

    def test_microvm_execute_always_raises(self, tmp_path):
        """execute() raises NotImplementedError unconditionally."""
        provider = MicroVMIsolationProvider()
        with pytest.raises(NotImplementedError, match="microVM execution not yet available"):
            import asyncio

            asyncio.run(provider.execute(["uname", "-a"], cwd=tmp_path))

    def test_microvm_execute_raises_with_arc_microvm_exec_enabled_set(self, monkeypatch, tmp_path):
        """execute() raises even when ARC_MICROVM_EXEC_ENABLED=1 is set (gate not yet honored)."""
        monkeypatch.setenv("ARC_MICROVM_EXEC_ENABLED", "1")
        provider = MicroVMIsolationProvider()
        with pytest.raises(NotImplementedError, match="microVM execution not yet available"):
            import asyncio

            asyncio.run(provider.execute(["uname", "-a"], cwd=tmp_path))

    def test_microvm_execute_raises_with_both_gates_set(self, monkeypatch, tmp_path):
        """execute() raises even when both ARC_MICROVM_EXEC_ENABLED=1 and ARC_MICROVM_INTEGRATION=1."""
        monkeypatch.setenv("ARC_MICROVM_EXEC_ENABLED", "1")
        monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
        provider = MicroVMIsolationProvider()
        with pytest.raises(NotImplementedError, match="microVM execution not yet available"):
            import asyncio

            asyncio.run(provider.execute(["echo", "hello"], cwd=tmp_path))

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
        """status()['available'] is always False."""
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

    def test_microvm_status_reason_execution_not_implemented(self):
        """status()['reason'] is 'execution_not_implemented'."""
        provider = MicroVMIsolationProvider()
        assert provider.status()["reason"] == "execution_not_implemented"

    def test_microvm_status_unblock_gate_present(self):
        """status()['unblock_gate'] describes the gate (not yet honored)."""
        provider = MicroVMIsolationProvider()
        gate = provider.status()["unblock_gate"]
        assert "ARC_MICROVM_EXEC_ENABLED" in gate
        assert "not yet honored" in gate

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
