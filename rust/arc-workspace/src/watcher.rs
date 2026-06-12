//! Debounced filesystem watcher — notify-debouncer-full per plan §3.7.
//! Storms collapse via 250 ms debounce; events map onto the SAME
//! `WorktreeModel::apply_change` path the tests drive deterministically.
//!
//! Lifetime: the watcher owns a background thread (notify's); dropping
//! [`WorkspaceWatcher`] stops watching. The receiver end is polled by the
//! shell's update loop (`drain_into`), keeping this crate runtime-free.

use crate::tree::{ChangeKind, WorktreeModel};
use notify::{EventKind, RecursiveMode};
use notify_debouncer_full::{new_debouncer, DebounceEventResult, DebouncedEvent};
use std::path::PathBuf;
use std::sync::mpsc;
use std::time::Duration;

pub struct WatchConfig {
    pub debounce: Duration,
}

impl Default for WatchConfig {
    fn default() -> Self {
        Self {
            debounce: Duration::from_millis(250),
        }
    }
}

pub struct WorkspaceWatcher {
    // Field order = drop order: debouncer (and its thread) goes first,
    // then the channel.
    _debouncer: notify_debouncer_full::Debouncer<
        notify::RecommendedWatcher,
        notify_debouncer_full::RecommendedCache,
    >,
    rx: mpsc::Receiver<DebounceEventResult>,
}

#[derive(Debug, thiserror::Error)]
pub enum WatchError {
    #[error("notify: {0}")]
    Notify(#[from] notify::Error),
}

impl WorkspaceWatcher {
    pub fn start(root: &std::path::Path, cfg: WatchConfig) -> Result<Self, WatchError> {
        let (tx, rx) = mpsc::channel();
        let mut debouncer = new_debouncer(cfg.debounce, None, tx)?;
        debouncer.watch(root, RecursiveMode::Recursive)?;
        Ok(Self {
            _debouncer: debouncer,
            rx,
        })
    }

    /// Map a debounced notify event onto our change vocabulary.
    /// Unknown/other kinds degrade to Modified for existing paths (safe:
    /// Modified never alters tree shape).
    fn map_event(ev: &DebouncedEvent) -> Vec<(PathBuf, ChangeKind)> {
        let kind = match ev.kind {
            EventKind::Create(_) => None, // decide per-path below (file vs dir)
            EventKind::Remove(_) => Some(ChangeKind::Removed),
            EventKind::Modify(_) => Some(ChangeKind::Modified),
            _ => Some(ChangeKind::Modified),
        };
        ev.paths
            .iter()
            .map(|p| {
                let k = kind.unwrap_or(if p.is_dir() {
                    ChangeKind::CreatedDir
                } else {
                    ChangeKind::CreatedFile
                });
                (p.clone(), k)
            })
            .collect()
    }

    /// Drain pending debounced events into the model. Returns the number of
    /// changes applied. Non-blocking — call from the shell's tick.
    pub fn drain_into(&self, model: &mut WorktreeModel) -> usize {
        let mut applied = 0usize;
        while let Ok(result) = self.rx.try_recv() {
            match result {
                Ok(events) => {
                    for ev in &events {
                        for (path, kind) in Self::map_event(ev) {
                            model.apply_change(&path, kind);
                            applied += 1;
                        }
                    }
                }
                Err(errors) => {
                    for e in errors {
                        tracing::warn!(error = %e, "watcher error (non-fatal; tree may need rescan)");
                    }
                }
            }
        }
        applied
    }

    /// Blocking variant with timeout, for tests.
    pub fn drain_into_timeout(&self, model: &mut WorktreeModel, timeout: Duration) -> usize {
        let mut applied = 0usize;
        if let Ok(Ok(events)) = self.rx.recv_timeout(timeout) {
            for ev in &events {
                for (path, kind) in Self::map_event(ev) {
                    model.apply_change(&path, kind);
                    applied += 1;
                }
            }
            // got a batch; drain whatever else is immediately ready
            applied += self.drain_into(model);
        }
        applied
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used, unused_imports)]
mod tests {
    use super::*;

    /// Live watcher proof (inotify/kqueue): create files -> debounced batch
    /// -> model updated through the same apply_change path the deterministic
    /// tests use. Linux-only: macOS sandbox restricts FSEvents in CI.
    #[test]
    #[cfg(target_os = "linux")]
    fn live_watch_create_updates_model() {
        let td = tempfile::tempdir().unwrap();
        let root = td.path().to_path_buf();
        std::fs::create_dir(root.join("src")).unwrap();

        let mut model = WorktreeModel::new(&root);
        model.scan().unwrap();

        let watcher = WorkspaceWatcher::start(&root, WatchConfig::default()).unwrap();
        std::fs::write(root.join("src/new_file.rs"), "fn x() {}").unwrap();

        let applied = watcher.drain_into_timeout(&mut model, Duration::from_secs(5));
        assert!(applied > 0, "watcher delivered within timeout");
        let names: Vec<&str> = model
            .children(&root.join("src"))
            .unwrap()
            .iter()
            .map(|c| c.name.as_str())
            .collect();
        assert!(names.contains(&"new_file.rs"), "model updated: {names:?}");
    }

    /// Storm collapse: 100 rapid writes to one file arrive as a small number
    /// of debounced batches, not 100 events. Linux-only: same FSEvents
    /// constraint as live_watch_create_updates_model.
    #[test]
    #[cfg(target_os = "linux")]
    fn debounce_collapses_storms() {
        let td = tempfile::tempdir().unwrap();
        let root = td.path().to_path_buf();
        let f = root.join("hot.txt");
        std::fs::write(&f, "0").unwrap();

        let mut model = WorktreeModel::new(&root);
        model.scan().unwrap();

        let watcher = WorkspaceWatcher::start(&root, WatchConfig::default()).unwrap();
        for i in 0..100 {
            std::fs::write(&f, format!("{i}")).unwrap();
        }
        let applied = watcher.drain_into_timeout(&mut model, Duration::from_secs(5));
        assert!(applied >= 1, "at least one change observed");
        assert!(
            applied < 100,
            "debounce collapsed the storm: {applied} events for 100 writes"
        );
    }
}
