"""Audit-log retention & rotation for ARC Mobile Runtime (Phase 12).

Deterministic retention for the JSONL decisions audit log (e.g. ``mobile_decisions.jsonl``
written by policy._log_decision, where each line carries a ``logged_at`` ISO timestamp).
Prunes by age (TTL) and/or by count (keep newest N), and can rotate the file when it grows
past a byte cap. Pure file/JSON work — no network. ``now`` is injectable for determinism.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(entry: dict[str, Any]) -> datetime | None:
    raw = entry.get("logged_at") or entry.get("timestamp")
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _read_lines(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # skip corrupt lines
    return out


def _write_lines(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(e, sort_keys=True) + "\n" for e in entries), encoding="utf-8"
    )


def apply_retention(
    path: str | Path,
    *,
    max_age_seconds: int | None = None,
    max_entries: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Prune the JSONL audit log by age and/or count (keeping the newest). Returns a summary."""
    path = Path(path)
    now = now or _now()
    entries = _read_lines(path)
    before = len(entries)

    if max_age_seconds is not None:
        kept = []
        for e in entries:
            ts = _parse_ts(e)
            # entries with no/unparseable timestamp are kept (cannot prove they're stale)
            if ts is None or (now - ts).total_seconds() <= max_age_seconds:
                kept.append(e)
        entries = kept

    if max_entries is not None and len(entries) > max_entries:
        entries = entries[-max_entries:]  # newest N (append-only log → tail is newest)

    _write_lines(path, entries)
    return {"before": before, "after": len(entries), "removed": before - len(entries)}


def rotate_if_oversized(path: str | Path, max_bytes: int) -> bool:
    """Rotate ``path`` to ``path.1`` when it exceeds ``max_bytes``. Returns True if rotated."""
    path = Path(path)
    if not path.exists() or path.stat().st_size <= max_bytes:
        return False
    rotated = path.with_suffix(path.suffix + ".1")
    if rotated.exists():
        rotated.unlink()
    path.rename(rotated)
    path.write_text("", encoding="utf-8")
    return True
