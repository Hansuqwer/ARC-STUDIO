//! Framework-free workspace tree controller for M6.
//!
//! Wraps `arc-workspace::WorktreeModel` with UI-facing selection, expansion,
//! flattening, and open-file effects. No framework types appear here.

use arc_workspace::{ChangeKind, NodeKind, WorktreeModel};
use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

#[derive(Debug, thiserror::Error)]
pub enum WorkspaceControllerError {
    #[error("workspace io: {0}")]
    Io(#[from] std::io::Error),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkspaceRowVm {
    pub path: PathBuf,
    pub label: String,
    pub depth: usize,
    pub kind: NodeKind,
    pub expanded: bool,
    pub selected: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WorkspaceEffect {
    None,
    OpenFile(PathBuf),
}

pub struct WorkspaceController {
    model: WorktreeModel,
    expanded: BTreeSet<PathBuf>,
    selected: usize,
    opened_file: Option<PathBuf>,
}

impl WorkspaceController {
    pub fn open(root: impl Into<PathBuf>) -> Result<Self, WorkspaceControllerError> {
        let root = root.into();
        let mut model = WorktreeModel::new(&root);
        model.scan()?;
        let mut expanded = BTreeSet::new();
        expanded.insert(root);
        Ok(Self {
            model,
            expanded,
            selected: 0,
            opened_file: None,
        })
    }

    pub fn from_model(model: WorktreeModel) -> Self {
        let mut expanded = BTreeSet::new();
        expanded.insert(model.root().to_path_buf());
        Self {
            model,
            expanded,
            selected: 0,
            opened_file: None,
        }
    }

    pub fn root(&self) -> &Path {
        self.model.root()
    }

    pub fn model(&self) -> &WorktreeModel {
        &self.model
    }

    pub fn selected_index(&self) -> usize {
        self.selected
    }

    pub fn opened_file(&self) -> Option<&Path> {
        self.opened_file.as_deref()
    }

    pub fn selected_row(&self) -> Option<WorkspaceRowVm> {
        self.rows().get(self.selected).cloned()
    }

    pub fn select_path(&mut self, path: &Path) -> bool {
        let rows = self.rows();
        if let Some(idx) = rows.iter().position(|row| row.path == path) {
            self.selected = idx;
            true
        } else {
            false
        }
    }

    pub fn rows(&self) -> Vec<WorkspaceRowVm> {
        let mut out = Vec::new();
        self.push_children(self.model.root(), 0, &mut out);
        out.into_iter()
            .enumerate()
            .map(|(idx, mut row)| {
                row.selected = idx == self.selected;
                row
            })
            .collect()
    }

    pub fn move_up(&mut self) {
        self.selected = self.selected.saturating_sub(1);
    }

    pub fn move_down(&mut self) {
        let max = self.rows().len().saturating_sub(1);
        self.selected = (self.selected + 1).min(max);
    }

    pub fn toggle_selected(&mut self) -> WorkspaceEffect {
        let rows = self.rows();
        let Some(row) = rows.get(self.selected) else {
            return WorkspaceEffect::None;
        };
        match row.kind {
            NodeKind::File => {
                self.opened_file = Some(row.path.clone());
                WorkspaceEffect::OpenFile(row.path.clone())
            }
            NodeKind::Dir => {
                if self.expanded.contains(&row.path) {
                    self.expanded.remove(&row.path);
                } else {
                    self.expanded.insert(row.path.clone());
                }
                let max = self.rows().len().saturating_sub(1);
                self.selected = self.selected.min(max);
                WorkspaceEffect::None
            }
        }
    }

    pub fn apply_change(&mut self, path: &Path, kind: ChangeKind) {
        self.model.apply_change(path, kind);
        if kind == ChangeKind::CreatedDir {
            self.expanded.insert(path.to_path_buf());
        }
        if kind == ChangeKind::Removed {
            let removed = path.to_path_buf();
            self.expanded.retain(|p| !p.starts_with(&removed));
            if self
                .opened_file
                .as_ref()
                .is_some_and(|p| p.starts_with(&removed))
            {
                self.opened_file = None;
            }
        }
        let max = self.rows().len().saturating_sub(1);
        self.selected = self.selected.min(max);
    }

    fn push_children(&self, dir: &Path, depth: usize, out: &mut Vec<WorkspaceRowVm>) {
        let Some(children) = self.model.children(dir) else {
            return;
        };
        for child in children {
            let path = dir.join(&child.name);
            let expanded = child.kind == NodeKind::Dir && self.expanded.contains(&path);
            out.push(WorkspaceRowVm {
                path: path.clone(),
                label: child.name.clone(),
                depth,
                kind: child.kind,
                expanded,
                selected: false,
            });
            if expanded {
                self.push_children(&path, depth + 1, out);
            }
        }
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    fn fixture() -> (PathBuf, WorkspaceController) {
        use std::sync::atomic::{AtomicU32, Ordering};
        static COUNTER: AtomicU32 = AtomicU32::new(0);
        let id = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "arc-workspace-controller-{}-{}",
            std::process::id(),
            id
        ));
        let _ = std::fs::remove_dir_all(&root);
        std::fs::create_dir_all(root.join("src")).unwrap();
        std::fs::create_dir_all(root.join("docs")).unwrap();
        std::fs::write(root.join("README.md"), "readme").unwrap();
        std::fs::write(root.join("src/main.rs"), "fn main() {}").unwrap();
        let controller = WorkspaceController::open(&root).unwrap();
        (root, controller)
    }

    #[test]
    fn rows_are_flattened_dirs_first() {
        let (_root, controller) = fixture();
        let labels: Vec<_> = controller.rows().into_iter().map(|r| r.label).collect();
        assert_eq!(labels, vec!["docs", "src", "README.md"]);
    }

    #[test]
    fn expand_and_open_file_effect() {
        let (_root, mut controller) = fixture();
        controller.move_down(); // src
        assert_eq!(controller.rows()[1].label, "src");
        assert_eq!(controller.toggle_selected(), WorkspaceEffect::None);
        let labels: Vec<_> = controller.rows().into_iter().map(|r| r.label).collect();
        assert!(labels.contains(&"main.rs".to_string()));
        controller.move_down(); // main.rs
        match controller.toggle_selected() {
            WorkspaceEffect::OpenFile(path) => assert!(path.ends_with("src/main.rs")),
            other => panic!("expected open file, got {other:?}"),
        }
        assert!(controller.opened_file().unwrap().ends_with("src/main.rs"));
    }

    #[test]
    fn select_path_marks_existing_row() {
        let (root, mut controller) = fixture();
        controller.move_down();
        controller.toggle_selected(); // expand src
        assert!(controller.select_path(&root.join("src/main.rs")));
        assert_eq!(controller.selected_row().unwrap().label, "main.rs");
    }

    #[test]
    fn apply_change_updates_rows_and_clamps_selection() {
        let (root, mut controller) = fixture();
        controller.apply_change(&root.join("AUTHORS"), ChangeKind::CreatedFile);
        assert!(controller.rows().iter().any(|r| r.label == "AUTHORS"));
        controller.apply_change(&root.join("src"), ChangeKind::Removed);
        assert!(!controller.rows().iter().any(|r| r.label == "src"));
        let _ = std::fs::remove_dir_all(root);
    }
}
