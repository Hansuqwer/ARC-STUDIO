//! HITL approval modal view-model (wireframe §6.5) — a SECURITY SURFACE.
//!
//! Hard rules encoded as types and tests, not conventions:
//! - the shell has NO approval authority: the only output of this model is a
//!   [`HitlDecision`] to POST to the daemon API (route inventoried in-sprint;
//!   finding F3: the endpoint does not exist daemon-side yet — this model is
//!   buildable now precisely because it never invents the route);
//! - there is intentionally no `auto_approve`, no policy evaluation, and no
//!   model call anywhere in this file;
//! - Escape is Deny-EQUIVALENT: it cancels without allow (`Dismissed`), it
//!   does NOT submit a deny — the prompt stays queued (AuditQueue semantics:
//!   security prompts never vanish);
//! - initial focus is the least-destructive action (Deny);
//! - prompts arrive via the AuditSecurity stream class: never dropped, never
//!   coalesced (enforced by `arc_daemon_client::streams::AuditQueue`).

use arc_daemon_client::streams::{AuditPush, AuditQueue};
use arc_protocol_rs::RunEvent;

/// What the daemon's HITL_PROMPT event carries (fixture-verified shape:
/// `protocol/fixtures/run-event/hitl-prompt.json`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HitlPrompt {
    pub hitl_id: String,
    pub run_id: String,
    pub step_id: String,
    pub prompt_text: String,
    pub options: Vec<String>,
    pub timeout_seconds: Option<u64>,
}

impl HitlPrompt {
    /// Strict extraction from a HITL_PROMPT RunEvent. Returns None for
    /// non-HITL events or missing required fields — a malformed security
    /// prompt is surfaced as a finding, never rendered half-empty.
    pub fn from_event(ev: &RunEvent) -> Option<Self> {
        if ev.kind != "HITL_PROMPT" {
            return None;
        }
        let d = &ev.data;
        let s = |k: &str| d.get(k).and_then(|v| v.as_str()).map(str::to_owned);
        Some(Self {
            hitl_id: s("hitl_id")?,
            run_id: ev.run_id.clone(),
            step_id: s("step_id")?,
            prompt_text: s("prompt_text")?,
            options: d
                .get("options")?
                .as_array()?
                .iter()
                .filter_map(|v| v.as_str().map(str::to_owned))
                .collect(),
            timeout_seconds: d.get("timeout_seconds").and_then(|v| v.as_u64()),
        })
    }
}

/// The verdicts a user can submit. Mirrors wireframe §6.5 buttons.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    ApproveOnce,
    Deny,
    AlwaysRequireApproval,
}

/// The ONLY artifact this surface produces: a decision to send to the daemon.
/// The daemon decides + audits; the shell renders + relays.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HitlDecision {
    pub hitl_id: String,
    pub verdict: Verdict,
    /// Operator identity field for the daemon's audit row (the daemon may
    /// override with its own session identity; shell passes what it knows).
    pub operator_hint: String,
}

/// Modal focus targets in tab order. Deny FIRST = initial focus on the
/// least-destructive action (a11y block, §6.5).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FocusTarget {
    Deny,
    ApproveOnce,
    AlwaysRequire,
    ViewDiff,
}

impl FocusTarget {
    pub const TAB_ORDER: [FocusTarget; 4] = [
        FocusTarget::Deny,
        FocusTarget::ApproveOnce,
        FocusTarget::AlwaysRequire,
        FocusTarget::ViewDiff,
    ];
}

/// Effects the render layer executes. `Submit` is the single egress.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HitlEffect {
    None,
    /// Focus moved (trap cycles, never leaves the modal while open).
    FocusMoved(FocusTarget),
    /// POST this to the daemon HITL decision API; modal stays open until the
    /// daemon acknowledges (the ack closes it via `decision_acked`).
    Submit(HitlDecision),
    /// Escape: modal closed WITHOUT any decision; prompt remains queued.
    Dismissed,
    /// Open the diff view for the pending action (read-only side effect).
    OpenDiff {
        run_id: String,
    },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HitlKey {
    Tab,
    ShiftTab,
    Enter,
    Escape,
}

pub struct HitlModal {
    queue: AuditQueue<HitlPrompt>,
    /// The prompt currently displayed (head of queue, not yet decided).
    current: Option<HitlPrompt>,
    focus: usize, // index into FocusTarget::TAB_ORDER
    pub operator_hint: String,
    /// True while a Submit is in flight (daemon not yet acked) — input to
    /// the render layer to disable buttons; decisions are idempotent-keyed
    /// by hitl_id daemon-side, but the shell still prevents double-submit.
    in_flight: bool,
}

impl HitlModal {
    pub fn new(queue_cap: usize, operator_hint: String) -> Self {
        Self {
            queue: AuditQueue::new(queue_cap),
            current: None,
            focus: 0,
            operator_hint,
            in_flight: false,
        }
    }

    /// Ingest an event from the per-run stream. Non-HITL events are ignored
    /// (None). Queue overflow propagates the hard-error semantics.
    pub fn on_event(&mut self, ev: &RunEvent) -> Option<AuditPush> {
        let prompt = HitlPrompt::from_event(ev)?;
        let outcome = self.queue.push(prompt);
        if self.current.is_none() {
            self.advance();
        }
        Some(outcome)
    }

    fn advance(&mut self) {
        self.current = self.queue.pop();
        self.focus = 0; // initial focus = Deny (least destructive)
        self.in_flight = false;
    }

    pub fn current(&self) -> Option<&HitlPrompt> {
        self.current.as_ref()
    }

    pub fn focused(&self) -> FocusTarget {
        FocusTarget::TAB_ORDER[self.focus]
    }

    pub fn queued(&self) -> usize {
        self.queue.len()
    }

    /// Keyboard handling — the modal is fully keyboard-operable (§6.5).
    pub fn key(&mut self, key: HitlKey) -> HitlEffect {
        let Some(prompt) = &self.current else {
            return HitlEffect::None;
        };
        if self.in_flight && key != HitlKey::Escape {
            return HitlEffect::None; // buttons disabled while submitting
        }
        match key {
            HitlKey::Tab => {
                self.focus = (self.focus + 1) % FocusTarget::TAB_ORDER.len();
                HitlEffect::FocusMoved(self.focused())
            }
            HitlKey::ShiftTab => {
                self.focus =
                    (self.focus + FocusTarget::TAB_ORDER.len() - 1) % FocusTarget::TAB_ORDER.len();
                HitlEffect::FocusMoved(self.focused())
            }
            HitlKey::Escape => {
                // Deny-EQUIVALENT: cancel without allow. No decision is sent;
                // the prompt goes BACK to the front conceptually — we keep it
                // as `current` so it cannot be lost, and the modal is marked
                // dismissed render-side. (AuditQueue: never drop.)
                HitlEffect::Dismissed
            }
            HitlKey::Enter => match self.focused() {
                FocusTarget::Deny => self.submit(Verdict::Deny, prompt.hitl_id.clone()),
                FocusTarget::ApproveOnce => {
                    self.submit(Verdict::ApproveOnce, prompt.hitl_id.clone())
                }
                FocusTarget::AlwaysRequire => {
                    self.submit(Verdict::AlwaysRequireApproval, prompt.hitl_id.clone())
                }
                FocusTarget::ViewDiff => HitlEffect::OpenDiff {
                    run_id: prompt.run_id.clone(),
                },
            },
        }
    }

    fn submit(&mut self, verdict: Verdict, hitl_id: String) -> HitlEffect {
        self.in_flight = true;
        HitlEffect::Submit(HitlDecision {
            hitl_id,
            verdict,
            operator_hint: self.operator_hint.clone(),
        })
    }

    /// Daemon acknowledged the decision (HITL_RESPONSE observed or POST 2xx):
    /// only now does the modal advance to the next queued prompt.
    pub fn decision_acked(&mut self, hitl_id: &str) {
        if self.current.as_ref().is_some_and(|p| p.hitl_id == hitl_id) {
            self.advance();
        }
    }

    /// Screen-reader announcement for the modal (focus trap entry).
    pub fn announce(&self) -> String {
        match &self.current {
            None => String::from("no approvals pending"),
            Some(p) => format!(
                "Approval required: {}. {} options. Focus on Deny. {} more queued.",
                p.prompt_text,
                p.options.len(),
                self.queue.len()
            ),
        }
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;
    use serde_json::json;

    fn prompt_event(hitl_id: &str, seq: u64) -> RunEvent {
        serde_json::from_value(json!({
            "schema_version": 2,
            "type": "HITL_PROMPT",
            "timestamp": "2026-06-11T12:00:00.000Z",
            "run_id": "01HV7B3S0K9N3W2Q5J4Y8A6C2P",
            "sequence": seq,
            "data": {
                "hitl_id": hitl_id,
                "step_id": "approval-gate",
                "prompt_text": "Apply patch to 3 files?",
                "options": ["approve", "reject"],
                "timeout_seconds": 60
            }
        }))
        .unwrap()
    }

    fn modal_with_one() -> HitlModal {
        let mut m = HitlModal::new(8, "user@example.com".into());
        m.on_event(&prompt_event("h1", 42)).unwrap();
        m
    }

    #[test]
    fn fixture_prompt_parses_strictly() {
        let raw = include_str!("../../../protocol/fixtures/run-event/hitl-prompt.json");
        let ev: RunEvent = serde_json::from_str(raw).unwrap();
        let p = HitlPrompt::from_event(&ev).unwrap();
        assert_eq!(p.options, vec!["approve", "reject"]);
        assert!(p.prompt_text.contains("Approve"));
    }

    #[test]
    fn malformed_prompt_is_rejected_not_half_rendered() {
        let ev: RunEvent = serde_json::from_value(json!({
            "schema_version": 2, "type": "HITL_PROMPT",
            "timestamp": "t", "run_id": "r", "sequence": 1,
            "data": { "hitl_id": "h" } // missing step_id/prompt_text/options
        }))
        .unwrap();
        assert!(HitlPrompt::from_event(&ev).is_none());
    }

    #[test]
    fn initial_focus_is_deny_least_destructive() {
        let m = modal_with_one();
        assert_eq!(m.focused(), FocusTarget::Deny);
        assert!(m.announce().contains("Focus on Deny"));
    }

    #[test]
    fn escape_dismisses_without_any_decision() {
        let mut m = modal_with_one();
        let eff = m.key(HitlKey::Escape);
        assert_eq!(eff, HitlEffect::Dismissed);
        // No Submit was produced; the prompt is still current (never lost).
        assert!(m.current().is_some());
    }

    #[test]
    fn enter_on_deny_submits_deny_and_blocks_double_submit() {
        let mut m = modal_with_one();
        match m.key(HitlKey::Enter) {
            HitlEffect::Submit(d) => {
                assert_eq!(d.verdict, Verdict::Deny);
                assert_eq!(d.hitl_id, "h1");
                assert_eq!(d.operator_hint, "user@example.com");
            }
            other => panic!("expected Submit, got {other:?}"),
        }
        // in-flight: further Enter is inert until daemon acks
        assert_eq!(m.key(HitlKey::Enter), HitlEffect::None);
        m.decision_acked("h1");
        assert!(m.current().is_none(), "advanced after ack");
    }

    #[test]
    fn tab_cycles_focus_trap_never_leaves_modal() {
        let mut m = modal_with_one();
        let mut seen = vec![m.focused()];
        for _ in 0..4 {
            match m.key(HitlKey::Tab) {
                HitlEffect::FocusMoved(t) => seen.push(t),
                other => panic!("expected FocusMoved, got {other:?}"),
            }
        }
        // full cycle returns to Deny — the trap wraps, it does not escape
        assert_eq!(seen.first(), seen.last());
        assert_eq!(seen.len(), 5);
        // shift-tab walks backward
        assert_eq!(
            m.key(HitlKey::ShiftTab),
            HitlEffect::FocusMoved(FocusTarget::ViewDiff)
        );
    }

    #[test]
    fn approve_requires_explicit_focus_then_enter_no_shortcut() {
        let mut m = modal_with_one();
        m.key(HitlKey::Tab); // Deny -> ApproveOnce
        match m.key(HitlKey::Enter) {
            HitlEffect::Submit(d) => assert_eq!(d.verdict, Verdict::ApproveOnce),
            other => panic!("expected Submit, got {other:?}"),
        }
        // There is no key that approves from initial focus in one stroke.
    }

    #[test]
    fn queue_holds_prompts_fifo_and_overflow_is_hard_error() {
        let mut m = HitlModal::new(1, "op".into());
        assert_eq!(
            m.on_event(&prompt_event("h1", 1)),
            Some(AuditPush::Accepted)
        );
        // h1 became current (popped), queue empty again -> h2 accepted
        assert_eq!(
            m.on_event(&prompt_event("h2", 2)),
            Some(AuditPush::Accepted)
        );
        // h3 overflows the cap-1 queue while h2 is queued
        assert_eq!(
            m.on_event(&prompt_event("h3", 3)),
            Some(AuditPush::OverflowHardError)
        );
        assert_eq!(m.queued(), 1);
        // decide h1 -> h2 advances; FIFO order preserved
        m.key(HitlKey::Enter);
        m.decision_acked("h1");
        assert_eq!(m.current().unwrap().hitl_id, "h2");
    }

    #[test]
    fn non_hitl_events_ignored() {
        let mut m = HitlModal::new(8, "op".into());
        let ev: RunEvent = serde_json::from_value(json!({
            "schema_version": 2, "type": "AGENT_START",
            "timestamp": "t", "run_id": "r", "sequence": 1,
            "data": {"agent_name": "x"}
        }))
        .unwrap();
        assert!(m.on_event(&ev).is_none());
        assert!(m.current().is_none());
    }

    #[test]
    fn view_diff_is_read_only_side_effect_not_a_decision() {
        let mut m = modal_with_one();
        m.key(HitlKey::Tab);
        m.key(HitlKey::Tab);
        m.key(HitlKey::Tab); // -> ViewDiff
        match m.key(HitlKey::Enter) {
            HitlEffect::OpenDiff { run_id } => assert!(!run_id.is_empty()),
            other => panic!("expected OpenDiff, got {other:?}"),
        }
        assert!(
            m.current().is_some(),
            "prompt still pending after viewing diff"
        );
    }
}
