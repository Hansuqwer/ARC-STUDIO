//! floem facade port — renders the arc-ui shell chrome (palette overlay,
//! focus ring, status rail, theme hook) per arc-v2-facade-cost-protocol.md.
//!
//! Scope (criterion #1): the candidate-specific RENDER layer only. The shared
//! models (PaletteModel/FocusRing/Theme from arc-ui) are imported unchanged —
//! zero edits to shared code is the F-CONCEPT=5 target. This file is the
//! tokei-counted F-LOC unit.
//!
//! Throwaway-by-contract like the rest of the spike.

use arc_ui::command::{Command, CommandRegistry, Enablement};
use arc_ui::focus::{FocusRing, Region};
use arc_ui::palette::{PaletteEffect, PaletteKey, PaletteModel};
use arc_ui::theme::{StatusLevel, Theme};
use floem::event::{Event, EventListener};
use floem::keyboard::{Key, Modifiers, NamedKey};
use floem::peniko::Color;
use floem::prelude::*;
use floem::reactive::{create_rw_signal, RwSignal};
use std::rc::Rc;

/// Minimal command context for the spike (mirrors arc-shell's ShellCtx shape
/// without the tokio/daemon-client weight — the render layer only reads it).
pub struct PortCtx {
    pub healthy: bool,
    pub trusted: bool,
}

/// Build the demo command set (same ids the ShellModel registers).
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

/// Theme → render colors. NO_COLOR / high-contrast actually change output.
fn palette_bg(t: &Theme) -> Color {
    if t.no_color {
        Color::WHITE
    } else if t.high_contrast {
        Color::BLACK
    } else {
        Color::rgb8(0x25, 0x25, 0x26)
    }
}

fn fg(t: &Theme) -> Color {
    if t.no_color {
        Color::BLACK
    } else if t.high_contrast {
        Color::WHITE
    } else {
        Color::rgb8(0xd4, 0xd4, 0xd4)
    }
}

fn selected_bg(t: &Theme) -> Color {
    if t.high_contrast {
        Color::rgb8(0xff, 0xff, 0x00)
    } else {
        Color::rgb8(0x09, 0x4f, 0x9c)
    }
}

/// Status rail line — same text contract as ShellModel::status_rail(),
/// rendered as one bottom-aligned floem label that honors NO_COLOR markers.
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

/// The shell chrome view. Signals carry the model state; floem re-renders
/// reactively on signal change — no shadow state, no parallel event machine.
pub fn shell_view(theme: Theme, ctx: Rc<PortCtx>) -> impl IntoView {
    let registry = Rc::new(demo_registry());
    let palette = Rc::new(std::cell::RefCell::new(PaletteModel::default()));
    let focus = Rc::new(std::cell::RefCell::new(FocusRing::new(vec![
        Region { id: "workspace", label: "Workspace tree" },
        Region { id: "editor", label: "Editor" },
        Region { id: "dock", label: "ARC dock" },
        Region { id: "status", label: "Status rail" },
    ])));

    let theme = Rc::new(theme);
    let open_sig: RwSignal<bool> = create_rw_signal(false);
    let query_sig: RwSignal<String> = create_rw_signal(String::new());
    let rows_sig: RwSignal<Vec<(String, String, bool)>> = create_rw_signal(Vec::new());
    let sel_sig: RwSignal<usize> = create_rw_signal(0);
    let focus_sig: RwSignal<String> = create_rw_signal("Workspace tree".to_string());
    let announce_sig: RwSignal<String> = create_rw_signal(String::new());

    // Sync model → signals (≤50 rows per protocol).
    let sync = {
        let palette = palette.clone();
        move || {
            let p = palette.borrow();
            open_sig.set(p.open);
            query_sig.set(p.query.clone());
            sel_sig.set(p.selected);
            let rows: Vec<(String, String, bool)> = p
                .items
                .iter()
                .take(50)
                .map(|it| {
                    let disabled = matches!(it.enablement, Enablement::Disabled { .. });
                    (it.title.clone(), it.category.clone(), disabled)
                })
                .collect();
            rows_sig.set(rows);
        }
    };

    let theme_for_view = theme.clone();
    let theme_palette = theme.clone();
    let theme_rows = theme.clone();

    // Keyboard routing: every key goes straight into PaletteModel::key or
    // FocusRing — F-EVENT=5 (no parallel state machine, model is truth).
    let route = {
        let palette = palette.clone();
        let focus = focus.clone();
        let registry = registry.clone();
        let ctx = ctx.clone();
        let sync = sync.clone();
        move |key: Key, modifiers: Modifiers| {
            let mut handled = false;
            // F6 / Shift-F6 focus ring.
            if let Key::Named(NamedKey::F6) = &key {
                let mut f = focus.borrow_mut();
                let r = if modifiers.shift() { f.focus_prev() } else { f.focus_next() };
                if let Some(region) = r {
                    focus_sig.set(region.label.to_string());
                    announce_sig.set(format!("focus: {}", region.label));
                }
                handled = true;
            }
            // Ctrl+Shift+P opens the palette.
            if !handled {
                if let Key::Character(c) = &key {
                    if c.eq_ignore_ascii_case("p") && modifiers.control() && modifiers.shift() {
                        palette.borrow_mut().open_with(registry.as_ref(), ctx.as_ref());
                        sync();
                        handled = true;
                    }
                }
            }
            // Palette-open key routing → PaletteModel::key.
            if !handled && palette.borrow().open {
                let pk = match &key {
                    Key::Named(NamedKey::Backspace) => Some(PaletteKey::Backspace),
                    Key::Named(NamedKey::ArrowUp) => Some(PaletteKey::Up),
                    Key::Named(NamedKey::ArrowDown) => Some(PaletteKey::Down),
                    Key::Named(NamedKey::Enter) => Some(PaletteKey::Enter),
                    Key::Named(NamedKey::Escape) => Some(PaletteKey::Escape),
                    Key::Character(s) => s.chars().next().map(PaletteKey::Char),
                    _ => None,
                };
                if let Some(pk) = pk {
                    let eff = palette.borrow_mut().key(pk, registry.as_ref(), ctx.as_ref());
                    match eff {
                        PaletteEffect::Announce(a) => announce_sig.set(a),
                        PaletteEffect::Execute(id) => announce_sig.set(format!("execute: {}", id.0)),
                        PaletteEffect::Rejected { reason } => {
                            announce_sig.set(format!("rejected: {reason}"))
                        }
                        PaletteEffect::Closed => announce_sig.set("closed".into()),
                        PaletteEffect::None => {}
                    }
                    sync();
                }
            }
        }
    };

    // Status rail (always visible, bottom).
    let rail = label(move || status_rail_text(&theme_for_view, &ctx))
        .style(move |s| s.color(fg(&theme)).padding(4.0));

    // Focus indicator.
    let focus_line = label(move || format!("focus ▸ {}", focus_sig.get()));

    // Announce line (a11y surface — print/log acceptable at spike stage).
    let announce_line = label(move || announce_sig.get());

    // Query line (meaningful only while open; empty otherwise).
    let query_line = label(move || {
        if open_sig.get() {
            format!("> {}", query_sig.get())
        } else {
            String::new()
        }
    });

    // Palette overlay rows (≤50). dyn_stack reads rows_sig; empty when closed.
    let palette_rows = dyn_stack(
        move || rows_sig.get().into_iter().enumerate(),
        |(i, _)| *i,
        move |(i, (title, category, disabled))| {
            let is_sel = i == sel_sig.get();
            let t = theme_rows.clone();
            label(move || {
                let mark = if disabled { " (disabled)" } else { "" };
                format!("{title}  ·  {category}{mark}")
            })
            .style(move |s| {
                let s = s.color(fg(&t)).padding(2.0);
                if is_sel {
                    s.background(selected_bg(&t))
                } else {
                    s
                }
            })
        },
    )
    .style({
        let t = theme_palette.clone();
        move |s| {
            let base = s.flex_col().width(600.0).padding(8.0);
            if open_sig.get() {
                base.background(palette_bg(&t))
            } else {
                base
            }
        }
    });

    v_stack((focus_line, announce_line, query_line, palette_rows, rail))
        .style(|s| s.size_full().flex_col())
        .keyboard_navigable()
        .on_event_stop(EventListener::KeyDown, move |e| {
            if let Event::KeyDown(ke) = e {
                route(ke.key.logical_key.clone(), ke.modifiers);
            }
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_rail_honors_no_color() {
        let t = Theme::from_vars(Some("1"), None);
        let ctx = PortCtx { healthy: true, trusted: false };
        assert!(status_rail_text(&t, &ctx).starts_with("[OK]"));
        let c = Theme::from_vars(None, None);
        assert!(status_rail_text(&c, &ctx).starts_with("●"));
    }

    #[test]
    fn theme_colors_differ_by_mode() {
        assert_ne!(
            palette_bg(&Theme::from_vars(Some("1"), None)),
            palette_bg(&Theme::from_vars(None, None))
        );
        assert_ne!(
            fg(&Theme::from_vars(None, Some("1"))),
            fg(&Theme::from_vars(None, None))
        );
    }

    #[test]
    fn demo_registry_has_gated_command() {
        let r = demo_registry();
        let ctx = PortCtx { healthy: false, trusted: true };
        let runs = r.iter().find(|c| c.id.0 == "arc.runs.open").unwrap();
        assert!(matches!(runs.enablement(&ctx), Enablement::Disabled { .. }));
    }
}
