"""Mobile DoD gate 7 (reliability: timeouts/cancellation) tests.

Phase 219 — R-MOBILE-POLISH2
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli._subapps import mobile_app

runner = CliRunner()


class TestMobileGate7Reliability:
    """DoD gate 7: step count limit on simulate (unbounded input protection)."""

    def test_simulate_respects_max_steps_limit(self, tmp_path):
        """simulate must exit 1 when plan exceeds --max-steps."""
        plan = {
            "plan_id": "test-limit",
            "name": "Test",
            "steps": [
                {"step_id": f"s{i}", "capability_id": "app.memory.retrieve.mock", "mock": True}
                for i in range(3)
            ],
        }
        p = tmp_path / "big_plan.json"
        p.write_text(json.dumps(plan))
        r = runner.invoke(mobile_app, ["simulate", str(p), "--max-steps", "2", "--json"])
        assert r.exit_code == 1
        d = json.loads(r.output)
        assert d["ok"] is False
        assert "step_count" in (d.get("error", {}).get("details") or {})

    def test_simulate_passes_under_max_steps(self, tmp_path):
        """simulate must succeed when steps <= --max-steps."""
        plan = {
            "plan_id": "test-ok",
            "name": "OK",
            "steps": [{"step_id": "s0", "capability_id": "app.memory.retrieve.mock", "mock": True}],
        }
        p = tmp_path / "ok_plan.json"
        p.write_text(json.dumps(plan))
        r = runner.invoke(mobile_app, ["simulate", str(p), "--max-steps", "10", "--json"])
        assert r.exit_code == 0

    def test_simulate_has_max_steps_option(self):
        """simulate must have a --max-steps option."""
        import re

        r = runner.invoke(mobile_app, ["simulate", "--help"])
        # Strip ANSI escape codes before searching
        text = re.sub(r"\x1b\[[0-9;]*m", "", r.output)
        assert "max-steps" in text or "max_steps" in text, (
            "simulate must have a --max-steps option in its help"
        )
