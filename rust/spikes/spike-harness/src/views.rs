//! Shared view-models — every candidate renders the same content.
//!
//! Contract per [`crate::script::Action`]:
//! `OpenWorkload` -> [`TextDoc::load`] + render [`TextDoc::viewport`]
//! `LoadDiff`     -> [`DiffDoc::parse`] + render viewport
//! `ScrollStep`   -> [`DiffDoc::scroll_step`] + render viewport
//! `AppendRows`   -> [`EventTable::append`] per row JSON + render
//! `TypeChar`     -> [`TypeBox::push`] + render its line
//! `TakeScreenshot` -> render [`bidi_sample_lines`] then capture

use std::path::Path;

pub const VIEWPORT_LINES: usize = 50;

pub struct TextDoc {
    text: String,
    line_starts: Vec<usize>,
}

impl TextDoc {
    pub fn load(path: &Path) -> std::io::Result<Self> {
        let text = std::fs::read_to_string(path)?;
        Ok(Self::from_text(text))
    }

    pub fn from_text(text: String) -> Self {
        let mut line_starts = vec![0usize];
        for (i, b) in text.bytes().enumerate() {
            if b == b'\n' {
                line_starts.push(i + 1);
            }
        }
        Self { text, line_starts }
    }

    pub fn len_lines(&self) -> usize {
        self.line_starts.len()
    }

    pub fn line(&self, idx: usize) -> &str {
        let start = self.line_starts[idx];
        let end = self
            .line_starts
            .get(idx + 1)
            .map(|e| e - 1)
            .unwrap_or(self.text.len());
        &self.text[start..end.max(start)]
    }

    pub fn viewport(&self) -> impl Iterator<Item = &str> {
        (0..VIEWPORT_LINES.min(self.len_lines())).map(|i| self.line(i))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DiffLineKind {
    Header,
    Hunk,
    Add,
    Remove,
    Context,
}

pub struct DiffDoc {
    lines: Vec<(DiffLineKind, String)>,
    pub scroll_top: usize,
}

impl DiffDoc {
    pub fn parse(patch: &str) -> Self {
        let lines = patch
            .lines()
            .map(|l| {
                let kind = if l.starts_with("+++") || l.starts_with("---") {
                    DiffLineKind::Header
                } else if l.starts_with("@@") {
                    DiffLineKind::Hunk
                } else if l.starts_with('+') {
                    DiffLineKind::Add
                } else if l.starts_with('-') {
                    DiffLineKind::Remove
                } else {
                    DiffLineKind::Context
                };
                (kind, l.to_string())
            })
            .collect();
        Self {
            lines,
            scroll_top: 0,
        }
    }

    pub fn len_lines(&self) -> usize {
        self.lines.len()
    }

    pub fn scroll_step(&mut self) -> bool {
        let max_top = self.lines.len().saturating_sub(VIEWPORT_LINES);
        if self.scroll_top >= max_top {
            return false;
        }
        self.scroll_top = (self.scroll_top + VIEWPORT_LINES / 2).min(max_top);
        true
    }

    pub fn viewport(&self) -> impl Iterator<Item = &(DiffLineKind, String)> {
        self.lines.iter().skip(self.scroll_top).take(VIEWPORT_LINES)
    }

    pub fn full_scroll_steps(&self) -> usize {
        let max_top = self.lines.len().saturating_sub(VIEWPORT_LINES);
        max_top.div_ceil(VIEWPORT_LINES / 2)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EventRow {
    pub sequence: u64,
    pub kind: String,
    pub timestamp: String,
    pub summary: String,
}

#[derive(Default)]
pub struct EventTable {
    rows: Vec<EventRow>,
}

impl EventTable {
    pub fn append(&mut self, raw_json: &str) {
        let v: serde_json::Value = serde_json::from_str(raw_json).unwrap_or_default();
        let kind = v["type"].as_str().unwrap_or("UNKNOWN").to_string();
        let data = &v["data"];
        let summary = data["agent_name"]
            .as_str()
            .or_else(|| data["tool_name"].as_str())
            .or_else(|| data["message_id"].as_str())
            .or_else(|| data["reason"].as_str())
            .unwrap_or("")
            .to_string();
        self.rows.push(EventRow {
            sequence: v["sequence"].as_u64().unwrap_or(0),
            kind,
            timestamp: v["timestamp"].as_str().unwrap_or("").to_string(),
            summary,
        });
    }

    pub fn len(&self) -> usize {
        self.rows.len()
    }

    pub fn is_empty(&self) -> bool {
        self.rows.is_empty()
    }

    pub fn tail_viewport(&self) -> impl Iterator<Item = &EventRow> {
        let start = self.rows.len().saturating_sub(VIEWPORT_LINES);
        self.rows[start..].iter()
    }

    pub fn display_line(row: &EventRow) -> String {
        format!(
            "{:>4} {:<24} {:<24} {}",
            row.sequence,
            &row.kind[..row.kind.len().min(24)],
            &row.timestamp[..row.timestamp.len().min(24)],
            row.summary
        )
    }
}

#[derive(Default)]
pub struct TypeBox {
    pub content: String,
    pub cursor: usize,
}

impl TypeBox {
    pub fn push(&mut self, ch: char) {
        if ch == '\n' {
            self.content.clear();
            self.cursor = 0;
        } else {
            self.content.push(ch);
            self.cursor += ch.len_utf8();
        }
    }
}

pub fn bidi_sample_lines() -> Vec<&'static str> {
    include_str!("../../g7-golden/sample.txt").lines().collect()
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn textdoc_lines_and_viewport() {
        let d = TextDoc::from_text("a\nbb\nccc\n".into());
        assert_eq!(d.len_lines(), 4);
        assert_eq!(d.line(1), "bb");
        assert_eq!(d.viewport().count(), 4.min(VIEWPORT_LINES));
    }

    #[test]
    fn textdoc_pathological_single_line_does_not_split() {
        let big = "x".repeat(1_000_000);
        let d = TextDoc::from_text(big);
        assert_eq!(d.len_lines(), 1);
        assert_eq!(d.viewport().count(), 1);
        assert_eq!(d.line(0).len(), 1_000_000);
    }

    #[test]
    fn diffdoc_classifies_and_scrolls_fully() {
        let patch = crate::workloads::synthetic_diff(5000, crate::workloads::seeds::G2_DIFF);
        let mut d = DiffDoc::parse(&patch);
        assert!(d.len_lines() > 5000);
        let adds = d
            .viewport()
            .filter(|(k, _)| *k == DiffLineKind::Add)
            .count();
        let removes = d
            .viewport()
            .filter(|(k, _)| *k == DiffLineKind::Remove)
            .count();
        assert!(adds + removes > 0);

        let steps = d.full_scroll_steps();
        let mut taken = 0;
        while d.scroll_step() {
            taken += 1;
        }
        assert_eq!(taken, steps);
        assert!(!d.scroll_step());
    }

    #[test]
    fn event_table_appends_real_fixture_and_formats_fixed_width() {
        let raw = include_str!(
            "../../../../protocol/fixtures/run-event-seq/tool-use-streaming/001-RUN_STARTED.json"
        );
        let mut t = EventTable::default();
        t.append(raw);
        assert_eq!(t.len(), 1);
        let row = t.tail_viewport().next().unwrap();
        assert_eq!(row.kind, "RUN_STARTED");
        assert_eq!(row.sequence, 1);
        let line = EventTable::display_line(row);
        assert!(line.starts_with("   1 RUN_STARTED"));
    }

    #[test]
    fn event_table_tolerates_garbage_without_panicking() {
        let mut t = EventTable::default();
        t.append("not json at all");
        assert_eq!(t.len(), 1);
        assert_eq!(t.tail_viewport().next().unwrap().kind, "UNKNOWN");
    }

    #[test]
    fn typebox_wraps_on_newline() {
        let mut tb = TypeBox::default();
        for ch in "abc\nde".chars() {
            tb.push(ch);
        }
        assert_eq!(tb.content, "de");
        assert_eq!(tb.cursor, 2);
    }

    #[test]
    fn bidi_sample_matches_golden_file_byte_for_byte() {
        let from_file = std::fs::read_to_string(
            std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../g7-golden/sample.txt"),
        )
        .unwrap();
        let embedded: String = bidi_sample_lines().join("\n") + "\n";
        assert_eq!(from_file, embedded);
    }
}
