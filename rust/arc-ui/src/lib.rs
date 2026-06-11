//! arc-ui — the facade crate (review brief §3.4, improvement #1).
//!
//! Rules enforced by `scripts/check-arc-ui-facade.sh` (CI):
//! - this is the ONLY workspace crate that may import `gpui`/`floem`;
//! - everything else programs against the ARC-owned vocabulary below, so a
//!   framework swap after the Sprint-3 spike touches exactly one crate.
//!
//! Sprint-2 status: **no framework selected** (ADR-0002 spike pending, gates
//! G1–G8). `kit` is therefore empty; the shell builds and tests headless.

pub mod command;
pub mod focus;
pub mod keymap;
pub mod palette;
pub mod theme;

/// The only framework import site in the workspace. Populated by the Sprint-3
/// decision; until then any attempt to use a framework type elsewhere fails
/// both compilation and the facade CI gate.
pub mod kit {
    // #[cfg(feature = "framework-gpui")]  pub use gpui::*;
    // #[cfg(feature = "framework-floem")] pub use floem::*;
}

pub use command::{Command, CommandId, CommandRegistry};
pub use focus::FocusRing;
pub use keymap::{Chord, Keymap, KeymapError};
pub use palette::PaletteModel;
pub use theme::Theme;
