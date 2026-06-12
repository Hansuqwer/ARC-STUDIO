//! SQLite metadata/symbol cache (plan §3.7 schema, verbatim) — rusqlite
//! bundled, WAL mode per review §13/Sprint-5 delta.

use rusqlite::{params, Connection};
use std::path::Path;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Symbol {
    pub path: String,
    pub name: String,
    pub kind: String,
    pub line: u32,
    pub col: u32,
}

#[derive(Debug, thiserror::Error)]
pub enum StoreError {
    #[error("sqlite: {0}")]
    Sqlite(#[from] rusqlite::Error),
}

pub struct SymbolStore {
    conn: Connection,
}

impl SymbolStore {
    /// Open (or create) the cache DB. WAL journal mode (review §13 delta).
    /// Corruption policy mirrors the search index: a DB that fails to open
    /// or migrate is deleted and recreated — rebuild, never crash.
    pub fn open_or_rebuild(db_path: &Path) -> Result<(Self, bool), StoreError> {
        match Self::try_open(db_path) {
            Ok(s) => Ok((s, false)),
            Err(_) => {
                let _ = std::fs::remove_file(db_path);
                // WAL sidecar files too
                let _ = std::fs::remove_file(db_path.with_extension("db-wal"));
                let _ = std::fs::remove_file(db_path.with_extension("db-shm"));
                Ok((Self::try_open(db_path)?, true))
            }
        }
    }

    fn try_open(db_path: &Path) -> Result<Self, StoreError> {
        let conn = Connection::open(db_path)?;
        conn.pragma_update(None, "journal_mode", "WAL")?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS files(
                path  TEXT PRIMARY KEY,
                mtime INTEGER,
                size  INTEGER,
                lang  TEXT
            );
            CREATE TABLE IF NOT EXISTS symbols(
                path TEXT,
                name TEXT,
                kind TEXT,
                line INTEGER,
                col  INTEGER
            );
            CREATE INDEX IF NOT EXISTS symbols_name ON symbols(name);",
        )?;
        // sanity probe: a corrupt DB often opens but fails on first query
        conn.query_row("SELECT count(*) FROM files", [], |r| r.get::<_, i64>(0))?;
        Ok(Self { conn })
    }

    pub fn record_file(
        &self,
        path: &str,
        mtime: i64,
        size: i64,
        lang: &str,
    ) -> Result<(), StoreError> {
        self.conn.execute(
            "INSERT INTO files(path, mtime, size, lang) VALUES (?1, ?2, ?3, ?4)
             ON CONFLICT(path) DO UPDATE SET mtime=?2, size=?3, lang=?4",
            params![path, mtime, size, lang],
        )?;
        Ok(())
    }

    /// True when the recorded mtime/size differ (file needs re-index).
    pub fn is_stale(&self, path: &str, mtime: i64, size: i64) -> Result<bool, StoreError> {
        let row: Option<(i64, i64)> = self
            .conn
            .query_row(
                "SELECT mtime, size FROM files WHERE path = ?1",
                params![path],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .map(Some)
            .or_else(|e| match e {
                rusqlite::Error::QueryReturnedNoRows => Ok(None),
                other => Err(other),
            })?;
        Ok(match row {
            None => true,
            Some((m, s)) => m != mtime || s != size,
        })
    }

    /// Replace a file's symbols atomically (delete + insert in one tx).
    pub fn replace_symbols(&mut self, path: &str, symbols: &[Symbol]) -> Result<(), StoreError> {
        let tx = self.conn.transaction()?;
        tx.execute("DELETE FROM symbols WHERE path = ?1", params![path])?;
        {
            let mut stmt = tx.prepare(
                "INSERT INTO symbols(path, name, kind, line, col) VALUES (?1, ?2, ?3, ?4, ?5)",
            )?;
            for s in symbols {
                stmt.execute(params![s.path, s.name, s.kind, s.line, s.col])?;
            }
        }
        tx.commit()?;
        Ok(())
    }

    /// Name-prefix lookup (the "Symbols" sidebar / palette feed).
    pub fn find_by_prefix(&self, prefix: &str, limit: usize) -> Result<Vec<Symbol>, StoreError> {
        let mut stmt = self.conn.prepare(
            "SELECT path, name, kind, line, col FROM symbols
             WHERE name LIKE ?1 || '%' ORDER BY name LIMIT ?2",
        )?;
        let rows = stmt.query_map(params![prefix, limit as i64], |r| {
            Ok(Symbol {
                path: r.get(0)?,
                name: r.get(1)?,
                kind: r.get(2)?,
                line: r.get(3)?,
                col: r.get(4)?,
            })
        })?;
        Ok(rows.collect::<Result<Vec<_>, _>>()?)
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    fn sym(path: &str, name: &str, line: u32) -> Symbol {
        Symbol {
            path: path.into(),
            name: name.into(),
            kind: "fn".into(),
            line,
            col: 0,
        }
    }

    #[test]
    fn wal_mode_and_schema() {
        let td = tempfile::tempdir().unwrap();
        let (store, rebuilt) = SymbolStore::open_or_rebuild(&td.path().join("cache.db")).unwrap();
        assert!(!rebuilt);
        let mode: String = store
            .conn
            .query_row("PRAGMA journal_mode", [], |r| r.get(0))
            .unwrap();
        assert_eq!(mode, "wal");
    }

    #[test]
    fn staleness_tracking() {
        let td = tempfile::tempdir().unwrap();
        let (store, _) = SymbolStore::open_or_rebuild(&td.path().join("c.db")).unwrap();
        assert!(
            store.is_stale("a.rs", 100, 10).unwrap(),
            "unknown file is stale"
        );
        store.record_file("a.rs", 100, 10, "rust").unwrap();
        assert!(!store.is_stale("a.rs", 100, 10).unwrap());
        assert!(store.is_stale("a.rs", 101, 10).unwrap(), "mtime change");
        assert!(store.is_stale("a.rs", 100, 11).unwrap(), "size change");
    }

    #[test]
    fn symbol_replace_is_atomic_and_prefix_lookup_sorted() {
        let td = tempfile::tempdir().unwrap();
        let (mut store, _) = SymbolStore::open_or_rebuild(&td.path().join("c.db")).unwrap();
        store
            .replace_symbols(
                "a.rs",
                &[sym("a.rs", "render", 5), sym("a.rs", "rebuild", 9)],
            )
            .unwrap();
        store
            .replace_symbols("b.rs", &[sym("b.rs", "redact", 1)])
            .unwrap();

        let hits = store.find_by_prefix("re", 10).unwrap();
        let names: Vec<&str> = hits.iter().map(|s| s.name.as_str()).collect();
        assert_eq!(names, vec!["rebuild", "redact", "render"]);

        // replace removes old symbols for the path
        store
            .replace_symbols("a.rs", &[sym("a.rs", "renamed", 7)])
            .unwrap();
        let names: Vec<String> = store
            .find_by_prefix("re", 10)
            .unwrap()
            .iter()
            .map(|s| s.name.clone())
            .collect();
        assert!(!names.contains(&"render".to_string()));
        assert!(names.contains(&"renamed".to_string()));
    }

    #[test]
    fn corrupt_db_rebuilds_never_crashes() {
        let td = tempfile::tempdir().unwrap();
        let db = td.path().join("c.db");
        std::fs::write(&db, b"this is not a sqlite database at all").unwrap();
        let (store, rebuilt) = SymbolStore::open_or_rebuild(&db).unwrap();
        assert!(rebuilt, "corruption triggered rebuild");
        store.record_file("x.rs", 1, 1, "rust").unwrap();
    }
}
