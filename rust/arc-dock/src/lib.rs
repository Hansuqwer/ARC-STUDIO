//! arc-dock — Sprint-7 + Sprint-8 panel + security surfaces, framework-free.
//!
//! Same architecture as arc-shell: panels are view-models + state machines,
//! proven against fixture replay (the Sprint-1 harness is the parity oracle);
//! the Sprint-3 framework only renders them. Every panel renders every
//! [`SurfaceState`] variant — that is a DoD gate, enforced here as tests.

pub mod diff_review;
pub mod event_stream;
pub mod hitl;
pub mod runs;
pub mod state;

pub use diff_review::{DiffEffect, DiffReview, FileDiff};
pub use event_stream::EventStreamPanel;
pub use hitl::{HitlDecision, HitlEffect, HitlModal, HitlPrompt, Verdict};
pub use runs::{RunRow, RunsPanel};
pub use state::{Datum, SurfaceState};
