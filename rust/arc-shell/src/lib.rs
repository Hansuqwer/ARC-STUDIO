//! arc-shell library surface: the framework-free shell model and daemon
//! supervision policies. The `arc-shell` binary (main.rs) and the Sprint-3
//! renderer both consume this API; tests exercise it headless.

pub mod shell;
pub mod supervisor;

pub use shell::{ShellCtx, ShellModel};
pub use supervisor::{await_healthy, Backoff, CircuitBreaker, DaemonState};
