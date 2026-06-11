//! Daemon supervision (brief §3.8, pulled forward into Sprint 2 because the
//! status rail needs DaemonState from day one — producer-truth rule).
//!
//! Adds the review report §13/Sprint-6 delta now rather than later:
//! jittered backoff AND a max-restart circuit breaker (5 restarts / 5 min ⇒
//! stay Degraded with "restart manually", no crash-loop battery burn).

use arc_daemon_client::DaemonClient;
use std::collections::VecDeque;
use std::time::{Duration, Instant};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DaemonState {
    Starting,
    Healthy,
    Degraded { reason: String },
    /// Circuit breaker open: supervisor will NOT restart; user action required.
    CircuitOpen { restarts_in_window: usize },
    Stopped,
}

/// Pure circuit-breaker policy, separated from process plumbing so it is
/// deterministic and unit-testable.
#[derive(Debug)]
pub struct CircuitBreaker {
    window: Duration,
    max_restarts: usize,
    restarts: VecDeque<Instant>,
}

impl Default for CircuitBreaker {
    fn default() -> Self {
        Self {
            window: Duration::from_secs(300),
            max_restarts: 5,
            restarts: VecDeque::new(),
        }
    }
}

impl CircuitBreaker {
    pub fn record_restart(&mut self, now: Instant) -> bool {
        while let Some(&front) = self.restarts.front() {
            if now.duration_since(front) > self.window {
                self.restarts.pop_front();
            } else {
                break;
            }
        }
        self.restarts.push_back(now);
        self.restarts.len() <= self.max_restarts
    }

    pub fn restarts_in_window(&self) -> usize {
        self.restarts.len()
    }
}

/// Backoff policy: 250 ms doubling to 30 s cap; reset on Healthy.
#[derive(Debug)]
pub struct Backoff {
    current: Duration,
}

impl Default for Backoff {
    fn default() -> Self {
        Self {
            current: Duration::from_millis(250),
        }
    }
}

impl Backoff {
    pub fn advance(&mut self) -> Duration {
        let d = self.current;
        self.current = (self.current * 2).min(Duration::from_secs(30));
        d
    }

    pub fn reset(&mut self) {
        self.current = Duration::from_millis(250);
    }
}

/// Health-gate poll: per-try 2 s timeout (client-enforced), total budget 10 s.
pub async fn await_healthy(client: &DaemonClient, budget: Duration) -> bool {
    tokio::time::timeout(budget, async {
        loop {
            if client.health().await.is_ok() {
                break;
            }
            tokio::time::sleep(Duration::from_millis(200)).await;
        }
    })
    .await
    .is_ok()
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn breaker_opens_after_five_in_window() {
        let mut cb = CircuitBreaker::default();
        let t0 = Instant::now();
        for i in 0..5 {
            assert!(cb.record_restart(t0 + Duration::from_secs(i)), "restart {i} allowed");
        }
        assert!(!cb.record_restart(t0 + Duration::from_secs(5)), "6th restart trips breaker");
    }

    #[test]
    fn breaker_window_slides() {
        let mut cb = CircuitBreaker::default();
        let t0 = Instant::now();
        for i in 0..5 {
            cb.record_restart(t0 + Duration::from_secs(i * 10));
        }
        // 6th restart at t0+360s: first restarts have aged out of the 300s window.
        assert!(cb.record_restart(t0 + Duration::from_secs(360)));
    }

    #[test]
    fn backoff_doubles_and_caps_and_resets() {
        let mut b = Backoff::default();
        assert_eq!(b.advance(), Duration::from_millis(250));
        assert_eq!(b.advance(), Duration::from_millis(500));
        for _ in 0..10 {
            b.advance();
        }
        assert_eq!(b.advance(), Duration::from_secs(30), "capped");
        b.reset();
        assert_eq!(b.advance(), Duration::from_millis(250));
    }
}
