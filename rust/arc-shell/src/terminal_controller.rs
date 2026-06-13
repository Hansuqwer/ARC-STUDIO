//! Framework-free terminal panel controller for M7.
//!
//! Owns `arc-terminal::TerminalSession` and exposes a bounded render cache plus
//! explicit lifecycle state for the native shell.

use arc_terminal::{TerminalError, TerminalSession};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TerminalStatus {
    Empty,
    Running,
    Exited(Option<i32>),
    Error(String),
}

pub struct TerminalController {
    session: Option<TerminalSession>,
    rows: Vec<String>,
    max_rows: usize,
    cols: u16,
    lines: u16,
    status: TerminalStatus,
    last_program: Option<(String, Vec<String>)>,
}

impl TerminalController {
    pub fn new(max_rows: usize, cols: u16, lines: u16) -> Self {
        Self {
            session: None,
            rows: Vec::new(),
            max_rows: max_rows.max(1),
            cols,
            lines,
            status: TerminalStatus::Empty,
            last_program: None,
        }
    }

    pub fn spawn(&mut self, program: &str, args: &[&str]) -> Result<(), TerminalError> {
        let session = TerminalSession::spawn(program, args, self.cols, self.lines)?;
        self.last_program = Some((
            program.to_string(),
            args.iter().map(|s| s.to_string()).collect(),
        ));
        self.session = Some(session);
        self.status = TerminalStatus::Running;
        self.rows.clear();
        Ok(())
    }

    pub fn spawn_default_shell(&mut self) -> Result<(), TerminalError> {
        let shell = std::env::var("SHELL").unwrap_or_else(|_| "/bin/sh".to_string());
        self.spawn(&shell, &[])
    }

    pub fn restart(&mut self) -> Result<(), TerminalError> {
        let (program, args) = self
            .last_program
            .clone()
            .unwrap_or_else(|| (default_shell(), Vec::new()));
        let refs: Vec<&str> = args.iter().map(String::as_str).collect();
        self.spawn(&program, &refs)
    }

    pub fn write_bytes(&mut self, bytes: &[u8]) -> Result<(), TerminalError> {
        match self.session.as_mut() {
            Some(session) => session.write(bytes),
            None => {
                self.status = TerminalStatus::Error("terminal is not running".into());
                Err(TerminalError::Channel)
            }
        }
    }

    pub fn write_text(&mut self, text: &str) -> Result<(), TerminalError> {
        self.write_bytes(text.as_bytes())
    }

    pub fn resize(&mut self, cols: u16, lines: u16) -> Result<(), TerminalError> {
        self.cols = cols.max(1);
        self.lines = lines.max(1);
        if let Some(session) = self.session.as_mut() {
            session.resize(self.cols, self.lines)?;
        }
        Ok(())
    }

    pub fn pump(&mut self) {
        if let Some(session) = self.session.as_mut() {
            let exited = session.pump();
            self.rows = bounded_rows(session.grid_text(), self.max_rows);
            if exited {
                self.status = TerminalStatus::Exited(session.exit_code());
            } else {
                self.status = TerminalStatus::Running;
            }
        }
    }

    pub fn shutdown(&mut self) {
        if let Some(session) = self.session.as_mut() {
            session.shutdown();
        }
        self.session = None;
        self.status = TerminalStatus::Exited(None);
    }

    pub fn rows(&self) -> &[String] {
        &self.rows
    }

    pub fn status(&self) -> &TerminalStatus {
        &self.status
    }

    pub fn size(&self) -> (u16, u16) {
        (self.cols, self.lines)
    }

    pub fn ingest_grid_for_test(&mut self, rows: Vec<String>) {
        self.rows = bounded_rows(rows, self.max_rows);
    }
}

fn default_shell() -> String {
    std::env::var("SHELL").unwrap_or_else(|_| "/bin/sh".to_string())
}

fn bounded_rows(mut rows: Vec<String>, max_rows: usize) -> Vec<String> {
    let cap = max_rows.max(1);
    if rows.len() > cap {
        rows.drain(0..rows.len() - cap);
    }
    rows
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn starts_empty_with_size() {
        let controller = TerminalController::new(10, 80, 24);
        assert_eq!(controller.status(), &TerminalStatus::Empty);
        assert_eq!(controller.size(), (80, 24));
    }

    #[test]
    fn bounded_grid_cache_keeps_tail() {
        let mut controller = TerminalController::new(3, 80, 24);
        controller.ingest_grid_for_test(vec!["a".into(), "b".into(), "c".into(), "d".into()]);
        assert_eq!(
            controller.rows(),
            &["b".to_string(), "c".to_string(), "d".to_string()]
        );
    }

    #[test]
    fn resize_updates_dimensions_without_session() {
        let mut controller = TerminalController::new(10, 80, 24);
        controller.resize(100, 30).unwrap();
        assert_eq!(controller.size(), (100, 30));
    }

    #[test]
    fn shutdown_without_session_is_explicit() {
        let mut controller = TerminalController::new(10, 80, 24);
        controller.shutdown();
        assert_eq!(controller.status(), &TerminalStatus::Exited(None));
    }
}
