"""Tests for adapters/_shared.py helpers."""

import sys

from agent_runtime_cockpit.adapters._shared import make_event, workspace_import_path


def test_make_event_fields():
    ev = make_event("run-1", 3, "ARC_STEP", {"k": "v"})
    assert ev.run_id == "run-1"
    assert ev.sequence == 3
    assert ev.type == "ARC_STEP"
    assert ev.data == {"k": "v"}


def test_make_event_timestamp_utc():
    ev = make_event("r", 0, "T", {})
    assert ev.timestamp.endswith("+00:00") or ev.timestamp.endswith("Z") or "T" in ev.timestamp


def test_workspace_import_path_adds_and_removes(tmp_path):
    assert str(tmp_path) not in sys.path
    with workspace_import_path(tmp_path):
        assert str(tmp_path) in sys.path
    assert str(tmp_path) not in sys.path


def test_workspace_import_path_src_subdir(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    with workspace_import_path(tmp_path):
        assert str(tmp_path) in sys.path
        assert str(src) in sys.path
    assert str(tmp_path) not in sys.path
    assert str(src) not in sys.path


def test_workspace_import_path_nonexistent_is_noop(tmp_path):
    before = list(sys.path)
    with workspace_import_path(tmp_path / "does_not_exist"):
        assert sys.path == before
    assert sys.path == before


def test_workspace_import_path_idempotent(tmp_path):
    """Already-present paths are not re-added."""
    sys.path.insert(0, str(tmp_path))
    try:
        count_before = sys.path.count(str(tmp_path))
        with workspace_import_path(tmp_path):
            assert sys.path.count(str(tmp_path)) == count_before
        assert sys.path.count(str(tmp_path)) == count_before
    finally:
        sys.path.remove(str(tmp_path))
