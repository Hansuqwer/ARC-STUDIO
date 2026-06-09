"""Tests: R84 ARC Index — build + search (Phases 303-304)."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app
from agent_runtime_cockpit.index import CodebaseIndex

runner = CliRunner()


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / "main.py").write_text("def hello():\n    pass\n\nclass Foo:\n    pass\n")
    (tmp_path / "utils.ts").write_text("function greet(name: string): string { return name; }\n")
    (tmp_path / "README.md").write_text("# Test Project\nHello world\n")
    return tmp_path


def test_build_indexes_files(workspace, monkeypatch):
    monkeypatch.setenv("ARC_INDEX_DIR", str(workspace / ".arc_index"))
    idx = CodebaseIndex(workspace)
    stats = idx.build()
    assert stats["indexed"] == 3
    assert stats["elapsed_s"] >= 0


def test_build_stats(workspace, monkeypatch):
    monkeypatch.setenv("ARC_INDEX_DIR", str(workspace / ".arc_index"))
    idx = CodebaseIndex(workspace)
    idx.build()
    stats = idx.stats()
    assert stats["file_count"] == 3
    assert stats["last_built"] is not None


def test_search_finds_symbol(workspace, monkeypatch):
    monkeypatch.setenv("ARC_INDEX_DIR", str(workspace / ".arc_index"))
    idx = CodebaseIndex(workspace)
    idx.build()
    results = idx.search("hello", limit=5)
    assert any("main.py" in r.path for r in results)


def test_search_empty_index(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_INDEX_DIR", str(tmp_path / ".arc_index"))
    idx = CodebaseIndex(tmp_path)
    # No build — search should return empty
    results = idx.search("anything", limit=5)
    assert results == []


def test_cli_build_json(workspace, monkeypatch):
    monkeypatch.setenv("ARC_INDEX_DIR", str(workspace / ".arc_index"))
    result = runner.invoke(app, ["index", "build", "--json", "--workspace", str(workspace)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["indexed"] == 3


def test_cli_search_empty_exits_1(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_INDEX_DIR", str(tmp_path / ".arc_index"))
    result = runner.invoke(app, ["index", "search", "hello", "--workspace", str(tmp_path)])
    assert result.exit_code == 1


def test_cli_search_json(workspace, monkeypatch):
    monkeypatch.setenv("ARC_INDEX_DIR", str(workspace / ".arc_index"))
    runner.invoke(app, ["index", "build", "--workspace", str(workspace)])
    result = runner.invoke(
        app, ["index", "search", "hello", "--json", "--workspace", str(workspace)]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    assert isinstance(data["results"], list)


def test_cli_stats_json(workspace, monkeypatch):
    monkeypatch.setenv("ARC_INDEX_DIR", str(workspace / ".arc_index"))
    runner.invoke(app, ["index", "build", "--workspace", str(workspace)])
    result = runner.invoke(app, ["index", "stats", "--json", "--workspace", str(workspace)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["file_count"] == 3
