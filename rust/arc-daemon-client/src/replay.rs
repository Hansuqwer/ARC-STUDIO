//! Replay harness without UI (brief §3.3.4).
//!
//! Feeds fixture events through the same `on_event` path the panels will use —
//! this is the panel-parity oracle from Sprint 7 onward. Also performs ordered-
//! stream gap detection on `sequence`, the same check the live SSE consumer
//! applies (gap => Stale surface state, never silence).

use arc_protocol_rs::RunEvent;
use std::path::Path;

#[derive(Debug, Default)]
pub struct ReplayReport {
    pub events: u64,
    /// (expected, got) per detected gap, grouped per run_id ordering.
    pub gaps: Vec<(u64, u64)>,
}

/// Replay every `*.json` fixture in `dir` (sorted by filename) through `on_event`.
/// Sorting by filename supports the future additive convention
/// `run-event-seq/<scenario>/NNN-<TYPE>.json`.
pub fn replay_dir(dir: &Path, mut on_event: impl FnMut(RunEvent)) -> std::io::Result<ReplayReport> {
    let mut files: Vec<_> = std::fs::read_dir(dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("json"))
        .collect();
    files.sort();

    let mut report = ReplayReport::default();
    let mut last_seq: Option<u64> = None;
    for p in files {
        let raw = std::fs::read_to_string(&p)?;
        let ev: RunEvent = serde_json::from_str(&raw).map_err(|e| {
            std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                format!("{}: {e}", p.display()),
            )
        })?;
        if let Some(last) = last_seq {
            if ev.sequence > last + 1 {
                report.gaps.push((last + 1, ev.sequence));
            }
        }
        last_seq = Some(ev.sequence);
        report.events += 1;
        on_event(ev);
    }
    Ok(report)
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn fixtures() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../protocol/fixtures/run-event")
    }

    #[test]
    fn ordered_scenario_replays_gap_free_through_panel_path() {
        // run-event-seq/<scenario>/NNN-<TYPE>.json (additive, brief §5.6):
        // the replay scrubber's oracle. Ordered streams must be gap-free at
        // rest; a gap here is fixture corruption, not a Stale surface state.
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../protocol/fixtures/run-event-seq/tool-use-streaming");
        let mut kinds = Vec::new();
        let report = replay_dir(&dir, |ev| kinds.push(ev.kind)).unwrap();
        assert!(
            report.events >= 18,
            "scenario unexpectedly short: {}",
            report.events
        );
        assert!(
            report.gaps.is_empty(),
            "ordered scenario has gaps: {:?}",
            report.gaps
        );
        // Lifecycle brackets present and ordered.
        assert_eq!(kinds.first().map(String::as_str), Some("RUN_STARTED"));
        assert_eq!(kinds.last().map(String::as_str), Some("RUN_COMPLETED"));
        // Streaming families the scrubber renders specially are present.
        for needed in [
            "TOOL_CALL_START",
            "TOOL_CALL_ARGS",
            "TEXT_MESSAGE_CONTENT",
            "STATE_SNAPSHOT",
            "SHELL_DENIED",
            "HITL_PROMPT",
            "HITL_RESPONSE",
        ] {
            assert!(
                kinds.iter().any(|k| k == needed),
                "scenario missing {needed}"
            );
        }
    }

    #[test]
    fn replays_all_fixtures_through_panel_path() {
        let mut kinds = Vec::new();
        let report = replay_dir(&fixtures(), |ev| {
            // the same projection the panels will use
            let known = arc_protocol_rs::KnownRunEvent::from(ev);
            kinds.push(format!("{known:?}").chars().take(20).collect::<String>());
        })
        .unwrap();
        assert!(report.events >= 17, "expected >=17 fixture events");
        assert_eq!(kinds.len() as u64, report.events);
        // Per-instance fixtures are not an ordered trace: gaps are *expected* here
        // and the harness must report them rather than panic. Ordered-sequence
        // assertions arrive with the additive run-event-seq/ fixtures (Sprint 7).
    }
}
