//! M6 workspace/search render helpers for the selected framework.

#![cfg(feature = "framework-gpui")]

use crate::search_controller::SearchController;
use crate::workspace_controller::WorkspaceController;
use arc_ui::kit::*;
use arc_ui::theme::Theme;
use arc_workspace::NodeKind;

fn fg(theme: &Theme) -> Rgba {
    if theme.no_color {
        rgb(0x000000)
    } else if theme.high_contrast {
        rgb(0xffffff)
    } else {
        rgb(0xd4d4d4)
    }
}

fn row_bg(theme: &Theme, selected: bool) -> Rgba {
    match (theme.no_color, theme.high_contrast, selected) {
        (true, _, true) => rgb(0xd0d0d0),
        (true, _, false) => rgb(0xffffff),
        (_, true, true) => rgb(0xffff00),
        (_, true, false) => rgb(0x000000),
        (_, _, true) => rgb(0x094f9c),
        (_, _, false) => rgb(0x252526),
    }
}

pub fn workspace_panel(theme: &Theme, workspace: &WorkspaceController) -> AnyElement {
    let rows: Vec<AnyElement> = workspace
        .rows()
        .into_iter()
        .map(|row| {
            let marker = match (row.kind, row.expanded) {
                (NodeKind::Dir, true) => "▾",
                (NodeKind::Dir, false) => "▸",
                (NodeKind::File, _) => " ",
            };
            div()
                .font_family("Menlo")
                .text_size(px(12.0))
                .text_color(fg(theme))
                .bg(row_bg(theme, row.selected))
                .child(format!(
                    "{}{} {}",
                    "  ".repeat(row.depth),
                    marker,
                    row.label
                ))
                .into_any_element()
        })
        .collect();

    div()
        .flex()
        .flex_col()
        .p_2()
        .child(div().child(format!("Workspace — {}", workspace.root().display())))
        .children(rows)
        .into_any_element()
}

pub fn search_panel(theme: &Theme, search: &SearchController) -> AnyElement {
    let rows: Vec<AnyElement> = search
        .rows()
        .iter()
        .map(|row| {
            let line = row.line_number.map(|n| format!(":{n}")).unwrap_or_default();
            let snippet = row
                .snippet
                .as_deref()
                .map(|s| format!(" — {s}"))
                .unwrap_or_default();
            div()
                .font_family("Menlo")
                .text_size(px(12.0))
                .text_color(fg(theme))
                .bg(row_bg(theme, row.selected))
                .child(format!("{}{}{}", row.label, line, snippet))
                .into_any_element()
        })
        .collect();

    div()
        .flex()
        .flex_col()
        .p_2()
        .child(div().child(format!("Search — {}", search.query())))
        .children(rows)
        .into_any_element()
}
