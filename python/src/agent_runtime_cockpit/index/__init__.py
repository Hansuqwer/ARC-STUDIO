"""ARC Index — local SQLite-backed codebase index (R84).

Provides:
  CodebaseIndex  — scan workspace files, extract symbols, store in SQLite
  IndexSearchResult — result dataclass
  build_index()  — scan and populate
  search_index() — top-k keyword/path search

Schema: codebase_index v1
  ~/.arc/index/{workspace_hash}/index.db

Design:
  - No heavy ML / vector embeddings. Pure keyword + path matching.
  - Fast enough for < 10s build on 100K files (file metadata only).
  - Symbol extraction: Python identifiers via regex (no AST for speed).
  - Search: SQLite FTS5 full-text search over path + symbols + content_preview.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

log = logging.getLogger(__name__)

_SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA wal_autocheckpoint = 1000;

CREATE TABLE IF NOT EXISTS index_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    path            TEXT NOT NULL UNIQUE,
    size_bytes      INTEGER,
    last_modified   REAL,
    language        TEXT,
    symbol_count    INTEGER DEFAULT 0,
    indexed_at      REAL NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
    path,
    symbols,
    content_preview
);

CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);
"""

# Languages to index (extension → language name)
_LANG_MAP = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".sh": "shell",
    ".bash": "shell",
}

# Max files to index; guard against pathologically large repos
_MAX_FILES = 100_000
MAX_INCREMENTAL_BATCH = 1000
DEFAULT_CHANGE_SCAN_TIMEOUT_S = 5.0
_PREVIEW_CHARS = 200
_SYMBOL_RE = re.compile(r"\b(def |class |function |fn |func |pub fn |async fn )(\w+)")


class IndexError(Exception):
    """Raised for structured codebase-index failures."""


@dataclass(frozen=True)
class IndexSearchResult:
    path: str
    language: str
    score: float
    symbols_preview: str
    content_preview: str


@dataclass(frozen=True)
class IndexBuildResult:
    file_count: int
    skipped: int
    elapsed_ms: float
    errors: list[str]
    state: str

    def to_dict(self) -> dict[str, object]:
        return {
            "indexed": self.file_count,
            "file_count": self.file_count,
            "skipped": self.skipped,
            "elapsed_s": round(self.elapsed_ms / 1000, 2),
            "elapsed_ms": self.elapsed_ms,
            "errors": self.errors,
            "state": self.state,
        }


@dataclass(frozen=True)
class IncrementalUpdateResult:
    files_added: int
    files_updated: int
    files_removed: int
    elapsed_ms: float
    errors: list[str]
    state: str = "success"

    def to_dict(self) -> dict[str, object]:
        updated = self.files_added + self.files_updated
        return {
            "updated": updated,
            "removed": self.files_removed,
            "elapsed_s": round(self.elapsed_ms / 1000, 3),
            "files_added": self.files_added,
            "files_updated": self.files_updated,
            "files_removed": self.files_removed,
            "elapsed_ms": self.elapsed_ms,
            "errors": self.errors,
            "state": self.state,
        }


def _workspace_hash(workspace: Path) -> str:
    return hashlib.sha256(str(workspace.resolve()).encode()).hexdigest()[:16]


def _get_index_path(workspace: Path) -> Path:
    override = os.environ.get("ARC_INDEX_DIR")
    base = Path(override).expanduser() if override else Path.home() / ".arc" / "index"
    idx_dir = base / _workspace_hash(workspace)
    idx_dir.mkdir(parents=True, exist_ok=True)
    return idx_dir / "index.db"


def _extract_symbols(text: str) -> str:
    """Extract top-50 symbol names from source text."""
    matches = _SYMBOL_RE.findall(text[:8192])
    names = [m[1] for m in matches]
    return " ".join(names[:50])


def _iter_files(workspace: Path, extensions: frozenset[str]) -> Iterator[Path]:
    """Yield workspace files matching extensions, skipping common noise dirs."""
    skip_dirs = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".cache",
        "dist",
        "build",
        "lib",
        ".arc",
    }
    count = 0
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            if Path(fname).suffix in extensions:
                yield Path(root) / fname
                count += 1
                if count >= _MAX_FILES:
                    log.warning("Index: reached %d file limit", _MAX_FILES)
                    return


class CodebaseIndex:
    """SQLite-backed codebase index for a workspace."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.db_path = _get_index_path(self.workspace)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_SCHEMA)

    def build(
        self,
        extensions: frozenset[str] | None = None,
        *,
        progress_callback=None,
    ) -> dict:
        """Scan workspace and populate index. Returns build stats."""
        exts = extensions or frozenset(_LANG_MAP.keys())
        t0 = time.perf_counter()
        indexed = 0
        skipped = 0
        errors: list[str] = []

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            for path in _iter_files(self.workspace, exts):
                try:
                    rel = str(path.relative_to(self.workspace))
                    stat = path.stat()
                    lang = _LANG_MAP.get(path.suffix, "unknown")
                    try:
                        text = path.read_text(encoding="utf-8", errors="ignore")[:16384]
                    except OSError:
                        skipped += 1
                        errors.append(str(path.relative_to(self.workspace)))
                        continue
                    symbols = _extract_symbols(text)
                    preview = text[:_PREVIEW_CHARS].replace("\n", " ")
                    conn.execute(
                        """INSERT INTO files (path, size_bytes, last_modified, language,
                           symbol_count, indexed_at)
                           VALUES (?,?,?,?,?,?)
                           ON CONFLICT(path) DO UPDATE SET
                             size_bytes=excluded.size_bytes,
                             last_modified=excluded.last_modified,
                             language=excluded.language,
                             symbol_count=excluded.symbol_count,
                             indexed_at=excluded.indexed_at""",
                        (rel, stat.st_size, stat.st_mtime, lang, len(symbols.split()), time.time()),
                    )
                    # Update FTS
                    conn.execute("DELETE FROM files_fts WHERE path=?", (rel,))
                    conn.execute(
                        "INSERT INTO files_fts(path, symbols, content_preview) VALUES (?,?,?)",
                        (rel, symbols, preview),
                    )
                    indexed += 1
                    if progress_callback:
                        progress_callback(indexed)
                except Exception as exc:
                    log.debug("Index skip %s: %s", path, exc)
                    skipped += 1
                    errors.append(f"{path}: {exc}")
            conn.execute(
                "INSERT OR REPLACE INTO index_meta (key,value) VALUES (?,?)",
                ("last_built", str(time.time())),
            )

        elapsed = time.perf_counter() - t0
        return IndexBuildResult(
            file_count=indexed,
            skipped=skipped,
            elapsed_ms=round(elapsed * 1000, 3),
            errors=errors,
            state="empty" if indexed == 0 else "success",
        ).to_dict()

    def search(self, query: str, limit: int = 10) -> list[IndexSearchResult]:
        """Top-k keyword/path search using FTS5 + path prefix match."""
        results: list[IndexSearchResult] = []
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            # FTS5 search
            try:
                rows = conn.execute(
                    """SELECT fts.path,
                              COALESCE(f.language, 'unknown'),
                              bm25(files_fts) AS score,
                              fts.symbols, fts.content_preview
                       FROM files_fts fts
                       LEFT JOIN files f ON f.path = fts.path
                       WHERE files_fts MATCH ?
                       ORDER BY score
                       LIMIT ?""",
                    (query, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []

            # Fallback: path LIKE search
            if not rows:
                like = f"%{query}%"
                rows = conn.execute(
                    """SELECT f.path, f.language, 0.0, '', ''
                       FROM files f
                       WHERE f.path LIKE ?
                       LIMIT ?""",
                    (like, limit),
                ).fetchall()

        for path, lang, score, symbols, preview in rows:
            results.append(
                IndexSearchResult(
                    path=path,
                    language=lang or "unknown",
                    score=float(score),
                    symbols_preview=symbols[:100],
                    content_preview=preview[:100],
                )
            )
        return results

    def stats(self) -> dict:
        """Return index statistics."""
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            last = conn.execute("SELECT value FROM index_meta WHERE key='last_built'").fetchone()
        return {
            "file_count": count,
            "last_built": float(last[0]) if last else None,
            "db_path": str(self.db_path),
        }

    def update_file(self, path: Path, extensions: frozenset[str] | None = None) -> bool:
        """Incrementally update a single file in the index. Returns True if indexed."""
        exts = extensions or frozenset(_LANG_MAP.keys())
        if path.suffix not in exts:
            return False

        try:
            rel = str(path.relative_to(self.workspace))
            stat = path.stat()
            lang = _LANG_MAP.get(path.suffix, "unknown")
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:16384]
            except OSError:
                return False
            symbols = _extract_symbols(text)
            preview = text[:_PREVIEW_CHARS].replace("\n", " ")

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute(
                    """INSERT INTO files (path, size_bytes, last_modified, language,
                       symbol_count, indexed_at)
                       VALUES (?,?,?,?,?,?)
                       ON CONFLICT(path) DO UPDATE SET
                         size_bytes=excluded.size_bytes,
                         last_modified=excluded.last_modified,
                         language=excluded.language,
                         symbol_count=excluded.symbol_count,
                         indexed_at=excluded.indexed_at""",
                    (rel, stat.st_size, stat.st_mtime, lang, len(symbols.split()), time.time()),
                )
                conn.execute("DELETE FROM files_fts WHERE path=?", (rel,))
                conn.execute(
                    "INSERT INTO files_fts(path, symbols, content_preview) VALUES (?,?,?)",
                    (rel, symbols, preview),
                )
            return True
        except Exception as exc:
            log.debug("Index update skip %s: %s", path, exc)
            return False

    def remove_file(self, path: Path) -> bool:
        """Remove a single file from the index. Returns True if removed."""
        try:
            rel = str(path.relative_to(self.workspace))
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode = WAL")
                cursor = conn.execute("DELETE FROM files WHERE path=?", (rel,))
                conn.execute("DELETE FROM files_fts WHERE path=?", (rel,))
                return cursor.rowcount > 0
        except Exception as exc:
            log.debug("Index remove skip %s: %s", path, exc)
            return False

    def _indexed_paths(self) -> set[str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT path FROM files").fetchall()
        return {str(row[0]) for row in rows}

    def get_changed_files(
        self, since: float | None = None, *, timeout_s: float = DEFAULT_CHANGE_SCAN_TIMEOUT_S
    ) -> list[Path]:
        """Get files that have changed since the given timestamp (or last index build)."""
        if since is None:
            with sqlite3.connect(self.db_path) as conn:
                last = conn.execute(
                    "SELECT value FROM index_meta WHERE key='last_built'"
                ).fetchone()
                since = float(last[0]) if last else 0.0

        changed = []
        started = time.perf_counter()
        exts = frozenset(_LANG_MAP.keys())
        for path in _iter_files(self.workspace, exts):
            if time.perf_counter() - started > timeout_s:
                break
            try:
                stat = path.stat()
                if stat.st_mtime > since:
                    changed.append(path)
            except OSError:
                continue
        indexed_paths = self._indexed_paths()
        existing_paths = {
            str(path.relative_to(self.workspace)) for path in _iter_files(self.workspace, exts)
        }
        for rel in sorted(indexed_paths - existing_paths):
            changed.append(self.workspace / rel)
        return changed

    def incremental_update(self, extensions: frozenset[str] | None = None) -> dict:
        """Incrementally update only changed files since last build. Returns update stats."""
        exts = extensions or frozenset(_LANG_MAP.keys())
        t0 = time.perf_counter()
        added = 0
        updated = 0
        removed = 0
        errors: list[str] = []

        before = self._indexed_paths()
        changed_files = self.get_changed_files()[:MAX_INCREMENTAL_BATCH]
        for path in changed_files:
            if path.exists():
                try:
                    rel = str(path.relative_to(self.workspace))
                    if self.update_file(path, exts):
                        if rel in before:
                            updated += 1
                        else:
                            added += 1
                except Exception as exc:
                    errors.append(f"{path}: {exc}")
            else:
                if self.remove_file(path):
                    removed += 1

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO index_meta (key,value) VALUES (?,?)",
                ("last_built", str(time.time())),
            )

        elapsed = time.perf_counter() - t0
        state = "degraded" if len(self.get_changed_files()) > MAX_INCREMENTAL_BATCH else "success"
        if state == "degraded":
            errors.append(f"batch capped at {MAX_INCREMENTAL_BATCH} files")
        return IncrementalUpdateResult(
            files_added=added,
            files_updated=updated,
            files_removed=removed,
            elapsed_ms=round(elapsed * 1000, 3),
            errors=errors,
            state=state,
        ).to_dict()


__all__ = [
    "CodebaseIndex",
    "IndexBuildResult",
    "IndexError",
    "IndexSearchResult",
    "IncrementalUpdateResult",
    "MAX_INCREMENTAL_BATCH",
]
