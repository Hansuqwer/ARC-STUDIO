//! M7 terminal render helpers for the selected framework.

#![cfg(feature = "framework-gpui")]

use crate::terminal_controller::{TerminalController, TerminalStatus};
use arc_ui::kit::*;
use arc_ui::theme::Theme;

fn fg(theme: &Theme) -> Rgba {
    if theme.no_color {
        rgb(0x000000)
    } else if theme.high_contrast {
        rgb(0xffffff)
    } else {
        rgb(0xd4d4d4)
    }
}

fn bg(theme: &Theme, focused: bool) -> Rgba {
    match (theme.no_color, theme.high_contrast, focused) {
        (true, _, true) => rgb(0xf0f0f0),
        (true, _, false) => rgb(0xffffff),
        (_, true, true) => rgb(0x202000),
        (_, true, false) => rgb(0x000000),
        (_, _, true) => rgb(0x102030),
        (_, _, false) => rgb(0x111111),
    }
}

fn status_text(status: &TerminalStatus) -> String {
    match status {
        TerminalStatus::Empty => "not started".into(),
        TerminalStatus::Running => "running".into(),
        TerminalStatus::Exited(code) => format!(
            "exited ({})",
            code.map(|c| c.to_string())
                .unwrap_or_else(|| "unknown".into())
        ),
        TerminalStatus::Error(err) => format!("error: {err}"),
    }
}

pub fn terminal_panel(theme: &Theme, focused: bool, terminal: &TerminalController) -> AnyElement {
    let (cols, lines) = terminal.size();
    let rows: Vec<AnyElement> = terminal
        .rows()
        .iter()
        .map(|row| {
            div()
                .font_family("Menlo")
                .text_size(px(11.0))
                .text_color(fg(theme))
                .child(row.clone())
                .into_any_element()
        })
        .collect();

    div()
        .flex()
        .flex_col()
        .p_2()
        .bg(bg(theme, focused))
        .child(div().child(format!(
            "Terminal — {} · {}x{}",
            status_text(terminal.status()),
            cols,
            lines
        )))
        .children(rows)
        .into_any_element()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_text_is_explicit() {
        assert_eq!(status_text(&TerminalStatus::Empty), "not started");
        assert!(status_text(&TerminalStatus::Error("boom".into())).contains("boom"));
    }
}
