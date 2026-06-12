//! gpui 0.2 spike — FrameScript via Window::on_next_frame.
//!
//! ROOT-CAUSE FIX (2026-06-12): the first version registered on_next_frame from
//! INSIDE render() and drove it with cx.notify(), which re-entered render() and
//! tripped gpui's update machinery; the failing eprintln! in the run loop then
//! aborted (SIGABRT via __eprint). The blessed Zed pattern (defer_in /
//! schedule_edge_scroll) is:
//!   1. register the FIRST on_next_frame ONCE at window open (not from render)
//!   2. each callback: entity.update(cx, ..) → re-register next on_next_frame → window.refresh()
//!   3. render() is PURE (no side effects, no frame registration)
//!   4. NO eprintln!/println! inside the run loop — report is written to file only
//!
//! on_next_frame is a trustworthy post-present hook, so G1/G4 timings are
//! accurate to GPU present (not render-call-return).

use gpui::*;
use spike_harness::views::{bidi_sample_lines, DiffDoc, EventTable, TextDoc, TypeBox};
use spike_harness::workloads::{seeds, synthetic_keystream};
use spike_harness::{assemble_report, Action, FrameScript, MachineIdentity, RunConfig, ScriptPlan};
use std::time::Instant;

const CANDIDATE: &str = "gpui";
const VERSION: &str = "0.2.2";

struct SpikeView {
    script: FrameScript,
    diff_doc: Option<DiffDoc>,
    event_table: EventTable,
    typebox: TypeBox,
    lines: Vec<String>,
    done: bool,
    cfg: RunConfig,
}

impl Render for SpikeView {
    /// PURE render — no side effects, no frame registration.
    fn render(&mut self, _window: &mut Window, _cx: &mut Context<Self>) -> impl IntoElement {
        div()
            .size_full()
            .flex()
            .flex_col()
            .bg(rgb(0x1e1e1e))
            .text_color(rgb(0xd4d4d4))
            .children(
                self.lines
                    .iter()
                    .map(|line| {
                        div()
                            .font_family("Menlo")
                            .text_size(px(11.0))
                            .child(line.clone())
                    })
                    .collect::<Vec<_>>(),
            )
    }
}

/// One frame tick: apply at most one Action, then re-register for the next
/// present. Driven entirely by on_next_frame chaining — never from render().
fn tick(weak: WeakEntity<SpikeView>, window: &mut Window, cx: &mut App) {
    let Some(view) = weak.upgrade() else { return };
    let now = Instant::now();

    let finished = view.update(cx, |v, cx| {
        if v.done {
            return true;
        }
        match v.script.on_present(now) {
            Action::OpenWorkload { path, label: _ } => {
                if let Ok(doc) = TextDoc::load(&path) {
                    v.lines = doc.viewport().map(str::to_owned).collect();
                }
            }
            Action::LoadDiff { path } => {
                if let Ok(text) = std::fs::read_to_string(&path) {
                    let doc = DiffDoc::parse(&text);
                    v.lines = doc.viewport().map(|(_, l)| l.clone()).collect();
                    v.diff_doc = Some(doc);
                }
            }
            Action::ScrollStep => {
                if let Some(doc) = v.diff_doc.as_mut() {
                    doc.scroll_step();
                    v.lines = doc.viewport().map(|(_, l)| l.clone()).collect();
                }
            }
            Action::AppendRows { from, count } => {
                for i in from..from + count {
                    v.event_table.append(&format!(
                        r#"{{"sequence":{i},"type":"TOOL_CALL","timestamp":"2026-06-12T00:00:00Z","data":{{"tool_name":"row_{i}"}}}}"#
                    ));
                }
                v.lines = v.event_table.tail_viewport().map(EventTable::display_line).collect();
            }
            Action::TypeChar { ch } => {
                v.typebox.push(ch);
                v.lines = vec![v.typebox.content.clone()];
            }
            Action::TakeScreenshot { out: _ } => {
                v.lines = bidi_sample_lines().iter().map(|s| s.to_string()).collect();
                // G7: operator screenshots the bidi frame → reports/spike-gpui-bidi.png
            }
            Action::Settle => {}
            Action::Finished => {
                v.done = true;
            }
        }
        cx.notify();
        v.done
    });

    if finished {
        // Assemble + write report (file I/O only — no stdout/stderr in run loop).
        view.update(cx, |v, _cx| {
            let dummy = FrameScript::new(empty_plan());
            let real = std::mem::replace(&mut v.script, dummy);
            let results = real.into_results();
            if let Ok(report) = assemble_report(CANDIDATE, VERSION, &results, &v.cfg) {
                let path = std::path::Path::new("../../reports/spike-gpui.json");
                let _ = report.write(path);
                // status sidecar so the operator knows it finished without stdout
                let blockers = report.spike_verdict().err().unwrap_or_default();
                let _ = std::fs::write(
                    "../../reports/spike-gpui.status",
                    format!("done\nblockers:\n{}", blockers.join("\n")),
                );
            }
        });
        cx.quit();
        return;
    }

    // Re-register for the next present, then request a repaint.
    let weak2 = weak.clone();
    window.on_next_frame(move |window, cx| tick(weak2, window, cx));
    window.refresh();
}

fn main() {
    Application::new().run(|cx: &mut App| {
        let options = WindowOptions {
            window_bounds: Some(WindowBounds::Windowed(Bounds {
                origin: point(px(100.0), px(100.0)),
                size: size(px(800.0), px(600.0)),
            })),
            titlebar: Some(TitlebarOptions {
                title: Some("gpui spike".into()),
                ..Default::default()
            }),
            ..Default::default()
        };
        cx.open_window(options, |window, cx| {
            let view = cx.new(|_cx| SpikeView {
                script: FrameScript::new(plan()),
                diff_doc: None,
                event_table: EventTable::default(),
                typebox: TypeBox::default(),
                lines: vec!["gpui spike — starting…".into()],
                done: false,
                cfg: config(),
            });
            // Register the FIRST tick here (not from render) — the chain self-sustains.
            let weak = view.downgrade();
            window.on_next_frame(move |window, cx| tick(weak, window, cx));
            view
        })
        .unwrap();
        cx.activate(true);
    });
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
        screenshot_out: "../../reports/spike-gpui-bidi.png".into(),
        warmup_frames: 5,
    }
}

fn empty_plan() -> ScriptPlan {
    ScriptPlan {
        source_100mb: "".into(),
        pathological_10mb: "".into(),
        diff_5k: "".into(),
        g1_reps: 0,
        scroll_frames: 0,
        rows: 0,
        g3_chunk: 10,
        keys: vec![],
        screenshot_out: "".into(),
        warmup_frames: 0,
    }
}
