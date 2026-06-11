//! arc-terminal — Sprint-6 PTY + grid core over alacritty_terminal.
//!
//! Framework-free: [`TerminalSession`] owns the PTY and the terminal state
//! machine; `grid_text()` is the render feed (the Sprint-3 framework draws
//! styled cells later; tests assert on text content now). The plan's
//! echo/resize/kill matrix (§3.8) is implemented as tests in THIS container
//! (Linux). macOS rows re-run on the M4; Windows/ConPTY rows when the
//! Windows shell lands. External-terminal fallback remains the escape hatch.

use alacritty_terminal::event::{Event, EventListener, WindowSize};
use alacritty_terminal::event_loop::{EventLoop, EventLoopSender, Msg};
use alacritty_terminal::grid::Dimensions;
use alacritty_terminal::index::{Column, Line, Point};
use alacritty_terminal::sync::FairMutex;
use alacritty_terminal::term::{test::TermSize, Config, Term};
use alacritty_terminal::tty;
use std::sync::mpsc;
use std::sync::Arc;
use std::time::{Duration, Instant};

#[derive(Debug, thiserror::Error)]
pub enum TerminalError {
    #[error("pty spawn: {0}")]
    Spawn(std::io::Error),
    #[error("event loop: {0}")]
    EventLoop(std::io::Error),
    #[error("channel closed")]
    Channel,
}

/// Forwards terminal events onto a plain mpsc the shell can poll.
#[derive(Clone)]
struct Forwarder(mpsc::Sender<Event>);

impl EventListener for Forwarder {
    fn send_event(&self, ev: Event) {
        let _ = self.0.send(ev);
    }
}

pub struct TerminalSession {
    term: Arc<FairMutex<Term<Forwarder>>>,
    channel: EventLoopSender,
    events: mpsc::Receiver<Event>,
    cols: u16,
    lines: u16,
    exited: Option<i32>,
}

impl TerminalSession {
    /// Spawn `program` (argv style) on a fresh PTY of `cols`x`lines`.
    pub fn spawn(
        program: &str,
        args: &[&str],
        cols: u16,
        lines: u16,
    ) -> Result<Self, TerminalError> {
        let (tx, rx) = mpsc::channel();
        let size = TermSize::new(cols as usize, lines as usize);
        let term = Arc::new(FairMutex::new(Term::new(
            Config::default(),
            &size,
            Forwarder(tx.clone()),
        )));
        let window_size = WindowSize {
            num_lines: lines,
            num_cols: cols,
            cell_width: 8,
            cell_height: 16,
        };
        let opts = tty::Options {
            shell: Some(tty::Shell::new(
                program.to_string(),
                args.iter().map(|s| s.to_string()).collect(),
            )),
            ..Default::default()
        };
        let pty = tty::new(&opts, window_size, 0u64).map_err(TerminalError::Spawn)?;
        let event_loop = EventLoop::new(term.clone(), Forwarder(tx), pty, false, false)
            .map_err(TerminalError::EventLoop)?;
        let channel = event_loop.channel();
        let _io_thread = event_loop.spawn();
        Ok(Self {
            term,
            channel,
            events: rx,
            cols,
            lines,
            exited: None,
        })
    }

    /// Write bytes to the child's stdin.
    pub fn write(&mut self, bytes: &[u8]) -> Result<(), TerminalError> {
        self.channel
            .send(Msg::Input(bytes.to_vec().into()))
            .map_err(|_| TerminalError::Channel)
    }

    /// Resize the grid + PTY (SIGWINCH lands child-side).
    pub fn resize(&mut self, cols: u16, lines: u16) -> Result<(), TerminalError> {
        self.cols = cols;
        self.lines = lines;
        let ws = WindowSize {
            num_lines: lines,
            num_cols: cols,
            cell_width: 8,
            cell_height: 16,
        };
        self.channel
            .send(Msg::Resize(ws))
            .map_err(|_| TerminalError::Channel)?;
        self.term
            .lock()
            .resize(TermSize::new(cols as usize, lines as usize));
        Ok(())
    }

    pub fn shutdown(&mut self) {
        let _ = self.channel.send(Msg::Shutdown);
    }

    pub fn size(&self) -> (u16, u16) {
        (self.cols, self.lines)
    }

    /// Pump pending terminal events; returns true if the child exited.
    /// (Wakeup => grid changed; ChildExit => record status, no zombie —
    /// alacritty's event loop reaps the child.)
    pub fn pump(&mut self) -> bool {
        while let Ok(ev) = self.events.try_recv() {
            if let Event::ChildExit(code) = ev {
                self.exited = Some(code);
            }
        }
        self.exited.is_some()
    }

    pub fn exit_code(&self) -> Option<i32> {
        self.exited
    }

    /// Plain-text snapshot of the visible grid (render feed; styling later).
    pub fn grid_text(&self) -> Vec<String> {
        let t = self.term.lock();
        let mut out = Vec::with_capacity(t.grid().screen_lines());
        for line in 0..t.grid().screen_lines() {
            let mut s = String::with_capacity(t.grid().columns());
            for col in 0..t.grid().columns() {
                s.push(t.grid()[Point::new(Line(line as i32), Column(col))].c);
            }
            out.push(s.trim_end().to_string());
        }
        out
    }

    /// Wait until `pred(grid_text)` or timeout; pumps events while waiting.
    pub fn wait_for(&mut self, timeout: Duration, mut pred: impl FnMut(&[String]) -> bool) -> bool {
        let deadline = Instant::now() + timeout;
        loop {
            self.pump();
            if pred(&self.grid_text()) {
                return true;
            }
            if Instant::now() >= deadline {
                return false;
            }
            // park briefly on the event channel to avoid a hot loop
            let _ = self
                .events
                .recv_timeout(Duration::from_millis(50))
                .map(|ev| {
                    if let Event::ChildExit(code) = ev {
                        self.exited = Some(code);
                    }
                });
        }
    }

    /// Wait for child exit (reaped by the IO thread; no zombie).
    pub fn wait_exit(&mut self, timeout: Duration) -> Option<i32> {
        let deadline = Instant::now() + timeout;
        while Instant::now() < deadline {
            if self.pump() {
                return self.exited;
            }
            let _ = self
                .events
                .recv_timeout(Duration::from_millis(50))
                .map(|ev| {
                    if let Event::ChildExit(code) = ev {
                        self.exited = Some(code);
                    }
                });
        }
        self.exited
    }
}

impl Drop for TerminalSession {
    fn drop(&mut self) {
        self.shutdown();
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    /// Matrix row 1 (§3.8): echo — write through the PTY, see it in the grid.
    #[test]
    fn echo_roundtrip() {
        let mut s = TerminalSession::spawn("/bin/cat", &[], 80, 24).unwrap();
        s.write(b"arc-echo-marker\n").unwrap();
        assert!(
            s.wait_for(Duration::from_secs(5), |g| g
                .iter()
                .any(|l| l.contains("arc-echo-marker"))),
            "echo visible in grid"
        );
    }

    /// Matrix row 2: resize 80x24 -> 120x40; child observes SIGWINCH
    /// (verified via `stty size` output rendered into the grid).
    #[test]
    fn resize_observed_by_child() {
        let mut s = TerminalSession::spawn("/bin/sh", &[], 80, 24).unwrap();
        assert!(s.wait_for(Duration::from_secs(5), |g| g
            .iter()
            .any(|l| l.contains('$') || l.contains('#'))));
        s.resize(120, 40).unwrap();
        assert_eq!(s.size(), (120, 40));
        s.write(b"stty size\n").unwrap();
        assert!(
            s.wait_for(Duration::from_secs(5), |g| g
                .iter()
                .any(|l| l.contains("40 120"))),
            "child sees new size: {:?}",
            s.grid_text()
                .iter()
                .filter(|l| !l.is_empty())
                .collect::<Vec<_>>()
        );
    }

    /// Matrix row 3: kill/exit — child exit is observed, status recorded,
    /// no zombie (the IO thread reaps; we assert the exit event arrives).
    #[test]
    fn child_exit_observed_no_zombie() {
        let mut s = TerminalSession::spawn("/bin/sh", &["-c", "exit 7"], 80, 24).unwrap();
        let code = s.wait_exit(Duration::from_secs(5));
        assert_eq!(code, Some(7), "exit status surfaced");
    }

    /// Throughput sanity (B15 is a benchmark, not a gate here): 1 MiB
    /// through `cat` lands in the scrollback without stalling the session.
    /// Linux-only: macOS PTY throughput in the macOS-sandbox environment does
    /// not reliably drain 1 MiB within a CI time budget. Re-run on the M4
    /// (pinned hardware) gives the real number.
    #[test]
    #[cfg(target_os = "linux")]
    fn one_mib_throughput_does_not_wedge() {
        let mut s = TerminalSession::spawn("/bin/cat", &[], 80, 24).unwrap();
        let chunk = "x".repeat(1024);
        for _ in 0..1024 {
            s.write(chunk.as_bytes()).unwrap();
        }
        s.write(b"\nEND-MARKER\n").unwrap();
        assert!(
            s.wait_for(Duration::from_secs(30), |g| g
                .iter()
                .any(|l| l.contains("END-MARKER"))),
            "1 MiB drained and tail visible"
        );
    }
}
