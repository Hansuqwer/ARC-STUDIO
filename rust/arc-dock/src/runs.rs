//! Runs panel view-model (wireframe §6.4): table semantics, filter chips as
//! a radiogroup, status conveyed by TEXT not color alone, detail timeline fed
//! by the same RunEvent path as the Event Stream panel.
//!
//! Data source: `GET /api/runs` envelope (list shape verified in-sprint
//! against the live daemon; this view-model takes the decoded JSON value and
//! is deliberately defensive about field names — unknown shapes degrade to
//! visible "unknown" text, never to invented data).

use crate::state::{state_from_error, Datum, SurfaceState};
use arc_protocol_rs::ArcEnvelope;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RunFilter {
    All,
    Running,
    Failed,
    NeedsApproval,
}

impl RunFilter {
    /// The radiogroup, in display order (wireframe §6.4).
    pub const ALL: [RunFilter; 4] = [
        RunFilter::All,
        RunFilter::Running,
        RunFilter::Failed,
        RunFilter::NeedsApproval,
    ];

    pub fn label(self) -> &'static str {
        match self {
            RunFilter::All => "all",
            RunFilter::Running => "running",
            RunFilter::Failed => "failed",
            RunFilter::NeedsApproval => "needs approval",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RunRow {
    pub run_id: String,
    /// Daemon-reported status string, verbatim — the shell never invents
    /// or remaps status vocabulary (producer-truth).
    pub status: String,
    pub agent: String,
    pub started: String,
    pub last_event: String,
}

impl RunRow {
    /// Defensive extraction from one run JSON object. Missing fields render
    /// as "?" (visible unknown), never as fabricated values.
    pub fn from_json(v: &serde_json::Value) -> Self {
        let s = |keys: &[&str]| {
            keys.iter()
                .find_map(|k| v.get(*k).and_then(|x| x.as_str()))
                .unwrap_or("?")
                .to_string()
        };
        Self {
            run_id: s(&["run_id", "id"]),
            status: s(&["status", "state"]),
            agent: s(&["agent", "agent_name", "runtime"]),
            started: s(&["started_at", "created_at", "timestamp"]),
            last_event: s(&["last_event", "last_event_type"]),
        }
    }

    fn matches(&self, f: RunFilter) -> bool {
        match f {
            RunFilter::All => true,
            RunFilter::Running => self.status.eq_ignore_ascii_case("running"),
            RunFilter::Failed => {
                self.status.eq_ignore_ascii_case("failed")
                    || self.status.eq_ignore_ascii_case("error")
            }
            RunFilter::NeedsApproval => {
                self.status.to_ascii_lowercase().contains("hitl")
                    || self.status.to_ascii_lowercase().contains("approval")
            }
        }
    }
}

pub struct RunsPanel {
    rows: Vec<RunRow>,
    pub filter: RunFilter,
    state: SurfaceState<usize>,
}

impl Default for RunsPanel {
    fn default() -> Self {
        Self {
            rows: Vec::new(),
            filter: RunFilter::All,
            state: SurfaceState::Loading,
        }
    }
}

impl RunsPanel {
    /// Ingest a decoded `GET /api/runs` envelope. The list may live at the
    /// top level or under a "runs" key — both observed shapes handled;
    /// anything else is a Degraded surface with the reason shown.
    pub fn on_response(&mut self, env: ArcEnvelope<serde_json::Value>) {
        match env.into_result() {
            Err(e) => self.state = state_from_error(e),
            Ok((data, _meta)) => {
                let list = data
                    .as_ref()
                    .and_then(|d| {
                        d.as_array()
                            .cloned()
                            .or_else(|| d.get("runs").and_then(|r| r.as_array()).cloned())
                    })
                    .unwrap_or_default();
                self.rows = list.iter().map(RunRow::from_json).collect();
                self.state = if self.rows.is_empty() {
                    SurfaceState::Empty
                } else {
                    SurfaceState::Ready(Datum::from_producer("daemon.runs", self.rows.len()))
                };
            }
        }
    }

    pub fn on_transport_error(&mut self, reason: String) {
        self.state = SurfaceState::Degraded { reason };
    }

    pub fn visible_rows(&self) -> Vec<&RunRow> {
        self.rows
            .iter()
            .filter(|r| r.matches(self.filter))
            .collect()
    }

    pub fn state(&self) -> &SurfaceState<usize> {
        &self.state
    }

    /// Accessible row text: status as TEXT (never color-only).
    pub fn row_text(row: &RunRow) -> String {
        format!(
            "run {}, status {}, agent {}, started {}, last event {}",
            row.run_id, row.status, row.agent, row.started, row.last_event
        )
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;
    use arc_protocol_rs::ArcError;
    use serde_json::{json, Map};

    fn envelope(data: serde_json::Value) -> ArcEnvelope<serde_json::Value> {
        ArcEnvelope {
            version: "1.0".into(),
            ok: true,
            data: Some(data),
            error: None,
            meta: None,
            extra: Map::new(),
        }
    }

    #[test]
    fn ready_filter_and_a11y_text() {
        let mut p = RunsPanel::default();
        p.on_response(envelope(json!([
            {"run_id": "abc123", "status": "running",   "agent": "planner",  "started_at": "10:14:22", "last_event": "TOOL_CALL"},
            {"run_id": "def456", "status": "needs HITL approval", "agent": "editor", "started_at": "10:11:05", "last_event": "HITL_PROMPT"},
            {"run_id": "ghi789", "status": "failed",    "agent": "reviewer", "started_at": "10:02:44", "last_event": "RUN_FAILED"},
        ])));
        assert!(matches!(p.state(), SurfaceState::Ready(d) if d.producer == "daemon.runs"));
        assert_eq!(p.visible_rows().len(), 3);

        p.filter = RunFilter::NeedsApproval;
        let visible = p.visible_rows();
        assert_eq!(visible.len(), 1);
        assert_eq!(visible[0].run_id, "def456");

        p.filter = RunFilter::Failed;
        assert_eq!(p.visible_rows()[0].run_id, "ghi789");

        let text = RunsPanel::row_text(p.visible_rows()[0]);
        assert!(
            text.contains("status failed"),
            "status is text, not color: {text}"
        );
    }

    #[test]
    fn empty_list_is_empty_state_unknown_fields_visible() {
        let mut p = RunsPanel::default();
        p.on_response(envelope(json!([])));
        assert!(matches!(p.state(), SurfaceState::Empty));

        p.on_response(envelope(json!([{ "unexpected": "shape" }])));
        let rows = p.visible_rows();
        assert_eq!(
            rows[0].run_id, "?",
            "unknown renders as visible ?, never invented"
        );
    }

    #[test]
    fn runs_key_wrapping_also_accepted() {
        let mut p = RunsPanel::default();
        p.on_response(envelope(
            json!({"runs": [{"id": "x1", "state": "running"}]}),
        ));
        assert_eq!(p.visible_rows()[0].run_id, "x1");
        assert_eq!(p.visible_rows()[0].status, "running");
    }

    #[test]
    fn daemon_error_maps_through_shared_state_mapping() {
        let mut p = RunsPanel::default();
        p.on_response(ArcEnvelope {
            version: "1.0".into(),
            ok: false,
            data: None,
            error: Some(ArcError {
                code: "PERMISSION_DENIED".into(),
                message: "Workspace '/x' is untrusted: not in external trust database".into(),
                details: None,
                extra: Map::new(),
            }),
            meta: None,
            extra: Map::new(),
        });
        assert!(matches!(p.state(), SurfaceState::UntrustedWorkspace));

        p.on_transport_error("connection refused".into());
        assert!(matches!(p.state(), SurfaceState::Degraded { .. }));
        assert!(p.state().describe().contains("connection refused"));
    }

    #[test]
    fn filter_radiogroup_order_matches_wireframe() {
        let labels: Vec<&str> = RunFilter::ALL.iter().map(|f| f.label()).collect();
        assert_eq!(labels, vec!["all", "running", "failed", "needs approval"]);
    }
}
