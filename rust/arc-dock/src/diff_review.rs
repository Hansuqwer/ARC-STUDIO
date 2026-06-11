//! Diff/review/apply view-model (wireframe §6.6) — confirmation-gated.
//!
//! Safety rules as types:
//! - ALL mutations go through the daemon: the only egress is
//!   [`DiffEffect::RequestApply`] carrying the selected file list to POST;
//!   the shell never writes workspace files;
//! - [Apply Selected] is enabled ONLY after explicit confirmation, and the
//!   button text carries the selection count ("Apply 2 of 3" — review §11.6);
//! - any selection change RESETS confirmation (you confirm a specific set,
//!   not a mood);
//! - hunk navigation is keyboard-first; +/- conveyed by prefix text and
//!   role, never color alone (a11y block §6.6).

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HunkLineKind {
    Context,
    Add,
    Remove,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HunkLine {
    pub kind: HunkLineKind,
    pub text: String,
}

impl HunkLine {
    /// Accessible text: prefix words, not color ("added: …" / "removed: …").
    pub fn a11y_text(&self) -> String {
        match self.kind {
            HunkLineKind::Add => format!("added: {}", self.text),
            HunkLineKind::Remove => format!("removed: {}", self.text),
            HunkLineKind::Context => self.text.clone(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FileDiff {
    pub path: String,
    pub hunks: Vec<Vec<HunkLine>>,
    pub included: bool,
}

/// Parse a unified diff into per-file hunk structures. Defensive: unknown
/// lines become Context; an empty patch yields zero files (Empty surface).
pub fn parse_unified(patch: &str) -> Vec<FileDiff> {
    let mut files: Vec<FileDiff> = Vec::new();
    for line in patch.lines() {
        if let Some(path) = line.strip_prefix("+++ b/") {
            files.push(FileDiff {
                path: path.to_string(),
                hunks: Vec::new(),
                included: true,
            });
        } else if line.starts_with("+++") || line.starts_with("---") {
            // header noise (/dev/null, a/ side) — ignore
        } else if line.starts_with("@@") {
            if let Some(f) = files.last_mut() {
                f.hunks.push(Vec::new());
            }
        } else if let Some(f) = files.last_mut() {
            if let Some(h) = f.hunks.last_mut() {
                let (kind, text) = if let Some(t) = line.strip_prefix('+') {
                    (HunkLineKind::Add, t)
                } else if let Some(t) = line.strip_prefix('-') {
                    (HunkLineKind::Remove, t)
                } else {
                    (
                        HunkLineKind::Context,
                        line.strip_prefix(' ').unwrap_or(line),
                    )
                };
                h.push(HunkLine {
                    kind,
                    text: text.to_string(),
                });
            }
        }
    }
    files
}

/// The apply request sent to the daemon (route inventoried in-sprint —
/// `GET /api/runs/diff` exists; the apply POST is part of the F3-adjacent
/// daemon inventory; this model never invents it).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ApplyRequest {
    pub run_id: String,
    pub proposal_id: String,
    pub files: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DiffEffect {
    None,
    /// POST to the daemon; the daemon applies, audits, and reports back.
    RequestApply(ApplyRequest),
    /// Run tests first (daemon-side task) — never gated off, never implicit.
    RequestTests {
        run_id: String,
    },
}

pub struct DiffReview {
    pub run_id: String,
    pub proposal_id: String,
    files: Vec<FileDiff>,
    /// Cursor: (file index, hunk index) for keyboard hunk navigation.
    cursor: (usize, usize),
    /// Confirmation state: armed only by `confirm()`, reset by ANY
    /// selection change. Apply without it is impossible (type-enforced).
    confirmed: bool,
    applying: bool,
}

impl DiffReview {
    pub fn from_patch(run_id: &str, proposal_id: &str, patch: &str) -> Self {
        Self {
            run_id: run_id.into(),
            proposal_id: proposal_id.into(),
            files: parse_unified(patch),
            cursor: (0, 0),
            confirmed: false,
            applying: false,
        }
    }

    pub fn files(&self) -> &[FileDiff] {
        &self.files
    }

    pub fn is_empty(&self) -> bool {
        self.files.is_empty()
    }

    // ── selection ──────────────────────────────────────────────────────────

    pub fn toggle_file(&mut self, idx: usize) {
        if let Some(f) = self.files.get_mut(idx) {
            f.included = !f.included;
            self.confirmed = false; // selection changed => re-confirm
        }
    }

    pub fn selected_count(&self) -> usize {
        self.files.iter().filter(|f| f.included).count()
    }

    /// Button label carries the count: "Apply 2 of 3" (review §11.6).
    pub fn apply_label(&self) -> String {
        format!("Apply {} of {}", self.selected_count(), self.files.len())
    }

    // ── confirmation gate ──────────────────────────────────────────────────

    /// Explicit confirmation of the CURRENT selection set.
    pub fn confirm(&mut self) {
        if self.selected_count() > 0 {
            self.confirmed = true;
        }
    }

    pub fn is_confirmed(&self) -> bool {
        self.confirmed
    }

    /// Apply: only yields a request if confirmed, selection non-empty, and
    /// not already in flight. Everything else is None — unconditionally.
    pub fn apply_selected(&mut self) -> DiffEffect {
        if !self.confirmed || self.applying || self.selected_count() == 0 {
            return DiffEffect::None;
        }
        self.applying = true;
        DiffEffect::RequestApply(ApplyRequest {
            run_id: self.run_id.clone(),
            proposal_id: self.proposal_id.clone(),
            files: self
                .files
                .iter()
                .filter(|f| f.included)
                .map(|f| f.path.clone())
                .collect(),
        })
    }

    pub fn run_tests(&self) -> DiffEffect {
        DiffEffect::RequestTests {
            run_id: self.run_id.clone(),
        }
    }

    /// Daemon reported the apply outcome; gate re-arms only via confirm().
    pub fn apply_finished(&mut self) {
        self.applying = false;
        self.confirmed = false;
    }

    // ── keyboard hunk navigation ───────────────────────────────────────────

    /// Next hunk (wraps across files). Returns the new (file, hunk) and an
    /// announcement string for the screen reader.
    pub fn next_hunk(&mut self) -> Option<((usize, usize), String)> {
        if self.files.is_empty() {
            return None;
        }
        let (mut fi, mut hi) = self.cursor;
        loop {
            if hi + 1 < self.files[fi].hunks.len() {
                hi += 1;
            } else {
                fi = (fi + 1) % self.files.len();
                hi = 0;
            }
            if !self.files[fi].hunks.is_empty() {
                break;
            }
            if (fi, hi) == self.cursor {
                break; // single file, no hunks
            }
        }
        self.cursor = (fi, hi);
        Some(((fi, hi), self.announce_cursor()))
    }

    pub fn announce_cursor(&self) -> String {
        let (fi, hi) = self.cursor;
        let f = &self.files[fi];
        let adds = f.hunks[hi]
            .iter()
            .filter(|l| l.kind == HunkLineKind::Add)
            .count();
        let dels = f.hunks[hi]
            .iter()
            .filter(|l| l.kind == HunkLineKind::Remove)
            .count();
        format!(
            "{}, hunk {} of {}: {} added, {} removed, {}",
            f.path,
            hi + 1,
            f.hunks.len(),
            adds,
            dels,
            if f.included { "included" } else { "excluded" }
        )
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    const PATCH: &str = "\
--- a/src/a.rs
+++ b/src/a.rs
@@ -1,3 +1,4 @@
 fn main() {
+    init();
 }
@@ -10,2 +11,2 @@
-let x = 1;
+let x = 2;
--- a/src/b.rs
+++ b/src/b.rs
@@ -5,1 +5,2 @@
+// new comment
 struct B;
";

    fn review() -> DiffReview {
        DiffReview::from_patch("abc123", "proposal-4", PATCH)
    }

    #[test]
    fn parses_files_hunks_and_kinds() {
        let r = review();
        assert_eq!(r.files().len(), 2);
        assert_eq!(r.files()[0].path, "src/a.rs");
        assert_eq!(r.files()[0].hunks.len(), 2);
        let h0 = &r.files()[0].hunks[0];
        assert_eq!(h0[1].kind, HunkLineKind::Add);
        assert_eq!(h0[1].a11y_text(), "added:     init();");
    }

    #[test]
    fn apply_without_confirmation_is_impossible() {
        let mut r = review();
        assert_eq!(r.apply_selected(), DiffEffect::None, "no confirm, no apply");
        r.confirm();
        match r.apply_selected() {
            DiffEffect::RequestApply(req) => {
                assert_eq!(req.files, vec!["src/a.rs", "src/b.rs"]);
                assert_eq!(req.run_id, "abc123");
            }
            other => panic!("expected RequestApply, got {other:?}"),
        }
    }

    #[test]
    fn selection_change_resets_confirmation() {
        let mut r = review();
        r.confirm();
        assert!(r.is_confirmed());
        r.toggle_file(1); // deselect b.rs
        assert!(!r.is_confirmed(), "you confirm a set, not a mood");
        assert_eq!(r.apply_selected(), DiffEffect::None);
        r.confirm();
        match r.apply_selected() {
            DiffEffect::RequestApply(req) => assert_eq!(req.files, vec!["src/a.rs"]),
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn apply_label_carries_count() {
        let mut r = review();
        assert_eq!(r.apply_label(), "Apply 2 of 2");
        r.toggle_file(0);
        assert_eq!(r.apply_label(), "Apply 1 of 2");
    }

    #[test]
    fn no_double_apply_and_gate_rearms_only_via_confirm() {
        let mut r = review();
        r.confirm();
        assert!(matches!(r.apply_selected(), DiffEffect::RequestApply(_)));
        assert_eq!(r.apply_selected(), DiffEffect::None, "in flight");
        r.apply_finished();
        assert_eq!(
            r.apply_selected(),
            DiffEffect::None,
            "finished resets confirm"
        );
        r.confirm();
        assert!(matches!(r.apply_selected(), DiffEffect::RequestApply(_)));
    }

    #[test]
    fn empty_selection_cannot_confirm_or_apply() {
        let mut r = review();
        r.toggle_file(0);
        r.toggle_file(1);
        r.confirm();
        assert!(!r.is_confirmed(), "empty set is not confirmable");
        assert_eq!(r.apply_selected(), DiffEffect::None);
    }

    #[test]
    fn hunk_navigation_wraps_and_announces_counts() {
        let mut r = review();
        let (_, a1) = r.next_hunk().unwrap();
        assert!(a1.contains("hunk 2 of 2"), "{a1}");
        assert!(a1.contains("1 added, 1 removed"));
        let (_, a2) = r.next_hunk().unwrap();
        assert!(a2.starts_with("src/b.rs"), "wrapped to next file: {a2}");
        let (_, a3) = r.next_hunk().unwrap();
        assert!(a3.starts_with("src/a.rs"), "wrapped around: {a3}");
        assert!(a3.contains("included"));
    }

    #[test]
    fn empty_patch_is_empty_surface() {
        let r = DiffReview::from_patch("r", "p", "");
        assert!(r.is_empty());
    }

    #[test]
    fn run_tests_is_always_available_and_separate_from_apply() {
        let r = review();
        assert_eq!(
            r.run_tests(),
            DiffEffect::RequestTests {
                run_id: "abc123".into()
            }
        );
        // no confirmation involved — tests are read-only daemon-side
    }
}
