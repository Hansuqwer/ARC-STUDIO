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
/// IME composition state for the palette TypeBox — holds the committed text,
/// the in-progress composition mark, and cursor position (all in UTF-16 units
/// as required by NSTextInputClient / kit InputHandler).
#[derive(Default)]
pub struct TypeBoxContent {
    pub committed: String,
    pub marked: Option<String>,
    pub selected: usize, // UTF-16 cursor after committed text
}

impl TypeBoxContent {
    /// Full content including composition mark (what the text field displays).
    pub fn display(&self) -> String {
        match &self.marked {
            Some(m) => format!("{}{}", self.committed, m),
            None => self.committed.clone(),
        }
    }

    fn utf16_len(s: &str) -> usize {
        s.encode_utf16().count()
    }

    fn committed_utf16_len(&self) -> usize {
        Self::utf16_len(&self.committed)
    }
}

/// kit InputHandler implementation — exposes the TypeBox to NSTextInputClient
/// so IME composition renders inline in the palette query line (G6).
struct TypeBoxHandler {
    entity: Entity<ShellChromeView>,
}

impl InputHandler for TypeBoxHandler {
    fn selected_text_range(
        &mut self,
        _ignore_disabled: bool,
        _window: &mut Window,
        cx: &mut App,
    ) -> Option<UTF16Selection> {
        self.entity.read(cx).typebox.committed_utf16_len().pipe(|n| {
            Some(UTF16Selection { range: n..n, reversed: false })
        })
    }

    fn marked_text_range(&mut self, _window: &mut Window, cx: &mut App) -> Option<std::ops::Range<usize>> {
        let tb = &self.entity.read(cx).typebox;
        tb.marked.as_ref().map(|m| {
            let start = TypeBoxContent::utf16_len(&tb.committed);
            start..start + TypeBoxContent::utf16_len(m)
        })
    }

    fn text_for_range(
        &mut self,
        range_utf16: std::ops::Range<usize>,
        adjusted: &mut Option<std::ops::Range<usize>>,
        _window: &mut Window,
        cx: &mut App,
    ) -> Option<String> {
        let full = self.entity.read(cx).typebox.display();
        let chars: Vec<u16> = full.encode_utf16().collect();
        let start = range_utf16.start.min(chars.len());
        let end = range_utf16.end.min(chars.len());
        *adjusted = Some(start..end);
        String::from_utf16(&chars[start..end]).ok()
    }

    fn replace_text_in_range(
        &mut self,
        _range: Option<std::ops::Range<usize>>,
        text: &str,
        _window: &mut Window,
        cx: &mut App,
    ) {
        self.entity.update(cx, |view, cx| {
            view.typebox.marked = None;
            view.typebox.committed.push_str(text);
            // Mirror into the PaletteModel query for palette filtering.
            for ch in text.chars() {
                view.model.palette.key(
                    arc_ui::palette::PaletteKey::Char(ch),
                    &view.model.registry,
                    &view.model.ctx,
                );
            }
            cx.notify();
        });
    }

    fn replace_and_mark_text_in_range(
        &mut self,
        _range: Option<std::ops::Range<usize>>,
        new_text: &str,
        _new_selected: Option<std::ops::Range<usize>>,
        _window: &mut Window,
        cx: &mut App,
    ) {
        self.entity.update(cx, |view, cx| {
            view.typebox.marked = Some(new_text.to_string());
            cx.notify();
        });
    }

    fn unmark_text(&mut self, _window: &mut Window, cx: &mut App) {
        self.entity.update(cx, |view, cx| {
            if let Some(m) = view.typebox.marked.take() {
                view.typebox.committed.push_str(&m);
            }
            cx.notify();
        });
    }

    fn bounds_for_range(
        &mut self,
        _range: std::ops::Range<usize>,
        _window: &mut Window,
        _cx: &mut App,
    ) -> Option<Bounds<Pixels>> {
        // Return None — platform will position the candidate window near the
        // focused element. Returning real coordinates requires layout info
        // not yet wired (K2 scope; good enough for G6 inline composition proof).
        None
    }

    fn character_index_for_point(
        &mut self,
        _point: Point<Pixels>,
        _window: &mut Window,
        cx: &mut App,
    ) -> Option<usize> {
        Some(self.entity.read(cx).typebox.committed_utf16_len())
    }
}

// Convenience extension to pipe a value through a closure (avoids temp bindings).
trait Pipe: Sized {
    fn pipe<R>(self, f: impl FnOnce(Self) -> R) -> R { f(self) }
}
impl<T: Sized> Pipe for T {}

pub struct ShellChromeView {
    pub model: ShellModel,
    pub announce: String,
    pub focus_handle: FocusHandle,
    /// IME composition state for the palette TypeBox (G6).
    pub typebox: TypeBoxContent,
    /// K4: Event Stream dock panel (replay-parity model → live SSE).
    pub events: arc_dock::EventStreamPanel,
    /// K4: live per-run SSE receiver (None = fixture-seeded only).
    pub live_rx: Option<std::sync::mpsc::Receiver<arc_protocol_rs::RunEvent>>,
}

/// K4: spawn a background per-run SSE feed from the live daemon.
///
/// Returns a receiver the gpui view drains in `render()`. The daemon stream
/// runs on its own thread+runtime (gpui owns the main thread); events cross
/// via a std mpsc channel. If the daemon is unreachable the thread exits
/// quietly and the panel keeps its fixture-seeded rows (producer-truth: the
/// footer still names `daemon.run_events`).
pub fn spawn_live_feed(
    base: String,
    run_id: String,
) -> std::sync::mpsc::Receiver<arc_protocol_rs::RunEvent> {
    use arc_daemon_client::DaemonClient;
    let (tx, rx) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let rt = match tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
        {
            Ok(rt) => rt,
            Err(_) => return,
        };
        rt.block_on(async move {
            let Ok(client) = DaemonClient::new(&base) else { return };
            let cancel = tokio_util::sync::CancellationToken::new();
            // stream_run_events feeds each decoded RunEvent to the channel;
            // ordered-queue gap handling stays in EventStreamPanel::on_event.
            let _ = client
                .stream_run_events(&run_id, cancel, |ev| {
                    let _ = tx.send(ev);
                })
                .await;
        });
    });
    rx
}

impl ShellChromeView {
    pub fn new(model: ShellModel, cx: &mut Context<Self>) -> Self {
        // K4: seed the Event Stream panel from the committed replay fixture so
        // the dock renders a real model→view path immediately. A live daemon
        // SSE feed (per-run) replaces this when connected (see feed_live_events).
        let mut events = arc_dock::EventStreamPanel::new(256);
        let fixture = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../protocol/fixtures/run-event-seq/tool-use-streaming");
        let _ = arc_daemon_client::replay::replay_dir(&fixture, |ev| {
            let _ = events.on_event(ev);
        });
        // K4 live path: if ARC_RUN_ID is set, attach a per-run SSE feed from the
        // daemon (ARC_DAEMON_URL or default loopback). Absent → fixture-only.
        let live_rx = std::env::var("ARC_RUN_ID").ok().map(|run_id| {
            let base = std::env::var("ARC_DAEMON_URL")
                .unwrap_or_else(|_| "http://127.0.0.1:7777".into());
            spawn_live_feed(base, run_id)
        });
        Self {
            announce: String::new(),
            focus_handle: cx.focus_handle(),
            typebox: TypeBoxContent::default(),
            events,
            live_rx,
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
    fn render(&mut self, window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        // K4: drain any live per-run SSE events into the panel (non-blocking).
        // Same on_event path as the fixture replay — ordered-queue gap handling
        // and SurfaceState transitions are identical (parity oracle holds).
        if self.live_rx.is_some() {
            let drained: Vec<_> = self
                .live_rx
                .as_ref()
                .map(|rx| rx.try_iter().collect())
                .unwrap_or_default();
            for ev in drained {
                let _ = self.events.on_event(ev);
            }
        }
        // Register the InputHandler so NSTextInputClient/IME sends composition
        // inline into the TypeBox rather than a floating fallback window (G6).
        window.handle_input(
            &self.focus_handle.clone(),
            TypeBoxHandler { entity: cx.entity().clone() },
            cx,
        );

        // G5: attach the ARC accessibility tree to the gpui NSView (macOS).
        // Truth lives in arc_ui::a11y; this only bridges it to NSAccessibility.
        #[cfg(target_os = "macos")]
        {
            let regions: Vec<(&str, &str)> = self
                .model
                .focus
                .regions_for_a11y();
            let rows: Vec<(String, bool)> = self
                .model
                .palette
                .items
                .iter()
                .take(50)
                .map(|it| (it.title.clone(), matches!(it.enablement, Enablement::Disabled { .. })))
                .collect();
            let status = self.model.status_rail();
            let snap = arc_ui::a11y::A11ySnapshot {
                focused_region_id: current_focus_id(&self.model),
                regions: &regions,
                palette_open: self.model.palette.open,
                palette_query: &self.model.palette.query,
                palette_rows: &rows,
                palette_selected: self.model.palette.selected,
                typebox_text: &self.typebox.committed,
                status_rail: &status,
            };
            let tree = arc_ui::a11y::ShellA11yTree::build(&snap);
            crate::a11y_macos::attach_a11y_tree(window, &tree);
        }
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
                .child(div().child(format!("> {}{}", self.model.palette.query,
                    self.typebox.marked.as_deref().map(|m| format!("[{m}]")).unwrap_or_default())))
                .children(rows)
                .into_any_element()
        } else {
            div().into_any_element()
        };

        // K4: Event Stream dock — render the EventStreamPanel rows with the
        // same fixed-width line discipline as the spike, plus surface-state
        // header and footer (rows/dropped/source). Last 12 rows shown.
        let ev_rows: Vec<AnyElement> = self
            .events
            .rows()
            .iter()
            .rev()
            .take(12)
            .rev()
            .map(|r| {
                div()
                    .font_family("Menlo")
                    .text_size(px(11.0))
                    .text_color(fg(&theme))
                    .child(r.display_line())
                    .into_any_element()
            })
            .collect();
        let ev_state = self.events.state().describe();
        let ev_footer = self.events.footer();
        let event_dock = div()
            .flex()
            .flex_col()
            .p_2()
            .bg(panel_bg(&theme, current == "dock"))
            .child(div().child(format!("ARC dock · Event Stream — {ev_state}")))
            .children(ev_rows)
            .child(div().text_size(px(10.0)).child(ev_footer));

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
            .child(event_dock)
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
