//! Surface-state machine shared by all arc-dock panels.
//!
//! Every panel renders every variant — that is a DoD gate enforced in tests.
//! Producer-truth: every Ready/Stale datum names the producer that generated it;
//! no panel may render data without naming its source.

use arc_protocol_rs::ArcError;

/// Named producer + lightweight payload. Cloneable so panels can carry it in
/// Stale without cloning the full row list.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Datum<T: Clone> {
    /// Source identifier, e.g. "daemon.runs" or "daemon.run_events".
    pub producer: &'static str,
    pub payload: T,
}

impl<T: Clone> Datum<T> {
    pub fn from_producer(producer: &'static str, payload: T) -> Self {
        Self { producer, payload }
    }
}

/// All user-visible states a panel surface can be in.
/// No variant is allowed to be "invisible" to a screen reader — each must
/// produce a non-empty `describe()` string (DoD §1 + §2).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SurfaceState<T: Clone> {
    /// Initial state before the first response arrives.
    Loading,
    /// Response received but the list is empty.
    Empty,
    /// Data present and fresh.
    Ready(Datum<T>),
    /// A sequence gap was detected; last good data retained for context.
    Stale { last: Datum<T>, gap: (u64, u64) },
    /// Transport or backend error; reason shown verbatim (producer-truth).
    Degraded { reason: String },
    /// Workspace not in the trust database; shown as a distinct modal state,
    /// not collapsed into Degraded.
    UntrustedWorkspace,
}

impl<T: Clone> SurfaceState<T> {
    /// Accessible one-line description for every state (DoD §2: no silent states).
    pub fn describe(&self) -> String {
        match self {
            Self::Loading => "loading…".into(),
            Self::Empty => "no items".into(),
            Self::Ready(d) => format!("ready (source: {})", d.producer),
            Self::Stale { gap, last } => format!(
                "stale — resync required (gap {}-{}; source: {})",
                gap.0, gap.1, last.producer
            ),
            Self::Degraded { reason } => format!("degraded: {reason}"),
            Self::UntrustedWorkspace => {
                "workspace not trusted — add to trust list to continue".into()
            }
        }
    }
}

/// Map an `ArcError` from a daemon response into the right surface state.
/// "PERMISSION_DENIED" / "UNTRUSTED_WORKSPACE" → `UntrustedWorkspace`;
/// everything else → `Degraded`.
pub fn state_from_error<T: Clone>(e: ArcError) -> SurfaceState<T> {
    if e.code == "PERMISSION_DENIED"
        || e.code == "UNTRUSTED_WORKSPACE"
        || e.message.to_ascii_lowercase().contains("untrusted")
    {
        SurfaceState::UntrustedWorkspace
    } else {
        SurfaceState::Degraded {
            reason: format!("{}: {}", e.code, e.message),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_states_have_non_empty_describe() {
        let states: Vec<SurfaceState<usize>> = vec![
            SurfaceState::Loading,
            SurfaceState::Empty,
            SurfaceState::Ready(Datum::from_producer("test", 0)),
            SurfaceState::Stale {
                last: Datum::from_producer("test", 0),
                gap: (3, 7),
            },
            SurfaceState::Degraded {
                reason: "timeout".into(),
            },
            SurfaceState::UntrustedWorkspace,
        ];
        for s in &states {
            assert!(!s.describe().is_empty(), "silent state: {s:?}");
        }
    }

    #[test]
    fn untrusted_workspace_maps_from_permission_denied() {
        let e = ArcError {
            code: "PERMISSION_DENIED".into(),
            message: "Workspace '/x' is untrusted: not in external trust database".into(),
            details: None,
            extra: serde_json::Map::new(),
        };
        assert!(matches!(
            state_from_error::<usize>(e),
            SurfaceState::UntrustedWorkspace
        ));
    }

    #[test]
    fn other_errors_degrade() {
        let e = ArcError {
            code: "INTERNAL_ERROR".into(),
            message: "something broke".into(),
            details: None,
            extra: serde_json::Map::new(),
        };
        assert!(matches!(
            state_from_error::<usize>(e),
            SurfaceState::Degraded { .. }
        ));
    }
}
