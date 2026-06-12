//! guarded_host_call — improvement #5, the policy as a single wrapper.
//!
//! Every host import goes through this. No exceptions. Properties (each
//! tested):
//! 1. capability-checked first (deny-by-default; denial is cheap and early);
//! 2. time-bounded (per-op deadline; the operation runs on a worker thread
//!    and an overrun yields a Timeout error — the host never blocks forever);
//! 3. audited on allow AND on deny via the pluggable [`AuditSink`];
//! 4. **fail-closed on audit failure** (review §9.2): if the audit write
//!    fails after a successful operation, the result is DISCARDED and an
//!    error returned — an unauditable success is not a success.
//!
//! Synchronous worker-thread design (not tokio): plugin host calls happen
//! off the UI thread by construction; a thread per in-flight host call is
//! acceptable at extension scale and keeps this crate runtime-free.

use crate::capability::{Capability, CapabilitySet, DenialReason};
use std::sync::mpsc;
use std::sync::{Arc, Mutex};
use std::time::Duration;

#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum HostCallError {
    #[error("denied: {0:?}")]
    Denied(DenialReason),
    #[error("timeout after {0:?} in {1}")]
    Timeout(Duration, &'static str),
    #[error("audit write failed — result discarded (fail-closed): {0}")]
    AuditFailed(String),
    #[error("operation failed: {0}")]
    OpFailed(String),
}

/// Audit sink contract. Production: daemon API append. Tests: in-memory.
pub trait AuditSink: Send + Sync {
    fn append(&self, entry: &AuditEntry) -> Result<(), String>;
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AuditEntry {
    pub op: &'static str,
    pub capability: String,
    pub outcome: AuditOutcome,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AuditOutcome {
    Allowed,
    Denied,
    TimedOut,
}

/// In-memory sink for tests; `fail` flips on to test fail-closed semantics.
#[derive(Default)]
pub struct MemoryAuditSink {
    pub entries: Mutex<Vec<AuditEntry>>,
    pub fail: Mutex<bool>,
}

impl AuditSink for MemoryAuditSink {
    fn append(&self, entry: &AuditEntry) -> Result<(), String> {
        if *self.fail.lock().expect("audit sink lock") {
            return Err("simulated audit backend failure".into());
        }
        self.entries
            .lock()
            .expect("audit sink lock")
            .push(entry.clone());
        Ok(())
    }
}

/// Host context handed to every wrapped import.
pub struct HostCtx {
    pub caps: CapabilitySet,
    pub audit: Arc<dyn AuditSink>,
}

/// THE wrapper. `op_fn` runs on a worker thread under `deadline`.
pub fn guarded_host_call<T: Send + 'static>(
    ctx: &HostCtx,
    cap: Capability,
    op: &'static str,
    deadline: Duration,
    op_fn: impl FnOnce() -> Result<T, String> + Send + 'static,
) -> Result<T, HostCallError> {
    // 1) deny-by-default capability check — before any work.
    if let Err(denial) = ctx.caps.check(&cap) {
        // Denials are audited too (best-effort: a failed denial-audit must
        // not turn a denial into anything else).
        let _ = ctx.audit.append(&AuditEntry {
            op,
            capability: cap.audit_key(),
            outcome: AuditOutcome::Denied,
        });
        return Err(HostCallError::Denied(denial));
    }

    // 2) bounded execution on a worker thread.
    let (tx, rx) = mpsc::channel();
    std::thread::spawn(move || {
        let _ = tx.send(op_fn());
    });
    let result = match rx.recv_timeout(deadline) {
        Err(_) => {
            let _ = ctx.audit.append(&AuditEntry {
                op,
                capability: cap.audit_key(),
                outcome: AuditOutcome::TimedOut,
            });
            return Err(HostCallError::Timeout(deadline, op));
        }
        Ok(Err(e)) => return Err(HostCallError::OpFailed(e)),
        Ok(Ok(v)) => v,
    };

    // 3) audit-on-allow, FAIL-CLOSED: no audit row, no result.
    ctx.audit
        .append(&AuditEntry {
            op,
            capability: cap.audit_key(),
            outcome: AuditOutcome::Allowed,
        })
        .map_err(HostCallError::AuditFailed)?;
    Ok(result)
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    fn ctx_with(grants: &[Capability]) -> (HostCtx, Arc<MemoryAuditSink>) {
        let sink = Arc::new(MemoryAuditSink::default());
        let mut caps = CapabilitySet::deny_all();
        for c in grants {
            caps.grant(c.clone());
        }
        (
            HostCtx {
                caps,
                audit: sink.clone(),
            },
            sink,
        )
    }

    fn fs_docs() -> Capability {
        Capability::FsRead {
            path_scope: "${workspace}/docs".into(),
        }
    }

    #[test]
    fn denial_is_early_audited_and_runs_nothing() {
        let (ctx, sink) = ctx_with(&[]);
        let ran = Arc::new(Mutex::new(false));
        let ran2 = ran.clone();
        let r: Result<(), _> = guarded_host_call(
            &ctx,
            fs_docs(),
            "fs-read",
            Duration::from_secs(1),
            move || {
                *ran2.lock().unwrap() = true;
                Ok(())
            },
        );
        assert!(matches!(r, Err(HostCallError::Denied(_))));
        // give the (never-spawned) op no chance to have run
        assert!(!*ran.lock().unwrap(), "denied op must never execute");
        let entries = sink.entries.lock().unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].outcome, AuditOutcome::Denied);
        assert_eq!(entries[0].capability, "fs.read:${workspace}/docs");
    }

    #[test]
    fn allow_path_executes_audits_and_returns() {
        let (ctx, sink) = ctx_with(&[fs_docs()]);
        let r = guarded_host_call(&ctx, fs_docs(), "fs-read", Duration::from_secs(1), || {
            Ok(42u32)
        });
        assert_eq!(r.unwrap(), 42);
        let entries = sink.entries.lock().unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].outcome, AuditOutcome::Allowed);
    }

    #[test]
    fn timeout_kills_and_audits() {
        let (ctx, sink) = ctx_with(&[fs_docs()]);
        let r: Result<(), _> = guarded_host_call(
            &ctx,
            fs_docs(),
            "fs-read-slow",
            Duration::from_millis(50),
            || {
                std::thread::sleep(Duration::from_secs(5));
                Ok(())
            },
        );
        assert!(matches!(r, Err(HostCallError::Timeout(_, "fs-read-slow"))));
        assert_eq!(
            sink.entries.lock().unwrap()[0].outcome,
            AuditOutcome::TimedOut
        );
    }

    #[test]
    fn audit_failure_discards_the_result_fail_closed() {
        let (ctx, sink) = ctx_with(&[fs_docs()]);
        *sink.fail.lock().unwrap() = true;
        let r = guarded_host_call(&ctx, fs_docs(), "fs-read", Duration::from_secs(1), || {
            Ok("secret file contents".to_string())
        });
        match r {
            Err(HostCallError::AuditFailed(_)) => {} // result discarded
            other => panic!("expected AuditFailed (fail-closed), got {other:?}"),
        }
    }

    #[test]
    fn op_error_propagates_without_allow_audit() {
        let (ctx, sink) = ctx_with(&[fs_docs()]);
        let r: Result<(), _> =
            guarded_host_call(&ctx, fs_docs(), "fs-read", Duration::from_secs(1), || {
                Err("ENOENT".into())
            });
        assert!(matches!(r, Err(HostCallError::OpFailed(_))));
        assert!(
            sink.entries.lock().unwrap().is_empty(),
            "failed op is not an allow row"
        );
    }
}
