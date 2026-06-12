//! gpui render seed for the real ARC shell chrome (K2).
//!
//! This module is compiled only with `arc-shell/framework-gpui`. It imports the
//! selected framework through `arc_ui::kit`, preserving the facade rule at the
//! source level while letting the shell prove model→render wiring on the M4.
//! Headless modes do not compile this module.

#![cfg(feature = "framework-gpui")]

use crate::ShellModel;
use arc_ui::command::Enablement;
use arc_ui::kit::*;
use arc_ui::palette::{PaletteEffect, PaletteKey};
use arc_ui::theme::Theme;

/// Open the native gpui window for the already-populated shell model.
///
/// Pixel evidence is intentionally collected on the pinned M4/display. This
/// sandbox can only prepare the cfg-gated structure and keep headless modes
/// green.
pub fn open_window(model: ShellModel) {
    Application::new().run(move |cx: &mut App| {
        let options = WindowOptions {
            window_bounds: Some(WindowBounds::Windowed(Bounds {
                origin: point(px(100.0), px(100.0)),
                size: size(px(960.0), px(640.0)),
            })),
            titlebar: Some(TitlebarOptions {
                title: Some("ARC Studio v2 — gpui shell".into()),
                ..Default::default()
            }),
            ..Default::default()
        };

        if cx
            .open_window(options, move |_window, cx| {
                cx.new(|cx| ShellChromeView::new(model, cx))
            })
            .is_err()
        {
            cx.quit();
            return;
        }
        cx.activate(true);
    });
}

fn shell_bg(theme: &Theme) -> Rgba {
    if theme.no_color {
        rgb(0xffffff)
    } else if theme.high_contrast {
        rgb(0x000000)
    } else {
        rgb(0x1e1e1e)
    }
}

fn fg(theme: &Theme) -> Rgba {
    if theme.no_color {
        rgb(0x000000)
    } else if theme.high_contrast {
        rgb(0xffffff)
    } else {
        rgb(0xd4d4d4)
    }
}

fn panel_bg(theme: &Theme, focused: bool) -> Rgba {
    match (theme.no_color, theme.high_contrast, focused) {
        (true, _, true) => rgb(0xe6e6e6),
        (true, _, false) => rgb(0xffffff),
        (_, true, true) => rgb(0x303000),
        (_, true, false) => rgb(0x000000),
        (_, _, true) => rgb(0x094f9c),
        (_, _, false) => rgb(0x252526),
    }
}

fn palette_bg(theme: &Theme) -> Rgba {
    if theme.no_color {
        rgb(0xffffff)
    } else if theme.high_contrast {
        rgb(0x000000)
    } else {
        rgb(0x252526)
    }
}

fn selected_bg(theme: &Theme) -> Rgba {
    if theme.high_contrast {
        rgb(0xffff00)
    } else if theme.no_color {
        rgb(0xd0d0d0)
    } else {
        rgb(0x094f9c)
    }
}

fn current_focus_id(model: &ShellModel) -> &'static str {
    model.focus.current().map(|r| r.id).unwrap_or("workspace")
}

fn current_focus_label(model: &ShellModel) -> &'static str {
    model
        .focus
        .current()
        .map(|r| r.label)
        .unwrap_or("Workspace tree")
}

fn region_card(
    theme: &Theme,
    current: &str,
    id: &'static str,
    label: &'static str,
    body: &'static str,
) -> AnyElement {
    let focused = current == id;
    let prefix = if focused { "focus ▸ " } else { "" };
    div()
        .p_2()
        .bg(panel_bg(theme, focused))
        .text_color(fg(theme))
        .child(format!("{prefix}{label}"))
        .child(div().child(body))
        .into_any_element()
}

/// The real shell-chrome gpui view. It holds the ARC-owned ShellModel directly:
/// input mutates the model, render reads the model, and `cx.notify()` requests
/// the repaint. No parallel palette/focus state is introduced.
pub struct ShellChromeView {
    pub model: ShellModel,
    pub announce: String,
    pub focus_handle: FocusHandle,
}

impl ShellChromeView {
    pub fn new(model: ShellModel, cx: &mut Context<Self>) -> Self {
        Self {
            announce: String::new(),
            focus_handle: cx.focus_handle(),
            model,
        }
    }

    fn on_key(&mut self, key: &str, modifiers: &Modifiers) {
        if key == "f6" {
            let focused = if modifiers.shift {
                self.model.focus.focus_prev()
            } else {
                self.model.focus.focus_next()
            };
            if let Some(region) = focused {
                self.announce = format!("focus: {}", region.label);
            }
            return;
        }

        if key == "p" && modifiers.control && modifiers.shift {
            self.model
                .palette
                .open_with(&self.model.registry, &self.model.ctx);
            self.announce = "palette opened".into();
            return;
        }

        if !self.model.palette.open {
            return;
        }

        let Some(key) = palette_key(key) else {
            return;
        };
        match self
            .model
            .palette
            .key(key, &self.model.registry, &self.model.ctx)
        {
            PaletteEffect::Announce(announcement) => self.announce = announcement,
            PaletteEffect::Execute(id) => self.announce = format!("execute: {}", id.0),
            PaletteEffect::Rejected { reason } => self.announce = format!("rejected: {reason}"),
            PaletteEffect::Closed => self.announce = "closed".into(),
            PaletteEffect::None => {}
        }
    }
}

fn palette_key(key: &str) -> Option<PaletteKey> {
    match key {
        "backspace" => Some(PaletteKey::Backspace),
        "up" => Some(PaletteKey::Up),
        "down" => Some(PaletteKey::Down),
        "enter" => Some(PaletteKey::Enter),
        "escape" => Some(PaletteKey::Escape),
        s if s.chars().count() == 1 => s.chars().next().map(PaletteKey::Char),
        _ => None,
    }
}

impl Render for ShellChromeView {
    fn render(&mut self, _window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        let theme = self.model.theme.clone();
        let current = current_focus_id(&self.model);
        let rows: Vec<AnyElement> = self
            .model
            .palette
            .items
            .iter()
            .take(50)
            .enumerate()
            .map(|(i, item)| {
                let disabled = matches!(item.enablement, Enablement::Disabled { .. });
                let mark = if disabled { " (disabled)" } else { "" };
                let shortcut = item
                    .shortcut
                    .as_deref()
                    .map(|s| format!(" [{s}]"))
                    .unwrap_or_default();
                let mut row = div().text_color(fg(&theme)).px_1().child(format!(
                    "{} · {}{}{}",
                    item.title, item.category, shortcut, mark
                ));
                if i == self.model.palette.selected {
                    row = row.bg(selected_bg(&theme));
                }
                row.into_any_element()
            })
            .collect();

        let palette_block = if self.model.palette.open {
            div()
                .bg(palette_bg(&theme))
                .p_2()
                .w(px(640.0))
                .flex()
                .flex_col()
                .child(div().child(format!("> {}", self.model.palette.query)))
                .children(rows)
                .into_any_element()
        } else {
            div().into_any_element()
        };

        div()
            .track_focus(&self.focus_handle)
            .key_context("ArcShell")
            .on_key_down(cx.listener(|view, event: &KeyDownEvent, _window, cx| {
                view.on_key(event.keystroke.key.as_str(), &event.keystroke.modifiers);
                cx.notify();
            }))
            .size_full()
            .flex()
            .flex_col()
            .bg(shell_bg(&theme))
            .text_color(fg(&theme))
            .child(div().p_1().child("ARC Studio v2 — native gpui shell"))
            .child(div().p_1().child(format!(
                "focus: {} | {}",
                current_focus_label(&self.model),
                self.announce
            )))
            .child(
                div()
                    .flex()
                    .child(region_card(
                        &theme,
                        current,
                        "workspace",
                        "Workspace tree",
                        "project files placeholder",
                    ))
                    .child(region_card(
                        &theme,
                        current,
                        "editor",
                        "Editor",
                        "editor surface placeholder",
                    ))
                    .child(region_card(
                        &theme,
                        current,
                        "dock",
                        "ARC dock",
                        "event stream / HITL dock placeholder",
                    ))
                    .child(region_card(
                        &theme,
                        current,
                        "status",
                        "Status rail",
                        "daemon/trust strip landmark",
                    )),
            )
            .child(palette_block)
            .child(div().mt_auto().p_1().child(self.model.status_rail()))
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;
    use crate::DaemonState;

    #[test]
    fn palette_key_maps_printable_and_controls() {
        assert_eq!(palette_key("x"), Some(PaletteKey::Char('x')));
        assert_eq!(palette_key("enter"), Some(PaletteKey::Enter));
        assert_eq!(palette_key("unknown"), None);
    }

    #[test]
    fn theme_colors_differ_by_mode() {
        assert_ne!(
            palette_bg(&Theme::from_vars(Some("1"), None)).r,
            palette_bg(&Theme::from_vars(None, None)).r
        );
        assert_ne!(
            panel_bg(&Theme::from_vars(None, Some("1")), true).g,
            panel_bg(&Theme::from_vars(None, None), true).g
        );
    }

    #[test]
    fn current_focus_defaults_to_workspace() {
        let model = ShellModel::new(Theme::from_vars(None, None));
        assert_eq!(current_focus_id(&model), "workspace");
        assert_eq!(current_focus_label(&model), "Workspace tree");
    }

    #[test]
    fn status_rail_renders_degraded_text_from_live_model_state() {
        let mut model = ShellModel::new(Theme::from_vars(Some("1"), None));
        model.ctx.daemon = DaemonState::Degraded {
            reason: "kill test".into(),
        };
        assert!(model.status_rail().contains("daemon degraded: kill test"));
        assert!(model.status_rail().starts_with("[ERR]"));
    }
}
