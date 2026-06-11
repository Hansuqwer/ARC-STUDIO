use spike_harness::workloads::{seeds, synthetic_keystream};
use spike_harness::{
    assemble_report, Action, FrameScript, MachineIdentity, RunConfig, ScriptPlan, ScriptResults,
};
use std::time::Instant;

const CANDIDATE: &str = "bespoke";
const VERSION: &str =
    "winit 0.31.0-beta.2 / vello 0.9.0 / parley 0.10.0 / accesskit_winit 0.33.0 / masonry 0.4.0";

fn main() -> anyhow::Result<()> {
    let cfg = config();
    let results = run_candidate_script(FrameScript::new(plan()))?;
    let report = assemble_report(CANDIDATE, VERSION, &results, &cfg)?;
    if let Err(blockers) = report.spike_verdict() {
        for blocker in blockers {
            println!("BLOCKER: {blocker}");
        }
    }
    Ok(())
}

/// Wire this loop into one winit/vello window. Call
/// `script.on_present(Instant::now())` from a trustworthy wgpu present or
/// RedrawRequested-complete callback, then apply the returned action once.
fn run_candidate_script(mut script: FrameScript) -> anyhow::Result<ScriptResults> {
    loop {
        match script.on_present(Instant::now()) {
            Action::OpenWorkload { path, label } => {
                todo!("G1: {label}; read {path:?}, swap text surface, request redraw, wait present")
            }
            Action::LoadDiff { path } => todo!("G2 setup: read {path:?}, swap diff surface"),
            Action::ScrollStep => todo!("G2: scroll diff one scripted step, request redraw once"),
            Action::AppendRows { from, count } => todo!(
                "G3: append rows [{from}..{}) this frame only, request redraw once",
                from + count
            ),
            Action::TypeChar { ch } => {
                todo!("G4: insert synthetic key {ch:?}, request redraw once")
            }
            Action::TakeScreenshot { out } => {
                todo!("G7: render bidi/ligature surface and write screenshot to {out:?}")
            }
            Action::Settle => todo!("settle frame: no sampled mutation, request redraw once"),
            Action::Finished => return Ok(script.into_results()),
        }
    }
}

fn config() -> RunConfig {
    RunConfig {
        machine: MachineIdentity {
            hostname: "BLUETEAM.local".into(),
            os: "Darwin 25.4.0".into(),
            arch: "arm64".into(),
            cpu: "Apple M4".into(),
            gpu: "Apple M4, 8 cores, Metal 4".into(),
            display: "Color LCD 2940x1912 physical, 1470x956 @ 60.00Hz logical".into(),
            power_profile: "No thermal/performance/CPU power warning recorded".into(),
            is_pinned_benchmark_machine: false,
        },
        date: "2026-06-11".into(),
        reports_dir: "../../reports".into(),
    }
}

fn plan() -> ScriptPlan {
    let root = std::path::PathBuf::from(
        "/var/folders/dp/1fh07k_922j5qk7xfncn1zv40000gn/T/opencode/arc-v2-spike/workloads",
    );
    ScriptPlan {
        source_100mb: root.join("g1-source-100mb.txt"),
        pathological_10mb: root.join("g1-pathological-10mb-single-line.txt"),
        diff_5k: root.join("g2-diff-5k-lines.patch"),
        g1_reps: 5,
        scroll_frames: 300,
        rows: 100,
        g3_chunk: 10,
        keys: synthetic_keystream(seeds::G4_KEYS),
        screenshot_out: "../../reports/spike-bespoke-bidi.png".into(),
        warmup_frames: 5,
    }
}
