//! arc-workspace — Sprint-5 worktree model, framework-free slice.
//!
//! Scope: worktree scan with ignore rules, file-tree model the shell renders,
//! and a debounced watcher (storms collapse per plan §3.7). The file tree is
//! a view-model like everything else: the Sprint-3 framework renders it; the
//! watcher feeds incremental updates through one `apply_change` path that the
//! tests drive directly (deterministic) and the watcher drives live.

pub mod tree;
pub mod watcher;

pub use tree::{ChangeKind, FileNode, NodeKind, WorktreeModel};
pub use watcher::{WatchConfig, WorkspaceWatcher};
