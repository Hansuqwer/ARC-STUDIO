//! gpui facade port — renders the arc-ui shell chrome (palette overlay, focus
//! ring, status rail, theme hook) per arc-v2-facade-cost-protocol.md.
//!
//! Scope (criterion #1): the candidate-specific RENDER layer only. Shared
//! models (PaletteModel/FocusRing/Theme from arc-ui) imported unchanged
//! (F-CONCEPT=5 target). tokei-counted F-LOC unit. Throwaway-by-contract.
//!
//! gpui idiom contrast vs floem: the view Entity HOLDS the models directly and
//! render() reads them — no model→signal mirror. Input routes straight into
//! PaletteModel::key / FocusRing inside an on_key_down listener, then cx.notify().

use arc_ui::command::{Command, CommandRegistry, Enablement};
use arc_ui::focus::{FocusRing, Region};
use arc_ui::palette::{PaletteEffect, PaletteKey, PaletteModel};
use arc_ui::theme::{StatusLevel, Theme};
use gpui::*;

/// Minimal command context (mirrors arc-shell's ShellCtx shape; render-only).
pub struct PortCtx {
    pub healthy: bool,
    pub trusted: bool,
}

pub fn demo_registry() -> CommandRegistry<PortCtx> {
    let mut r: CommandRegistry<PortCtx> = CommandRegistry::default();
    let gated = |c: &PortCtx| {
        if c.healthy {
            Enablement::Enabled
        } else {
            Enablement::Disabled {
                reason: "daemon not healthy".into(),
            }
        }
    };
    let _ = r.register(Command::new("arc.palette.open", "ARC: Command Palette", "shell"));
    let _ = r.register(Command::new("arc.focus.next", "ARC: Focus Next Region", "shell"));
    let _ = r.register(Command::new("arc.theme.contrast", "ARC: Toggle High Contrast", "shell"));
    let _ = r.register(Command::new("arc.daemon.health", "ARC: Show Daemon Health", "daemon"));
    let _ = r.register(
        Command::new("arc.runs.open", "ARC: Open Runs Panel", "panels").enabled_when(gated),
    );
    let _ = r.register(
        Command::new("arc.events.open", "ARC: Open Event Stream", "panels").enabled_when(gated),
    );
    let _ = r.register(Command::new("arc.replay.fixture", "ARC: Replay Fixture", "debug"));
    r
}

fn palette_bg(t: &Theme) -> Rgba {
    if t.no_color {
        rgb(0xffffff)
    } else if t.high_contrast {
        rgb(0x000000)
    } else {
        rgb(0x252526)
    }
}

fn fg(t: &Theme) -> Rgba {
    if t.no_color {
        rgb(0x000000)
    } else if t.high_contrast {
        rgb(0xffffff)
    } else {
        rgb(0xd4d4d4)
    }
}

fn selected_bg(t: &Theme) -> Rgba {
    if t.high_contrast {
        rgb(0xffff00)
    } else {
        rgb(0x094f9c)
    }
}

fn status_rail_text(theme: &Theme, ctx: &PortCtx) -> String {
    let (level, text) = if ctx.healthy {
        (StatusLevel::Ok, "daemon healthy")
    } else {
        (StatusLevel::Error, "daemon degraded")
    };
    let marker = theme.status_marker(level);
    let trust = if ctx.trusted { "trust: trusted" } else { "trust: UNTRUSTED" };
    format!("{marker} {text} | {trust}")
}

/// The shell-chrome view Entity. Holds arc-ui models directly.
pub struct ShellPortView {
    pub palette: PaletteModel,
    pub focus: FocusRing,
    pub theme: Theme,
    pub ctx: PortCtx,
    pub registry: CommandRegistry<PortCtx>,
    pub announce: String,
    pub focus_label: String,
    pub focus_handle: FocusHandle,
}

impl ShellPortView {
    pub fn new(theme: Theme, ctx: PortCtx, cx: &mut Context<Self>) -> Self {
        Self {
            palette: PaletteModel::default(),
            focus: FocusRing::new(vec![
                Region { id: "workspace", label: "Workspace tree" },
                Region { id: "editor", label: "Editor" },
                Region { id: "dock", label: "ARC dock" },
                Region { id: "status", label: "Status rail" },
            ]),
            theme,
            ctx,
            registry: demo_registry(),
            announce: String::new(),
            focus_label: "Workspace tree".to_string(),
            focus_handle: cx.focus_handle(),
        }
    }

    /// Input routing — straight into PaletteModel::key / FocusRing, no shadow
    /// state. Called from the on_key_down listener.
    fn on_key(&mut self, key: &str, m: &Modifiers) {
        // F6 / Shift-F6 focus ring.
        if key == "f6" {
            let r = if m.shift { self.focus.focus_prev() } else { self.focus.focus_next() };
            if let Some(region) = r {
                self.focus_label = region.label.to_string();
                self.announce = format!("focus: {}", region.label);
            }
            return;
        }
        // Ctrl+Shift+P opens the palette.
        if key == "p" && m.control && m.shift {
            self.palette.open_with(&self.registry, &self.ctx);
            return;
        }
        if !self.palette.open {
            return;
        }
        let pk = match key {
            "backspace" => Some(PaletteKey::Backspace),
            "up" => Some(PaletteKey::Up),
            "down" => Some(PaletteKey::Down),
            "enter" => Some(PaletteKey::Enter),
            "escape" => Some(PaletteKey::Escape),
            s if s.chars().count() == 1 => s.chars().next().map(PaletteKey::Char),
            _ => None,
        };
        if let Some(pk) = pk {
            match self.palette.key(pk, &self.registry, &self.ctx) {
                PaletteEffect::Announce(a) => self.announce = a,
                PaletteEffect::Execute(id) => self.announce = format!("execute: {}", id.0),
                PaletteEffect::Rejected { reason } => self.announce = format!("rejected: {reason}"),
                PaletteEffect::Closed => self.announce = "closed".into(),
                PaletteEffect::None => {}
            }
        }
    }
}

impl Render for ShellPortView {
    fn render(&mut self, _window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        let theme = self.theme.clone();
        let rows: Vec<AnyElement> = self
            .palette
            .items
            .iter()
            .take(50)
            .enumerate()
            .map(|(i, it)| {
                let disabled = matches!(it.enablement, Enablement::Disabled { .. });
                let mark = if disabled { " (disabled)" } else { "" };
                let mut row = div()
                    .text_color(fg(&theme))
                    .px_1()
                    .child(format!("{}  ·  {}{}", it.title, it.category, mark));
                if i == self.palette.selected {
                    row = row.bg(selected_bg(&theme));
                }
                row.into_any_element()
            })
            .collect();

        let palette_block = if self.palette.open {
            div()
                .bg(palette_bg(&theme))
                .p_2()
                .w(px(600.0))
                .flex()
                .flex_col()
                .child(div().child(format!("> {}", self.palette.query)))
                .children(rows)
                .into_any_element()
        } else {
            div().into_any_element()
        };

        div()
            .track_focus(&self.focus_handle)
            .key_context("ShellPort")
            .on_key_down(cx.listener(|view, ev: &KeyDownEvent, _window, cx| {
                view.on_key(ev.keystroke.key.as_str(), &ev.keystroke.modifiers);
                cx.notify();
            }))
            .size_full()
            .flex()
            .flex_col()
            .bg(rgb(0x1e1e1e))
            .text_color(fg(&theme))
            .child(div().child(format!("focus ▸ {}", self.focus_label)))
            .child(div().child(self.announce.clone()))
            .child(palette_block)
            .child(
                div()
                    .mt_auto()
                    .p_1()
                    .child(status_rail_text(&self.theme, &self.ctx)),
            )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_rail_honors_no_color() {
        let ctx = PortCtx { healthy: true, trusted: false };
        assert!(status_rail_text(&Theme::from_vars(Some("1"), None), &ctx).starts_with("[OK]"));
        assert!(status_rail_text(&Theme::from_vars(None, None), &ctx).starts_with("●"));
    }

    #[test]
    fn theme_colors_differ_by_mode() {
        assert_ne!(
            palette_bg(&Theme::from_vars(Some("1"), None)).r,
            palette_bg(&Theme::from_vars(None, None)).r
        );
    }

    #[test]
    fn demo_registry_gates_when_unhealthy() {
        let r = demo_registry();
        let ctx = PortCtx { healthy: false, trusted: true };
        let runs = r.iter().find(|c| c.id.0 == "arc.runs.open").unwrap();
        assert!(matches!(runs.enablement(&ctx), Enablement::Disabled { .. }));
    }
}
