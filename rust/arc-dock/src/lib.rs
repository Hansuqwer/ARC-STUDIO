//! arc-dock — Sprint-7 panel layer, framework-free slice.
//!
//! Same architecture as arc-shell: panels are view-models + state machines,
//! proven against fixture replay (the Sprint-1 harness is the parity oracle);
//! the Sprint-3 framework only renders them. Every panel renders every
//! [`SurfaceState`] variant — that is a DoD gate, enforced here as tests.

pub mod event_stream;
pub mod runs;
pub mod state;

pub use event_stream::EventStreamPanel;
pub use runs::{RunRow, RunsPanel};
pub use state::{Datum, SurfaceState};
