//! Worktree model — sorted, ignore-aware, incrementally updatable.
//!
//! Rules:
//! - directories before files, both lexicographic (stable render order);
//! - default ignores mirror the workspace-snapshot exclusion list (target/,
//!   node_modules/, __pycache__/, .git/ …) plus `.gitignore`-style additions
//!   are a Sprint-5 follow-up (the `ignored` hook is the single seam);
//! - incremental updates go through ONE path (`apply_change`) used by both
//!   the live watcher and the deterministic tests — same oracle pattern as
//!   the event panels.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NodeKind {
    Dir,
    File,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FileNode {
    pub name: String,
    pub kind: NodeKind,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ChangeKind {
    CreatedFile,
    CreatedDir,
    Removed,
    /// Content modified (tree shape unchanged; index layer cares, tree may
    /// surface a dirty badge later).
    Modified,
}

/// Directory-keyed model: each known directory maps to its sorted children.
/// Flat map (not a recursive struct) keeps incremental updates O(log n) and
/// renders trivially as an expandable tree.
pub struct WorktreeModel {
    root: PathBuf,
    dirs: BTreeMap<PathBuf, Vec<FileNode>>,
    ignored_dirs: Vec<&'static str>,
}

/// Default ignored directory names — mirrors the repo's snapshot exclusions.
pub const DEFAULT_IGNORED: &[&str] = &[
    ".git",
    "target",
    "node_modules",
    "__pycache__",
    ".venv",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
];

impl WorktreeModel {
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self {
            root: root.into(),
            dirs: BTreeMap::new(),
            ignored_dirs: DEFAULT_IGNORED.to_vec(),
        }
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    fn ignored(&self, name: &str) -> bool {
        self.ignored_dirs.contains(&name)
    }

    /// Full scan (initial load or explicit rebuild — rebuild is a command,
    /// never a side effect, per ADR-0005).
    pub fn scan(&mut self) -> std::io::Result<usize> {
        self.dirs.clear();
        let root = self.root.clone();
        let mut stack = vec![root];
        let mut count = 0usize;
        while let Some(dir) = stack.pop() {
            let mut children = Vec::new();
            for entry in std::fs::read_dir(&dir)? {
                let entry = entry?;
                let name = entry.file_name().to_string_lossy().to_string();
                let is_dir = entry.file_type()?.is_dir();
                if is_dir && self.ignored(&name) {
                    continue;
                }
                if is_dir {
                    stack.push(entry.path());
                    children.push(FileNode {
                        name,
                        kind: NodeKind::Dir,
                    });
                } else {
                    children.push(FileNode {
                        name,
                        kind: NodeKind::File,
                    });
                }
                count += 1;
            }
            Self::sort(&mut children);
            self.dirs.insert(dir, children);
        }
        Ok(count)
    }

    fn sort(children: &mut [FileNode]) {
        children.sort_by(|a, b| match (a.kind, b.kind) {
            (NodeKind::Dir, NodeKind::File) => std::cmp::Ordering::Less,
            (NodeKind::File, NodeKind::Dir) => std::cmp::Ordering::Greater,
            _ => a.name.cmp(&b.name),
        });
    }

    /// Sorted children of a directory (None = not scanned / not a dir).
    pub fn children(&self, dir: &Path) -> Option<&[FileNode]> {
        self.dirs.get(dir).map(Vec::as_slice)
    }

    pub fn dir_count(&self) -> usize {
        self.dirs.len()
    }

    /// THE single incremental-update path (watcher + tests both call this).
    pub fn apply_change(&mut self, path: &Path, kind: ChangeKind) {
        let Some(parent) = path.parent().map(Path::to_path_buf) else {
            return;
        };
        let Some(name) = path.file_name().map(|n| n.to_string_lossy().to_string()) else {
            return;
        };
        if self.ignored(&name) {
            return;
        }
        match kind {
            ChangeKind::CreatedFile | ChangeKind::CreatedDir => {
                let node_kind = if kind == ChangeKind::CreatedDir {
                    NodeKind::Dir
                } else {
                    NodeKind::File
                };
                if node_kind == NodeKind::Dir {
                    self.dirs.entry(path.to_path_buf()).or_default();
                }
                if let Some(children) = self.dirs.get_mut(&parent) {
                    if !children.iter().any(|c| c.name == name) {
                        children.push(FileNode {
                            name,
                            kind: node_kind,
                        });
                        Self::sort(children);
                    }
                }
            }
            ChangeKind::Removed => {
                self.dirs.remove(path);
                // prune any nested dirs under the removed path
                let prefix = path.to_path_buf();
                let nested: Vec<PathBuf> = self
                    .dirs
                    .keys()
                    .filter(|d| d.starts_with(&prefix))
                    .cloned()
                    .collect();
                for d in nested {
                    self.dirs.remove(&d);
                }
                if let Some(children) = self.dirs.get_mut(&parent) {
                    children.retain(|c| c.name != name);
                }
            }
            ChangeKind::Modified => { /* tree shape unchanged */ }
        }
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    fn fixture_tree() -> (tempfile::TempDir, WorktreeModel) {
        let td = tempfile::tempdir().unwrap();
        let r = td.path();
        std::fs::create_dir_all(r.join("src/sub")).unwrap();
        std::fs::create_dir_all(r.join("docs")).unwrap();
        std::fs::create_dir_all(r.join("target/debug")).unwrap(); // ignored
        std::fs::create_dir_all(r.join(".git")).unwrap(); // ignored
        std::fs::write(r.join("README.md"), "x").unwrap();
        std::fs::write(r.join("src/main.rs"), "x").unwrap();
        std::fs::write(r.join("src/sub/a.rs"), "x").unwrap();
        std::fs::write(r.join("docs/guide.md"), "x").unwrap();
        let mut m = WorktreeModel::new(r);
        m.scan().unwrap();
        (td, m)
    }

    #[test]
    fn scan_ignores_excluded_dirs_and_sorts_dirs_first() {
        let (_td, m) = fixture_tree();
        let root_children = m.children(m.root()).unwrap();
        let names: Vec<&str> = root_children.iter().map(|c| c.name.as_str()).collect();
        assert_eq!(
            names,
            vec!["docs", "src", "README.md"],
            "dirs first, sorted; ignored absent"
        );
        assert!(
            m.children(&m.root().join("target")).is_none(),
            "ignored dir not scanned"
        );
    }

    #[test]
    fn incremental_create_inserts_sorted_no_duplicates() {
        let (_td, mut m) = fixture_tree();
        let root = m.root().to_path_buf();
        m.apply_change(&root.join("AUTHORS"), ChangeKind::CreatedFile);
        m.apply_change(&root.join("AUTHORS"), ChangeKind::CreatedFile); // dup event (debouncer artifacts)
        let names: Vec<&str> = m
            .children(&root)
            .unwrap()
            .iter()
            .map(|c| c.name.as_str())
            .collect();
        assert_eq!(names, vec!["docs", "src", "AUTHORS", "README.md"]);
    }

    #[test]
    fn incremental_dir_create_then_remove_prunes_nested() {
        let (_td, mut m) = fixture_tree();
        let root = m.root().to_path_buf();
        m.apply_change(&root.join("new"), ChangeKind::CreatedDir);
        m.apply_change(&root.join("new/deep.rs"), ChangeKind::CreatedFile);
        assert!(m.children(&root.join("new")).is_some());

        m.apply_change(&root.join("src"), ChangeKind::Removed);
        assert!(m.children(&root.join("src")).is_none());
        assert!(m.children(&root.join("src/sub")).is_none(), "nested pruned");
        let names: Vec<&str> = m
            .children(&root)
            .unwrap()
            .iter()
            .map(|c| c.name.as_str())
            .collect();
        assert!(!names.contains(&"src"));
    }

    #[test]
    fn ignored_names_never_enter_via_watcher_path_either() {
        let (_td, mut m) = fixture_tree();
        let root = m.root().to_path_buf();
        m.apply_change(&root.join("node_modules"), ChangeKind::CreatedDir);
        let names: Vec<&str> = m
            .children(&root)
            .unwrap()
            .iter()
            .map(|c| c.name.as_str())
            .collect();
        assert!(!names.contains(&"node_modules"));
    }
}
