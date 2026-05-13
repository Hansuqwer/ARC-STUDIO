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
    assert "stub direct response" in run.events[1].data["final_output"].lower()
    # Verify it was persisted
    loaded = store.load(run.id)
    assert loaded is not None


def test_adopt_candidate(tmp_path):
    req = ArenaAdoptRequest(run_id="test", candidate_id="c1", target_file="src/test.py")
    result = adopt_candidate(tmp_path, req)
    assert result.applied is True


# ── Live arena mode tests (no real API calls) ────────────────────────────


def test_live_arena_disabled_by_default():
    """Stub mode is the default — no env var set."""
    req = ArenaRequest(
        mode=ArenaMode.DIRECT,
        prompt="Hello",
        model="gpt-4o-mini-2024-07-18",
        allow_paid_calls=True,
    )
    resp = arena_request(Path("/tmp"), req)
    assert resp.mode == ArenaMode.DIRECT
    assert len(resp.candidates) == 1
    # Stub responses have a specific format
    assert "stub" in resp.candidates[0].text.lower() or "response" in resp.candidates[0].text.lower()


def test_live_arena_enabled_missing_api_key_returns_warning(monkeypatch):
    """Live mode enabled but no API key — returns an explicit warning."""
    monkeypatch.setenv("ARC_ALLOW_LIVE_ARENA", "true")
    monkeypatch.setenv("ARC_LMARENA_ALLOW_COSTS", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    req = ArenaRequest(
        mode=ArenaMode.DIRECT,
        prompt="Hello",
        model="gpt-4o-mini-2024-07-18",
        allow_paid_calls=True,
    )
    resp = arena_request(Path("/tmp"), req)
    assert resp.mode == ArenaMode.DIRECT
    assert resp.candidates == []
    assert any("OPENAI_API_KEY" in warning for warning in resp.warnings)


def test_live_arena_requires_lmarena_cost_gate(monkeypatch):
    """Live mode needs both live flag and LM Arena cost gate."""
    monkeypatch.setenv("ARC_ALLOW_LIVE_ARENA", "true")
    monkeypatch.delenv("ARC_LMARENA_ALLOW_COSTS", raising=False)
    req = ArenaRequest(
        mode=ArenaMode.DIRECT,
        prompt="Hello",
        model="gpt-4o-mini-2024-07-18",
        allow_paid_calls=True,
    )
    resp = arena_request(Path("/tmp"), req)
    assert resp.candidates == []
    assert any("ARC_LMARENA_ALLOW_COSTS" in warning for warning in resp.warnings)


def test_live_arena_enabled_no_paid_calls_gate(monkeypatch):
    """Live mode enabled but allow_paid_calls=False — blocked with warning."""
    monkeypatch.setenv("ARC_ALLOW_LIVE_ARENA", "true")
    monkeypatch.setenv("ARC_LMARENA_ALLOW_COSTS", "true")
    req = ArenaRequest(
        mode=ArenaMode.DIRECT,
        prompt="Hello",
        model="gpt-4o-mini-2024-07-18",
        allow_paid_calls=False,
    )
    resp = arena_request(Path("/tmp"), req)
    assert resp.mode == ArenaMode.DIRECT
    assert resp.candidates == []
    assert "allow_paid_calls" in " ".join(resp.warnings)


def test_live_arena_battle_failure_returns_warning(monkeypatch):
    """Battle mode with live enabled but no keys — returns an explicit warning."""
    monkeypatch.setenv("ARC_ALLOW_LIVE_ARENA", "true")
    monkeypatch.setenv("ARC_LMARENA_ALLOW_COSTS", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    req = ArenaRequest(
        mode=ArenaMode.BATTLE,
        prompt="Compare",
        model_tags=["fast"],
        allow_paid_calls=True,
    )
    resp = arena_request(Path("/tmp"), req)
    assert resp.mode == ArenaMode.BATTLE
    assert resp.candidates == []
    assert any("API_KEY" in warning for warning in resp.warnings)


def test_live_arena_unknown_model_returns_warning(monkeypatch):
    """Unknown model in live mode — returns an explicit warning."""
    monkeypatch.setenv("ARC_ALLOW_LIVE_ARENA", "true")
    monkeypatch.setenv("ARC_LMARENA_ALLOW_COSTS", "true")
    req = ArenaRequest(
        mode=ArenaMode.DIRECT,
        prompt="Hello",
        model="unknown-model-42",
        allow_paid_calls=True,
    )
    resp = arena_request(Path("/tmp"), req)
    assert resp.mode == ArenaMode.DIRECT
    assert resp.candidates == []
    assert any("No live provider configuration" in warning for warning in resp.warnings)


def test_live_arena_no_api_key_leakage(monkeypatch):
    """Secrets are not leaked in warnings or candidate text."""
    monkeypatch.setenv("ARC_ALLOW_LIVE_ARENA", "true")
    monkeypatch.setenv("ARC_LMARENA_ALLOW_COSTS", "true")
    # Set a real-looking key so the provider attempts a call but it fails.
    # The key should never appear in response text or warnings.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-live-arena-secret-abc123")
    req = ArenaRequest(
        mode=ArenaMode.DIRECT,
        prompt="Hello",
        model="gpt-4o-mini-2024-07-18",
        allow_paid_calls=True,
    )
    resp = arena_request(Path("/tmp"), req)
    serialized = resp.model_dump_json()
    # The raw secret must not appear in any response field
    assert "sk-test-live-arena-secret-abc123" not in serialized
