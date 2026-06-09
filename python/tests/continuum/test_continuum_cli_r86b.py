"""Tests: arc continuum list/resume CLI (Phase 279)."""

from __future__ import annotations

import json

import pytest
from cryptography.fernet import Fernet
from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app
from agent_runtime_cockpit.continuum.store import SessionStore, TranscriptEntry
import agent_runtime_cockpit.cli.continuum as continuum_mod

runner = CliRunner()


@pytest.fixture
def sessions_dir(tmp_path):
    return str(tmp_path)


@pytest.fixture
def populated_store(tmp_path, monkeypatch):
    key = Fernet.generate_key()
    monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path))
    store = SessionStore("sess-abc", key)
    store.append_transcript_entry(
        TranscriptEntry(seq_id=0, timestamp="2026-01-01T00:00:00Z", role="user", content="hello")
    )
    store.save_ui_state({"active_tab": "runs"})
    return store, str(tmp_path), key


def test_continuum_list_empty(sessions_dir, monkeypatch):
    monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", sessions_dir)
    result = runner.invoke(app, ["continuum", "list", "--sessions-dir", sessions_dir])
    assert result.exit_code == 0
    assert "No sessions found" in result.output


def test_continuum_list_shows_session(populated_store):
    _, sdir, _ = populated_store
    result = runner.invoke(app, ["continuum", "list", "--sessions-dir", sdir])
    assert result.exit_code == 0
    assert "sess-abc" in result.output


def test_continuum_list_json(populated_store):
    _, sdir, _ = populated_store
    result = runner.invoke(app, ["continuum", "list", "--sessions-dir", sdir, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert any(r["session_id"] == "sess-abc" for r in data)


def test_continuum_resume_not_found(sessions_dir):
    result = runner.invoke(
        app, ["continuum", "resume", "no-such-session", "--sessions-dir", sessions_dir]
    )
    assert result.exit_code == 1


def test_continuum_resume_json(populated_store, monkeypatch):
    store, sdir, key = populated_store
    # Patch _load_key in the continuum module to return our test key
    monkeypatch.setattr(continuum_mod, "_load_key", lambda: key)
    result = runner.invoke(
        app, ["continuum", "resume", "sess-abc", "--sessions-dir", sdir, "--json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["session_id"] == "sess-abc"
    assert data["transcript_entries"] == 1


def test_continuum_resume_text(populated_store, monkeypatch):
    store, sdir, key = populated_store
    monkeypatch.setattr(continuum_mod, "_load_key", lambda: key)
    result = runner.invoke(app, ["continuum", "resume", "sess-abc", "--sessions-dir", sdir])
    assert result.exit_code == 0
    assert "sess-abc" in result.output
    assert "hello" in result.output
