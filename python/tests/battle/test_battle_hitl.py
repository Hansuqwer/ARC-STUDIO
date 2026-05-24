"""Battle HITL integration tests (Phase 34.4/R26A)."""

import tempfile
from pathlib import Path

from agent_runtime_cockpit.audit.hitl import HitlDecision
from agent_runtime_cockpit.audit.hitl_sqlite_store import HitlSqliteStore
from agent_runtime_cockpit.battle import BattleRun, BattleRunner
from agent_runtime_cockpit.battle.store import BattleStore


def _store(tmpdir: Path) -> BattleStore:
    store = BattleStore(db_path=tmpdir / "battles.db")
    store.init_db()
    return store


def test_battle_with_require_hitl_emits_event_and_persists_prompt():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        battle = BattleRun(prompt="Pick the best candidate", workers=2, require_hitl=True)
        runner = BattleRunner(store=_store(workspace), workspace=workspace)

        result = runner.run_battle(battle)

        assert result["status"] == "completed"
        event_types = [event["type"] for event in result["events"]]
        assert "BATTLE_HITL_REQUIRED" in event_types
        prompt = HitlSqliteStore(workspace / ".arc" / "hitl.db").get_prompt(
            f"battle-hitl-{battle.id}"
        )
        assert prompt is not None
        assert prompt.context["battle_id"] == battle.id


def test_battle_hitl_timeout_event_when_no_response():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        battle = BattleRun(
            prompt="Pick the best candidate",
            workers=2,
            require_hitl=True,
            metadata={"hitl_timeout_seconds": 1},
        )
        runner = BattleRunner(store=_store(workspace), workspace=workspace)

        result = runner.run_battle(battle)

        timeout_events = [event for event in result["events"] if event["type"] == "HITL_TIMEOUT"]
        assert timeout_events
        assert timeout_events[0]["data"]["hitl_id"] == f"battle-hitl-{battle.id}"


def test_existing_hitl_response_is_integrated_as_human_votes():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        hitl_id = "battle-hitl-fixed"
        battle = BattleRun(
            prompt="Pick the best candidate",
            workers=2,
            require_hitl=True,
            metadata={"hitl_id": hitl_id},
        )
        store = _store(workspace)
        runner = BattleRunner(store=store, workspace=workspace)
        candidates = runner._execute_workers(battle, ["model-a", "model-b"])
        prompt_store = HitlSqliteStore(workspace / ".arc" / "hitl.db")
        runner._collect_hitl_votes(battle, candidates)
        token = prompt_store.get_token(hitl_id)
        assert token is not None
        prompt_store.respond(
            hitl_id,
            HitlDecision.APPROVE,
            token,
            operator_id="human-judge",
            notes=candidates[1].id,
        )

        votes = runner._collect_hitl_votes(battle, candidates)

        assert len(votes) == 2
        assert {vote.voter_type.value for vote in votes} == {"human"}
        approved = [vote for vote in votes if vote.approved]
        assert len(approved) == 1
        assert approved[0].candidate_id == candidates[1].id
