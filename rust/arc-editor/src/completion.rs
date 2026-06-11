//! Inline-completion provider stub (plan §3.6) — unblocks ARC2-20 arena
//! prototype without committing to an implementation. The daemon-backed
//! provider arrives Sprint 9; arena parity remains prototype-gated (R5).
//!
//! Deliberately free of async-runtime types: the contract is a callback with
//! cancellation, so it binds equally to tokio (daemon-backed) or a synchronous
//! test double. No LLM is involved in any allow/deny path — completions are
//! suggestions; application of one goes through the normal Buffer transaction
//! path like any other edit.

use crate::buffer::Buffer;
use std::ops::Range;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

/// Cooperative cancellation token (no tokio dependency at this layer).
#[derive(Clone, Default)]
pub struct CancelFlag(Arc<AtomicBool>);

impl CancelFlag {
    pub fn cancel(&self) {
        self.0.store(true, Ordering::Relaxed);
    }

    pub fn is_cancelled(&self) -> bool {
        self.0.load(Ordering::Relaxed)
    }
}

/// One completion proposal: replace `replace_range` with `text`.
/// `display` is the ghost-text shown inline (may differ from `text`, e.g.
/// truncated); both are plain strings — rendering decides presentation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompletionSpan {
    pub replace_range: Range<usize>,
    pub text: String,
    pub display: String,
}

/// Provider contract. Implementations must:
/// - return promptly when `cancel` flips (poll it between work units);
/// - never mutate the buffer (read-only view of text + cursor);
/// - tolerate being called at any revision (caller revalidates spans
///   against `buffer.revision()` before applying).
pub trait InlineCompletionProvider: Send + Sync {
    fn completions(
        &self,
        buffer: &Buffer,
        cursor_char: usize,
        cancel: &CancelFlag,
    ) -> Vec<CompletionSpan>;
}

/// Null provider: always empty. The shell can wire the editor end-to-end
/// (ghost-text plumbing, accept/dismiss keybinds) before any real backend.
pub struct NullProvider;

impl InlineCompletionProvider for NullProvider {
    fn completions(&self, _: &Buffer, _: usize, _: &CancelFlag) -> Vec<CompletionSpan> {
        Vec::new()
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::single_range_in_vec_init)]
// single_range_in_vec_init: selections ARE vecs of ranges; a one-element
// vec![a..b] is the intended literal, not a mistyped vec![a; b].
mod tests {
    use super::*;
    use crate::buffer::{Edit, Transaction};

    /// Test double proving the contract is implementable + cancellable.
    struct StaticProvider;

    impl InlineCompletionProvider for StaticProvider {
        fn completions(
            &self,
            buffer: &Buffer,
            cursor: usize,
            cancel: &CancelFlag,
        ) -> Vec<CompletionSpan> {
            if cancel.is_cancelled() {
                return Vec::new();
            }
            // complete "fn " -> "fn main() {}" when cursor at end of "fn "
            let text = buffer.text();
            if text.ends_with("fn ") && cursor == buffer.len_chars() {
                vec![CompletionSpan {
                    replace_range: cursor..cursor,
                    text: "main() {}".into(),
                    display: "main() {}".into(),
                }]
            } else {
                Vec::new()
            }
        }
    }

    #[test]
    fn provider_suggests_and_apply_goes_through_buffer_transaction() {
        let mut b = Buffer::from_text("fn ");
        let p = StaticProvider;
        let spans = p.completions(&b, 3, &CancelFlag::default());
        assert_eq!(spans.len(), 1);
        let s = &spans[0];
        // applying a completion is a NORMAL transaction — undoable like typing
        b.apply(Transaction {
            edits: vec![Edit {
                char_range: s.replace_range.clone(),
                new_text: s.text.clone(),
            }],
            selections_before: vec![3..3],
        })
        .unwrap();
        assert_eq!(b.text(), "fn main() {}");
        b.undo().unwrap();
        assert_eq!(b.text(), "fn ");
    }

    #[test]
    fn cancellation_yields_empty() {
        let b = Buffer::from_text("fn ");
        let cancel = CancelFlag::default();
        cancel.cancel();
        assert!(StaticProvider.completions(&b, 3, &cancel).is_empty());
    }

    #[test]
    fn null_provider_is_always_empty() {
        let b = Buffer::from_text("anything");
        assert!(NullProvider
            .completions(&b, 0, &CancelFlag::default())
            .is_empty());
    }
}
