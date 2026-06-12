//! floem 0.2 spike — uses the official timer pattern from floem/examples/timer:
//!   Effect::new(|_| { tick.track(); exec_after(d, |_| { tick.set(()); }); });
//! exec_after MUST be called inside floem::launch (needs current_view context).

use floem::action::exec_after;
use floem::prelude::*;
use floem_reactive::{create_effect, RwSignal, SignalGet, SignalUpdate};
use spike_harness::views::{bidi_sample_lines, DiffDoc, EventTable, TextDoc, TypeBox};
use spike_harness::workloads::{seeds, synthetic_keystream};
use spike_harness::{assemble_report, Action, FrameScript, MachineIdentity, RunConfig, ScriptPlan};
use std::cell::RefCell;
use std::rc::Rc;
use std::time::{Duration, Instant};

const CANDIDATE: &str = "floem";
const VERSION: &str = "0.2.0";

fn main() {
    let spike = Rc::new(RefCell::new(Spike {
        script: FrameScript::new(plan()),
        diff_doc: None,
        event_table: EventTable::default(),
        typebox: TypeBox::default(),
    }));

    floem::launch(move || {
        let lines: RwSignal<Vec<String>> = RwSignal::new(vec!["floem spike…".into()]);
        let tick: RwSignal<Instant> = RwSignal::new(Instant::now());
        let done: RwSignal<bool> = RwSignal::new(false);
        let spike = spike.clone();

        // Official floem timer loop pattern.
        create_effect(move |_| {
            let t = tick.get(); // subscribe
            if done.get() { return; }

            let action = spike.borrow_mut().script.on_present(t);
            match action {
                Action::OpenWorkload { path, label: _ } => {
                    if let Ok(doc) = TextDoc::load(&path) {
                        lines.set(doc.viewport().map(str::to_owned).collect());
                    }
                }
                Action::LoadDiff { path } => {
                    if let Ok(text) = std::fs::read_to_string(&path) {
                        let doc = DiffDoc::parse(&text);
                        lines.set(doc.viewport().map(|(_, l)| l.clone()).collect());
                        spike.borrow_mut().diff_doc = Some(doc);
                    }
                }
                Action::ScrollStep => {
                    if let Some(doc) = spike.borrow_mut().diff_doc.as_mut() {
                        doc.scroll_step();
                        lines.set(doc.viewport().map(|(_, l)| l.clone()).collect());
                    }
                }
                Action::AppendRows { from, count } => {
                    let mut sp = spike.borrow_mut();
                    for i in from..from + count {
                        sp.event_table.append(&format!(
                            r#"{{"sequence":{i},"type":"TOOL_CALL","timestamp":"2026-06-12T00:00:00Z","data":{{"tool_name":"row_{i}"}}}}"#
                        ));
                    }
                    lines.set(sp.event_table.tail_viewport().map(EventTable::display_line).collect());
                }
                Action::TypeChar { ch } => {
                    spike.borrow_mut().typebox.push(ch);
                    lines.set(vec![spike.borrow().typebox.content.clone()]);
                }
                Action::TakeScreenshot { out: _ } => {
                    lines.set(bidi_sample_lines().iter().map(|s| s.to_string()).collect());
                    // G7: take screenshot now with Cmd+Shift+4, save to reports/spike-floem-bidi.png
                }
                Action::Settle => {} // no mutation, just tick again
                Action::Finished => {
                    done.set(true);
                    let dummy = FrameScript::new(ScriptPlan {
                        source_100mb: "".into(), pathological_10mb: "".into(),
                        diff_5k: "".into(), g1_reps: 0, scroll_frames: 0,
                        rows: 0, g3_chunk: 10, keys: vec![],
                        screenshot_out: "".into(), warmup_frames: 0,
                    });
                    let real = std::mem::replace(&mut spike.borrow_mut().script, dummy);
                    let results = real.into_results();
                    let cfg = config();
                    match assemble_report(CANDIDATE, VERSION, &results, &cfg) {
                        Ok(report) => {
                            if let Err(bs) = report.spike_verdict() {
                                for b in bs { eprintln!("BLOCKER: {b}"); }
                            }
                            eprintln!("✓ Report: {}/spike-floem.json", cfg.reports_dir.display());
                        }
                        Err(e) => eprintln!("report error: {e}"),
                    }
                    floem::quit_app();
                    return;
                }
            }

            // Self-reschedule: fires after ~1ms, sets tick → re-runs this effect.
            exec_after(Duration::from_millis(1), move |_| {
                tick.set(Instant::now());
            });
        });

        // View: scrollable line list.
        dyn_stack(
            move || lines.get().into_iter().enumerate(),
            |(i, _)| *i,
            |(_, line)| {
                label(move || line.clone())
                    .style(|s| s.font_family("Menlo".to_string()).font_size(11.0).padding_vert(1.0))
            },
        )
        .style(|s| s.flex_col().width_pct(100.0))
        .scroll()
        .style(|s| s.size_pct(100.0, 100.0))
    });
}

struct Spike {
    script: FrameScript,
    diff_doc: Option<DiffDoc>,
    event_table: EventTable,
    typebox: TypeBox,
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
        date: "2026-06-12".into(),
        reports_dir: "../../reports".into(),
    }
}

fn plan() -> ScriptPlan {
    let root = std::path::PathBuf::from(
        "/private/var/folders/dp/1fh07k_922j5qk7xfncn1zv40000gn/T/opencode/arc-v2-spike/workloads",
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
        screenshot_out: "../../reports/spike-floem-bidi.png".into(),
        warmup_frames: 5,
    }
}
