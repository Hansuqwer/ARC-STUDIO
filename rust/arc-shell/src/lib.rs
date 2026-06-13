//! arc-shell library surface: the framework-free shell model and daemon
//! supervision policies. The `arc-shell` binary (main.rs) and the Sprint-3
//! renderer both consume this API; tests exercise it headless.

#![recursion_limit = "512"]

#[cfg(all(feature = "framework-gpui", target_os = "macos"))]
pub mod a11y_macos;
pub mod editor_controller;
#[cfg(feature = "framework-gpui")]
pub mod render_editor_gpui;
#[cfg(feature = "framework-gpui")]
pub mod render_gpui;
#[cfg(feature = "framework-gpui")]
pub mod render_terminal_gpui;
#[cfg(feature = "framework-gpui")]
pub mod render_workspace_gpui;
pub mod search_controller;
pub mod shell;
pub mod supervisor;
pub mod terminal_controller;
pub mod workspace_controller;

pub use shell::{ShellCtx, ShellModel};
pub use supervisor::{await_healthy, Backoff, CircuitBreaker, DaemonState};
