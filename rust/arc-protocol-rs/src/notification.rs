//! DaemonNotification — the shape actually carried by the *global* SSE stream
//! `GET /api/events/stream` (Sprint-1 live finding F5; the review brief assumed
//! RunEvent there — it is not).
//!
//! Observed live (2026-06-11):
//! `{"event_id":"evt-…","event_type":"task_state_changed","run_id":null,
//!   "timestamp":"…","payload":{…}, …extras}`
//!
//! `RunEvent` shapes are carried by the per-run stream
//! `GET /api/runs/{run_id}/events` (AG-UI compatible; `event:` names match
//! registry types; closes with STREAM_END).

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct DaemonNotification {
    pub event_id: String,
    /// e.g. "task_state_changed", "audit_verified", "hitl_required",
    /// "run_completed", "session_changed" (lowercase snake — a DIFFERENT
    /// namespace from the SCREAMING_SNAKE RunEvent registry).
    pub event_type: String,
    /// Nullable: many notifications are not run-scoped.
    #[serde(default)]
    pub run_id: Option<String>,
    /// RFC3339; kept as string, parsed lazily.
    pub timestamp: String,
    #[serde(default)]
    pub payload: Map<String, Value>,
    /// Additive tolerance: notification kinds carry extra top-level fields
    /// (e.g. task_state_changed adds task_id/old_status/new_status).
    #[serde(flatten)]
    pub extra: Map<String, Value>,
}
