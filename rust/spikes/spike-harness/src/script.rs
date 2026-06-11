//! Frame-driven spike script — replaces the blocking `CandidateHooks` design.
//!
//! Frameworks own the event loop. Candidates call [`FrameScript::on_present`]
//! from their present/frame-complete callback and apply the returned [`Action`]
//! for the next frame. At most one sampled action is issued per present.

use std::path::PathBuf;
use std::time::Instant;

/// What the candidate must do during the upcoming frame.
#[derive(Debug, Clone, PartialEq)]
pub enum Action {
    /// G1: replace view contents with this file; next present closes sample.
    OpenWorkload { path: PathBuf, label: &'static str },
    /// G2: load diff document; not sampled.
    LoadDiff { path: PathBuf },
    /// G2: scroll diff view by one step.
    ScrollStep,
    /// G3: append this chunk of rows to event panel this frame.
    AppendRows { from: usize, count: usize },
    /// G4: insert exactly this char at cursor.
    TypeChar { ch: char },
    /// G7: write screenshot of bidi/ligature sample to this path.
    TakeScreenshot { out: PathBuf },
    /// Render an empty/settle frame.
    Settle,
    /// Script complete.
    Finished,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum SampleTag {
    None,
    FirstPaint(usize),
    RowFrame,
    KeyFrame,
}

struct Step {
    action: Action,
    tag: SampleTag,
}

pub struct ScriptPlan {
    pub source_100mb: PathBuf,
    pub pathological_10mb: PathBuf,
    pub diff_5k: PathBuf,
    pub g1_reps: usize,
    pub scroll_frames: usize,
    pub rows: usize,
    /// Rows appended per G3 frame. Default spike value: 10.
    pub g3_chunk: usize,
    pub keys: Vec<char>,
    pub screenshot_out: PathBuf,
    pub warmup_frames: usize,
}

#[derive(Debug, Default, Clone)]
pub struct ScriptResults {
    /// (workload label, first-paint ms) per rep; runner medians per label family.
    pub g1_first_paint_ms: Vec<(String, u64)>,
    /// Present-to-present deltas during scripted scrolling.
    pub g2_frame_us: Vec<u64>,
    /// Per-burst issue-to-present and total wall time for G3.
    pub g3_frame_us: Vec<u64>,
    pub g3_total_ms: u64,
    /// Per-key issue-to-present.
    pub g4_us: Vec<u64>,
    pub g7_screenshot: Option<PathBuf>,
}

pub struct FrameScript {
    steps: std::collections::VecDeque<Step>,
    g1_labels: Vec<String>,
    results: ScriptResults,
    pending: SampleTag,
    issued_at: Option<Instant>,
    prev_present: Option<Instant>,
    in_scroll: bool,
    g3_started: Option<Instant>,
    g3_remaining: usize,
}

impl FrameScript {
    pub fn new(plan: ScriptPlan) -> Self {
        let mut steps = std::collections::VecDeque::new();
        let mut g1_labels = Vec::new();
        let settle = |steps: &mut std::collections::VecDeque<Step>, count: usize| {
            for _ in 0..count {
                steps.push_back(Step {
                    action: Action::Settle,
                    tag: SampleTag::None,
                });
            }
        };

        for rep in 0..plan.g1_reps.max(1) {
            for (path, label) in [
                (&plan.source_100mb, "source-100mb"),
                (&plan.pathological_10mb, "pathological-10mb"),
            ] {
                let idx = g1_labels.len();
                g1_labels.push(format!("{label}#rep{rep}"));
                steps.push_back(Step {
                    action: Action::OpenWorkload {
                        path: path.clone(),
                        label,
                    },
                    tag: SampleTag::FirstPaint(idx),
                });
                settle(&mut steps, 2);
            }
        }

        steps.push_back(Step {
            action: Action::LoadDiff {
                path: plan.diff_5k.clone(),
            },
            tag: SampleTag::None,
        });
        settle(&mut steps, plan.warmup_frames);
        for _ in 0..plan.scroll_frames {
            steps.push_back(Step {
                action: Action::ScrollStep,
                tag: SampleTag::None,
            });
        }
        settle(&mut steps, 2);

        let chunk = plan.g3_chunk.max(1);
        let mut from = 0;
        let mut g3_chunks = 0usize;
        while from < plan.rows {
            let count = chunk.min(plan.rows - from);
            steps.push_back(Step {
                action: Action::AppendRows { from, count },
                tag: SampleTag::RowFrame,
            });
            from += count;
            g3_chunks += 1;
        }
        settle(&mut steps, 2);

        for ch in &plan.keys {
            steps.push_back(Step {
                action: Action::TypeChar { ch: *ch },
                tag: SampleTag::KeyFrame,
            });
        }
        settle(&mut steps, 2);

        steps.push_back(Step {
            action: Action::TakeScreenshot {
                out: plan.screenshot_out.clone(),
            },
            tag: SampleTag::None,
        });

        Self {
            steps,
            g1_labels,
            results: ScriptResults::default(),
            pending: SampleTag::None,
            issued_at: None,
            prev_present: None,
            in_scroll: false,
            g3_started: None,
            g3_remaining: g3_chunks,
        }
    }

    /// Call from the framework's present/frame-complete callback. Returns the
    /// action for the next frame.
    pub fn on_present(&mut self, now: Instant) -> Action {
        if let Some(start) = self.issued_at.take() {
            let us = now.duration_since(start).as_micros() as u64;
            match self.pending {
                SampleTag::FirstPaint(idx) => {
                    let label = self.g1_labels[idx].clone();
                    self.results.g1_first_paint_ms.push((label, us / 1000));
                }
                SampleTag::RowFrame => {
                    self.results.g3_frame_us.push(us);
                    self.g3_remaining -= 1;
                    if self.g3_remaining == 0 {
                        if let Some(started) = self.g3_started {
                            self.results.g3_total_ms =
                                now.duration_since(started).as_millis() as u64;
                        }
                    }
                }
                SampleTag::KeyFrame => self.results.g4_us.push(us),
                SampleTag::None => {}
            }
            self.pending = SampleTag::None;
        }

        if self.in_scroll {
            if let Some(prev) = self.prev_present {
                self.results
                    .g2_frame_us
                    .push(now.duration_since(prev).as_micros() as u64);
            }
        }
        self.prev_present = Some(now);

        match self.steps.pop_front() {
            None => Action::Finished,
            Some(step) => {
                self.in_scroll = matches!(step.action, Action::ScrollStep);
                match &step.action {
                    Action::AppendRows { from, .. } if *from == 0 => {
                        self.g3_started = Some(now);
                    }
                    Action::TakeScreenshot { out } => {
                        self.results.g7_screenshot = Some(out.clone());
                    }
                    _ => {}
                }
                if step.tag != SampleTag::None {
                    self.pending = step.tag;
                    self.issued_at = Some(now);
                }
                step.action
            }
        }
    }

    pub fn frames_remaining(&self) -> usize {
        self.steps.len()
    }

    pub fn into_results(self) -> ScriptResults {
        self.results
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;
    use std::time::Duration;

    fn plan(rows: usize, keys: usize) -> ScriptPlan {
        ScriptPlan {
            source_100mb: PathBuf::from("/w/src.txt"),
            pathological_10mb: PathBuf::from("/w/path.txt"),
            diff_5k: PathBuf::from("/w/d.patch"),
            g1_reps: 3,
            scroll_frames: 50,
            rows,
            g3_chunk: 10,
            keys: vec!['x'; keys],
            screenshot_out: PathBuf::from("/r/shot.png"),
            warmup_frames: 5,
        }
    }

    fn drive(mut script: FrameScript, frame: Duration) -> ScriptResults {
        let mut now = Instant::now();
        let mut rows_seen = 0usize;
        loop {
            let action = script.on_present(now);
            match &action {
                Action::Finished => break,
                Action::AppendRows { count, .. } => rows_seen += count,
                _ => {}
            }
            now += frame;
        }
        assert!(rows_seen > 0);
        script.into_results()
    }

    #[test]
    fn one_chunk_per_frame_and_one_key_per_frame_by_construction() {
        let results = drive(FrameScript::new(plan(100, 200)), Duration::from_millis(8));
        assert_eq!(results.g3_frame_us.len(), 10);
        assert_eq!(results.g4_us.len(), 200);
        assert!(results.g3_frame_us.iter().all(|&us| us == 8_000));
        assert!(results.g4_us.iter().all(|&us| us == 8_000));
    }

    #[test]
    fn g3_chunking_covers_all_rows_including_remainder() {
        let mut script = FrameScript::new(plan(95, 0));
        let mut covered = 0usize;
        let mut bursts = 0usize;
        let mut now = Instant::now();
        loop {
            match script.on_present(now) {
                Action::Finished => break,
                Action::AppendRows { from, count } => {
                    assert_eq!(from, covered);
                    covered += count;
                    bursts += 1;
                }
                _ => {}
            }
            now += Duration::from_millis(8);
        }
        assert_eq!(covered, 95);
        assert_eq!(bursts, 10);
    }

    #[test]
    fn g1_collects_reps_for_both_workloads() {
        let results = drive(FrameScript::new(plan(10, 10)), Duration::from_millis(8));
        assert_eq!(results.g1_first_paint_ms.len(), 6);
        let sources = results
            .g1_first_paint_ms
            .iter()
            .filter(|(label, _)| label.starts_with("source"))
            .count();
        assert_eq!(sources, 3);
        assert!(results.g1_first_paint_ms.iter().all(|(_, ms)| *ms == 8));
    }

    #[test]
    fn g2_samples_present_to_present_only_during_scroll() {
        let results = drive(FrameScript::new(plan(10, 10)), Duration::from_millis(10));
        assert_eq!(results.g2_frame_us.len(), 50);
        assert!(results.g2_frame_us.iter().all(|&us| us == 10_000));
    }

    #[test]
    fn g3_total_spans_first_issue_to_last_present() {
        let results = drive(FrameScript::new(plan(100, 0)), Duration::from_millis(2));
        assert_eq!(results.g3_total_ms, 20);
    }

    #[test]
    fn screenshot_path_recorded_and_script_finishes() {
        let results = drive(FrameScript::new(plan(5, 5)), Duration::from_millis(8));
        assert_eq!(
            results.g7_screenshot.as_ref().unwrap().to_str().unwrap(),
            "/r/shot.png"
        );
    }

    #[test]
    fn slow_frames_produce_slow_samples() {
        let results = drive(FrameScript::new(plan(10, 50)), Duration::from_millis(40));
        assert!(results.g4_us.iter().all(|&us| us == 40_000));
    }
}
