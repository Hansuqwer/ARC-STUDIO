"""Tests: R-PERF5 — SQLite WAL + wal_autocheckpoint on all stores."""

from __future__ import annotations


def test_sqlite_store_uses_wal(tmp_path):
    from agent_runtime_cockpit.storage.sqlite import SqliteStore

    store = SqliteStore(tmp_path / "runs.db")
    store.init_db()
    with store._conn() as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        chk = conn.execute("PRAGMA wal_autocheckpoint").fetchone()[0]
    assert mode == "wal"
    assert chk == 1000


def test_task_storage_uses_wal(tmp_path):
    from agent_runtime_cockpit.tasks.storage import TaskStorage

    store = TaskStorage(tmp_path / "tasks.db")
    store.init_db()
    with store._conn() as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        chk = conn.execute("PRAGMA wal_autocheckpoint").fetchone()[0]
    assert mode == "wal"
    assert chk == 1000


def test_battle_store_uses_wal(tmp_path):
    from agent_runtime_cockpit.battle.store import BattleStore

    store = BattleStore(tmp_path / "battle.db")
    store.init_db()
    with store._conn() as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        chk = conn.execute("PRAGMA wal_autocheckpoint").fetchone()[0]
    assert mode == "wal"
    assert chk == 1000
