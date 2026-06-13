//! a11y — ARC-owned semantic accessibility tree (framework-free).
//!
//! The accessibility *truth* lives here, in ARC vocabulary, not in any
//! framework's render code. A platform bridge (e.g. macOS NSAccessibility in
//! `arc-shell::render_gpui`) translates this tree into the OS a11y API. If the
//! Sprint-3 framework ever swaps (floem escape), this exact tree is reused —
//! only the ~50-line platform bridge changes.
//!
//! Wireframe §6.1: every region is a labeled landmark. This module is the
//! single source of those labels/roles, derived from the live ShellModel state.

/// Accessibility roles ARC cares about (mapped to NSAccessibilityRole /
/// AT-SPI / UIA at the platform bridge).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum A11yRole {
    /// A labeled landmark region (workspace/editor/dock/status).
    Group,
    /// The command palette modal overlay.
    Dialog,
    /// A single-line text input (the palette query / type box).
    TextField,
    /// A list of rows (palette results, event table).
    List,
    /// A row within a list.
    Row,
    /// A static status/label line.
    StaticText,
}

/// One node in the ARC accessibility tree.
#[derive(Debug, Clone, PartialEq)]
pub struct A11yNode {
    pub role: A11yRole,
    /// Accessible name announced by the screen reader.
    pub label: String,
    /// Optional value (e.g. the current text in a field, or row content).
    pub value: Option<String>,
    /// Whether this node is the currently focused element.
    pub focused: bool,
    pub children: Vec<A11yNode>,
}

impl A11yNode {
    pub fn new(role: A11yRole, label: impl Into<String>) -> Self {
        Self {
            role,
            label: label.into(),
            value: None,
            focused: false,
            children: Vec::new(),
        }
    }

    pub fn with_value(mut self, value: impl Into<String>) -> Self {
        self.value = Some(value.into());
        self
    }

    pub fn focused(mut self, focused: bool) -> Self {
        self.focused = focused;
        self
    }

    pub fn child(mut self, node: A11yNode) -> Self {
        self.children.push(node);
        self
    }
}

/// The full shell accessibility tree (the root is the window).
#[derive(Debug, Clone, PartialEq)]
pub struct ShellA11yTree {
    /// Window title (announced on focus per G5 step 1).
    pub window_title: String,
    pub root: A11yNode,
}

/// Inputs the tree builder reads — kept framework-free and trivially
/// constructible from ShellModel in the render layer.
pub struct A11ySnapshot<'a> {
    pub focused_region_id: &'a str,
    /// (id, label) for the four landmark regions in focus order.
    pub regions: &'a [(&'a str, &'a str)],
    pub palette_open: bool,
    pub palette_query: &'a str,
    /// (title, disabled) for visible palette rows (≤50).
    pub palette_rows: &'a [(String, bool)],
    pub palette_selected: usize,
    pub typebox_text: &'a str,
    pub status_rail: &'a str,
    /// M8: current editor summary/value.
    pub editor_value: &'a str,
    pub editor_dirty: bool,
    /// M9: workspace/search semantic rows.
    pub workspace_rows: &'a [(String, bool)],
    pub search_query: &'a str,
    pub search_rows: &'a [(String, bool)],
    /// M10: terminal semantic status.
    pub terminal_status: &'a str,
    pub terminal_current_line: &'a str,
}

impl ShellA11yTree {
    /// Build the tree from a snapshot of live shell state. Pure; testable
    /// without any framework.
    pub fn build(snap: &A11ySnapshot) -> Self {
        let mut root = A11yNode::new(A11yRole::Group, "ARC Studio shell");

        // Four labeled landmark regions (wireframe §6.1).
        for (id, label) in snap.regions {
            let focused = *id == snap.focused_region_id;
            root = root.child(A11yNode::new(A11yRole::Group, *label).focused(focused));
        }

        // Status rail landmark (always present; text equivalent of daemon dot).
        root = root
            .child(A11yNode::new(A11yRole::StaticText, "Status rail").with_value(snap.status_rail));

        // M8: editor semantic text area summary.
        let editor_state = if snap.editor_dirty { "dirty" } else { "clean" };
        root = root.child(
            A11yNode::new(A11yRole::TextField, "Editor")
                .with_value(format!("{}; {editor_state}", snap.editor_value))
                .focused(snap.focused_region_id == "editor"),
        );

        // M9: workspace tree rows and search results.
        let mut workspace = A11yNode::new(A11yRole::List, "Workspace tree")
            .focused(snap.focused_region_id == "workspace");
        for (label, selected) in snap.workspace_rows.iter().take(100) {
            workspace =
                workspace.child(A11yNode::new(A11yRole::Row, label.clone()).focused(*selected));
        }
        root = root.child(workspace);
        if !snap.search_query.is_empty() || !snap.search_rows.is_empty() {
            let search_focused = snap.focused_region_id == "search";
            let mut search = A11yNode::new(A11yRole::Dialog, "Workspace search")
                .focused(search_focused)
                .child(
                    A11yNode::new(A11yRole::TextField, "Search query")
                        .with_value(snap.search_query)
                        // M12: query field is focused when the search region is active
                        // so VoiceOver announces it and the cursor lands on the input.
                        .focused(search_focused),
                );
            let mut results = A11yNode::new(A11yRole::List, "Search results");
            for (label, selected) in snap.search_rows.iter().take(100) {
                results =
                    results.child(A11yNode::new(A11yRole::Row, label.clone()).focused(*selected));
            }
            search = search.child(results);
            root = root.child(search);
        }

        // M10: terminal status/current line summary.
        root = root.child(
            A11yNode::new(A11yRole::StaticText, "Terminal")
                .with_value(format!(
                    "{}; {}",
                    snap.terminal_status, snap.terminal_current_line
                ))
                .focused(snap.focused_region_id == "dock"),
        );

        // Command palette dialog (only when open).
        if snap.palette_open {
            let mut dialog = A11yNode::new(A11yRole::Dialog, "Command palette").focused(true);
            dialog = dialog.child(
                A11yNode::new(A11yRole::TextField, "Command query").with_value(snap.palette_query),
            );
            let mut list = A11yNode::new(A11yRole::List, "Command results");
            for (i, (title, disabled)) in snap.palette_rows.iter().enumerate().take(50) {
                let state = if *disabled { "disabled" } else { "enabled" };
                list = list.child(
                    A11yNode::new(A11yRole::Row, title.clone())
                        .with_value(state)
                        .focused(i == snap.palette_selected),
                );
            }
            dialog = dialog.child(list);
            root = root.child(dialog);
        } else {
            // Type box exposed even when palette closed (G5 step 4: char echo).
            root = root.child(
                A11yNode::new(A11yRole::TextField, "Type box").with_value(snap.typebox_text),
            );
        }

        Self {
            window_title: "ARC Studio v2 — gpui shell".to_string(),
            root,
        }
    }

    /// Flatten to (role, label, value, focused) tuples in tree order — what a
    /// flat platform bridge (one NSAccessibilityElement per node) consumes.
    pub fn flatten(&self) -> Vec<(A11yRole, String, Option<String>, bool)> {
        fn walk(n: &A11yNode, out: &mut Vec<(A11yRole, String, Option<String>, bool)>) {
            out.push((n.role, n.label.clone(), n.value.clone(), n.focused));
            for c in &n.children {
                walk(c, out);
            }
        }
        let mut out = Vec::new();
        walk(&self.root, &mut out);
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn regions() -> Vec<(&'static str, &'static str)> {
        vec![
            ("workspace", "Workspace tree"),
            ("editor", "Editor"),
            ("dock", "ARC dock"),
            ("status", "Status rail"),
        ]
    }

    fn base_snapshot<'a>(regions: &'a [(&'a str, &'a str)]) -> A11ySnapshot<'a> {
        A11ySnapshot {
            focused_region_id: "workspace",
            regions,
            palette_open: false,
            palette_query: "",
            palette_rows: &[],
            palette_selected: 0,
            typebox_text: "",
            status_rail: "● daemon healthy | trust: trusted",
            editor_value: "line 1 column 1",
            editor_dirty: false,
            workspace_rows: &[],
            search_query: "",
            search_rows: &[],
            terminal_status: "running",
            terminal_current_line: "prompt$",
        }
    }

    #[test]
    fn tree_has_window_title_and_four_landmarks() {
        let r = regions();
        let tree = ShellA11yTree::build(&base_snapshot(&r));
        assert!(tree.window_title.contains("ARC Studio"));
        let groups: Vec<_> = tree
            .root
            .children
            .iter()
            .filter(|n| n.role == A11yRole::Group)
            .collect();
        assert_eq!(groups.len(), 4, "four labeled landmark regions");
        assert!(groups.iter().any(|g| g.label == "Editor"));
    }

    #[test]
    fn focused_region_is_marked() {
        let r = regions();
        let mut snap = base_snapshot(&r);
        snap.focused_region_id = "dock";
        let tree = ShellA11yTree::build(&snap);
        let Some(dock) = tree.root.children.iter().find(|n| n.label == "ARC dock") else {
            panic!("ARC dock landmark present in a11y tree");
        };
        assert!(dock.focused, "focused landmark flagged for VO");
    }

    #[test]
    fn open_palette_exposes_dialog_field_and_rows() {
        let r = regions();
        let mut snap = base_snapshot(&r);
        snap.palette_open = true;
        snap.palette_query = "run";
        let rows = vec![
            ("ARC: Open Runs".to_string(), false),
            ("ARC: Replay".to_string(), true),
        ];
        snap.palette_rows = &rows;
        snap.palette_selected = 0;
        let tree = ShellA11yTree::build(&snap);
        let flat = tree.flatten();
        assert!(flat.iter().any(|(role, _, _, _)| *role == A11yRole::Dialog));
        assert!(flat
            .iter()
            .any(|(role, l, _, _)| *role == A11yRole::TextField && l == "Command query"));
        let rows_flat: Vec<_> = flat
            .iter()
            .filter(|(role, _, _, _)| *role == A11yRole::Row)
            .collect();
        assert_eq!(rows_flat.len(), 2);
        // disabled state announced via value
        assert!(rows_flat
            .iter()
            .any(|(_, l, v, _)| l == "ARC: Replay" && v.as_deref() == Some("disabled")));
    }

    #[test]
    fn closed_palette_exposes_typebox() {
        let r = regions();
        let mut snap = base_snapshot(&r);
        snap.typebox_text = "abc";
        let tree = ShellA11yTree::build(&snap);
        let flat = tree.flatten();
        assert!(flat
            .iter()
            .any(|(role, l, v, _)| *role == A11yRole::TextField
                && l == "Type box"
                && v.as_deref() == Some("abc")));
    }

    #[test]
    fn status_rail_value_carries_text() {
        let r = regions();
        let tree = ShellA11yTree::build(&base_snapshot(&r));
        let flat = tree.flatten();
        assert!(flat
            .iter()
            .any(|(role, l, v, _)| *role == A11yRole::StaticText
                && l == "Status rail"
                && v.as_deref().unwrap_or("").contains("daemon healthy")));
    }

    #[test]
    fn flatten_is_tree_order_root_first() {
        let r = regions();
        let tree = ShellA11yTree::build(&base_snapshot(&r));
        let flat = tree.flatten();
        assert_eq!(flat[0].1, "ARC Studio shell", "root first");
    }

    #[test]
    fn polish_surfaces_have_semantic_nodes() {
        let r = regions();
        let workspace_rows = vec![("src/main.rs".to_string(), true)];
        let search_rows = vec![("src/main.rs: fn main".to_string(), false)];
        let snap = A11ySnapshot {
            workspace_rows: &workspace_rows,
            search_query: "main",
            search_rows: &search_rows,
            editor_value: "line 2 column 3",
            editor_dirty: true,
            terminal_status: "running",
            terminal_current_line: "arc$ echo hi",
            ..base_snapshot(&r)
        };
        let flat = ShellA11yTree::build(&snap).flatten();
        assert!(flat.iter().any(|(role, label, value, _)| {
            *role == A11yRole::TextField
                && label == "Editor"
                && value.as_deref().unwrap_or("").contains("dirty")
        }));
        assert!(flat.iter().any(|(role, label, _, focused)| {
            *role == A11yRole::Row && label == "src/main.rs" && *focused
        }));
        assert!(flat.iter().any(|(_, label, value, _)| {
            label == "Terminal" && value.as_deref().unwrap_or("").contains("echo hi")
        }));
    }

    // M12 a11y tests ─────────────────────────────────────────────────────────

    #[test]
    fn search_region_focused_marks_query_field_focused() {
        let r = regions();
        let search_rows = vec![("docs/audit.md".to_string(), false)];
        let mut snap = base_snapshot(&r);
        snap.focused_region_id = "search";
        snap.search_query = "audit";
        snap.search_rows = &search_rows;
        let flat = ShellA11yTree::build(&snap).flatten();
        let Some(dialog) = flat
            .iter()
            .find(|(role, label, _, _)| *role == A11yRole::Dialog && label == "Workspace search")
        else {
            panic!("Workspace search dialog absent from a11y tree");
        };
        assert!(dialog.3, "Workspace search dialog is focused");
        let Some(query_field) = flat
            .iter()
            .find(|(role, label, _, _)| *role == A11yRole::TextField && label == "Search query")
        else {
            panic!("Search query field absent from a11y tree");
        };
        assert!(
            query_field.3,
            "Search query field focused when search region is active"
        );
    }

    #[test]
    fn search_panel_absent_from_tree_when_empty() {
        let r = regions();
        let snap = base_snapshot(&r);
        let flat = ShellA11yTree::build(&snap).flatten();
        assert!(
            !flat
                .iter()
                .any(|(_, label, _, _)| label == "Workspace search"),
            "search dialog absent when query and results are both empty"
        );
    }

    #[test]
    fn m12_all_surfaces_have_labeled_nodes() {
        let r = regions();
        let workspace_rows = vec![(".github".to_string(), false), ("docs".to_string(), true)];
        let search_rows = vec![("docs/audit.md".to_string(), true)];
        let degraded_rail = "◯ daemon degraded: health probe timeout (2s) | trust: UNTRUSTED";
        let snap = A11ySnapshot {
            focused_region_id: "search",
            workspace_rows: &workspace_rows,
            search_query: "audit",
            search_rows: &search_rows,
            editor_value: "line 1 column 1",
            editor_dirty: false,
            terminal_status: "exited (0)",
            terminal_current_line: "",
            status_rail: degraded_rail,
            ..base_snapshot(&r)
        };
        let flat = ShellA11yTree::build(&snap).flatten();
        let labels: Vec<&str> = flat.iter().map(|(_, l, _, _)| l.as_str()).collect();
        for required in [
            "ARC Studio shell",
            "Workspace tree",
            "Editor",
            "ARC dock",
            "Status rail",
            "Workspace search",
            "Search query",
            "Terminal",
        ] {
            assert!(
                labels.contains(&required),
                "M12 audit: missing node '{required}' in a11y tree"
            );
        }
        let Some(status_node) = flat
            .iter()
            .find(|(role, l, _, _)| *role == A11yRole::StaticText && l == "Status rail")
        else {
            panic!("Status rail StaticText node missing from a11y tree");
        };
        assert!(
            status_node.2.as_deref().unwrap_or("").contains("degraded"),
            "status rail value announces degraded state"
        );
    }
}
