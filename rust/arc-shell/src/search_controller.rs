//! Framework-free workspace search controller for M6.
//!
//! Owns an `arc-index::SearchIndex`, exposes deterministic query/result state,
//! and returns file-open effects for the editor controller.

use arc_index::search::{redact_for_index, IndexError};
use arc_index::{RebuildOutcome, SearchIndex};
use std::path::{Path, PathBuf};

#[derive(Debug, thiserror::Error)]
pub enum SearchControllerError {
    #[error("index: {0}")]
    Index(#[from] IndexError),
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
    #[error("search index is not open")]
    NotOpen,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SearchRowVm {
    pub path: PathBuf,
    pub label: String,
    pub line_number: Option<usize>,
    pub snippet: Option<String>,
    pub selected: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SearchEffect {
    None,
    OpenFile(PathBuf),
}

pub struct SearchController {
    root: PathBuf,
    index_dir: PathBuf,
    index: Option<SearchIndex>,
    query: String,
    rows: Vec<SearchRowVm>,
    selected: usize,
    last_rebuild: Option<RebuildOutcome>,
}

impl SearchController {
    pub fn open(
        root: impl Into<PathBuf>,
        index_dir: impl Into<PathBuf>,
    ) -> Result<Self, SearchControllerError> {
        let root = root.into();
        let index_dir = index_dir.into();
        let (index, outcome) = SearchIndex::open_or_rebuild(&index_dir)?;
        Ok(Self {
            root,
            index_dir,
            index: Some(index),
            query: String::new(),
            rows: Vec::new(),
            selected: 0,
            last_rebuild: Some(outcome),
        })
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    pub fn index_dir(&self) -> &Path {
        &self.index_dir
    }

    pub fn query(&self) -> &str {
        &self.query
    }

    pub fn rows(&self) -> &[SearchRowVm] {
        &self.rows
    }

    pub fn selected_index(&self) -> usize {
        self.selected
    }

    pub fn last_rebuild(&self) -> Option<&RebuildOutcome> {
        self.last_rebuild.as_ref()
    }

    pub fn rebuild(&mut self) -> Result<(), SearchControllerError> {
        let index = self.index.take().ok_or(SearchControllerError::NotOpen)?;
        let (rebuilt, outcome) = index.rebuild()?;
        self.index = Some(rebuilt);
        self.last_rebuild = Some(outcome);
        self.rows.clear();
        self.selected = 0;
        Ok(())
    }

    /// Walk the workspace root and upsert all text files into the index.
    /// Skips hidden dirs, binary files, and files larger than 512 KB.
    /// Best-effort: individual file errors are silently skipped.
    pub fn index_workspace(&mut self) {
        let root = self.root.clone();
        self.walk_and_index(&root);
        let _ = self.index.as_mut().map(|idx| idx.commit());
    }

    fn walk_and_index(&mut self, dir: &std::path::Path) {
        let Ok(entries) = std::fs::read_dir(dir) else {
            return;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            let name = entry.file_name();
            let name_str = name.to_string_lossy();
            // Skip hidden dirs/files and common non-text dirs.
            if name_str.starts_with('.') {
                continue;
            }
            if matches!(
                name_str.as_ref(),
                "node_modules" | "target" | "dist" | "build" | ".git"
            ) {
                continue;
            }
            if path.is_dir() {
                self.walk_and_index(&path);
            } else if path.is_file() {
                // Skip large files.
                if path.metadata().map(|m| m.len()).unwrap_or(0) > 512 * 1024 {
                    continue;
                }
                let Ok(body) = std::fs::read_to_string(&path) else {
                    continue; // binary or unreadable
                };
                let rel = path
                    .strip_prefix(&self.root)
                    .unwrap_or(&path)
                    .to_string_lossy()
                    .to_string();
                let Some(idx) = self.index.as_mut() else {
                    continue;
                };
                let _ = idx.upsert(&rel, &body);
            }
        }
    }

    pub fn upsert_file(&mut self, path: impl AsRef<Path>) -> Result<(), SearchControllerError> {
        let path = path.as_ref();
        let body = std::fs::read_to_string(path)?;
        let rel = path
            .strip_prefix(&self.root)
            .unwrap_or(path)
            .to_string_lossy()
            .to_string();
        let index = self.index.as_mut().ok_or(SearchControllerError::NotOpen)?;
        index.upsert(&rel, &body)?;
        index.commit()?;
        Ok(())
    }

    pub fn remove_file(&mut self, path: impl AsRef<Path>) -> Result<(), SearchControllerError> {
        let path = path.as_ref();
        let rel = path
            .strip_prefix(&self.root)
            .unwrap_or(path)
            .to_string_lossy()
            .to_string();
        let index = self.index.as_mut().ok_or(SearchControllerError::NotOpen)?;
        index.remove(&rel);
        index.commit()?;
        Ok(())
    }

    pub fn set_query(
        &mut self,
        query: impl Into<String>,
        limit: usize,
    ) -> Result<(), SearchControllerError> {
        self.query = query.into();
        self.rows.clear();
        self.selected = 0;
        if self.query.trim().is_empty() {
            return Ok(());
        }
        let index = self.index.as_ref().ok_or(SearchControllerError::NotOpen)?;
        let hits = index.search(&self.query, limit)?;
        self.rows = hits
            .into_iter()
            .enumerate()
            .map(|(idx, hit)| {
                let path = self.root.join(&hit.path);
                let (line_number, snippet) = snippet_for_query(&path, &self.query);
                SearchRowVm {
                    label: hit.path,
                    path,
                    line_number,
                    snippet,
                    selected: idx == 0,
                }
            })
            .collect();
        Ok(())
    }

    pub fn move_up(&mut self) {
        self.selected = self.selected.saturating_sub(1);
        self.refresh_selected_flags();
    }

    pub fn move_down(&mut self) {
        self.selected = (self.selected + 1).min(self.rows.len().saturating_sub(1));
        self.refresh_selected_flags();
    }

    pub fn activate_selected(&self) -> SearchEffect {
        self.rows
            .get(self.selected)
            .map(|r| SearchEffect::OpenFile(r.path.clone()))
            .unwrap_or(SearchEffect::None)
    }

    fn refresh_selected_flags(&mut self) {
        for (idx, row) in self.rows.iter_mut().enumerate() {
            row.selected = idx == self.selected;
        }
    }
}

fn snippet_for_query(path: &Path, query: &str) -> (Option<usize>, Option<String>) {
    let Ok(body) = std::fs::read_to_string(path) else {
        return (None, None);
    };
    let redacted = redact_for_index(&body);
    let q = query.to_ascii_lowercase();
    for (idx, line) in redacted.lines().enumerate() {
        if line.to_ascii_lowercase().contains(&q) {
            let snippet = line.trim();
            let snippet = if snippet.chars().count() > 120 {
                snippet.chars().take(117).collect::<String>() + "..."
            } else {
                snippet.to_string()
            };
            return (Some(idx + 1), Some(snippet));
        }
    }
    (None, None)
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    fn fixture() -> (PathBuf, SearchController) {
        use std::sync::atomic::{AtomicU32, Ordering};
        static COUNTER: AtomicU32 = AtomicU32::new(0);
        let id = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "arc-search-controller-{}-{}",
            std::process::id(),
            id
        ));
        let _ = std::fs::remove_dir_all(&root);
        std::fs::create_dir_all(root.join("src")).unwrap();
        std::fs::write(root.join("src/a.rs"), "fn alpha() { unique_alpha }").unwrap();
        std::fs::write(
            root.join("src/b.rs"),
            "fn beta() { API_KEY=hidden\nunique_beta }",
        )
        .unwrap();
        let index_dir = root.join(".arc-index");
        let mut controller = SearchController::open(&root, &index_dir).unwrap();
        controller.upsert_file(root.join("src/a.rs")).unwrap();
        controller.upsert_file(root.join("src/b.rs")).unwrap();
        (root, controller)
    }

    #[test]
    fn search_returns_open_file_effect() {
        let (_root, mut controller) = fixture();
        controller.set_query("unique_alpha", 10).unwrap();
        assert_eq!(controller.rows().len(), 1);
        assert_eq!(controller.rows()[0].line_number, Some(1));
        assert_eq!(
            controller.rows()[0].snippet.as_deref(),
            Some("fn alpha() { unique_alpha }")
        );
        match controller.activate_selected() {
            SearchEffect::OpenFile(path) => assert!(path.ends_with("src/a.rs")),
            other => panic!("expected OpenFile, got {other:?}"),
        }
    }

    #[test]
    fn secret_lines_are_not_found() {
        let (_root, mut controller) = fixture();
        controller.set_query("hidden", 10).unwrap();
        assert!(controller.rows().is_empty());
    }

    #[test]
    fn rebuild_is_explicit_and_clears_rows() {
        let (_root, mut controller) = fixture();
        controller.set_query("unique_alpha", 10).unwrap();
        assert!(!controller.rows().is_empty());
        controller.rebuild().unwrap();
        assert!(controller.rows().is_empty());
        assert!(controller.last_rebuild().is_some());
    }
}
