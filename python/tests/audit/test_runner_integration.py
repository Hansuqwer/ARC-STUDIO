"""Integration tests: adapter runners create HMAC-signed audit chains."""
from __future__ import annotations

import json
import pathlib
from pathlib import Path

import pytest

from agent_runtime_cockpit.audit.key_manager import AuditKeyManager


@pytest.fixture(autouse=True)
def _set_test_audit_key(monkeypatch):
    """Give all adapters a test HMAC key so AuditSession signs events."""
    monkeypatch.setenv(
        "ARC_AUDIT_HMAC_KEY",
        "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899",
    )


def _get_stored_hmac_chains(workspace: Path) -> list[Path]:
    audit_dir = workspace / ".arc" / "audit"
    if not audit_dir.exists():
        return []
    return sorted(audit_dir.glob("*.audit.jsonl"))


class TestSwarmGraphAuditIntegration:
    async def test_swarmgraph_stub_creates_hmac_chain(self, tmp_path: Path, monkeypatch):
        from agent_runtime_cockpit.adapters.swarmgraph.runner import SwarmGraphRunner

        runner = SwarmGraphRunner(tmp_path)
        run_id = await runner.run("test_entrypoint", {})

        hmac_chains = _get_stored_hmac_chains(tmp_path)
        assert len(hmac_chains) == 1, f"Expected 1 HMAC chain, got {hmac_chains}"
        chain_path = hmac_chains[0]

        lines = [l for l in chain_path.read_text().splitlines() if l.strip()]
        assert len(lines) >= 2, f"Expected >=2 audit events (start+complete), got {len(lines)}"

        # Verify chain is HMAC-signed
        first = json.loads(lines[0])
        assert "signature" in first, "HMAC signature missing from audit record"
        assert first["event"]["type"] == "run_started"

        last = json.loads(lines[-1])
        assert last["event"]["type"] == "run_completed"

    async def test_swarmgraph_sha256_chain_still_written(self, tmp_path: Path, monkeypatch):
        """Existing SHA-256 audit chain is preserved alongside the new HMAC chain."""
        from agent_runtime_cockpit.adapters.swarmgraph.runner import SwarmGraphRunner

        runner = SwarmGraphRunner(tmp_path)
        await runner.run("test_entrypoint", {})

        audit_dir = tmp_path / ".arc" / "audit"
        sha256_chains = list(audit_dir.glob("*.chain.jsonl"))
        hmac_chains = list(audit_dir.glob("*.audit.jsonl"))

        assert len(sha256_chains) == 1, (
            f"Expected SHA-256 chain preserved, got {sha256_chains}"
        )
        assert len(hmac_chains) == 1, (
            f"Expected HMAC chain created, got {hmac_chains}"
        )
        assert sha256_chains[0].stem.replace(".chain", "") == hmac_chains[0].stem.replace(".audit", ""), (
            "SHA-256 and HMAC chains should share the same run_id"
        )


class TestLangGraphAuditIntegration:
    async def test_langgraph_creates_hmac_chain(self, tmp_path: Path, monkeypatch):
        from agent_runtime_cockpit.adapters.langgraph.runner import LangGraphRunner

        workspace = tmp_path
        runner = LangGraphRunner(workspace)
        project_file = workspace / "test_graph.py"
        project_file.write_text("from langgraph.graph import StateGraph; graph = StateGraph(dict)")
        monkeypatch.chdir(workspace)

        with pytest.raises(Exception) as exc_info:
            await runner.run("test_graph:graph", {})
        assert exc_info.type is not SystemExit

        hmac_chains = _get_stored_hmac_chains(tmp_path)
        if hmac_chains:
            lines = [l for l in hmac_chains[0].read_text().splitlines() if l.strip()]
            assert any("run_started" in line for line in lines)


class TestCrewAIAuditIntegration:
    async def test_crewai_creates_hmac_chain(self, tmp_path: Path, monkeypatch):
        from agent_runtime_cockpit.adapters.crewai.runner import CrewAIRunner

        runner = CrewAIRunner(tmp_path)
        project_file = tmp_path / "test_crew.py"
        project_file.write_text("class FakeCrew:\n    def kickoff(self, inputs):\n        return 'done'")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(Exception) as exc_info:
            await runner.run("test_crew:FakeCrew", {})
        assert exc_info.type is not SystemExit

        hmac_chains = _get_stored_hmac_chains(tmp_path)
        if hmac_chains:
            lines = [l for l in hmac_chains[0].read_text().splitlines() if l.strip()]
            assert any("run_started" in line for line in lines)


class TestAuditChainVerifyIntegration:
    async def test_verify_created_chain(self, tmp_path: Path, monkeypatch):
        """created HMAC audit chain can be verified end-to-end."""
        from agent_runtime_cockpit.adapters.swarmgraph.runner import SwarmGraphRunner
        from agent_runtime_cockpit.audit.storage import AuditChainStore

        runner = SwarmGraphRunner(tmp_path)
        run_id = await runner.run("test_entrypoint", {})

        store = AuditChainStore(audit_dir=tmp_path / ".arc" / "audit")
        ok, msg = store.verify_run(run_id)
        assert ok is True, f"Audit chain verification failed: {msg}"
