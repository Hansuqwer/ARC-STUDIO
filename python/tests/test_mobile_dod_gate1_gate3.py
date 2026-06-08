"""Mobile DoD gate 1 (UX states) + gate 3 (parity) tests for arc mobile CLI.

Phase 218 — R-MOBILE-POLISH1
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.cli._subapps import mobile_app

runner = CliRunner()
FIXTURES = Path(__file__).parent / "mobile" / "fixtures"


def _json(r):
    return json.loads(r.output)


class TestMobileGate1UXStates:
    """DoD gate 1: explicit loading/empty/error/success states in CLI output."""

    def test_doctor_returns_state_ok(self):
        r = runner.invoke(mobile_app, ["doctor", "--json"])
        assert r.exit_code == 0
        d = _json(r)
        assert "state" in d["data"], "doctor must return explicit 'state' field"
        assert d["data"]["state"] == "ok"

    def test_doctor_state_ok_when_caps_present(self):
        r = runner.invoke(mobile_app, ["doctor", "--json"])
        assert r.exit_code == 0
        d = _json(r)
        assert d["data"]["capability_count"] > 0
        assert d["data"]["state"] == "ok"

    def test_validate_valid_returns_state_ok(self):
        r = runner.invoke(
            mobile_app, ["validate", str(FIXTURES / "valid_mobile_runtime.json"), "--json"]
        )
        assert r.exit_code == 0
        d = _json(r)
        assert d["data"]["state"] == "ok"

    def test_validate_invalid_returns_state_error(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "id": "t",
                    "name": "t",
                    "background_execution": True,  # blocked in MVP
                    "network_by_default": False,
                    "simulator_mode": True,
                    "capabilities": [],
                }
            )
        )
        r = runner.invoke(mobile_app, ["validate", str(bad), "--json"])
        assert r.exit_code == 1
        d = _json(r)
        assert d["error"]["details"]["state"] in ("error", "degraded")

    def test_capabilities_empty_state_on_no_results(self, tmp_path):
        """capabilities with empty manifest returns count=0 (empty state)."""
        empty_mf = tmp_path / "arc-mobile-capabilities.json"
        empty_mf.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "id": "empty.manifest",
                    "name": "Empty",
                    "background_execution": False,
                    "network_by_default": False,
                    "simulator_mode": True,
                    "capabilities": [],
                }
            )
        )
        r = runner.invoke(mobile_app, ["capabilities", "--manifest", str(empty_mf), "--json"])
        assert r.exit_code == 0
        d = _json(r)
        assert d["data"]["count"] == 0, "empty manifest must show count=0 (empty state)"


class TestMobileGate3Parity:
    """DoD gate 3: CLI --json output is structurally consistent with Python API."""

    def test_capabilities_cli_matches_python_api(self):
        """arc mobile capabilities --json matches Python list_capabilities() count."""
        from agent_runtime_cockpit.mobile import list_capabilities

        r = runner.invoke(mobile_app, ["capabilities", "--json"])
        assert r.exit_code == 0
        d = _json(r)
        python_caps = list_capabilities()
        assert d["data"]["count"] == len(python_caps), (
            "CLI capability count must match Python list_capabilities() count"
        )

    def test_validate_cli_matches_python_api(self):
        """arc mobile validate matches Python validate_manifest() ok field."""
        from agent_runtime_cockpit.mobile.manifest import load_manifest
        from agent_runtime_cockpit.mobile import validate_manifest

        mf = FIXTURES / "valid_mobile_runtime.json"
        r = runner.invoke(mobile_app, ["validate", str(mf), "--json"])
        assert r.exit_code == 0
        d = _json(r)
        manifest = load_manifest(mf)
        report = validate_manifest(manifest)
        assert d["data"]["ok"] == report.ok, (
            "CLI validate ok must match Python validate_manifest().ok"
        )
