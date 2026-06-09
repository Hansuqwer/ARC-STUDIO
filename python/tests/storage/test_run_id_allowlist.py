"""Tests: R-SEC4 — run_id allowlist + relative_to() confinement (Phase 288)."""

from __future__ import annotations

import pytest


def test_safe_run_id_accepts_uuid():
    from agent_runtime_cockpit.storage.jsonl import _safe_run_id

    rid = "550e8400-e29b-41d4-a716-446655440000"
    assert _safe_run_id(rid) == rid


def test_safe_run_id_accepts_alphanumeric():
    from agent_runtime_cockpit.storage.jsonl import _safe_run_id

    assert _safe_run_id("run-001") == "run-001"
    assert _safe_run_id("run_abc") == "run_abc"


def test_safe_run_id_rejects_path_traversal():
    from agent_runtime_cockpit.storage.jsonl import _safe_run_id

    with pytest.raises(ValueError):
        _safe_run_id("../secret")


def test_safe_run_id_rejects_slash():
    from agent_runtime_cockpit.storage.jsonl import _safe_run_id

    with pytest.raises(ValueError):
        _safe_run_id("a/b")


def test_safe_run_id_rejects_null_byte():
    from agent_runtime_cockpit.storage.jsonl import _safe_run_id

    with pytest.raises(ValueError):
        _safe_run_id("run\x00id")


def test_safe_run_id_rejects_empty():
    from agent_runtime_cockpit.storage.jsonl import _safe_run_id

    with pytest.raises(ValueError):
        _safe_run_id("")


def test_run_path_stays_within_base_dir(tmp_path):
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

    store = JsonlTraceStore(base_dir=tmp_path)
    path = store._run_path("run-001")
    assert path.parent == tmp_path


def test_run_path_rejects_traversal_run_id(tmp_path):
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

    store = JsonlTraceStore(base_dir=tmp_path)
    with pytest.raises(ValueError):
        store._run_path("../evil")
