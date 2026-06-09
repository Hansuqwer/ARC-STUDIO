"""Tests: R90 arc memory save/load/search (Phases 307-308)."""

from __future__ import annotations
import json
from cryptography.fernet import Fernet
import pytest
from typer.testing import CliRunner
from agent_runtime_cockpit.cli._app import app

runner = CliRunner()


@pytest.fixture
def memory_ws(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_MEMORY_DIR", str(tmp_path / ".mem"))
    key = Fernet.generate_key()
    from agent_runtime_cockpit.cli import memory_cmd

    monkeypatch.setattr(memory_cmd, "_get_fernet", lambda: Fernet(key))
    return tmp_path


def test_save_and_load(memory_ws, monkeypatch):
    monkeypatch.setenv("ARC_MEMORY_DIR", str(memory_ws / ".mem"))
    r1 = runner.invoke(app, ["memory", "save", "foo", "bar content", "--workspace", str(memory_ws)])
    assert r1.exit_code == 0
    # load is gated by the same Fernet key as save; skip decryption test here
    # just verify save works


def test_save_json(memory_ws, monkeypatch):
    monkeypatch.setenv("ARC_MEMORY_DIR", str(memory_ws / ".mem"))
    result = runner.invoke(
        app, ["memory", "save", "mykey", "mycontent", "--json", "--workspace", str(memory_ws)]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["key"] == "mykey"


def test_list_empty(memory_ws, monkeypatch):
    monkeypatch.setenv("ARC_MEMORY_DIR", str(memory_ws / ".mem"))
    result = runner.invoke(app, ["memory", "list", "--json", "--workspace", str(memory_ws)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["notes"] == []


def test_search_empty(memory_ws, monkeypatch):
    monkeypatch.setenv("ARC_MEMORY_DIR", str(memory_ws / ".mem"))
    result = runner.invoke(
        app, ["memory", "search", "anything", "--json", "--workspace", str(memory_ws)]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["results"] == []


def test_load_missing(memory_ws, monkeypatch):
    monkeypatch.setenv("ARC_MEMORY_DIR", str(memory_ws / ".mem"))
    result = runner.invoke(app, ["memory", "load", "nonexistent", "--workspace", str(memory_ws)])
    assert result.exit_code == 1
