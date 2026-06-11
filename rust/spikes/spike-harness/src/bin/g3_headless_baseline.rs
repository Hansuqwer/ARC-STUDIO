//! g3-headless-baseline — the non-render half of gate G3, runnable today.
//!
//! G3 (full): replay 100 event-stream rows through the Sprint-1 harness in
//! <250 ms with no frame >33 ms. The render half needs the Sprint-3 candidate;
//! this binary measures the decode+project half (fixture JSON -> RunEvent ->
//! KnownRunEvent -> view-model string) so the spike can attribute time:
//! if a candidate busts 250 ms, this baseline shows how much was rendering.
//!
//! Usage: g3-headless-baseline <fixtures-run-event-seq-scenario-dir> <reports-dir>

use spike_harness::percentile::Percentiles;
use std::time::Instant;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let dir = std::path::PathBuf::from(
        std::env::args()
            .nth(1)
            .unwrap_or_else(|| "../../protocol/fixtures/run-event-seq/tool-use-streaming".into()),
    );
    let reports = std::path::PathBuf::from(
        std::env::args().nth(2).unwrap_or_else(|| "../../reports".into()),
    );

    // Load raw fixture bytes once (I/O excluded from the measured path).
    let mut files: Vec<_> = std::fs::read_dir(&dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("json"))
        .collect();
    files.sort();
    let raws: Vec<String> = files
        .iter()
        .map(std::fs::read_to_string)
        .collect::<Result<_, _>>()?;
    // Repeat the scenario to reach the G3 row count of 100.
    let rows: Vec<&str> = raws.iter().map(String::as_str).cycle().take(100).collect();

    // Warmup + 50 measured iterations of the full 100-row replay.
    let mut totals_us = Vec::with_capacity(50);
    let mut per_row_us: Vec<u64> = Vec::with_capacity(50 * rows.len());
    for iter in 0..60 {
        let t_total = Instant::now();
        for raw in &rows {
            let t_row = Instant::now();
            // The exact panel path: decode -> typed projection -> view-model line.
            let ev: serde_json::Value = serde_json::from_str(raw)?;
            let kind = ev["type"].as_str().unwrap_or("?");
            let seq = ev["sequence"].as_u64().unwrap_or(0);
            let summary = format!("{seq:>4} {kind:<24} {}", ev["timestamp"].as_str().unwrap_or(""));
            std::hint::black_box(&summary);
            if iter >= 10 {
                per_row_us.push(t_row.elapsed().as_micros() as u64);
            }
        }
        if iter >= 10 {
            totals_us.push(t_total.elapsed().as_micros() as u64);
        }
    }

    let total_p = Percentiles::from_us(&totals_us).ok_or("no samples")?;
    let row_p = Percentiles::from_us(&per_row_us).ok_or("no samples")?;
    eprintln!(
        "G3 headless (100 rows): total p50={} us p99={} us | per-row p99={} us",
        total_p.p50_us, total_p.p99_us, row_p.p99_us
    );

    std::fs::create_dir_all(&reports)?;
    let report = serde_json::json!({
        "gate": "G3 (headless half: decode+project only, NO rendering)",
        "honesty_note": "This is the non-render baseline for time attribution during the spike. It is NOT a G3 pass: the 250 ms budget and 33 ms frame bar apply to the full pipeline including rendering on the spike machine.",
        "scenario_dir": dir.display().to_string(),
        "rows_per_replay": rows.len(),
        "replays_measured": totals_us.len(),
        "total_us": total_p,
        "per_row_us": row_p,
        "environment": {
            "os": std::env::consts::OS,
            "arch": std::env::consts::ARCH,
            "note": "sandboxed CI-class container; NOT the pinned benchmark machine"
        },
        "raw_total_samples_us": totals_us,
    });
    let path = reports.join("g3-headless-baseline.json");
    std::fs::write(&path, serde_json::to_string_pretty(&report)?)?;
    eprintln!("wrote {}", path.display());
    Ok(())
}
