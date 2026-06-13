//! M5 editor render helpers for the selected framework.
//!
//! Framework items are imported only through `arc_ui::kit::*`; editor state is
//! supplied by the framework-free `EditorController`.

#![cfg(feature = "framework-gpui")]

use crate::editor_controller::EditorController;
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

fn editor_bg(theme: &Theme, focused: bool) -> Rgba {
    match (theme.no_color, theme.high_contrast, focused) {
        (true, _, true) => rgb(0xf0f0f0),
        (true, _, false) => rgb(0xffffff),
        (_, true, true) => rgb(0x202000),
        (_, true, false) => rgb(0x000000),
        (_, _, true) => rgb(0x1f2f46),
        (_, _, false) => rgb(0x1e1e1e),
    }
}

fn cursor_line(text: &str, cursor_col: Option<usize>) -> String {
    let Some(col) = cursor_col else {
        return text.to_string();
    };
    let mut out = String::new();
    for (idx, ch) in text.chars().enumerate() {
        if idx == col {
            out.push('▏');
        }
        out.push(ch);
    }
    if col >= text.chars().count() {
        out.push('▏');
    }
    out
}

pub fn editor_panel(theme: &Theme, focused: bool, editor: &EditorController) -> AnyElement {
    let title = editor
        .path()
        .map(|p| p.display().to_string())
        .unwrap_or_else(|| "Untitled".to_string());
    let dirty = if editor.dirty() { " ● dirty" } else { "" };
    let rows: Vec<AnyElement> = editor
        .visible_lines(24)
        .into_iter()
        .map(|line| {
            let selected = line
                .selected
                .as_ref()
                .map(|r| format!("  selected:{}..{}", r.start, r.end))
                .unwrap_or_default();
            div()
                .font_family("Menlo")
                .text_size(px(12.0))
                .text_color(fg(theme))
                .child(format!(
                    "{:>4} {}{}",
                    line.line_index + 1,
                    cursor_line(&line.text, line.cursor_col),
                    selected
                ))
                .into_any_element()
        })
        .collect();

    div()
        .flex()
        .flex_col()
        .p_2()
        .bg(editor_bg(theme, focused))
        .child(div().child(format!("Editor — {title}{dirty}")))
        .children(rows)
        .into_any_element()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cursor_line_inserts_marker() {
        assert_eq!(cursor_line("abc", Some(1)), "a▏bc");
        assert_eq!(cursor_line("abc", Some(3)), "abc▏");
        assert_eq!(cursor_line("abc", None), "abc");
    }
}
