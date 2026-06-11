//! ArcEnvelope / ArcError / ArcMeta — mirrors `protocol/event_envelope.py` (ADR-018).
//!
//! Fixture ground truth: `protocol/fixtures/arc-envelope/*.json`.
//! Note: fixtures serialize absent data/error as explicit `null`
//! (`"data": null`), so `data`/`error`/`meta` must NOT use
//! `skip_serializing_if` — re-encode must preserve the explicit null.

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ArcError {
    /// e.g. "RUN_FAILED", "WORKSPACE_NOT_FOUND" — registry in `protocol/fixtures/error-codes/`.
    pub code: String,
    pub message: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub details: Option<Value>,
    /// Additive-protocol tolerance: unknown fields are retained, not dropped.
    #[serde(flatten)]
    pub extra: Map<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct ArcMeta {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub duration_ms: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub adapter: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub workspace: Option<String>,
    /// RFC3339; kept as string, parsed lazily by consumers.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<String>,
    #[serde(flatten)]
    pub extra: Map<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ArcEnvelope<T> {
    /// "1.0" today; never assume — compare via handshake.
    pub version: String,
    pub ok: bool,
    /// Explicit `null` on the wire when absent (fixture-verified); do not skip.
    #[serde(default = "none_of")]
    pub data: Option<T>,
    #[serde(default)]
    pub error: Option<ArcError>,
    #[serde(default)]
    pub meta: Option<ArcMeta>,
    #[serde(flatten)]
    pub extra: Map<String, Value>,
}

fn none_of<T>() -> Option<T> {
    None
}

impl<T> ArcEnvelope<T> {
    /// `ok=false` with no error object is itself a protocol violation — surface it.
    ///
    /// `ArcError` is intentionally returned by value (not boxed): it mirrors the
    /// wire type and callers usually destructure it immediately.
    #[allow(clippy::result_large_err)]
    pub fn into_result(self) -> Result<(Option<T>, Option<ArcMeta>), ArcError> {
        match (self.ok, self.error) {
            (true, _) => Ok((self.data, self.meta)),
            (false, Some(e)) => Err(e),
            (false, None) => Err(ArcError {
                code: "PROTOCOL_VIOLATION".into(),
                message: "ok=false without error object".into(),
                details: None,
                extra: Map::new(),
            }),
        }
    }
}
