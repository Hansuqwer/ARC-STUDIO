//! G1–G8 gate definitions (ADR-0002 + review-report addendum).
//!
//! Pass bars are *placeholders until hardware is pinned* (brief §3.5 says so
//! explicitly); they are encoded here so every candidate is judged by the same
//! code, and so changing a bar is a reviewed diff, not a spreadsheet edit.
//! G5/G6/G7/G8 are evidence gates (manual/recorded), not auto-pass/fail.

use crate::percentile::Percentiles;

fn to_vec(items: &[&str]) -> Vec<String> {
    items.iter().map(|s| s.to_string()).collect()
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum Gate {
    G1HugeFileFirstPaint,
    G2DiffScrollFrameTime,
    G3EventReplayBudget,
    G4TypingLatency,
    G5Accessibility,
    G6Ime,
    G7BidiLigatures,
    G8Sustainability,
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum PassBar {
    /// Automatic: compared against measured numbers.
    P99FramesAtMost {
        frames: f64,
    },
    FirstPaintAtMostMs {
        ms: u64,
    },
    TotalBudgetMs {
        ms: u64,
        no_frame_over_ms: u64,
    },
    /// Evidence gate: requires recorded artifacts per OS, never auto-passes.
    Evidence {
        required_artifacts: Vec<String>,
    },
}

impl Gate {
    pub fn pass_bar(self) -> PassBar {
        match self {
            // Placeholders per brief §3.5 — re-pin with hardware.
            Gate::G1HugeFileFirstPaint => PassBar::FirstPaintAtMostMs { ms: 1000 },
            Gate::G2DiffScrollFrameTime => PassBar::P99FramesAtMost { frames: 1.1 }, // R1: ≤1.1 frames AND 0% >2vsync
            Gate::G3EventReplayBudget => PassBar::TotalBudgetMs {
                ms: 250,
                no_frame_over_ms: 33,
            },
            Gate::G4TypingLatency => PassBar::P99FramesAtMost { frames: 1.1 }, // R1: ≤1.1 frames AND 0% >2vsync
            Gate::G5Accessibility => PassBar::Evidence {
                required_artifacts: to_vec(&[
                    "voiceover-recording-or-tree-dump (macOS)",
                    "orca-recording-or-atspi-dump (Linux, X11 AND Wayland)",
                    "nvda-recording-or-uia-dump (Windows)",
                ]),
            },
            Gate::G6Ime => PassBar::Evidence {
                required_artifacts: to_vec(&[
                    "macos: ja-hiragana->kanji, zh-pinyin, ko-2set (compose+commit+cancel)",
                    "linux-wayland: fcitx5 AND ibus, same scripts",
                    "linux-x11: fcitx5 smoke (best-effort, documented)",
                    "windows: TSF, same scripts, inline composition verified",
                    "dead-keys/compose-key row (European layouts)",
                ]),
            },
            Gate::G7BidiLigatures => PassBar::Evidence {
                required_artifacts: to_vec(&[
                    "golden-image match: bidi paragraph + programming ligatures",
                ]),
            },
            Gate::G8Sustainability => PassBar::Evidence {
                required_artifacts: to_vec(&[
                    "release cadence trailing 12mo",
                    "bus factor / governance summary",
                    "breaking-change rate vs pinned version",
                    "vendoring cost estimate if upstream stalls",
                ]),
            },
        }
    }
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum GateOutcome {
    Pass,
    Fail {
        reason: String,
    },
    /// Evidence gates start here and flip to Pass only when artifacts exist.
    EvidencePending {
        missing: Vec<String>,
    },
    NotRun,
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct GateRow {
    pub gate: Gate,
    pub candidate: String,
    pub refresh_hz: f64,
    pub percentiles: Option<Percentiles>,
    pub first_paint_ms: Option<u64>,
    pub total_ms: Option<u64>,
    pub worst_frame_ms: Option<u64>,
    pub outcome: GateOutcome,
    pub raw_data_path: Option<String>,
    pub notes: String,
}

impl GateRow {
    /// Evaluate automatic gates from measured numbers; evidence gates return
    /// EvidencePending with the full artifact list (nothing auto-passes).
    pub fn evaluate(
        gate: Gate,
        candidate: &str,
        refresh_hz: f64,
        percentiles: Option<Percentiles>,
        first_paint_ms: Option<u64>,
        total_ms: Option<u64>,
        worst_frame_ms: Option<u64>,
    ) -> Self {
        Self::evaluate_with_raw(
            gate,
            candidate,
            refresh_hz,
            percentiles,
            None,
            first_paint_ms,
            total_ms,
            worst_frame_ms,
        )
    }

    /// Full form: P99 gates require `raw_samples` for the R1 discriminator.
    #[allow(clippy::too_many_arguments)]
    pub fn evaluate_with_raw(
        gate: Gate,
        candidate: &str,
        refresh_hz: f64,
        percentiles: Option<Percentiles>,
        raw_samples: Option<&[u64]>,
        first_paint_ms: Option<u64>,
        total_ms: Option<u64>,
        worst_frame_ms: Option<u64>,
    ) -> Self {
        let outcome = match gate.pass_bar() {
            PassBar::P99FramesAtMost { frames } => match &percentiles {
                None => GateOutcome::NotRun,
                Some(p) => {
                    let got = p.p99_frames(refresh_hz);
                    // R1 (owner-accepted 2026-06-12): pass requires BOTH
                    // p99 within the bar AND zero samples beyond two vsync
                    // periods. Raw samples are required for P99 gates —
                    // absent raws = NotRun, never a blind pass.
                    match raw_samples {
                        None => GateOutcome::NotRun,
                        Some(raw) => {
                            let over =
                                crate::percentile::Percentiles::over_two_vsync(raw, refresh_hz);
                            if got <= frames && over == 0 {
                                GateOutcome::Pass
                            } else if over > 0 {
                                GateOutcome::Fail {
                                    reason: format!(
                                        "{over}/{} samples > 2 vsyncs ({:.1}%) — real missed frames (R1)",
                                        raw.len(),
                                        100.0 * over as f64 / raw.len() as f64
                                    ),
                                }
                            } else {
                                GateOutcome::Fail {
                                    reason: format!(
                                        "p99 = {got:.2} frames @ {refresh_hz} Hz (bar {frames})"
                                    ),
                                }
                            }
                        }
                    }
                }
            },
            PassBar::FirstPaintAtMostMs { ms } => match first_paint_ms {
                None => GateOutcome::NotRun,
                Some(got) if got <= ms => GateOutcome::Pass,
                Some(got) => GateOutcome::Fail {
                    reason: format!("first paint {got} ms (bar {ms} ms)"),
                },
            },
            PassBar::TotalBudgetMs {
                ms,
                no_frame_over_ms,
            } => match (total_ms, worst_frame_ms) {
                (Some(t), Some(w)) => {
                    if t <= ms && w <= no_frame_over_ms {
                        GateOutcome::Pass
                    } else {
                        GateOutcome::Fail {
                            reason: format!(
                                "total {t} ms (bar {ms}), worst frame {w} ms (bar {no_frame_over_ms})"
                            ),
                        }
                    }
                }
                _ => GateOutcome::NotRun,
            },
            PassBar::Evidence { required_artifacts } => GateOutcome::EvidencePending {
                missing: required_artifacts,
            },
        };
        Self {
            gate,
            candidate: candidate.to_string(),
            refresh_hz,
            percentiles,
            first_paint_ms,
            total_ms,
            worst_frame_ms,
            outcome,
            raw_data_path: None,
            notes: String::new(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn g4_pass_and_fail_are_vsync_aware_r1() {
        // R1: raws REQUIRED for P99 gates; evaluate() without raws => NotRun.
        let raw = [15_000u64; 100];
        let p = Percentiles::from_us(&raw);
        let no_raws = GateRow::evaluate(
            Gate::G4TypingLatency,
            "x",
            60.0,
            p.clone(),
            None,
            None,
            None,
        );
        assert_eq!(
            no_raws.outcome,
            GateOutcome::NotRun,
            "no raws = NotRun, not pass"
        );

        // 15 ms p99, 0% >2vsync: pass at 60 Hz (0.9f), FAIL at 120 Hz (1.8f > 1.1 bar).
        let pass = GateRow::evaluate_with_raw(
            Gate::G4TypingLatency,
            "x",
            60.0,
            p.clone(),
            Some(&raw),
            None,
            None,
            None,
        );
        assert_eq!(pass.outcome, GateOutcome::Pass);
        let fail = GateRow::evaluate_with_raw(
            Gate::G4TypingLatency,
            "x",
            120.0,
            p,
            Some(&raw),
            None,
            None,
            None,
        );
        assert!(matches!(fail.outcome, GateOutcome::Fail { .. }));
    }

    #[test]
    fn r1_discriminator_separates_artifact_from_regression() {
        // The gpui-ce case in miniature: p99 marginal but 90% of frames at
        // ~3 vsyncs => FAIL with the R1 reason; and the floem/gpui case:
        // p99 = 1.03 frames but 0% >2vsync => PASS under the 1.1 bar.
        let regression: Vec<u64> = (0..100)
            .map(|i| if i < 90 { 50_000 } else { 16_700 })
            .collect();
        let p = Percentiles::from_us(&regression);
        let r = GateRow::evaluate_with_raw(
            Gate::G4TypingLatency,
            "x",
            60.0,
            p,
            Some(&regression),
            None,
            None,
            None,
        );
        match &r.outcome {
            GateOutcome::Fail { reason } => assert!(reason.contains("R1"), "{reason}"),
            other => panic!("expected R1 fail, got {other:?}"),
        }

        let artifact = [17_100u64; 100]; // 1.03 frames, never >2vsync
        let p = Percentiles::from_us(&artifact);
        let r = GateRow::evaluate_with_raw(
            Gate::G4TypingLatency,
            "x",
            60.0,
            p,
            Some(&artifact),
            None,
            None,
            None,
        );
        assert_eq!(
            r.outcome,
            GateOutcome::Pass,
            "1.03f with 0% >2v passes the R1 bar"
        );
    }

    #[test]
    fn g1_first_paint_bar() {
        let r = GateRow::evaluate(
            Gate::G1HugeFileFirstPaint,
            "x",
            60.0,
            None,
            Some(999),
            None,
            None,
        );
        assert_eq!(r.outcome, GateOutcome::Pass);
        let r = GateRow::evaluate(
            Gate::G1HugeFileFirstPaint,
            "x",
            60.0,
            None,
            Some(1001),
            None,
            None,
        );
        assert!(matches!(r.outcome, GateOutcome::Fail { .. }));
    }

    #[test]
    fn g3_both_conditions_required() {
        let ok = GateRow::evaluate(
            Gate::G3EventReplayBudget,
            "x",
            60.0,
            None,
            None,
            Some(200),
            Some(30),
        );
        assert_eq!(ok.outcome, GateOutcome::Pass);
        let slow_frame = GateRow::evaluate(
            Gate::G3EventReplayBudget,
            "x",
            60.0,
            None,
            None,
            Some(200),
            Some(40),
        );
        assert!(matches!(slow_frame.outcome, GateOutcome::Fail { .. }));
    }

    #[test]
    fn evidence_gates_never_autopass() {
        for g in [
            Gate::G5Accessibility,
            Gate::G6Ime,
            Gate::G7BidiLigatures,
            Gate::G8Sustainability,
        ] {
            let r = GateRow::evaluate(g, "x", 60.0, None, None, None, None);
            assert!(
                matches!(r.outcome, GateOutcome::EvidencePending { .. }),
                "{g:?}"
            );
        }
    }

    #[test]
    fn missing_measurements_are_notrun_not_pass() {
        let r = GateRow::evaluate(
            Gate::G2DiffScrollFrameTime,
            "x",
            60.0,
            None,
            None,
            None,
            None,
        );
        assert_eq!(r.outcome, GateOutcome::NotRun);
    }
}
