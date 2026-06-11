//! arc-editor — Sprint-4 editor core, framework-free slice.
//!
//! Scope (per plan §3.6): buffer + transactions + undo/redo + inline-completion
//! provider trait stub. Rendering, Tree-sitter wiring and huge-file mmap path
//! land after the Sprint-3 framework decision.
//!
//! Facade rule: no rope-crate type appears in any public signature — the
//! bake-off (ropey 1.x / ropey 2 / crop) swaps internals without touching
//! callers.

pub mod buffer;
pub mod completion;

pub use buffer::{Buffer, BufferError, Edit, Transaction};
pub use completion::{CompletionSpan, InlineCompletionProvider};
