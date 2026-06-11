//! Stream taxonomy and backpressure (review brief §3.12 — normative table).
//!
//! | Class         | Queue policy            | Drop policy                      | UI obligation        |
//! |---------------|-------------------------|----------------------------------|----------------------|
//! | Ordered       | bounded, block producer | NEVER drop                       | gap => Stale + resync|
//! | Telemetry     | bounded ring            | drop-oldest WITH visible counter | show "N dropped"     |
//! | ViewModel     | coalesce to latest      | replace                          | none (derived)       |
//! | AuditSecurity | bounded, block producer | NEVER drop; overflow => hard err | modal, never coalesce|
//!
//! These are deliberately synchronous data structures (no tokio dependency in
//! the types themselves): the SSE task pushes, the UI thread drains. Async
//! wakeup is the caller's transport concern; policy lives here and is
//! unit-testable without a runtime.

use std::collections::VecDeque;
use std::sync::atomic::{AtomicU64, Ordering};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StreamClass {
    Ordered,
    Telemetry,
    ViewModel,
    AuditSecurity,
}

// ─────────────────────────── Ordered (never drop) ───────────────────────────

/// Push outcome for producer-blocking classes.
#[derive(Debug, PartialEq, Eq)]
pub enum PushOutcome {
    Accepted,
    /// Queue full: the PRODUCER must pause (SSE task stops reading the socket;
    /// TCP backpressure does the rest). Dropping is not an option here.
    ProducerMustBlock,
}

/// Bounded ordered queue: never drops, never reorders; detects sequence gaps.
/// A gap is surfaced as data (`gap_detected`) — the consumer flips the surface
/// to `Stale` and triggers resync from `sequence`; silence is impossible.
pub struct OrderedQueue<T> {
    buf: VecDeque<(u64, T)>,
    cap: usize,
    last_seq: Option<u64>,
    /// (expected, got) for the most recent gap; cleared by `take_gap`.
    gap: Option<(u64, u64)>,
}

impl<T> OrderedQueue<T> {
    pub fn new(cap: usize) -> Self {
        Self {
            buf: VecDeque::with_capacity(cap),
            cap,
            last_seq: None,
            gap: None,
        }
    }

    pub fn push(&mut self, seq: u64, item: T) -> PushOutcome {
        if self.buf.len() >= self.cap {
            return PushOutcome::ProducerMustBlock; // item NOT consumed-and-lost
        }
        if let Some(last) = self.last_seq {
            if seq > last + 1 {
                self.gap = Some((last + 1, seq));
            }
        }
        self.last_seq = Some(seq);
        self.buf.push_back((seq, item));
        PushOutcome::Accepted
    }

    pub fn pop(&mut self) -> Option<(u64, T)> {
        self.buf.pop_front()
    }

    pub fn len(&self) -> usize {
        self.buf.len()
    }

    pub fn is_empty(&self) -> bool {
        self.buf.is_empty()
    }

    /// Non-destructive read of the gap state; `take_gap` clears it once the
    /// consumer has flipped the surface to Stale and scheduled resync.
    pub fn gap_detected(&self) -> Option<(u64, u64)> {
        self.gap
    }

    pub fn take_gap(&mut self) -> Option<(u64, u64)> {
        self.gap.take()
    }

    /// Resync entry point: after re-fetching from the daemon, the consumer
    /// resets sequence tracking to resume from `seq`.
    pub fn reset_after_resync(&mut self, seq: u64) {
        self.last_seq = Some(seq);
        self.gap = None;
    }
}

// ───────────────────────── Telemetry (drop-oldest) ──────────────────────────

/// Bounded ring: drop-oldest with a visible counter. The counter is monotone
/// and never resets silently — the UI shows "N dropped" (wireframe §6.3).
pub struct TelemetryRing<T> {
    buf: VecDeque<T>,
    cap: usize,
    dropped: AtomicU64,
}

impl<T> TelemetryRing<T> {
    pub fn new(cap: usize) -> Self {
        Self {
            buf: VecDeque::with_capacity(cap),
            cap,
            dropped: AtomicU64::new(0),
        }
    }

    pub fn push(&mut self, item: T) {
        if self.buf.len() >= self.cap {
            self.buf.pop_front();
            self.dropped.fetch_add(1, Ordering::Relaxed);
        }
        self.buf.push_back(item);
    }

    pub fn pop(&mut self) -> Option<T> {
        self.buf.pop_front()
    }

    pub fn dropped(&self) -> u64 {
        self.dropped.load(Ordering::Relaxed)
    }

    pub fn len(&self) -> usize {
        self.buf.len()
    }

    pub fn is_empty(&self) -> bool {
        self.buf.is_empty()
    }
}

// ───────────────────────── ViewModel (coalesce) ─────────────────────────────

/// Latest-value cell: every push replaces; consumer reads the newest state.
/// Derived data only — losing intermediates is correct by definition.
pub struct LatestCell<T> {
    value: Option<T>,
    /// Number of replaced (coalesced) intermediate values, for diagnostics.
    coalesced: u64,
}

impl<T> Default for LatestCell<T> {
    fn default() -> Self {
        Self {
            value: None,
            coalesced: 0,
        }
    }
}

impl<T> LatestCell<T> {
    pub fn push(&mut self, item: T) {
        if self.value.is_some() {
            self.coalesced += 1;
        }
        self.value = Some(item);
    }

    pub fn take(&mut self) -> Option<T> {
        self.value.take()
    }

    pub fn coalesced(&self) -> u64 {
        self.coalesced
    }
}

// ──────────────────── AuditSecurity (never drop, never coalesce) ────────────

/// Outcome for the audit/security class: overflow is a HARD ERROR surface,
/// not a drop — HITL prompts and audit confirmations may never vanish.
#[derive(Debug, PartialEq, Eq)]
pub enum AuditPush {
    Accepted,
    /// The UI must render a hard error state; the producer must block.
    /// This is distinct from ProducerMustBlock: it is also a user-visible
    /// failure ("approval queue overflow — daemon paused") because losing
    /// even the *ordering pressure* of security prompts is reportable.
    OverflowHardError,
}

pub struct AuditQueue<T> {
    buf: VecDeque<T>,
    cap: usize,
    overflowed: bool,
}

impl<T> AuditQueue<T> {
    pub fn new(cap: usize) -> Self {
        Self {
            buf: VecDeque::with_capacity(cap),
            cap,
            overflowed: false,
        }
    }

    pub fn push(&mut self, item: T) -> AuditPush {
        if self.buf.len() >= self.cap {
            self.overflowed = true;
            return AuditPush::OverflowHardError; // item retained by producer
        }
        self.buf.push_back(item);
        AuditPush::Accepted
    }

    /// FIFO only — coalescing security prompts is forbidden by design;
    /// there is intentionally no bulk-drain-to-latest API on this type.
    pub fn pop(&mut self) -> Option<T> {
        self.buf.pop_front()
    }

    pub fn overflow_seen(&self) -> bool {
        self.overflowed
    }

    pub fn len(&self) -> usize {
        self.buf.len()
    }

    pub fn is_empty(&self) -> bool {
        self.buf.is_empty()
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn ordered_never_drops_blocks_producer_instead() {
        let mut q = OrderedQueue::new(2);
        assert_eq!(q.push(1, "a"), PushOutcome::Accepted);
        assert_eq!(q.push(2, "b"), PushOutcome::Accepted);
        assert_eq!(q.push(3, "c"), PushOutcome::ProducerMustBlock);
        assert_eq!(q.len(), 2, "nothing was silently lost");
        q.pop().unwrap();
        assert_eq!(q.push(3, "c"), PushOutcome::Accepted, "resumes after drain");
    }

    #[test]
    fn ordered_gap_is_detected_and_survives_until_taken() {
        let mut q = OrderedQueue::new(10);
        q.push(1, ());
        q.push(2, ());
        q.push(5, ()); // gap: 3..5
        assert_eq!(q.gap_detected(), Some((3, 5)));
        assert_eq!(q.gap_detected(), Some((3, 5)), "peek does not clear");
        assert_eq!(q.take_gap(), Some((3, 5)));
        assert_eq!(q.gap_detected(), None);
    }

    #[test]
    fn ordered_resync_resets_tracking() {
        let mut q = OrderedQueue::new(10);
        q.push(1, ());
        q.push(9, ());
        assert!(q.take_gap().is_some());
        q.reset_after_resync(9);
        q.push(10, ());
        assert_eq!(q.gap_detected(), None, "contiguous after resync");
    }

    #[test]
    fn telemetry_drops_oldest_with_visible_counter() {
        let mut r = TelemetryRing::new(3);
        for i in 0..5 {
            r.push(i);
        }
        assert_eq!(r.dropped(), 2);
        assert_eq!(r.pop(), Some(2), "oldest surviving item is #2");
        assert_eq!(r.len(), 2);
    }

    #[test]
    fn viewmodel_coalesces_to_latest() {
        let mut c = LatestCell::default();
        c.push(1);
        c.push(2);
        c.push(3);
        assert_eq!(c.take(), Some(3));
        assert_eq!(c.coalesced(), 2);
        assert_eq!(c.take(), None);
    }

    #[test]
    fn audit_overflow_is_hard_error_not_drop() {
        let mut q = AuditQueue::new(1);
        assert_eq!(q.push("hitl-1"), AuditPush::Accepted);
        assert_eq!(q.push("hitl-2"), AuditPush::OverflowHardError);
        assert!(q.overflow_seen());
        assert_eq!(q.len(), 1, "queued prompt untouched");
        assert_eq!(q.pop(), Some("hitl-1"), "FIFO, no coalescing");
    }
}
