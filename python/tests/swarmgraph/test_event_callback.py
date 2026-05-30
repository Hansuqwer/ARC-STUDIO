from __future__ import annotations

from agent_runtime_cockpit.swarmgraph.runner import SwarmGraphRunner


def test_on_event_callback_fires() -> None:
    received = []
    runner = SwarmGraphRunner(on_event=received.append)

    runner.run("test prompt")

    assert len(received) > 0
    assert received == runner.events


def test_on_event_callback_error_does_not_crash() -> None:
    def bad_callback(_event) -> None:
        raise RuntimeError("boom")

    runner = SwarmGraphRunner(on_event=bad_callback)
    result = runner.run("test prompt")

    assert result["status"] == "completed"
    assert len(runner.events) > 0
