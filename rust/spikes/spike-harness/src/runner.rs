//! Report assembly — turns [`crate::script::ScriptResults`] into the gate
//! rows + SpikeReport. Methodology stays centralized; candidates own only
//! their event loop and how each [`crate::script::Action`] mutates the view.

use crate::gates::{Gate, GateRow};
use crate::percentile::Percentiles;
use crate::report::{MachineIdentity, SpikeReport};
use crate::script::ScriptResults;

pub struct RunConfig {
    pub machine: MachineIdentity,
    pub date: String,
    /// Where raw per-gate sample JSON and the final report land.
    pub reports_dir: std::path::PathBuf,
}

impl RunConfig {
    pub fn refresh_hz(&self) -> f64 {
        self.machine
            .display
            .split('@')
            .nth(1)
            .and_then(|s| s.split("Hz").next())
            .and_then(|s| s.trim().parse::<f64>().ok())
            .unwrap_or(60.0)
    }
}

fn write_raw(
    dir: &std::path::Path,
    candidate: &str,
    gate: &str,
    samples_us: &[u64],
) -> std::io::Result<String> {
    std::fs::create_dir_all(dir)?;
    let path = dir.join(format!("spike-raw-{candidate}-{gate}.json"));
    std::fs::write(
        &path,
        serde_json::to_string_pretty(&serde_json::json!({
            "candidate": candidate,
            "gate": gate,
            "unit": "microseconds",
            "n": samples_us.len(),
            "samples": samples_us,
        }))
        .map_err(std::io::Error::other)?,
    )?;
    Ok(path.display().to_string())
}

fn median(mut values: Vec<u64>) -> Option<u64> {
    if values.is_empty() {
        return None;
    }
    values.sort_unstable();
    Some(values[values.len() / 2])
}

/// Assemble `reports/spike-<candidate>.json` from frame-script results.
pub fn assemble_report(
    candidate: &str,
    version: &str,
    results: &ScriptResults,
    cfg: &RunConfig,
) -> anyhow::Result<SpikeReport> {
    let hz = cfg.refresh_hz();
    let mut report = SpikeReport::new(candidate, version, &cfg.date, cfg.machine.clone());

    // G1: median per workload family; either family missing => NotRun.
    let family = |prefix: &str| -> Vec<u64> {
        results
            .g1_first_paint_ms
            .iter()
            .filter(|(label, _)| label.starts_with(prefix))
            .map(|(_, ms)| *ms)
            .collect()
    };
    let source = median(family("source"));
    let pathological = median(family("pathological"));
    let governing = match (source, pathological) {
        (Some(a), Some(b)) => Some(a.max(b)),
        _ => None,
    };
    let mut g1 = GateRow::evaluate(
        Gate::G1HugeFileFirstPaint,
        candidate,
        hz,
        None,
        governing,
        None,
        None,
    );
    g1.notes = format!(
        "median first paint: source-100mb {source:?} ms, pathological {pathological:?} ms (worst governs)"
    );
    report.rows.push(g1);

    // G2: present-to-present scroll frames.
    let mut g2 = GateRow::evaluate(
        Gate::G2DiffScrollFrameTime,
        candidate,
        hz,
        Percentiles::from_us(&results.g2_frame_us),
        None,
        None,
        None,
    );
    if !results.g2_frame_us.is_empty() {
        g2.raw_data_path = Some(write_raw(
            &cfg.reports_dir,
            candidate,
            "g2",
            &results.g2_frame_us,
        )?);
    }
    report.rows.push(g2);

    // G3: total budget + worst-frame budget.
    let worst_ms = results.g3_frame_us.iter().max().copied().unwrap_or(0) / 1000;
    let has_g3 = !results.g3_frame_us.is_empty();
    let mut g3 = GateRow::evaluate(
        Gate::G3EventReplayBudget,
        candidate,
        hz,
        Percentiles::from_us(&results.g3_frame_us),
        None,
        has_g3.then_some(results.g3_total_ms),
        has_g3.then_some(worst_ms),
    );
    if has_g3 {
        g3.raw_data_path = Some(write_raw(
            &cfg.reports_dir,
            candidate,
            "g3",
            &results.g3_frame_us,
        )?);
    }
    g3.notes = "headless decode baseline: reports/g3-headless-baseline.json".into();
    report.rows.push(g3);

    // G4: issue-to-present per key.
    let mut g4 = GateRow::evaluate(
        Gate::G4TypingLatency,
        candidate,
        hz,
        Percentiles::from_us(&results.g4_us),
        None,
        None,
        None,
    );
    if !results.g4_us.is_empty() {
        g4.raw_data_path = Some(write_raw(
            &cfg.reports_dir,
            candidate,
            "g4",
            &results.g4_us,
        )?);
    }
    report.rows.push(g4);

    // G7: screenshot path recorded; golden compare remains operator evidence.
    let mut g7 = GateRow::evaluate(Gate::G7BidiLigatures, candidate, hz, None, None, None, None);
    g7.raw_data_path = results
        .g7_screenshot
        .as_ref()
        .map(|path| path.display().to_string());
    report.rows.push(g7);

    for gate in [Gate::G5Accessibility, Gate::G6Ime, Gate::G8Sustainability] {
        report.rows.push(GateRow::evaluate(
            gate, candidate, hz, None, None, None, None,
        ));
    }

    std::fs::create_dir_all(&cfg.reports_dir)?;
    report.write(&cfg.reports_dir.join(format!("spike-{candidate}.json")))?;
    Ok(report)
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;
    use crate::gates::GateOutcome;
    use crate::script::{Action, FrameScript, ScriptPlan};
    use std::time::{Duration, Instant};

    fn cfg(dir: &std::path::Path) -> RunConfig {
        RunConfig {
            machine: MachineIdentity {
                hostname: "test".into(),
                os: "test".into(),
                arch: "test".into(),
                cpu: "test".into(),
                gpu: "test".into(),
                display: "1920x1080@60Hz test".into(),
                power_profile: "test".into(),
                is_pinned_benchmark_machine: false,
            },
            date: "2026-06-11".into(),
            reports_dir: dir.to_path_buf(),
        }
    }

    fn plan() -> ScriptPlan {
        ScriptPlan {
            source_100mb: "/w/src.txt".into(),
            pathological_10mb: "/w/path.txt".into(),
            diff_5k: "/w/d.patch".into(),
            g1_reps: 3,
            scroll_frames: 60,
            rows: 100,
            g3_chunk: 10,
            keys: vec!['x'; 500],
            screenshot_out: "/r/shot.png".into(),
            warmup_frames: 5,
        }
    }

    fn run_with_frame_time(dir: &std::path::Path, frame: Duration) -> SpikeReport {
        let mut script = FrameScript::new(plan());
        let mut now = Instant::now();
        loop {
            match script.on_present(now) {
                Action::Finished => break,
                _ => now += frame,
            }
        }
        assemble_report("mock", "0.0.0-test", &script.into_results(), &cfg(dir)).unwrap()
    }

    #[test]
    fn fast_loop_passes_automatic_gates_evidence_still_blocks() {
        let dir = std::env::temp_dir().join("spike-asm-fast");
        let report = run_with_frame_time(&dir, Duration::from_millis(8));
        for row in &report.rows {
            match row.gate {
                Gate::G1HugeFileFirstPaint
                | Gate::G2DiffScrollFrameTime
                | Gate::G3EventReplayBudget
                | Gate::G4TypingLatency => {
                    assert_eq!(row.outcome, GateOutcome::Pass, "{:?}", row.gate)
                }
                Gate::G7BidiLigatures => {
                    assert!(matches!(row.outcome, GateOutcome::EvidencePending { .. }));
                    assert!(row.raw_data_path.is_some(), "screenshot path recorded");
                }
                _ => assert!(matches!(row.outcome, GateOutcome::EvidencePending { .. })),
            }
        }
        let blockers = report.spike_verdict().unwrap_err();
        assert_eq!(blockers.len(), 4, "G5,G6,G7,G8 pending: {blockers:?}");
        assert!(dir.join("spike-mock.json").exists());
        let raw = std::fs::read_to_string(dir.join("spike-raw-mock-g4.json")).unwrap();
        assert!(raw.contains("\"n\": 500"));
    }

    #[test]
    fn slow_loop_fails_g2_g3_g4_with_reasons() {
        let dir = std::env::temp_dir().join("spike-asm-slow");
        let report = run_with_frame_time(&dir, Duration::from_millis(40));
        let outcome = |gate: Gate| {
            report
                .rows
                .iter()
                .find(|row| row.gate == gate)
                .map(|row| row.outcome.clone())
                .unwrap()
        };
        assert!(matches!(
            outcome(Gate::G2DiffScrollFrameTime),
            GateOutcome::Fail { .. }
        ));
        assert!(matches!(
            outcome(Gate::G3EventReplayBudget),
            GateOutcome::Fail { .. }
        ));
        assert!(matches!(
            outcome(Gate::G4TypingLatency),
            GateOutcome::Fail { .. }
        ));
        assert_eq!(outcome(Gate::G1HugeFileFirstPaint), GateOutcome::Pass);
    }

    #[test]
    fn empty_results_are_notrun_not_pass() {
        let dir = std::env::temp_dir().join("spike-asm-empty");
        let report =
            assemble_report("mock", "0.0.0-test", &ScriptResults::default(), &cfg(&dir)).unwrap();
        for gate in [
            Gate::G1HugeFileFirstPaint,
            Gate::G2DiffScrollFrameTime,
            Gate::G3EventReplayBudget,
            Gate::G4TypingLatency,
        ] {
            let row = report.rows.iter().find(|row| row.gate == gate).unwrap();
            assert_eq!(row.outcome, GateOutcome::NotRun, "{gate:?}");
        }
        assert!(report.spike_verdict().is_err(), "NotRun blocks verdict");
    }
}
