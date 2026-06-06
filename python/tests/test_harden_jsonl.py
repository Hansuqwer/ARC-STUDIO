"""R-OPEN-HARDEN: poison-pill failure-injection tests for JsonlTraceStore.

Verify the store never raises on malformed/corrupt/binary/oversized inputs.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore


def _store(tmp_path: Path) -> JsonlTraceStore:
    d = tmp_path / "traces"
    d.mkdir()
    return JsonlTraceStore(d)


def _valid_run_json(run_id: str = "run-abc123") -> str:
    return json.dumps(
        {
            "id": run_id,
            "workflow_id": "wf-1",
            "runtime": "fake",
            "status": "completed",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "events": [],
        }
    )


# ── 1. Empty file ─────────────────────────────────────────────────────────────


def test_empty_file_returns_none(tmp_path):
    s = _store(tmp_path)
    (s.base_dir / "run-empty.jsonl").write_bytes(b"")
    assert s.load("run-empty") is None
    assert "run-empty" in s.list_runs()


# ── 2. Truncated JSON ─────────────────────────────────────────────────────────


def test_truncated_json_returns_none(tmp_path):
    s = _store(tmp_path)
    (s.base_dir / "run-trunc.jsonl").write_text('{"id": "run-trunc", "status":', encoding="utf-8")
    assert s.load("run-trunc") is None


# ── 3. Valid JSON, wrong schema ───────────────────────────────────────────────


def test_wrong_schema_returns_none(tmp_path):
    s = _store(tmp_path)
    (s.base_dir / "run-bad.jsonl").write_text(
        json.dumps({"not": "a run", "foo": 42}) + "\n", encoding="utf-8"
    )
    assert s.load("run-bad") is None


# ── 4. Binary / non-UTF-8 bytes ───────────────────────────────────────────────


def test_binary_content_returns_none(tmp_path):
    s = _store(tmp_path)
    (s.base_dir / "run-bin.jsonl").write_bytes(b"\xff\xfe\x00\x01\x80\x90" * 20)
    assert s.load("run-bin") is None


# ── 5. Oversized line (no OOM) ────────────────────────────────────────────────


def test_oversized_line_returns_none(tmp_path):
    s = _store(tmp_path)
    (s.base_dir / "run-big.jsonl").write_text("x" * (12 * 1024 * 1024) + "\n", encoding="utf-8")
    result = s.load("run-big")
    assert result is None


# ── 6. Corrupt second line doesn't affect first-line load ────────────────────


def test_corrupt_second_line_ignored(tmp_path):
    s = _store(tmp_path)
    first = _valid_run_json("run-multiline")
    (s.base_dir / "run-multiline.jsonl").write_text(
        first + "\n" + "{corrupt\n" * 10, encoding="utf-8"
    )
    result = s.load("run-multiline")
    assert result is not None
    assert result.id == "run-multiline"


# ── 7. Null bytes embedded ────────────────────────────────────────────────────


def test_null_bytes_does_not_raise(tmp_path):
    s = _store(tmp_path)
    (s.base_dir / "run-null.jsonl").write_bytes(b'{"id":"run-null\x00","status":"ok"}\n')
    try:
        s.load("run-null")  # None or partial — must not raise
    except Exception as exc:
        pytest.fail(f"load() raised on null bytes: {exc}")


# ── 8. Path-traversal run_id does not escape base_dir ────────────────────────


@pytest.mark.parametrize(
    "suspicious",
    [
        "../../../etc/passwd",
        "run\x00id",
        "." * 200,
    ],
)
def test_path_traversal_run_id_safe(suspicious, tmp_path):
    s = _store(tmp_path)
    try:
        result = s.load(suspicious)
        assert result is None
    except Exception as exc:
        pytest.fail(f"load raised: {exc}")


# ── 9. Valid header + corrupt appended events → header still loads ────────────


def test_valid_header_with_appended_garbage(tmp_path):
    s = _store(tmp_path)
    first = _valid_run_json("run-appended")
    (s.base_dir / "run-appended.jsonl").write_text(
        first + "\n" + "not json\n" * 50, encoding="utf-8"
    )
    result = s.load("run-appended")
    assert result is not None
    assert result.id == "run-appended"


# ── 10. Concurrent save + load race ──────────────────────────────────────────


def test_concurrent_save_load_no_raise(tmp_path):
    from datetime import datetime, timezone
    from agent_runtime_cockpit.protocol.schemas import RunRecord, RunStatus

    s = _store(tmp_path)
    run_id = "run-race"
    errors: list[Exception] = []
    now = datetime.now(timezone.utc).isoformat()

    def saver():
        try:
            for _ in range(15):
                r = RunRecord(
                    id=run_id,
                    workflow_id="wf-1",
                    runtime="fake",
                    status=RunStatus.COMPLETED,
                    started_at=now,
                    events=[],
                )
                s.save(r)
        except Exception as e:
            errors.append(e)

    def loader():
        try:
            for _ in range(15):
                s.load(run_id)  # may return None mid-write
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=saver), threading.Thread(target=loader)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"Race errors: {errors}"
