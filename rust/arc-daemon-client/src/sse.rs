//! Minimal SSE frame parser, separable from transport so it is unit-testable
//! against partial chunks, CRLF, heartbeats, and multi-line `data:`.
//!
//! Rules (WHATWG EventSource semantics, subset we need):
//! - frames split on blank line; `data:` lines accumulate (joined by `\n`);
//! - `:` comment lines are heartbeats — they reset the caller's idle timer by
//!   virtue of being received bytes, and are otherwise ignored;
//! - `event:` is recorded (daemon currently sends unnamed events; tolerated);
//! - `id:` is recorded per Sprint-1 decision (review report §6.7): retained for
//!   inventory, but resume is **sequence-driven** (daemon-owned), not SSE-id-driven.

/// One complete SSE frame with accumulated data payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Frame {
    pub data: String,
    pub event: Option<String>,
    pub id: Option<String>,
    /// Line number (1-based, across the whole stream) of the frame-terminating
    /// blank line; used in decode error context.
    pub line_no: u64,
}

#[derive(Default)]
pub struct SseParser {
    buf: Vec<u8>,
    data: String,
    event: Option<String>,
    id: Option<String>,
    line_no: u64,
}

impl SseParser {
    /// Push a transport chunk; returns zero or more completed frames.
    pub fn push(&mut self, chunk: &[u8]) -> Vec<Frame> {
        self.buf.extend_from_slice(chunk);
        let mut out = Vec::new();
        while let Some(nl) = self.buf.iter().position(|&b| b == b'\n') {
            let line: Vec<u8> = self.buf.drain(..=nl).collect();
            self.line_no += 1;
            let line = String::from_utf8_lossy(&line[..line.len() - 1]);
            let line = line.strip_suffix('\r').unwrap_or(&line);

            if line.is_empty() {
                if !self.data.is_empty() {
                    out.push(Frame {
                        data: std::mem::take(&mut self.data).trim_end().to_string(),
                        event: self.event.take(),
                        id: self.id.take(),
                        line_no: self.line_no,
                    });
                } else {
                    // blank line with no data: frame separator noise; clear field state
                    self.event = None;
                }
            } else if let Some(rest) = line.strip_prefix("data:") {
                self.data.push_str(rest.strip_prefix(' ').unwrap_or(rest));
                self.data.push('\n');
            } else if let Some(rest) = line.strip_prefix("event:") {
                self.event = Some(rest.trim().to_string());
            } else if let Some(rest) = line.strip_prefix("id:") {
                self.id = Some(rest.trim().to_string());
            } else if line.starts_with(':') {
                // heartbeat comment — bytes received already reset the idle timer
            }
            // unknown fields (e.g. "retry:") tolerated and ignored, recorded in Sprint-1 notes
        }
        out
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn single_frame() {
        let mut p = SseParser::default();
        let f = p.push(b"data: {\"a\":1}\n\n");
        assert_eq!(f.len(), 1);
        assert_eq!(f[0].data, "{\"a\":1}");
    }

    #[test]
    fn partial_chunks_reassemble() {
        let mut p = SseParser::default();
        assert!(p.push(b"da").is_empty());
        assert!(p.push(b"ta: {\"a\"").is_empty());
        let f = p.push(b":1}\n\n");
        assert_eq!(f.len(), 1);
        assert_eq!(f[0].data, "{\"a\":1}");
    }

    #[test]
    fn crlf_and_heartbeats() {
        let mut p = SseParser::default();
        let f = p.push(b": ping\r\ndata: {\"a\":1}\r\n\r\n: ping\r\n");
        assert_eq!(f.len(), 1);
        assert_eq!(f[0].data, "{\"a\":1}");
    }

    #[test]
    fn multiline_data_joined_with_newline() {
        let mut p = SseParser::default();
        let f = p.push(b"data: line1\ndata: line2\n\n");
        assert_eq!(f[0].data, "line1\nline2");
    }

    #[test]
    fn event_and_id_recorded() {
        let mut p = SseParser::default();
        let f = p.push(b"event: run\nid: 42\ndata: {}\n\n");
        assert_eq!(f[0].event.as_deref(), Some("run"));
        assert_eq!(f[0].id.as_deref(), Some("42"));
    }

    #[test]
    fn two_frames_one_chunk() {
        let mut p = SseParser::default();
        let f = p.push(b"data: 1\n\ndata: 2\n\n");
        assert_eq!(f.len(), 2);
        assert_eq!((f[0].data.as_str(), f[1].data.as_str()), ("1", "2"));
    }
}
