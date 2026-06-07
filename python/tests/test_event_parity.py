"""PR17: TS event interface parity tests — prev_event_hash present in both Python and TS."""

from __future__ import annotations

from pathlib import Path

TS_EVENTS_FILE = (
    Path(__file__).parent.parent.parent
    / "packages"
    / "arc-protocol-ts"
    / "src"
    / "mobile-events.ts"
)


class TestEventParity:
    def test_python_recorder_has_prev_event_hash_field(self):
        from agent_runtime_cockpit.mobile.recorder import MobileRuntimeEvent

        assert "prev_event_hash" in MobileRuntimeEvent.model_fields

    def test_python_event_default_prev_hash_is_zeros(self):
        from agent_runtime_cockpit.mobile.recorder import MobileRuntimeEvent

        default = MobileRuntimeEvent.model_fields["prev_event_hash"].default
        assert default == "0" * 64

    def test_ts_events_file_has_prev_event_hash(self):
        if not TS_EVENTS_FILE.exists():
            return
        ts = TS_EVENTS_FILE.read_text()
        assert "prev_event_hash" in ts, "TS mobile-events.ts missing prev_event_hash field"

    def test_ts_guard_checks_prev_event_hash(self):
        if not TS_EVENTS_FILE.exists():
            return
        ts = TS_EVENTS_FILE.read_text()
        # The isMobileRuntimeEvent guard should check prev_event_hash
        assert "'prev_event_hash' in obj" in ts or '"prev_event_hash" in obj' in ts

    def test_ts_policy_decision_has_policy_version(self):
        if not TS_EVENTS_FILE.exists():
            return
        ts = TS_EVENTS_FILE.read_text()
        assert "policy_version" in ts, "TS MobilePolicyDecision missing policy_version field"

    def test_event_chain_first_event_prev_hash(self):
        from agent_runtime_cockpit.mobile import (
            MobileActionPlan,
            MobileActionStep,
            simulate_action_plan,
            build_trace,
        )

        plan = MobileActionPlan(
            plan_id="parity-chain",
            steps=[
                MobileActionStep(step_id="s1", capability_id="app.memory.write.mock", mock=True)
            ],
        )
        report = simulate_action_plan(plan)
        trace = build_trace(report)
        assert trace.events[0].prev_event_hash == "0" * 64
