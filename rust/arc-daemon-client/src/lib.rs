//! arc-daemon-client — Sprint 1 HTTP+SSE client for the ARC daemon.
//!
//! Endpoints (verified in `python/src/agent_runtime_cockpit/web/routes.py:1395-1413`):
//! - `GET /health`
//! - `GET /api/runs`
//! - `GET /api/events/stream`         (global SSE)
//! - `GET /api/runs/{run_id}/events`  (per-run SSE — inventoried; same parser)
//!
//! Posture: loopback only; cancellation wins every select; idle timeout with
//! heartbeat reset; structured errors; ordered-stream consumers resume from
//! `sequence` (gap => Degraded/Stale surface state upstream, never silence).

pub mod replay;
pub mod sse;

use arc_protocol_rs::{ArcEnvelope, ArcError, DaemonNotification, RunEvent};
use std::time::Duration;
use tokio_util::sync::CancellationToken;

#[derive(Debug, thiserror::Error)]
pub enum ClientError {
    #[error("transport: {0}")]
    Transport(#[from] reqwest::Error),
    #[error("idle timeout after {0:?}")]
    IdleTimeout(Duration),
    #[error("decode at sse line {line}: {source}")]
    Decode {
        line: u64,
        source: serde_json::Error,
    },
    #[error("daemon error: {0:?}")]
    Daemon(Box<ArcError>),
    #[error("cancelled")]
    Cancelled,
    #[error("invalid base url")]
    BadUrl,
}

pub struct DaemonClient {
    http: reqwest::Client,
    base: reqwest::Url,
    /// SSE: max silence before reconnect; ":" heartbeat comments reset it.
    pub idle_timeout: Duration,
}

impl DaemonClient {
    /// `base` must be loopback (e.g. `http://127.0.0.1:8765`); enforced here.
    pub fn new(base: &str) -> Result<Self, ClientError> {
        let url = reqwest::Url::parse(base).map_err(|_| ClientError::BadUrl)?;
        let loopback = matches!(url.host_str(), Some("127.0.0.1") | Some("localhost") | Some("[::1]"));
        if !loopback {
            return Err(ClientError::BadUrl);
        }
        Ok(Self {
            http: reqwest::Client::builder()
                .connect_timeout(Duration::from_secs(2))
                .build()?,
            base: url,
            idle_timeout: Duration::from_secs(30),
        })
    }

    fn url(&self, path: &str) -> Result<reqwest::Url, ClientError> {
        self.base.join(path).map_err(|_| ClientError::BadUrl)
    }

    pub async fn health(&self) -> Result<(), ClientError> {
        let r = self
            .http
            .get(self.url("/health")?)
            .timeout(Duration::from_secs(2))
            .send()
            .await?;
        r.error_for_status().map(|_| ()).map_err(Into::into)
    }

    pub async fn list_runs(&self) -> Result<serde_json::Value, ClientError> {
        let env: ArcEnvelope<serde_json::Value> = self
            .http
            .get(self.url("/api/runs")?)
            .timeout(Duration::from_secs(10))
            .send()
            .await?
            .json()
            .await?;
        env.into_result()
            .map(|(d, _)| d.unwrap_or_default())
            .map_err(|e| ClientError::Daemon(Box::new(e)))
    }

    /// Stream `GET /api/events/stream` (global daemon notifications).
    ///
    /// Sprint-1 live finding F5: this stream carries `DaemonNotification`
    /// (lowercase event_type namespace), NOT registry `RunEvent`s. RunEvents
    /// flow on the per-run stream — use [`Self::stream_run_events`].
    pub async fn stream_notifications(
        &self,
        cancel: CancellationToken,
        on_event: impl FnMut(DaemonNotification),
    ) -> Result<(), ClientError> {
        self.stream_from(self.url("/api/events/stream")?, cancel, on_event)
            .await
    }

    /// Stream a single run's events (`GET /api/runs/{run_id}/events`).
    pub async fn stream_run_events(
        &self,
        run_id: &str,
        cancel: CancellationToken,
        on_event: impl FnMut(RunEvent),
    ) -> Result<(), ClientError> {
        self.stream_from(
            self.url(&format!("/api/runs/{run_id}/events"))?,
            cancel,
            on_event,
        )
        .await
    }

    async fn stream_from<T: serde::de::DeserializeOwned>(
        &self,
        url: reqwest::Url,
        cancel: CancellationToken,
        mut on_event: impl FnMut(T),
    ) -> Result<(), ClientError> {
        use futures_util::StreamExt;
        let resp = self
            .http
            .get(url)
            .header(reqwest::header::ACCEPT, "text/event-stream")
            .send()
            .await?
            .error_for_status()?;
        let mut body = resp.bytes_stream();
        let mut parser = sse::SseParser::default();
        loop {
            let chunk = tokio::select! {
                biased;
                _ = cancel.cancelled() => return Err(ClientError::Cancelled),
                c = tokio::time::timeout(self.idle_timeout, body.next()) => match c {
                    Err(_) => return Err(ClientError::IdleTimeout(self.idle_timeout)),
                    Ok(None) => return Ok(()),            // server closed cleanly
                    Ok(Some(c)) => c?,
                },
            };
            for frame in parser.push(&chunk) {
                let ev: T =
                    serde_json::from_str(&frame.data).map_err(|source| ClientError::Decode {
                        line: frame.line_no,
                        source,
                    })?;
                on_event(ev);
            }
        }
    }
}

/// Capped, jittered exponential backoff wrapper around
/// [`DaemonClient::stream_notifications`]. 250 ms -> 30 s cap; resets to 250 ms
/// after any successful event. For per-run ordered streams, gap detection
/// (resume from `sequence`) is the caller's obligation: a gap is a `Stale`
/// surface state with a visible counter, never silence.
pub async fn stream_notifications_with_reconnect(
    client: &DaemonClient,
    cancel: CancellationToken,
    mut on_event: impl FnMut(DaemonNotification),
    mut on_state: impl FnMut(StreamState),
) -> Result<(), ClientError> {
    let mut backoff = Duration::from_millis(250);
    loop {
        on_state(StreamState::Connecting);
        let got_any = std::cell::Cell::new(false);
        let r = client
            .stream_notifications(cancel.clone(), |ev| {
                got_any.set(true);
                on_event(ev);
            })
            .await;
        match r {
            Err(ClientError::Cancelled) => return Err(ClientError::Cancelled),
            Ok(()) | Err(_) => {
                if got_any.get() {
                    backoff = Duration::from_millis(250);
                }
                on_state(StreamState::Backoff(backoff));
                tokio::select! {
                    biased;
                    _ = cancel.cancelled() => return Err(ClientError::Cancelled),
                    _ = tokio::time::sleep(jitter(backoff)) => {}
                }
                backoff = (backoff * 2).min(Duration::from_secs(30));
            }
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum StreamState {
    Connecting,
    Backoff(Duration),
}

fn jitter(d: Duration) -> Duration {
    // +/-20% deterministic-ish jitter from a timestamp; good enough for backoff
    // (no rand dependency in Sprint 1).
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.subsec_nanos())
        .unwrap_or(0) as u64;
    let pct = 80 + (nanos % 41); // 80..=120
    d * (pct as u32) / 100
}
