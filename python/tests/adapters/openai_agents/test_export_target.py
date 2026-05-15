"""
Tests: OpenAI Agents export target (ARC_OPENAI_AGENTS_EXPORT).

Verifies that the adapter:
1. Loads the Agent from ``ARC_OPENAI_AGENTS_EXPORT=module:attr``.
2. Refuses targets outside the workspace.
3. Reports ``missing_export_target`` when unset.
"""
from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

from agent_runtime_cockpit.adapters.openai_agents import (
    OpenAIAgentsAdapter,
    _load_exported_agent,
    ExportTargetError,
    _EXPORT_ENV,
)


# ---- helpers ---------------------------------------------------------------

def _make_fake_agent_class():
    """Return a stub ``Agent`` class so ``from agents import Agent`` works."""
    import dataclasses

    @dataclasses.dataclass
    class FakeAgent:
        name: str = "test-agent"
        instructions: str = "test instructions"

    return FakeAgent


def _with_fake_agents_module():
    """Context manager that injects a fake ``agents`` module into sys.modules."""
    import types

    FakeAgentCls = _make_fake_agent_class()

    class FakeRunHooks:
        async def on_agent_start(self, context, agent): pass
        async def on_agent_end(self, context, agent, output): pass
        async def on_tool_start(self, context, agent, tool): pass
        async def on_tool_end(self, context, agent, tool, result): pass
        async def on_handoff(self, context, from_agent, to_agent): pass

    class FakeRunResult:
        final_output = "mock output"

    class FakeRunner:
        @staticmethod
        async def run(agent, prompt, hooks=None):
            return FakeRunResult()

    agents_mod = types.ModuleType("agents")
    agents_mod.Agent = FakeAgentCls
    agents_mod.Runner = FakeRunner
    agents_mod.RunHooks = FakeRunHooks
    return mock.patch.dict(sys.modules, {"agents": agents_mod})


# ---------------------------------------------------------------------------
# Unit: _load_exported_agent
# ---------------------------------------------------------------------------

class TestLoadExportedAgent:
    """Tests for the lower-level loader function."""

    def test_raises_when_env_unset(self):
        """No ARC_OPENAI_AGENTS_EXPORT → ExportTargetError."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ExportTargetError) as exc:
                _load_exported_agent({"workspace": "/tmp"})
            assert _EXPORT_ENV in str(exc.value)

    def test_raises_on_malformed_format(self):
        """Bad format (missing colon) → ExportTargetError."""
        with mock.patch.dict(os.environ, {_EXPORT_ENV: "no_colon"}, clear=True):
            with pytest.raises(ExportTargetError) as exc:
                _load_exported_agent({"workspace": "/tmp"})
            assert "module:attr" in str(exc.value)

    def test_raises_on_empty_module(self):
        """module:attr with empty module → ExportTargetError."""
        with mock.patch.dict(os.environ, {_EXPORT_ENV: ":my_agent"}, clear=True):
            with pytest.raises(ExportTargetError) as exc:
                _load_exported_agent({"workspace": "/tmp"})
            assert "module:attr" in str(exc.value)

    def test_raises_on_empty_attr(self):
        """module:attr with empty attr → ExportTargetError."""
        with mock.patch.dict(os.environ, {_EXPORT_ENV: "my_module:"}, clear=True):
            with pytest.raises(ExportTargetError) as exc:
                _load_exported_agent({"workspace": "/tmp"})
            assert "module:attr" in str(exc.value)

    def test_raises_when_module_not_found(self):
        """Module not found by find_spec → ExportTargetError."""
        # find_spec returns None for a truly non-existent module.
        with (
            mock.patch.dict(os.environ, {_EXPORT_ENV: "nonexistent.module:agent"}, clear=True),
            mock.patch("importlib.util.find_spec", return_value=None),
        ):
            with pytest.raises(ExportTargetError) as exc:
                _load_exported_agent({"workspace": "/tmp"})
            assert "not found" in str(exc.value).lower()

    def test_raises_when_outside_workspace(self, tmp_path):
        """Module outside workspace → ExportTargetError (security)."""
        workspace = tmp_path / "my_project"
        workspace.mkdir()

        outside_mod = tmp_path / "outside" / "evil.py"
        outside_mod.parent.mkdir(parents=True)
        outside_mod.write_text("# pretend module")

        spec = mock.Mock()
        spec.origin = str(outside_mod)
        spec.name = "evil"

        with mock.patch.dict(os.environ, {_EXPORT_ENV: "evil:agent"}, clear=True):
            with mock.patch("importlib.util.find_spec", return_value=spec):
                with pytest.raises(ExportTargetError) as exc:
                    _load_exported_agent({"workspace": str(workspace)})
                assert "outside the workspace" in str(exc.value)

    def test_raises_when_not_an_agent_instance(self, tmp_path):
        """Exported attr is not an Agent → ExportTargetError."""
        workspace = tmp_path / "proj"
        workspace.mkdir()

        spec = mock.Mock()
        spec.origin = str(workspace / "myagent.py")
        spec.name = "myagent"

        fake_mod = mock.Mock()
        fake_mod.my_thing = object()  # not an Agent

        with (
            mock.patch.dict(os.environ, {_EXPORT_ENV: "myagent:my_thing"}, clear=True),
            mock.patch("importlib.util.find_spec", return_value=spec),
            mock.patch("importlib.import_module", return_value=fake_mod),
            _with_fake_agents_module(),
        ):
            with pytest.raises(ExportTargetError) as exc:
                _load_exported_agent({"workspace": str(workspace)})
            assert "not an Agent" in str(exc.value)

    def test_allows_trusted_path_outside_workspace(self, tmp_path):
        """Module outside workspace but on ARC_TRUSTED_PATHS → allowed, then
        fails on the isinstance check (proving workspace check passed)."""
        workspace = tmp_path / "my_project"
        workspace.mkdir()

        trusted_dir = tmp_path / "trusted"
        trusted_dir.mkdir()
        mod_file = trusted_dir / "mylib.py"
        mod_file.write_text("# pretend module")

        spec = mock.Mock()
        spec.origin = str(mod_file)
        spec.name = "mylib"

        fake_mod = mock.Mock()
        fake_mod.agent = object()  # not an Agent but inside trusted path

        with (
            mock.patch.dict(
                os.environ,
                {
                    _EXPORT_ENV: "mylib:agent",
                    "ARC_TRUSTED_PATHS": str(trusted_dir),
                },
                clear=True,
            ),
            mock.patch("importlib.util.find_spec", return_value=spec),
            mock.patch("importlib.import_module", return_value=fake_mod),
            _with_fake_agents_module(),
        ):
            with pytest.raises(ExportTargetError) as exc:
                _load_exported_agent({"workspace": str(workspace)})
            # Should fail on "not an Agent", NOT "outside the workspace"
            assert "not an Agent" in str(exc.value)
            assert "outside the workspace" not in str(exc.value)


# ---------------------------------------------------------------------------
# CapabilityReport: missing_export_target
# ---------------------------------------------------------------------------

class TestCapabilityReportExportTarget:
    """Tests that capability_report returns missing_export_target correctly."""

    def test_reports_missing_export_target(self, tmp_path):
        """Without ARC_OPENAI_AGENTS_EXPORT → missing_export_target."""
        adapter = OpenAIAgentsAdapter()
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch("importlib.util.find_spec", return_value=mock.Mock()),
        ):
            report = adapter.capability_report(tmp_path)
            assert report.can_run is False
            assert report.availability == "missing_export_target"
            assert _EXPORT_ENV in report.reason

    def test_reports_runnable_when_export_set(self, tmp_path):
        """With ARC_OPENAI_AGENTS_EXPORT → can_run=True (if other gates pass)."""
        adapter = OpenAIAgentsAdapter()
        with (
            mock.patch.dict(
                os.environ,
                {
                    _EXPORT_ENV: "my_project.agent:my_agent",
                    "ARC_OPENAI_RUN_BACKEND": "stub",
                    "ARC_OPENAI_ALLOW_COSTS": "true",
                },
                clear=True,
            ),
            mock.patch("importlib.util.find_spec", return_value=mock.Mock()),
            mock.patch(
                "agent_runtime_cockpit.gating.require_dual_gate",
                return_value=("stub", False),
            ),
        ):
            report = adapter.capability_report(tmp_path)
            assert report.can_run is True
            assert report.availability == "runnable"


# ---------------------------------------------------------------------------
# run_workflow: export target integration
# ---------------------------------------------------------------------------

class TestRunWorkflowExport:
    """Tests that run_workflow uses export target (and fails without it)."""

    def test_fails_without_export_target(self, tmp_path):
        """No ARC_OPENAI_AGENTS_EXPORT → RUN_FAILED record."""
        import asyncio

        async def _run():
            adapter = OpenAIAgentsAdapter()
            with (
                mock.patch.dict(os.environ, {}, clear=True),
                mock.patch("importlib.util.find_spec", return_value=mock.Mock()),
                mock.patch(
                    "agent_runtime_cockpit.gating.require_dual_gate",
                    return_value=("stub", False),
                ),
                _with_fake_agents_module(),
            ):
                return await adapter.run_workflow("test-wf", {"workspace": str(tmp_path)})

        run = asyncio.run(_run())
        assert run.status.value == "failed"
        assert any(
            _EXPORT_ENV in e.data.get("error", "")
            for e in run.events
        )

    def test_fails_with_bad_export_target(self, tmp_path):
        """Invalid module in ARC_OPENAI_AGENTS_EXPORT → RUN_FAILED record."""
        import asyncio

        async def _run():
            adapter = OpenAIAgentsAdapter()
            spec = mock.Mock()
            spec.origin = None

            with (
                mock.patch.dict(
                    os.environ,
                    {_EXPORT_ENV: "nonexistent.module:agent"},
                    clear=True,
                ),
                mock.patch("importlib.util.find_spec", return_value=spec),
                mock.patch(
                    "agent_runtime_cockpit.gating.require_dual_gate",
                    return_value=("stub", False),
                ),
            ):
                return await adapter.run_workflow("test-wf", {"workspace": str(tmp_path)})

        run = asyncio.run(_run())
        assert run.status.value == "failed"
