//! ShellModel — the framework-free shell state: layout regions, palette,
//! keymap, theme, daemon status strip. The Sprint-3 framework renders this
//! model; nothing in here may import a UI framework (facade rule).

use crate::supervisor::DaemonState;
use arc_ui::command::{Command, CommandRegistry, Enablement};
use arc_ui::focus::{FocusRing, Region};
use arc_ui::keymap::{Chord, Keymap};
use arc_ui::palette::{PaletteEffect, PaletteKey, PaletteModel};
use arc_ui::theme::{StatusLevel, Theme};

/// Context the command enablement predicates read. Deterministic inputs only.
pub struct ShellCtx {
    pub daemon: DaemonState,
    pub workspace_trusted: bool,
}

pub struct ShellModel {
    pub theme: Theme,
    pub focus: FocusRing,
    pub palette: PaletteModel,
    pub registry: CommandRegistry<ShellCtx>,
    pub keymap: Keymap,
    pub ctx: ShellCtx,
}

impl ShellModel {
    pub fn new(theme: Theme) -> Self {
        let mut registry: CommandRegistry<ShellCtx> = CommandRegistry::default();
        let daemon_gated = |c: &ShellCtx| match &c.daemon {
            DaemonState::Healthy => Enablement::Enabled,
            other => Enablement::Disabled {
                reason: format!("daemon not healthy: {other:?}"),
            },
        };
        // Sprint-2 command set (placeholders execute as no-ops until panels land).
        #[allow(clippy::unwrap_used)] // static registration; duplicate = programming error
        {
            registry
                .register(
                    Command::new("arc.palette.open", "ARC: Command Palette", "shell")
                        .shortcut("ctrl+shift+p"),
                )
                .unwrap();
            registry
                .register(
                    Command::new("arc.focus.next", "ARC: Focus Next Region", "shell")
                        .shortcut("f6"),
                )
                .unwrap();
            registry
                .register(
                    Command::new("arc.focus.prev", "ARC: Focus Previous Region", "shell")
                        .shortcut("ctrl+shift+f6"),
                )
                .unwrap();
            registry
                .register(Command::new(
                    "arc.theme.contrast",
                    "ARC: Toggle High Contrast",
                    "shell",
                ))
                .unwrap();
            registry
                .register(Command::new(
                    "arc.daemon.health",
                    "ARC: Show Daemon Health",
                    "daemon",
                ))
                .unwrap();
            registry
                .register(
                    Command::new("arc.runs.open", "ARC: Open Runs Panel", "panels")
                        .enabled_when(daemon_gated),
                )
                .unwrap();
            registry
                .register(
                    Command::new("arc.events.open", "ARC: Open Event Stream", "panels")
                        .enabled_when(daemon_gated),
                )
                .unwrap();
            registry
                .register(Command::new(
                    "arc.replay.fixture",
                    "ARC: Replay Event Stream Fixture",
                    "debug",
                ))
                .unwrap();
        }

        let mut keymap = Keymap::default();
        #[allow(clippy::unwrap_used)]
        {
            for (chord, id) in [
                ("ctrl+shift+p", "arc.palette.open"),
                ("f6", "arc.focus.next"),
                ("ctrl+shift+f6", "arc.focus.prev"),
            ] {
                let cmd = registry
                    .iter()
                    .find(|c| c.id.0 == id)
                    .map(|c| c.id)
                    .unwrap();
                keymap.bind(Chord::parse(chord).unwrap(), cmd).unwrap();
            }
        }

        Self {
            theme,
            focus: FocusRing::new(vec![
                Region {
                    id: "workspace",
                    label: "Workspace tree",
                },
                Region {
                    id: "editor",
                    label: "Editor",
                },
                Region {
                    id: "dock",
                    label: "ARC dock",
                },
                Region {
                    id: "status",
                    label: "Status rail",
                },
            ]),
            palette: PaletteModel::default(),
            registry,
            keymap,
            ctx: ShellCtx {
                daemon: DaemonState::Starting,
                workspace_trusted: false,
            },
        }
    }

    /// Status rail line (wireframe §6.1) — daemon dot has a text equivalent,
    /// trust state is text, honors NO_COLOR via Theme markers.
    pub fn status_rail(&self) -> String {
        let (marker, text) = match &self.ctx.daemon {
            DaemonState::Healthy => (
                self.theme.status_marker(StatusLevel::Ok),
                "daemon healthy".to_string(),
            ),
            DaemonState::Starting => (
                self.theme.status_marker(StatusLevel::Warn),
                "daemon starting".to_string(),
            ),
            DaemonState::Degraded { reason } => (
                self.theme.status_marker(StatusLevel::Error),
                format!("daemon degraded: {reason}"),
            ),
            DaemonState::CircuitOpen { restarts_in_window } => (
                self.theme.status_marker(StatusLevel::Error),
                format!("daemon crash-loop ({restarts_in_window} restarts) — restart manually"),
            ),
            DaemonState::Stopped => (
                self.theme.status_marker(StatusLevel::Error),
                "daemon stopped".to_string(),
            ),
        };
        let trust = if self.ctx.workspace_trusted {
            "trust: trusted"
        } else {
            "trust: UNTRUSTED"
        };
        format!("{marker} {text} | {trust}")
    }

    /// Route a key chord: keymap → command → palette/focus effects.
    /// Returns a human/SR-readable description of what happened (testable).
    pub fn handle_chord(&mut self, chord: &Chord) -> String {
        let Some(cmd) = self.keymap.resolve(chord) else {
            return String::from("unbound");
        };
        match cmd.0 {
            "arc.palette.open" => {
                self.palette.open_with(&self.registry, &self.ctx);
                String::from("palette opened")
            }
            "arc.focus.next" => self
                .focus
                .focus_next()
                .map(|r| format!("focus: {}", r.label))
                .unwrap_or_default(),
            "arc.focus.prev" => self
                .focus
                .focus_prev()
                .map(|r| format!("focus: {}", r.label))
                .unwrap_or_default(),
            other => format!("execute: {other}"),
        }
    }

    pub fn palette_key(&mut self, key: PaletteKey) -> PaletteEffect {
        self.palette.key(key, &self.registry, &self.ctx)
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    fn shell() -> ShellModel {
        ShellModel::new(Theme::from_vars(None, None))
    }

    #[test]
    fn status_rail_degraded_is_explicit_text() {
        let mut s = shell();
        s.ctx.daemon = DaemonState::Degraded {
            reason: "health timeout".into(),
        };
        let rail = s.status_rail();
        assert!(rail.contains("daemon degraded: health timeout"));
        assert!(rail.contains("UNTRUSTED"), "untrusted state never hidden");
    }

    #[test]
    fn status_rail_honors_no_color() {
        let mut s = ShellModel::new(Theme::from_vars(Some("1"), None));
        s.ctx.daemon = DaemonState::Healthy;
        assert!(
            s.status_rail().starts_with("[OK]"),
            "text marker, not glyph"
        );
    }

    #[test]
    fn keyboard_only_palette_flow_through_shell() {
        let mut s = shell();
        s.ctx.daemon = DaemonState::Healthy;
        assert_eq!(
            s.handle_chord(&Chord::parse("ctrl+shift+p").unwrap()),
            "palette opened"
        );
        for c in "runs".chars() {
            s.palette_key(PaletteKey::Char(c));
        }
        match s.palette_key(PaletteKey::Enter) {
            PaletteEffect::Execute(id) => assert_eq!(id.0, "arc.runs.open"),
            other => panic!("expected Execute, got {other:?}"),
        }
    }

    #[test]
    fn daemon_gated_commands_blocked_when_degraded() {
        let mut s = shell();
        s.ctx.daemon = DaemonState::Degraded {
            reason: "down".into(),
        };
        s.handle_chord(&Chord::parse("ctrl+shift+p").unwrap());
        for c in "open runs".chars() {
            s.palette_key(PaletteKey::Char(c));
        }
        match s.palette_key(PaletteKey::Enter) {
            PaletteEffect::Rejected { reason } => assert!(reason.contains("daemon")),
            other => panic!("expected Rejected, got {other:?}"),
        }
    }

    #[test]
    fn f6_traversal_deterministic() {
        let mut s = shell();
        let a = s.handle_chord(&Chord::parse("f6").unwrap());
        let b = s.handle_chord(&Chord::parse("f6").unwrap());
        assert_eq!(
            (a.as_str(), b.as_str()),
            ("focus: Editor", "focus: ARC dock")
        );
    }
}
