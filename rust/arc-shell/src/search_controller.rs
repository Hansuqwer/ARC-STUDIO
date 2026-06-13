//! Framework-free workspace search controller for M6.
//!
//! Owns an `arc-index::SearchIndex`, exposes deterministic query/result state,
//! and returns file-open effects for the editor controller.

use arc_index::search::IndexError;
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
                SearchRowVm {
                    label: hit.path,
                    path,
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
