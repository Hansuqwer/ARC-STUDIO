"""Tests for PR7: trace replay engine."""

from __future__ import annotations


def _make_trace(plan_id: str = "test-replay"):
    from agent_runtime_cockpit.mobile import (
        MobileActionPlan,
        MobileActionStep,
        simulate_action_plan,
        build_trace,
    )

    plan = MobileActionPlan(
        plan_id=plan_id,
        steps=[
            MobileActionStep(step_id="s1", capability_id="app.memory.write.mock", mock=True),
            MobileActionStep(step_id="s2", capability_id="app.memory.retrieve.mock", mock=True),
        ],
    )
    return build_trace(simulate_action_plan(plan))


class TestReplay:
    def test_identical_traces_match(self):
        from agent_runtime_cockpit.mobile.replay import replay_trace

        t = _make_trace()
        diff = replay_trace(t, t)
        assert diff.match
        assert diff.diffs == []

    def test_deterministic_traces_match(self):
        from agent_runtime_cockpit.mobile.replay import replay_trace

        t1 = _make_trace()
        t2 = _make_trace()
        diff = replay_trace(t1, t2)
        assert diff.match, diff.summary

    def test_different_plan_id_does_not_match(self):
        from agent_runtime_cockpit.mobile.replay import replay_trace

        t1 = _make_trace("plan-a")
        t2 = _make_trace("plan-b")
        diff = replay_trace(t1, t2)
        # plan_id is included in event key → should not match
        assert not diff.match

    def test_count_mismatch_detected(self):
        from agent_runtime_cockpit.mobile import (
            MobileActionPlan,
            MobileActionStep,
            simulate_action_plan,
            build_trace,
        )
        from agent_runtime_cockpit.mobile.replay import replay_trace

        plan_2 = MobileActionPlan(
            plan_id="test-replay",
            steps=[
                MobileActionStep(step_id="s1", capability_id="app.memory.write.mock", mock=True)
            ],
        )
        t1 = _make_trace()
        t_short = build_trace(simulate_action_plan(plan_2))
        diff = replay_trace(t1, t_short)
        assert not diff.match
        assert "count" in diff.summary.lower()

    def test_mutated_step_detected(self):
        from agent_runtime_cockpit.mobile.replay import replay_trace
        import copy

        t1 = _make_trace()
        t2 = copy.deepcopy(_make_trace())
        # Mutate allowed flag on first event
        t2.events[0] = t2.events[0].model_copy(update={"allowed": not t2.events[0].allowed})
        diff = replay_trace(t1, t2)
        assert not diff.match
        assert diff.first_diff_index == 0
