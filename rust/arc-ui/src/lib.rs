//! arc-ui — the facade crate (review brief §3.4, improvement #1).
//!
//! Rules enforced by `scripts/check-arc-ui-facade.sh` (CI):
//! - this is the ONLY workspace crate that may import `gpui`/`floem`;
//! - everything else programs against the ARC-owned vocabulary below, so a
//!   framework swap after the Sprint-3 spike touches exactly one crate.
//!
//! K1 (2026-06-12): framework-gpui feature active, gpui 0.2.2 exact pin.
//! Sprint-1 "no framework in lock" gate formally retired — its job is done.

pub mod a11y;
pub mod command;
pub mod focus;
pub mod keymap;
pub mod palette;
pub mod theme;

/// The only framework import site in the workspace. K1: gpui live behind the
/// feature flag. Floem entry preserved as the tested escape (adjudication §3).
pub mod kit {
    #[cfg(feature = "framework-gpui")]
    pub use gpui::*;
    // #[cfg(feature = "framework-floem")] pub use floem::*;  // escape — kept
}

pub use a11y::{A11yNode, A11yRole, A11ySnapshot, ShellA11yTree};
pub use command::{Command, CommandId, CommandRegistry};
pub use focus::FocusRing;
pub use keymap::{Chord, Keymap, KeymapError};
pub use palette::PaletteModel;
pub use theme::Theme;
