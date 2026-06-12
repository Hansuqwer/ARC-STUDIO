//! arc-shell library surface: the framework-free shell model and daemon
//! supervision policies. The `arc-shell` binary (main.rs) and the Sprint-3
//! renderer both consume this API; tests exercise it headless.

#![recursion_limit = "512"]

#[cfg(feature = "framework-gpui")]
pub mod render_gpui;
pub mod shell;
pub mod supervisor;

pub use shell::{ShellCtx, ShellModel};
pub use supervisor::{await_healthy, Backoff, CircuitBreaker, DaemonState};
