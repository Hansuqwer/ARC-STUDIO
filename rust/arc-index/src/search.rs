//! Tantivy full-text index with corruption-rebuilds semantics and
//! redaction-aware ingestion.

use std::path::{Path, PathBuf};
use tantivy::collector::TopDocs;
use tantivy::query::QueryParser;
use tantivy::schema::{Field, Schema, Value, STORED, STRING, TEXT};
use tantivy::{doc, Index, IndexWriter, TantivyDocument, Term};

#[derive(Debug, thiserror::Error)]
pub enum IndexError {
    #[error("tantivy: {0}")]
    Tantivy(#[from] tantivy::TantivyError),
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
    #[error("query parse: {0}")]
    Query(#[from] tantivy::query::QueryParserError),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SearchHit {
    pub path: String,
}

#[derive(Debug, PartialEq, Eq)]
pub struct RebuildOutcome {
    /// True when the on-disk index was corrupt/missing and was recreated.
    pub rebuilt: bool,
}

/// Secret patterns excluded from indexed bodies (review §9.6). Deliberately
/// simple line-level heuristics — false positives only cost a line of search
/// coverage; false negatives cost a leak. Extended in Sprint 12 hardening.
const SECRET_MARKERS: &[&str] = &[
    "api_key",
    "apikey",
    "secret",
    "password",
    "passwd",
    "token",
    "private_key",
    "BEGIN RSA PRIVATE KEY",
    "BEGIN OPENSSH PRIVATE KEY",
    "AKIA", // AWS access key id prefix
];

/// Strip lines that look secret-bearing before indexing.
pub fn redact_for_index(body: &str) -> String {
    body.lines()
        .filter(|line| {
            let l = line.to_ascii_lowercase();
            !SECRET_MARKERS
                .iter()
                .any(|m| l.contains(&m.to_ascii_lowercase()))
        })
        .collect::<Vec<_>>()
        .join("\n")
}

pub struct SearchIndex {
    index: Index,
    writer: IndexWriter,
    f_path: Field,
    f_body: Field,
    dir: PathBuf,
}

impl SearchIndex {
    fn schema() -> (Schema, Field, Field) {
        let mut b = Schema::builder();
        let f_path = b.add_text_field("path", STRING | STORED);
        let f_body = b.add_text_field("body", TEXT);
        let schema = b.build();
        (schema, f_path, f_body)
    }

    /// Open the index at `dir`; ANY failure (corrupt meta, version drift,
    /// partial files) wipes and recreates — rebuild, never crash (ADR-0005).
    pub fn open_or_rebuild(dir: &Path) -> Result<(Self, RebuildOutcome), IndexError> {
        let (schema, f_path, f_body) = Self::schema();
        let attempt = || -> Result<Index, tantivy::TantivyError> { Index::open_in_dir(dir) };
        let (index, rebuilt) = match attempt() {
            Ok(idx) => (idx, false),
            Err(_) => {
                // corrupt or absent: recreate from scratch
                if dir.exists() {
                    std::fs::remove_dir_all(dir)?;
                }
                std::fs::create_dir_all(dir)?;
                (Index::create_in_dir(dir, schema.clone())?, true)
            }
        };
        let writer = index.writer(50_000_000)?; // 50 MB heap: CI-friendly
        Ok((
            Self {
                index,
                writer,
                f_path,
                f_body,
                dir: dir.to_path_buf(),
            },
            RebuildOutcome { rebuilt },
        ))
    }

    /// Full rebuild as an explicit command (never a side effect).
    pub fn rebuild(self) -> Result<(Self, RebuildOutcome), IndexError> {
        let dir = self.dir.clone();
        drop(self); // release writer lock before wiping
        std::fs::remove_dir_all(&dir)?;
        let (idx, _) = Self::open_or_rebuild(&dir)?;
        Ok((idx, RebuildOutcome { rebuilt: true }))
    }

    /// Upsert one file: delete old doc, add redacted body. Caller commits.
    pub fn upsert(&mut self, path: &str, body: &str) -> Result<(), IndexError> {
        let term = Term::from_field_text(self.f_path, path);
        self.writer.delete_term(term);
        self.writer.add_document(doc!(
            self.f_path => path,
            self.f_body => redact_for_index(body),
        ))?;
        Ok(())
    }

    pub fn remove(&mut self, path: &str) {
        self.writer
            .delete_term(Term::from_field_text(self.f_path, path));
    }

    pub fn commit(&mut self) -> Result<(), IndexError> {
        self.writer.commit()?;
        Ok(())
    }

    pub fn search(&self, query: &str, limit: usize) -> Result<Vec<SearchHit>, IndexError> {
        let reader = self.index.reader()?;
        let searcher = reader.searcher();
        let parser = QueryParser::for_index(&self.index, vec![self.f_body]);
        let q = parser.parse_query(query)?;
        let top = searcher.search(&q, &TopDocs::with_limit(limit.max(1)))?;
        let mut hits = Vec::with_capacity(top.len());
        for (_score, addr) in top {
            let stored: TantivyDocument = searcher.doc(addr)?;
            if let Some(p) = stored.get_first(self.f_path).and_then(|v| v.as_str()) {
                hits.push(SearchHit {
                    path: p.to_string(),
                });
            }
        }
        Ok(hits)
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn index_search_update_delete_roundtrip() {
        let td = tempdir::TempDir::new("arc-idx").unwrap();
        let (mut idx, outcome) = SearchIndex::open_or_rebuild(td.path()).unwrap();
        assert!(outcome.rebuilt, "fresh dir counts as rebuilt");

        idx.upsert("src/a.rs", "fn alpha() { unique_marker_alpha }")
            .unwrap();
        idx.upsert("src/b.rs", "fn beta() { unique_marker_beta }")
            .unwrap();
        idx.commit().unwrap();

        let hits = idx.search("unique_marker_alpha", 10).unwrap();
        assert_eq!(
            hits,
            vec![SearchHit {
                path: "src/a.rs".into()
            }]
        );

        // update replaces, not duplicates
        idx.upsert("src/a.rs", "fn alpha2() { unique_marker_gamma }")
            .unwrap();
        idx.commit().unwrap();
        assert!(idx.search("unique_marker_alpha", 10).unwrap().is_empty());
        assert_eq!(idx.search("unique_marker_gamma", 10).unwrap().len(), 1);

        idx.remove("src/b.rs");
        idx.commit().unwrap();
        assert!(idx.search("unique_marker_beta", 10).unwrap().is_empty());
    }

    /// Review §9.6: plant a fake secret; it must be unfindable via search.
    #[test]
    fn planted_secret_is_not_indexed() {
        let td = tempdir::TempDir::new("arc-idx-secret").unwrap();
        let (mut idx, _) = SearchIndex::open_or_rebuild(td.path()).unwrap();
        let body = "normal code line with findable_needle\n\
                    API_KEY=sk-supersecret12345\n\
                    password = \"hunter2\"\n\
                    more normal code";
        idx.upsert("config/app.conf", body).unwrap();
        idx.commit().unwrap();

        assert_eq!(
            idx.search("findable_needle", 10).unwrap().len(),
            1,
            "normal line indexed"
        );
        assert!(
            idx.search("supersecret12345", 10).unwrap().is_empty(),
            "secret value absent"
        );
        assert!(
            idx.search("hunter2", 10).unwrap().is_empty(),
            "password value absent"
        );
    }

    /// ADR-0005: corruption rebuilds, never crashes.
    #[test]
    fn corrupt_index_dir_rebuilds_never_crashes() {
        let td = tempdir::TempDir::new("arc-idx-corrupt").unwrap();
        // garbage where tantivy expects meta.json
        std::fs::write(td.path().join("meta.json"), "{ not valid tantivy meta").unwrap();
        std::fs::write(td.path().join("junk.bin"), [0u8; 64]).unwrap();

        let (mut idx, outcome) = SearchIndex::open_or_rebuild(td.path()).unwrap();
        assert!(outcome.rebuilt, "corruption triggered rebuild");
        idx.upsert("x.rs", "post_rebuild_marker").unwrap();
        idx.commit().unwrap();
        assert_eq!(idx.search("post_rebuild_marker", 10).unwrap().len(), 1);
    }

    #[test]
    fn explicit_rebuild_is_a_command() {
        let td = tempdir::TempDir::new("arc-idx-cmd").unwrap();
        let (mut idx, _) = SearchIndex::open_or_rebuild(td.path()).unwrap();
        idx.upsert("a.rs", "before_rebuild_marker").unwrap();
        idx.commit().unwrap();

        let (idx2, outcome) = idx.rebuild().unwrap();
        assert!(outcome.rebuilt);
        assert!(
            idx2.search("before_rebuild_marker", 10).unwrap().is_empty(),
            "fresh index"
        );
    }
}
