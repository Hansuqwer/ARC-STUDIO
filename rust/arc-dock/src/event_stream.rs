//! Event Stream panel view-model (wireframe §6.3) — fed by per-run RunEvents
//! (finding F5: ordered semantics live on `/api/runs/{run_id}/events`).
//!
//! Parity oracle: the Sprint-1 replay harness drives the SAME `on_event`
//! path the live SSE consumer uses; tests below replay the committed
//! `run-event-seq/tool-use-streaming` scenario row-for-row.

use crate::state::{Datum, SurfaceState};
use arc_daemon_client::streams::{OrderedQueue, PushOutcome};
use arc_protocol_rs::RunEvent;

/// One rendered row: same projection as spike views::EventTable (and the
/// fixed-width discipline), so spike numbers transfer to the real panel.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EventRowVm {
    pub sequence: u64,
    pub kind: String,
    pub timestamp: String,
    pub summary: String,
}

impl EventRowVm {
    pub fn from_event(ev: &RunEvent) -> Self {
        let d = &ev.data;
        let s = |k: &str| d.get(k).and_then(|v| v.as_str()).map(str::to_owned);
        let summary = s("agent_name")
            .or_else(|| s("tool_name"))
            .or_else(|| s("message_id"))
            .or_else(|| s("reason"))
            .or_else(|| s("prompt_text"))
            .unwrap_or_default();
        Self {
            sequence: ev.sequence,
            kind: ev.kind.clone(),
            timestamp: ev.timestamp.clone(),
            summary,
        }
    }

    /// Fixed-width display line: `SEQ(4) KIND(24) TIME(24) SUMMARY`.
    pub fn display_line(&self) -> String {
        format!(
            "{:>4} {:<24} {:<24} {}",
            self.sequence,
            &self.kind[..self.kind.len().min(24)],
            &self.timestamp[..self.timestamp.len().min(24)],
            self.summary
        )
    }
}

/// Panel state machine: ordered queue in, rows + surface state out.
pub struct EventStreamPanel {
    queue: OrderedQueue<RunEvent>,
    rows: Vec<EventRowVm>,
    state: SurfaceState<usize>, // payload = row count (cheap, cloneable)
    producer: &'static str,
}

impl EventStreamPanel {
    pub fn new(queue_cap: usize) -> Self {
        Self {
            queue: OrderedQueue::new(queue_cap),
            rows: Vec::new(),
            state: SurfaceState::Loading,
            producer: "daemon.run_events",
        }
    }

    /// SSE/replay ingestion point — the single on_event path.
    /// Returns the push outcome so the transport can apply backpressure.
    pub fn on_event(&mut self, ev: RunEvent) -> PushOutcome {
        let seq = ev.sequence;
        let outcome = self.queue.push(seq, ev);
        if outcome == PushOutcome::Accepted {
            self.drain();
        }
        outcome
    }

    /// Move queued events into rendered rows; refresh surface state.
    fn drain(&mut self) {
        while let Some((_, ev)) = self.queue.pop() {
            self.rows.push(EventRowVm::from_event(&ev));
        }
        self.state = if let Some(gap) = self.queue.gap_detected() {
            SurfaceState::Stale {
                last: Datum::from_producer(self.producer, self.rows.len()),
                gap,
            }
        } else if self.rows.is_empty() {
            SurfaceState::Empty
        } else {
            SurfaceState::Ready(Datum::from_producer(self.producer, self.rows.len()))
        };
    }

    /// Resync completed (daemon re-fetch landed): clear the gap, resume.
    pub fn resync_complete(&mut self, resumed_from_seq: u64) {
        self.queue.take_gap();
        self.queue.reset_after_resync(resumed_from_seq);
        self.drain();
    }

    pub fn rows(&self) -> &[EventRowVm] {
        &self.rows
    }

    pub fn state(&self) -> &SurfaceState<usize> {
        &self.state
    }

    /// Footer line (wireframe §6.3): rows, drops (always 0 for ordered —
    /// asserting that in text is the point), source.
    pub fn footer(&self) -> String {
        format!(
            "{} rows | 0 dropped | source: {}",
            self.rows.len(),
            self.producer
        )
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn scenario_dir() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../protocol/fixtures/run-event-seq/tool-use-streaming")
    }

    /// Row-for-row fixture parity: the committed ordered scenario through the
    /// same on_event path the live consumer uses (retirement gate 2 oracle).
    #[test]
    fn replays_committed_scenario_row_for_row() {
        let mut panel = EventStreamPanel::new(64);
        let report = arc_daemon_client::replay::replay_dir(&scenario_dir(), |ev| {
            assert_eq!(panel.on_event(ev), PushOutcome::Accepted);
        })
        .unwrap();
        assert_eq!(report.events, 18);
        assert_eq!(panel.rows().len(), 18, "row-for-row");
        assert!(
            matches!(panel.state(), SurfaceState::Ready(d) if d.producer == "daemon.run_events")
        );

        // First and last rows match the scenario's lifecycle brackets.
        assert_eq!(panel.rows()[0].kind, "RUN_STARTED");
        assert_eq!(panel.rows()[17].kind, "RUN_COMPLETED");
        // Display line discipline holds (fixed-width prefix).
        assert!(panel.rows()[0]
            .display_line()
            .starts_with("   1 RUN_STARTED"));
        assert_eq!(
            panel.footer(),
            "18 rows | 0 dropped | source: daemon.run_events"
        );
    }

    #[test]
    fn gap_flips_to_stale_resync_recovers() {
        let mk = |seq: u64| RunEvent {
            schema_version: 2,
            kind: "MESSAGE".into(),
            timestamp: "2026-06-11T12:00:00.000Z".into(),
            run_id: "01HV7B3S0K9N3W2Q5J4Y8A6C2P".into(),
            sequence: seq,
            data: serde_json::Map::new(),
            extra: serde_json::Map::new(),
        };
        let mut panel = EventStreamPanel::new(64);
        panel.on_event(mk(1));
        panel.on_event(mk(2));
        panel.on_event(mk(7)); // gap 3..7
        match panel.state() {
            SurfaceState::Stale { gap, .. } => assert_eq!(*gap, (3, 7)),
            other => panic!("expected Stale, got {other:?}"),
        }
        assert!(panel.state().describe().contains("resync required"));

        panel.resync_complete(7);
        panel.on_event(mk(8));
        assert!(
            matches!(panel.state(), SurfaceState::Ready(_)),
            "recovered after resync"
        );
    }

    #[test]
    fn full_queue_blocks_producer_loses_nothing() {
        let mk = |seq: u64| RunEvent {
            schema_version: 2,
            kind: "MESSAGE".into(),
            timestamp: String::new(),
            run_id: String::new(),
            sequence: seq,
            data: serde_json::Map::new(),
            extra: serde_json::Map::new(),
        };
        // cap 1 and never drain between pushes: second push must block, not drop
        let mut panel = EventStreamPanel::new(1);
        assert_eq!(panel.on_event(mk(1)), PushOutcome::Accepted);
        // queue drained into rows by on_event, so push 2 is accepted; force the
        // block by pushing directly at the queue layer instead:
        let mut q: OrderedQueue<u8> = OrderedQueue::new(1);
        assert_eq!(q.push(1, 0), PushOutcome::Accepted);
        assert_eq!(q.push(2, 0), PushOutcome::ProducerMustBlock);
    }
}
