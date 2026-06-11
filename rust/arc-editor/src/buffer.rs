//! Buffer — rope-backed text with transactional edits and undo/redo.
//!
//! Design decisions carried from the planning package (ADR-0002 §transaction
//! model) and the review report:
//! - snapshot + undo-stack of inverted transactions (NOT CRDT; single-seat,
//!   loopback posture) — but edits are op-based records, so the model stays
//!   CRDT-compatible for a future major without paying the complexity now;
//! - char-index addressing at the API (UTF-8 byte safety stays internal);
//! - applying a transaction validates EVERY edit against the *current* text
//!   before mutating anything: a bad transaction is rejected whole
//!   (atomicity), never half-applied;
//! - undo restores text AND returns the selections captured before the
//!   original transaction (cursor restoration is the part editors get wrong).

use ropey::Rope;
use std::ops::Range;

#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum BufferError {
    #[error("edit range {start}..{end} exceeds buffer length {len}")]
    OutOfBounds {
        start: usize,
        end: usize,
        len: usize,
    },
    #[error("edit range start {start} > end {end}")]
    InvertedRange { start: usize, end: usize },
    #[error("edits within a transaction must be sorted and non-overlapping")]
    OverlappingEdits,
    #[error("nothing to undo")]
    NothingToUndo,
    #[error("nothing to redo")]
    NothingToRedo,
}

/// One edit: replace `char_range` with `new_text` (empty = deletion,
/// empty range = insertion).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Edit {
    pub char_range: Range<usize>,
    pub new_text: String,
}

/// A transaction: one undo unit. `selections_before` is captured by the
/// caller (the future selection model) and returned verbatim on undo.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Transaction {
    pub edits: Vec<Edit>,
    pub selections_before: Vec<Range<usize>>,
}

/// Inverse transaction stored on the undo/redo stacks.
#[derive(Debug, Clone)]
struct Recorded {
    /// Applying this undoes/redoes the original.
    inverse: Transaction,
    /// Selections to restore when this record is applied.
    selections: Vec<Range<usize>>,
}

pub struct Buffer {
    rope: Rope,
    undo: Vec<Recorded>,
    redo: Vec<Recorded>,
    /// Monotone edit revision; rendering/highlight layers key caches off it.
    revision: u64,
}

impl Buffer {
    pub fn from_text(text: &str) -> Self {
        Self {
            rope: Rope::from_str(text),
            undo: Vec::new(),
            redo: Vec::new(),
            revision: 0,
        }
    }

    pub fn len_chars(&self) -> usize {
        self.rope.len_chars()
    }

    pub fn len_lines(&self) -> usize {
        self.rope.len_lines()
    }

    pub fn revision(&self) -> u64 {
        self.revision
    }

    /// Full text snapshot (named `text`, not `to_string`, to avoid colliding
    /// with the Display-trait convention — clippy::inherent_to_string).
    pub fn text(&self) -> String {
        self.rope.to_string()
    }

    /// Line content without the trailing newline (viewport feed).
    pub fn line(&self, idx: usize) -> Option<String> {
        if idx >= self.rope.len_lines() {
            return None;
        }
        let line = self.rope.line(idx);
        let mut s = line.to_string();
        if s.ends_with('\n') {
            s.pop();
            if s.ends_with('\r') {
                s.pop();
            }
        }
        Some(s)
    }

    pub fn slice(&self, range: Range<usize>) -> Option<String> {
        if range.start > range.end || range.end > self.rope.len_chars() {
            return None;
        }
        Some(self.rope.slice(range).to_string())
    }

    /// Validate a transaction against current text: in-bounds, sorted,
    /// non-overlapping. Adjacent (touching) edits are allowed.
    fn validate(&self, tx: &Transaction) -> Result<(), BufferError> {
        let len = self.rope.len_chars();
        let mut prev_end: Option<usize> = None;
        for e in &tx.edits {
            if e.char_range.start > e.char_range.end {
                return Err(BufferError::InvertedRange {
                    start: e.char_range.start,
                    end: e.char_range.end,
                });
            }
            if e.char_range.end > len {
                return Err(BufferError::OutOfBounds {
                    start: e.char_range.start,
                    end: e.char_range.end,
                    len,
                });
            }
            if let Some(pe) = prev_end {
                if e.char_range.start < pe {
                    return Err(BufferError::OverlappingEdits);
                }
            }
            prev_end = Some(e.char_range.end);
        }
        Ok(())
    }

    /// Apply atomically; on success the inverse lands on the undo stack and
    /// the redo stack clears (standard linear-undo semantics).
    pub fn apply(&mut self, tx: Transaction) -> Result<(), BufferError> {
        self.validate(&tx)?;

        // Build the inverse BEFORE mutating (needs original text).
        // Process in reverse order so earlier indices stay valid while
        // mutating; the inverse's edits are computed against the
        // post-transaction coordinate space.
        let mut inverse_edits: Vec<Edit> = Vec::with_capacity(tx.edits.len());
        // Compute position deltas: applying edits left->right shifts later
        // positions by (new_len - old_len) of each earlier edit.
        let mut shift: isize = 0;
        for e in &tx.edits {
            let removed: String = self.rope.slice(e.char_range.clone()).to_string();
            let new_start = (e.char_range.start as isize + shift) as usize;
            let new_len = e.new_text.chars().count();
            inverse_edits.push(Edit {
                char_range: new_start..new_start + new_len,
                new_text: removed.clone(),
            });
            shift += new_len as isize - (e.char_range.end - e.char_range.start) as isize;
        }

        // Mutate, reverse order keeps original indices valid.
        for e in tx.edits.iter().rev() {
            self.rope.remove(e.char_range.clone());
            self.rope.insert(e.char_range.start, &e.new_text);
        }

        self.undo.push(Recorded {
            inverse: Transaction {
                edits: inverse_edits,
                selections_before: Vec::new(),
            },
            selections: tx.selections_before.clone(),
        });
        self.redo.clear();
        self.revision += 1;
        Ok(())
    }

    /// Undo: returns the selections captured before the undone transaction.
    pub fn undo(&mut self) -> Result<Vec<Range<usize>>, BufferError> {
        let rec = self.undo.pop().ok_or(BufferError::NothingToUndo)?;
        let redo_rec = self.apply_recorded(&rec);
        self.redo.push(redo_rec);
        self.revision += 1;
        Ok(rec.selections)
    }

    pub fn redo(&mut self) -> Result<Vec<Range<usize>>, BufferError> {
        let rec = self.redo.pop().ok_or(BufferError::NothingToRedo)?;
        let undo_rec = self.apply_recorded(&rec);
        self.undo.push(undo_rec);
        self.revision += 1;
        Ok(rec.selections)
    }

    /// Apply a recorded inverse and produce its own inverse for the
    /// opposite stack. Recorded inverses are pre-validated by construction.
    fn apply_recorded(&mut self, rec: &Recorded) -> Recorded {
        let tx = &rec.inverse;
        let mut counter_edits: Vec<Edit> = Vec::with_capacity(tx.edits.len());
        let mut shift: isize = 0;
        for e in &tx.edits {
            let removed: String = self.rope.slice(e.char_range.clone()).to_string();
            let new_start = (e.char_range.start as isize + shift) as usize;
            let new_len = e.new_text.chars().count();
            counter_edits.push(Edit {
                char_range: new_start..new_start + new_len,
                new_text: removed,
            });
            shift += new_len as isize - (e.char_range.end - e.char_range.start) as isize;
        }
        for e in tx.edits.iter().rev() {
            self.rope.remove(e.char_range.clone());
            self.rope.insert(e.char_range.start, &e.new_text);
        }
        Recorded {
            inverse: Transaction {
                edits: counter_edits,
                selections_before: Vec::new(),
            },
            selections: rec.selections.clone(),
        }
    }

    pub fn can_undo(&self) -> bool {
        !self.undo.is_empty()
    }

    pub fn can_redo(&self) -> bool {
        !self.redo.is_empty()
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::single_range_in_vec_init)]
// single_range_in_vec_init: selections ARE vecs of ranges; a one-element
// vec![a..b] is the intended literal, not a mistyped vec![a; b].
mod tests {
    use super::*;

    fn tx(edits: Vec<Edit>) -> Transaction {
        Transaction {
            edits,
            selections_before: vec![0..0],
        }
    }

    fn ins(at: usize, text: &str) -> Edit {
        Edit {
            char_range: at..at,
            new_text: text.into(),
        }
    }

    fn del(range: Range<usize>) -> Edit {
        Edit {
            char_range: range,
            new_text: String::new(),
        }
    }

    #[test]
    fn insert_delete_replace_roundtrip() {
        let mut b = Buffer::from_text("hello world");
        b.apply(tx(vec![ins(5, ",")])).unwrap();
        assert_eq!(b.text(), "hello, world");
        b.apply(tx(vec![del(0..5)])).unwrap();
        assert_eq!(b.text(), ", world");
        b.apply(tx(vec![Edit {
            char_range: 0..1,
            new_text: "Hi".into(),
        }]))
        .unwrap();
        assert_eq!(b.text(), "Hi world");
    }

    #[test]
    fn multi_edit_transaction_is_atomic_and_ordered() {
        let mut b = Buffer::from_text("abc def ghi");
        // two inserts in one tx, sorted by position
        b.apply(tx(vec![ins(3, "X"), ins(7, "Y")])).unwrap();
        assert_eq!(b.text(), "abcX defY ghi");
        // single undo reverts BOTH edits (one undo unit)
        b.undo().unwrap();
        assert_eq!(b.text(), "abc def ghi");
    }

    #[test]
    fn invalid_transaction_rejected_whole_no_partial_apply() {
        let mut b = Buffer::from_text("short");
        let bad = tx(vec![ins(0, "ok"), del(2..999)]);
        assert!(matches!(b.apply(bad), Err(BufferError::OutOfBounds { .. })));
        assert_eq!(b.text(), "short", "first edit must NOT have landed");
        assert!(!b.can_undo());
    }

    #[test]
    fn overlapping_edits_rejected() {
        let mut b = Buffer::from_text("abcdef");
        let bad = tx(vec![del(0..3), del(2..5)]);
        assert_eq!(b.apply(bad), Err(BufferError::OverlappingEdits));
    }

    #[test]
    fn undo_redo_chain_restores_text_and_selections() {
        let mut b = Buffer::from_text("v1");
        let mut t = tx(vec![Edit {
            char_range: 0..2,
            new_text: "v2".into(),
        }]);
        t.selections_before = vec![1..1];
        b.apply(t).unwrap();
        b.apply(tx(vec![Edit {
            char_range: 0..2,
            new_text: "v3".into(),
        }]))
        .unwrap();
        assert_eq!(b.text(), "v3");

        assert_eq!(b.undo().unwrap(), vec![0..0]);
        assert_eq!(b.text(), "v2");
        assert_eq!(b.undo().unwrap(), vec![1..1], "selections from before tx1");
        assert_eq!(b.text(), "v1");
        assert!(matches!(b.undo(), Err(BufferError::NothingToUndo)));

        b.redo().unwrap();
        assert_eq!(b.text(), "v2");
        b.redo().unwrap();
        assert_eq!(b.text(), "v3");
        assert!(matches!(b.redo(), Err(BufferError::NothingToRedo)));
    }

    #[test]
    fn new_edit_clears_redo() {
        let mut b = Buffer::from_text("a");
        b.apply(tx(vec![ins(1, "b")])).unwrap();
        b.undo().unwrap();
        assert!(b.can_redo());
        b.apply(tx(vec![ins(1, "c")])).unwrap();
        assert!(!b.can_redo(), "divergent history kills redo (linear undo)");
        assert_eq!(b.text(), "ac");
    }

    #[test]
    fn unicode_char_addressing() {
        // 'ö' is one char, multiple bytes; char indices must address it cleanly.
        let mut b = Buffer::from_text("öäü");
        b.apply(tx(vec![Edit {
            char_range: 1..2,
            new_text: "X".into(),
        }]))
        .unwrap();
        assert_eq!(b.text(), "öXü");
        b.undo().unwrap();
        assert_eq!(b.text(), "öäü");
    }

    #[test]
    fn revision_increments_on_apply_undo_redo() {
        let mut b = Buffer::from_text("");
        assert_eq!(b.revision(), 0);
        b.apply(tx(vec![ins(0, "x")])).unwrap();
        b.undo().unwrap();
        b.redo().unwrap();
        assert_eq!(b.revision(), 3);
    }

    #[test]
    fn line_access_strips_newlines() {
        let b = Buffer::from_text("one\ntwo\r\nthree");
        assert_eq!(b.line(0).unwrap(), "one");
        assert_eq!(b.line(1).unwrap(), "two");
        assert_eq!(b.line(2).unwrap(), "three");
        assert!(b.line(3).is_none());
    }
}
