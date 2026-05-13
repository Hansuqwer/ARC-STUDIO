"""Tests for the Arena service (stub mode)."""
from pathlib import Path
from agent_runtime_cockpit.arena.service import (
    list_models,
    list_tags,
    arena_request,
    store_arena_run,
    adopt_candidate,
)
from agent_runtime_cockpit.arena.models import (
    ArenaMode,
    ArenaRequest,
    ArenaAdoptRequest,
    PrivacyLevel,
)
from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore


def test_list_models():
    models = list_models()
    assert len(models) > 0
    assert any(m.id == "gpt-4o-mini-2024-07-18" for m in models)


def test_list_models_filtered_by_tag():
    models = list_models(tags=["agent"])
    assert all("agent" in m.tags for m in models)


def test_list_tags():
    tags = list_tags()
    assert "fast" in tags
    assert "best" in tags


def test_stub_battle():
    req = ArenaRequest(
        mode=ArenaMode.BATTLE,
        prompt="Write a function",
        model_tags=["fast", "code"],
    )
    resp = arena_request(Path("/tmp"), req)
    assert resp.mode == ArenaMode.BATTLE
    assert len(resp.candidates) >= 2
    assert resp.run_id != ""


def test_stub_direct():
    req = ArenaRequest(
        mode=ArenaMode.DIRECT,
        prompt="Hello",
        model="gpt-4o-mini-2024-07-18",
    )
    resp = arena_request(Path("/tmp"), req)
    assert resp.mode == ArenaMode.DIRECT
    assert len(resp.candidates) == 1


def test_stub_code():
    req = ArenaRequest(mode=ArenaMode.CODE, prompt="Create a Python class")
    resp = arena_request(Path("/tmp"), req)
    assert resp.mode == ArenaMode.CODE
    assert len(resp.candidates) >= 1
    assert resp.candidates[0].patch != ""


def test_stub_agent_preview():
    req = ArenaRequest(mode=ArenaMode.AGENT_ARENA_PREVIEW, prompt="Build a web app")
    resp = arena_request(Path("/tmp"), req)
    assert resp.mode == ArenaMode.AGENT_ARENA_PREVIEW
    assert resp.candidates[0].plan != ""


def test_store_arena_run(tmp_path):
    store = JsonlTraceStore(tmp_path / ".arc" / "traces")
    req = ArenaRequest(mode=ArenaMode.DIRECT, prompt="Test")
    resp = arena_request(tmp_path, req)
    run = store_arena_run(store, resp, req)
    assert run.runtime == "lmarena"
    assert run.workflow_id == "arena-direct"
    assert len(run.events) == 2
    assert run.events[0].type == "LMARENA_REQUESTED"
    # Verify it was persisted
    loaded = store.load(run.id)
    assert loaded is not None


def test_adopt_candidate(tmp_path):
    req = ArenaAdoptRequest(run_id="test", candidate_id="c1", target_file="src/test.py")
    result = adopt_candidate(tmp_path, req)
    assert result.applied is True
