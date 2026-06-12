//! HITL decision API client (F3 — additive endpoint, Sprint-8 daemon integration).
//!
//! Routes (proposal: `docs/planning/arc-v2-hitl-decision-api-proposal.md`):
//! - `GET  /api/hitl`                     — pending prompt queue
//! - `POST /api/hitl/{hitl_id}/decision`  — submit verdict
//!
//! Verdict vocabulary follows the daemon's enum: `approve | reject | modify | skip`.
//! The shell's `AlwaysRequireApproval` maps to `reject` + notes explaining the
//! policy request (documented in `arc-dock::hitl`). No shell-side authorization;
//! the daemon validates, audits, and decides.

use crate::{ClientError, DaemonClient};
use arc_protocol_rs::ArcError;
use serde::{Deserialize, Serialize};
use serde_json::Map;
use std::time::Duration;

/// Request body for `POST /api/hitl/{hitl_id}/decision`.
#[derive(Debug, Clone, Serialize)]
pub struct HitlDecisionRequest {
    /// Daemon vocabulary: `"approve"` | `"reject"` | `"modify"` | `"skip"`.
    pub decision: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub operator_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub notes: Option<String>,
}

/// One pending prompt from `GET /api/hitl`.
#[derive(Debug, Clone, Deserialize)]
pub struct HitlPromptSummary {
    pub hitl_id: String,
    pub run_id: String,
    pub step_id: String,
    pub prompt_text: String,
    pub options: Vec<String>,
    #[serde(default)]
    pub timeout_seconds: Option<u64>,
}

/// Successful response from `POST /api/hitl/{hitl_id}/decision`.
#[derive(Debug, Clone, Deserialize)]
pub struct HitlDecisionResponse {
    pub hitl_id: String,
    pub decision: String,
    #[serde(default)]
    pub operator_id: Option<String>,
    pub responded_at: String,
}

/// Response envelope for `GET /api/hitl`.
#[derive(Debug, Clone, Deserialize)]
pub struct HitlListData {
    pub prompts: Vec<HitlPromptSummary>,
}

impl DaemonClient {
    /// `GET /api/hitl` — list pending HITL prompts.
    pub async fn hitl_list(&self) -> Result<Vec<HitlPromptSummary>, ClientError> {
        let resp = self
            .http
            .get(self.url("/api/hitl")?)
            .timeout(Duration::from_secs(10))
            .send()
            .await?;
        let status = resp.status();
        if !status.is_success() {
            return Err(ClientError::Http {
                status: status.as_u16(),
                body: resp.text().await.unwrap_or_default(),
            });
        }
        let env: arc_protocol_rs::ArcEnvelope<HitlListData> = resp.json().await?;
        env.into_result()
            .map(|(d, _)| d.map(|d| d.prompts).unwrap_or_default())
            .map_err(|e| ClientError::Daemon(Box::new(e)))
    }

    /// `POST /api/hitl/{hitl_id}/decision` — submit a verdict.
    ///
    /// The single egress for the shell's HITL modal. The daemon validates,
    /// audits, emits `HITL_RESPONSE` on the run's event stream, and unblocks
    /// the waiting step. Single-use: a second POST for the same hitl_id
    /// returns 404.
    #[allow(clippy::result_large_err)]
    pub async fn hitl_decide(
        &self,
        hitl_id: &str,
        req: HitlDecisionRequest,
    ) -> Result<HitlDecisionResponse, ClientError> {
        let resp = self
            .http
            .post(self.url(&format!("/api/hitl/{hitl_id}/decision"))?)
            .timeout(Duration::from_secs(10))
            .json(&req)
            .send()
            .await?;
        let status = resp.status();
        if !status.is_success() {
            return Err(ClientError::Http {
                status: status.as_u16(),
                body: resp.text().await.unwrap_or_default(),
            });
        }
        let env: arc_protocol_rs::ArcEnvelope<HitlDecisionResponse> = resp.json().await?;
        env.into_result()
            .and_then(|(d, _)| {
                d.ok_or_else(|| ArcError {
                    code: "INVALID_RESPONSE".into(),
                    message: "daemon returned empty response".into(),
                    details: None,
                    extra: Map::new(),
                })
            })
            .map_err(|e| ClientError::Daemon(Box::new(e)))
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn decision_request_serializes_without_optional_fields() {
        let req = HitlDecisionRequest {
            decision: "approve".into(),
            operator_id: None,
            notes: None,
        };
        let json = serde_json::to_value(&req).unwrap();
        assert_eq!(json["decision"], "approve");
        assert!(json.get("operator_id").is_none());
        assert!(json.get("notes").is_none());
    }

    #[test]
    fn decision_request_serializes_with_all_fields() {
        let req = HitlDecisionRequest {
            decision: "reject".into(),
            operator_id: Some("user@example.com".into()),
            notes: Some("policy: always require approval".into()),
        };
        let json = serde_json::to_value(&req).unwrap();
        assert_eq!(json["decision"], "reject");
        assert_eq!(json["operator_id"], "user@example.com");
        assert_eq!(json["notes"], "policy: always require approval");
    }

    #[test]
    fn decision_response_deserializes() {
        let json = r#"{
            "hitl_id": "h1",
            "decision": "approve",
            "operator_id": "user@example.com",
            "responded_at": "2026-06-11T12:00:00.000Z"
        }"#;
        let resp: HitlDecisionResponse = serde_json::from_str(json).unwrap();
        assert_eq!(resp.hitl_id, "h1");
        assert_eq!(resp.decision, "approve");
        assert_eq!(resp.operator_id.as_deref(), Some("user@example.com"));
    }

    #[test]
    fn prompt_summary_deserializes() {
        let json = r#"{
            "hitl_id": "h1",
            "run_id": "r1",
            "step_id": "s1",
            "prompt_text": "Apply patch?",
            "options": ["approve", "reject"],
            "timeout_seconds": 60
        }"#;
        let p: HitlPromptSummary = serde_json::from_str(json).unwrap();
        assert_eq!(p.hitl_id, "h1");
        assert_eq!(p.options.len(), 2);
        assert_eq!(p.timeout_seconds, Some(60));
    }

    #[test]
    fn prompt_summary_deserializes_without_optional_timeout() {
        let json = r#"{
            "hitl_id": "h1",
            "run_id": "r1",
            "step_id": "s1",
            "prompt_text": "Apply patch?",
            "options": ["approve", "reject"]
        }"#;
        let p: HitlPromptSummary = serde_json::from_str(json).unwrap();
        assert_eq!(p.timeout_seconds, None);
    }
}
