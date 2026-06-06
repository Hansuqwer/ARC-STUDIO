"""R-OPEN-HARDEN: property-based + failure-injection tests for SQLiteWALStorage."""

from __future__ import annotations

import threading
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from agent_runtime_cockpit.budget.storage import SQLiteWALStorage


def _storage(db_path: Path) -> SQLiteWALStorage:
    return SQLiteWALStorage(db_path)


# ── property: save/load round-trip is exact ──────────────────────────────────


@settings(max_examples=60, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    st.decimals(
        min_value="0", max_value="9999.9999", places=4, allow_nan=False, allow_infinity=False
    )
)
def test_session_round_trip_exact(tmp_path, amount):
    db = tmp_path / f"rt_{abs(hash(str(amount))) % 100000}.db"
    s = _storage(db)
    s.save_session(amount)
    assert s.load_session() == amount


@settings(max_examples=40, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    provider=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_-", min_size=1, max_size=20),
    date=st.dates().map(str),
    amount=st.decimals(
        min_value="0", max_value="999.99", places=4, allow_nan=False, allow_infinity=False
    ),
)
def test_provider_day_round_trip_exact(tmp_path, provider, date, amount):
    db = tmp_path / f"pd_{abs(hash((provider, date, str(amount)))) % 100000}.db"
    s = _storage(db)
    s.save_provider_day(provider, date, amount)
    assert s.load_provider_day(provider, date) == amount


# ── concurrent writes: documented last-writer-wins, no corruption ─────────────


@pytest.mark.parametrize(
    "n_threads,writes_per_thread",
    [
        (2, 15),
        (4, 8),
    ],
)
def test_concurrent_writes_no_corruption(n_threads, writes_per_thread, tmp_path):
    """Concurrent save_session() calls are last-writer-wins (documented limitation).
    No DB corruption, final value is non-negative, readable, and was written by
    some thread. OperationalError('database is locked') is NOT expected — the
    5s busy_timeout absorbs contention; if it occurs that's a genuine regression.
    """
    db = tmp_path / f"concurrent_{n_threads}.db"
    errors: list[Exception] = []
    written: list[Decimal] = []
    lock = threading.Lock()

    def worker(thread_id: int) -> None:
        try:
            s = SQLiteWALStorage(db)
            for i in range(writes_per_thread):
                amount = Decimal(str(thread_id * 100 + i)) / 1000
                s.save_session(amount)
                with lock:
                    written.append(amount)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"Concurrent write errors (busy_timeout should absorb this): {errors}"
    final = SQLiteWALStorage(db).load_session()
    assert final >= Decimal("0")
    assert final in written or final == Decimal("0")


# ── property: reset_session always leaves 0 ──────────────────────────────────


@settings(max_examples=40, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    amounts=st.lists(
        st.decimals(
            min_value="0", max_value="100", places=4, allow_nan=False, allow_infinity=False
        ),
        min_size=1,
        max_size=10,
    )
)
def test_reset_after_writes_is_zero(tmp_path, amounts):
    db = tmp_path / f"reset_{abs(hash(tuple(str(a) for a in amounts))) % 100000}.db"
    s = _storage(db)
    for a in amounts:
        s.save_session(a)
    s.reset_session()
    assert s.load_session() == Decimal("0")


# ── provider_day keys isolated ────────────────────────────────────────────────


def test_provider_day_keys_isolated(tmp_path):
    s = _storage(tmp_path / "isolated.db")
    s.save_provider_day("anthropic", "2026-01-01", Decimal("1.23"))
    s.save_provider_day("openai", "2026-01-01", Decimal("4.56"))
    s.save_provider_day("anthropic", "2026-01-02", Decimal("7.89"))
    assert s.load_provider_day("anthropic", "2026-01-01") == Decimal("1.23")
    assert s.load_provider_day("openai", "2026-01-01") == Decimal("4.56")
    assert s.load_provider_day("anthropic", "2026-01-02") == Decimal("7.89")
    assert s.load_provider_day("gemini", "2026-01-01") == Decimal("0")


# ── WAL crash: committed data survives truncated WAL ─────────────────────────


def test_truncated_wal_committed_data_survives(tmp_path):
    import sqlite3

    db = tmp_path / "wal_crash.db"
    s = SQLiteWALStorage(db)
    s.save_session(Decimal("42.00"))

    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()

    wal = Path(str(db) + "-wal")
    if wal.exists():
        wal.write_bytes(b"")

    s2 = SQLiteWALStorage(db)
    assert s2.load_session() == Decimal("42.00")
