import json

from agent_runtime_cockpit.notifications.outbox import NotificationOutbox


def test_append_and_read(tmp_path):
    ob = NotificationOutbox(tmp_path / "out.jsonl")
    ob.append({"type": "vote", "value": 1})
    entries = ob.read_all()
    assert len(entries) == 1
    assert entries[0]["type"] == "vote"


def test_gc_removes_old_non_pending(tmp_path):
    ob = NotificationOutbox(tmp_path / "out.jsonl", ttl_days=0)
    ob.append({"type": "vote"})
    entries = ob.read_all()
    entries[0]["ts"] = 0.0
    entries[0]["status"] = "SENT"
    (tmp_path / "out.jsonl").write_text(json.dumps(entries[0]) + "\n")
    removed = ob.gc()
    assert removed == 1
    assert ob.read_all() == []


def test_gc_keeps_pending(tmp_path):
    ob = NotificationOutbox(tmp_path / "out.jsonl", ttl_days=0)
    ob.append({"type": "vote"})
    entries = ob.read_all()
    entries[0]["ts"] = 0.0  # old but PENDING
    (tmp_path / "out.jsonl").write_text(json.dumps(entries[0]) + "\n")
    ob.gc()
    assert len(ob.read_all()) == 1


def test_gc_empty_file(tmp_path):
    ob = NotificationOutbox(tmp_path / "out.jsonl")
    assert ob.gc() == 0
