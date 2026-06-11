#![allow(clippy::unwrap_used)] // example/diagnostic binary
//! Sprint-1 RTT baseline (brief §3.3.5): 200x GET /api/runs against a live
//! loopback daemon; writes p50/p95/p99 + raw samples to reports/rtt-http.json.
//! This is the input to ADR-0001 kill criterion A3 (p95 > 50 ms after the UDS
//! step => escalate). Also exercises health + SSE connect/cancel as a live smoke.
//!
//! Usage: rtt_baseline <base-url> <reports-dir>

use arc_daemon_client::DaemonClient;
use tokio_util::sync::CancellationToken;

#[tokio::main(flavor = "current_thread")]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let base = args
        .next()
        .unwrap_or_else(|| "http://127.0.0.1:7777".into());
    let reports = std::path::PathBuf::from(args.next().unwrap_or_else(|| "../reports".into()));

    let client = DaemonClient::new(&base)?;

    // 1) health gate
    client.health().await?;
    eprintln!("health: ok");

    // 2) warmup + 200 timed GET /api/runs
    for _ in 0..10 {
        let _ = client.list_runs().await?;
    }
    let mut samples_us: Vec<u64> = Vec::with_capacity(200);
    for _ in 0..200 {
        let t0 = std::time::Instant::now();
        let _ = client.list_runs().await?;
        samples_us.push(t0.elapsed().as_micros() as u64);
    }
    let mut sorted = samples_us.clone();
    sorted.sort_unstable();
    let pct =
        |p: f64| sorted[((sorted.len() as f64 * p).ceil() as usize - 1).min(sorted.len() - 1)];
    let (p50, p95, p99) = (pct(0.50), pct(0.95), pct(0.99));
    eprintln!("rtt GET /api/runs: p50={p50}us p95={p95}us p99={p99}us (n=200)");

    // 3) SSE live smoke (global notification stream): connect, cancel after 1500 ms;
    //    cancellation must win. Decodes DaemonNotification (Sprint-1 finding F5).
    let cancel = CancellationToken::new();
    let c2 = cancel.clone();
    tokio::spawn(async move {
        tokio::time::sleep(std::time::Duration::from_millis(1500)).await;
        c2.cancel();
    });
    let mut n_events = 0u64;
    let sse_result = client
        .stream_notifications(cancel, |_ev| n_events += 1)
        .await;
    let sse_outcome = match &sse_result {
        Err(arc_daemon_client::ClientError::Cancelled) => "cancelled-cleanly",
        Ok(()) => "server-closed",
        Err(e) => {
            eprintln!("sse: {e}");
            "error"
        }
    };
    eprintln!("sse: outcome={sse_outcome} events={n_events}");

    // 4) raw report
    std::fs::create_dir_all(&reports)?;
    let report = serde_json::json!({
        "generated": chrono_free_now(),
        "endpoint": "GET /api/runs",
        "transport": "http-loopback",
        "base": base,
        "n": samples_us.len(),
        "unit": "microseconds",
        "p50_us": p50, "p95_us": p95, "p99_us": p99,
        "a3_kill_criterion": "p95 > 50ms after UDS step => escalate",
        "a3_status": if p95 < 50_000 { "pass (HTTP baseline)" } else { "ESCALATE" },
        "sse_smoke": { "outcome": sse_outcome, "events_seen": n_events },
        "environment": {
            "os": std::env::consts::OS,
            "arch": std::env::consts::ARCH,
            "note": "sandboxed CI-class container; NOT the pinned benchmark machine; numbers are indicative only per do-not-overclaim policy"
        },
        "raw_samples_us": samples_us,
    });
    let path = reports.join("rtt-http.json");
    std::fs::write(&path, serde_json::to_string_pretty(&report)?)?;
    eprintln!("wrote {}", path.display());
    Ok(())
}

/// RFC3339-ish UTC timestamp without pulling in chrono for one line.
fn chrono_free_now() -> String {
    let d = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    format!("unix:{}", d.as_secs())
}
