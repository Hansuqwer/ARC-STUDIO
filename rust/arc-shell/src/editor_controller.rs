//! Framework-free editor controller for M5.
//!
//! This adapts `arc-editor::Buffer` into shell-level state the native renderer
//! can consume: file path, dirty state, cursor/selection, viewport rows, and
//! edit commands. It deliberately exposes no framework or rope types.

use arc_editor::{Buffer, BufferError, Edit, Transaction};
use std::ops::Range;
use std::path::{Path, PathBuf};

#[derive(Debug, thiserror::Error)]
pub enum EditorControllerError {
    #[error("editor io: {0}")]
    Io(#[from] std::io::Error),
    #[error("buffer: {0}")]
    Buffer(#[from] BufferError),
    #[error("cannot save editor buffer without a path")]
    MissingPath,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditorLineVm {
    pub line_index: usize,
    pub char_start: usize,
    pub text: String,
    pub cursor_col: Option<usize>,
    pub selected: Option<Range<usize>>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EditorEffect {
    None,
    Saved(PathBuf),
    DirtyChanged(bool),
}

pub struct EditorController {
    buffer: Buffer,
    path: Option<PathBuf>,
    dirty: bool,
    cursor: usize,
    selection: Option<Range<usize>>,
    viewport_start_line: usize,
    saved_revision: u64,
}

impl EditorController {
    pub fn empty() -> Self {
        Self::from_text("", None)
    }

    pub fn from_text(text: &str, path: Option<PathBuf>) -> Self {
        let buffer = Buffer::from_text(text);
        let saved_revision = buffer.revision();
        Self {
            buffer,
            path,
            dirty: false,
            cursor: 0,
            selection: None,
            viewport_start_line: 0,
            saved_revision,
        }
    }

    pub fn open_path(path: impl AsRef<Path>) -> Result<Self, EditorControllerError> {
        let path = path.as_ref().to_path_buf();
        let text = std::fs::read_to_string(&path)?;
        Ok(Self::from_text(&text, Some(path)))
    }

    pub fn path(&self) -> Option<&Path> {
        self.path.as_deref()
    }

    pub fn buffer(&self) -> &Buffer {
        &self.buffer
    }

    pub fn text(&self) -> String {
        self.buffer.text()
    }

    pub fn dirty(&self) -> bool {
        self.dirty
    }

    pub fn cursor(&self) -> usize {
        self.cursor
    }

    pub fn selection(&self) -> Option<Range<usize>> {
        self.selection.clone()
    }

    pub fn viewport_start_line(&self) -> usize {
        self.viewport_start_line
    }

    pub fn set_viewport_start_line(&mut self, line: usize) {
        self.viewport_start_line = line.min(self.buffer.len_lines().saturating_sub(1));
    }

    pub fn save(&mut self) -> Result<EditorEffect, EditorControllerError> {
        let path = self
            .path
            .clone()
            .ok_or(EditorControllerError::MissingPath)?;
        std::fs::write(&path, self.buffer.text())?;
        self.saved_revision = self.buffer.revision();
        self.dirty = false;
        Ok(EditorEffect::Saved(path))
    }

    pub fn save_as(
        &mut self,
        path: impl Into<PathBuf>,
    ) -> Result<EditorEffect, EditorControllerError> {
        self.path = Some(path.into());
        self.save()
    }

    pub fn insert_text(&mut self, text: &str) -> Result<EditorEffect, EditorControllerError> {
        let range = self.take_edit_range();
        let start = range.start;
        let new_len = text.chars().count();
        self.apply_single(range, text.to_string())?;
        self.cursor = start + new_len;
        self.selection = None;
        self.mark_dirty();
        Ok(EditorEffect::DirtyChanged(true))
    }

    pub fn delete_backward(&mut self) -> Result<EditorEffect, EditorControllerError> {
        if let Some(range) = self.take_non_empty_selection() {
            self.cursor = range.start;
            self.apply_single(range, String::new())?;
            self.mark_dirty();
            return Ok(EditorEffect::DirtyChanged(true));
        }
        if self.cursor == 0 {
            return Ok(EditorEffect::None);
        }
        let start = self.cursor - 1;
        self.apply_single(start..self.cursor, String::new())?;
        self.cursor = start;
        self.mark_dirty();
        Ok(EditorEffect::DirtyChanged(true))
    }

    pub fn delete_forward(&mut self) -> Result<EditorEffect, EditorControllerError> {
        if let Some(range) = self.take_non_empty_selection() {
            self.cursor = range.start;
            self.apply_single(range, String::new())?;
            self.mark_dirty();
            return Ok(EditorEffect::DirtyChanged(true));
        }
        if self.cursor >= self.buffer.len_chars() {
            return Ok(EditorEffect::None);
        }
        self.apply_single(self.cursor..self.cursor + 1, String::new())?;
        self.mark_dirty();
        Ok(EditorEffect::DirtyChanged(true))
    }

    pub fn undo(&mut self) -> Result<EditorEffect, EditorControllerError> {
        let selections = self.buffer.undo()?;
        self.restore_selection_or_clamp(selections);
        self.dirty = self.buffer.revision() != self.saved_revision;
        Ok(EditorEffect::DirtyChanged(self.dirty))
    }

    pub fn redo(&mut self) -> Result<EditorEffect, EditorControllerError> {
        let selections = self.buffer.redo()?;
        self.restore_selection_or_clamp(selections);
        self.dirty = self.buffer.revision() != self.saved_revision;
        Ok(EditorEffect::DirtyChanged(self.dirty))
    }

    pub fn move_left(&mut self) {
        self.selection = None;
        self.cursor = self.cursor.saturating_sub(1);
        self.keep_cursor_visible();
    }

    pub fn move_right(&mut self) {
        self.selection = None;
        self.cursor = (self.cursor + 1).min(self.buffer.len_chars());
        self.keep_cursor_visible();
    }

    pub fn move_home(&mut self) {
        self.selection = None;
        let (line, _) = self.line_col_for_char(self.cursor);
        self.cursor = self.line_start_char(line);
        self.keep_cursor_visible();
    }

    pub fn move_end(&mut self) {
        self.selection = None;
        let (line, _) = self.line_col_for_char(self.cursor);
        self.cursor =
            self.line_start_char(line) + self.buffer.line(line).unwrap_or_default().chars().count();
        self.keep_cursor_visible();
    }

    pub fn move_up(&mut self) {
        self.selection = None;
        let (line, col) = self.line_col_for_char(self.cursor);
        let target_line = line.saturating_sub(1);
        self.cursor = self.char_for_line_col(target_line, col);
        self.keep_cursor_visible();
    }

    pub fn move_down(&mut self) {
        self.selection = None;
        let (line, col) = self.line_col_for_char(self.cursor);
        let target_line = (line + 1).min(self.buffer.len_lines().saturating_sub(1));
        self.cursor = self.char_for_line_col(target_line, col);
        self.keep_cursor_visible();
    }

    pub fn page_up(&mut self, page_lines: usize) {
        let (line, col) = self.line_col_for_char(self.cursor);
        let target_line = line.saturating_sub(page_lines.max(1));
        self.cursor = self.char_for_line_col(target_line, col);
        self.viewport_start_line = self.viewport_start_line.saturating_sub(page_lines.max(1));
    }

    pub fn page_down(&mut self, page_lines: usize) {
        let (line, col) = self.line_col_for_char(self.cursor);
        let max_line = self.buffer.len_lines().saturating_sub(1);
        let step = page_lines.max(1);
        let target_line = (line + step).min(max_line);
        self.cursor = self.char_for_line_col(target_line, col);
        self.viewport_start_line = (self.viewport_start_line + step).min(max_line);
    }

    pub fn select(&mut self, range: Range<usize>) {
        let len = self.buffer.len_chars();
        let start = range.start.min(len);
        let end = range.end.min(len);
        self.selection = Some(start.min(end)..start.max(end));
        self.cursor = end;
    }

    pub fn visible_lines(&self, height: usize) -> Vec<EditorLineVm> {
        let max = self.buffer.len_lines();
        let end = (self.viewport_start_line + height.max(1)).min(max);
        (self.viewport_start_line..end)
            .map(|line_index| {
                let text = self.buffer.line(line_index).unwrap_or_default();
                let char_start = self.line_start_char(line_index);
                let char_end = char_start + text.chars().count();
                let cursor_col = if (char_start..=char_end).contains(&self.cursor) {
                    Some(self.cursor.saturating_sub(char_start))
                } else {
                    None
                };
                let selected = self.selection.as_ref().and_then(|s| {
                    let start = s.start.max(char_start);
                    let end = s.end.min(char_end);
                    (start < end).then(|| start - char_start..end - char_start)
                });
                EditorLineVm {
                    line_index,
                    char_start,
                    text,
                    cursor_col,
                    selected,
                }
            })
            .collect()
    }

    fn apply_single(
        &mut self,
        char_range: Range<usize>,
        new_text: String,
    ) -> Result<(), BufferError> {
        self.buffer.apply(Transaction {
            edits: vec![Edit {
                char_range,
                new_text,
            }],
            selections_before: vec![self.cursor..self.cursor],
        })
    }

    fn mark_dirty(&mut self) {
        self.dirty = self.buffer.revision() != self.saved_revision;
    }

    fn take_edit_range(&mut self) -> Range<usize> {
        self.take_non_empty_selection()
            .unwrap_or(self.cursor..self.cursor)
    }

    fn take_non_empty_selection(&mut self) -> Option<Range<usize>> {
        self.selection.take().filter(|r| r.start < r.end)
    }

    fn restore_selection_or_clamp(&mut self, selections: Vec<Range<usize>>) {
        let len = self.buffer.len_chars();
        if let Some(sel) = selections.into_iter().next() {
            let start = sel.start.min(len);
            let end = sel.end.min(len);
            self.cursor = end;
            self.selection = (start != end).then_some(start.min(end)..start.max(end));
        } else {
            self.cursor = self.cursor.min(len);
            self.selection = None;
        }
        self.keep_cursor_visible();
    }

    fn keep_cursor_visible(&mut self) {
        let (line, _) = self.line_col_for_char(self.cursor);
        if line < self.viewport_start_line {
            self.viewport_start_line = line;
        }
    }

    fn line_start_char(&self, line_index: usize) -> usize {
        let mut line = 0usize;
        let mut pos = 0usize;
        for ch in self.buffer.text().chars() {
            if line == line_index {
                return pos;
            }
            pos += 1;
            if ch == '\n' {
                line += 1;
            }
        }
        pos
    }

    fn line_col_for_char(&self, char_idx: usize) -> (usize, usize) {
        let mut line = 0usize;
        let mut col = 0usize;
        for (idx, ch) in self.buffer.text().chars().enumerate() {
            if idx >= char_idx {
                break;
            }
            if ch == '\n' {
                line += 1;
                col = 0;
            } else {
                col += 1;
            }
        }
        (line, col)
    }

    fn char_for_line_col(&self, target_line: usize, target_col: usize) -> usize {
        let start = self.line_start_char(target_line);
        let line_len = self
            .buffer
            .line(target_line)
            .unwrap_or_default()
            .chars()
            .count();
        start + target_col.min(line_len)
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn insert_undo_redo_tracks_dirty_and_cursor() {
        let mut editor = EditorController::from_text("fn ", None);
        editor.insert_text("main").unwrap();
        assert_eq!(editor.text(), "mainfn ");
        assert!(editor.dirty());
        assert_eq!(editor.cursor(), 4);
        editor.undo().unwrap();
        assert_eq!(editor.text(), "fn ");
        editor.redo().unwrap();
        assert_eq!(editor.text(), "mainfn ");
    }

    #[test]
    fn selection_replacement_is_atomic() {
        let mut editor = EditorController::from_text("abcdef", None);
        editor.select(1..4);
        editor.insert_text("X").unwrap();
        assert_eq!(editor.text(), "aXef");
        assert_eq!(editor.cursor(), 2);
    }

    #[test]
    fn movement_clamps_across_lines() {
        let mut editor = EditorController::from_text("abc\ndef", None);
        editor.move_right();
        editor.move_right();
        editor.move_right();
        editor.move_down();
        assert_eq!(editor.cursor(), 7);
        editor.move_home();
        assert_eq!(editor.cursor(), 4);
        editor.move_end();
        assert_eq!(editor.cursor(), 7);
    }

    #[test]
    fn visible_lines_include_cursor_and_selection() {
        let mut editor = EditorController::from_text("abc\ndef\nghi", None);
        editor.set_viewport_start_line(1);
        editor.select(5..7);
        let lines = editor.visible_lines(2);
        assert_eq!(lines.len(), 2);
        assert_eq!(lines[0].text, "def");
        assert_eq!(lines[0].selected, Some(1..3));
    }

    #[test]
    fn save_as_clears_dirty() {
        let dir =
            std::env::temp_dir().join(format!("arc-editor-controller-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("file.txt");
        let mut editor = EditorController::from_text("hello", None);
        editor.insert_text("!").unwrap();
        assert!(editor.dirty());
        editor.save_as(&path).unwrap();
        assert!(!editor.dirty());
        assert_eq!(std::fs::read_to_string(&path).unwrap(), "!hello");
        let _ = std::fs::remove_dir_all(&dir);
    }
}
