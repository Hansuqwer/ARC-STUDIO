//! SpikeReport — the raw-JSON artifact each candidate writes to reports/.
//! Machine identity is embedded in the report itself (review §10.6), not in a
//! side document that can drift.

use crate::gates::{Gate, GateOutcome, GateRow};

fn is_evidence_gate(gate: Gate) -> bool {
    matches!(
        gate,
        Gate::G5Accessibility | Gate::G6Ime | Gate::G7BidiLigatures | Gate::G8Sustainability
    )
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct MachineIdentity {
    pub hostname: String,
    pub os: String,
    pub arch: String,
    pub cpu: String,
    pub gpu: String,
    pub display: String, // e.g. "2560x1440@120Hz, Wayland"
    pub power_profile: String,
    /// True only for the pinned benchmark machine from arc-v2-benchmark-plan §Environment.
    pub is_pinned_benchmark_machine: bool,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SpikeReport {
    pub candidate: String, // "gpui" | "gpui-ce" | "floem" | "bespoke-masonry"
    pub candidate_version: String, // exact pinned version/rev
    pub date: String,
    pub machine: MachineIdentity,
    pub rows: Vec<GateRow>,
    pub honesty_note: String,
}

impl SpikeReport {
    pub fn new(candidate: &str, version: &str, date: &str, machine: MachineIdentity) -> Self {
        Self {
            candidate: candidate.into(),
            candidate_version: version.into(),
            date: date.into(),
            honesty_note: if machine.is_pinned_benchmark_machine {
                "pinned benchmark machine".into()
            } else {
                "NOT the pinned benchmark machine; numbers are indicative only \
                 and may not be used for pass/fail claims (do-not-overclaim)"
                    .into()
            },
            machine,
            rows: Vec::new(),
        }
    }

    /// A candidate "passes the spike" only when every automatic gate passes
    /// and no evidence gate has missing artifacts. NotRun blocks too: silence
    /// is not a pass.
    pub fn spike_verdict(&self) -> Result<(), Vec<String>> {
        let mut blockers = Vec::new();
        for row in &self.rows {
            match &row.outcome {
                GateOutcome::Pass => {
                    if is_evidence_gate(row.gate)
                        && row
                            .raw_data_path
                            .as_deref()
                            .unwrap_or_default()
                            .trim()
                            .is_empty()
                        && row.notes.trim().is_empty()
                    {
                        blockers.push(format!(
                            "{:?}: evidence pass missing artifact path",
                            row.gate
                        ));
                    }
                }
                GateOutcome::Fail { reason } => {
                    blockers.push(format!("{:?}: FAIL — {reason}", row.gate))
                }
                GateOutcome::EvidencePending { missing } => blockers.push(format!(
                    "{:?}: evidence missing ({} artifacts)",
                    row.gate,
                    missing.len()
                )),
                GateOutcome::NotRun => blockers.push(format!("{:?}: not run", row.gate)),
            }
        }
        if blockers.is_empty() {
            Ok(())
        } else {
            Err(blockers)
        }
    }

    pub fn write(&self, path: &std::path::Path) -> std::io::Result<()> {
        std::fs::write(
            path,
            serde_json::to_string_pretty(self).map_err(std::io::Error::other)?,
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::gates::{Gate, GateRow};
    use crate::percentile::Percentiles;

    fn machine() -> MachineIdentity {
        MachineIdentity {
            hostname: "test".into(),
            os: "linux".into(),
            arch: "x86_64".into(),
            cpu: "test".into(),
            gpu: "test".into(),
            display: "60Hz".into(),
            power_profile: "balanced".into(),
            is_pinned_benchmark_machine: false,
        }
    }

    #[test]
    fn unpinned_machine_gets_honesty_note() {
        let r = SpikeReport::new("floem", "0.2.0", "2026-06-11", machine());
        assert!(r.honesty_note.contains("NOT the pinned"));
    }

    #[test]
    fn verdict_blocks_on_pending_evidence_and_notrun() {
        let mut r = SpikeReport::new("floem", "0.2.0", "2026-06-11", machine());
        let raw = [10_000u64; 100];
        let p = Percentiles::from_us(&raw);
        // R1: P99 gates need raws to pass.
        r.rows.push(GateRow::evaluate_with_raw(
            Gate::G4TypingLatency,
            "floem",
            60.0,
            p,
            Some(&raw),
            None,
            None,
            None,
        ));
        r.rows.push(GateRow::evaluate(
            Gate::G6Ime,
            "floem",
            60.0,
            None,
            None,
            None,
            None,
        ));
        let blockers = r.spike_verdict().unwrap_err();
        assert_eq!(
            blockers.len(),
            1,
            "G4 passed; G6 evidence blocks: {blockers:?}"
        );
        assert!(blockers[0].contains("G6Ime"));
    }

    #[test]
    fn report_round_trips_as_json() {
        let r = SpikeReport::new("gpui-ce", "rev abc123", "2026-06-11", machine());
        let json = serde_json::to_string(&r).unwrap();
        let back: SpikeReport = serde_json::from_str(&json).unwrap();
        assert_eq!(back.candidate, "gpui-ce");
    }

    #[test]
    fn evidence_pass_requires_artifact_path() {
        let mut r = SpikeReport::new("floem", "0.2.0", "2026-06-11", machine());
        let mut row =
            GateRow::evaluate(Gate::G7BidiLigatures, "floem", 60.0, None, None, None, None);
        row.outcome = GateOutcome::Pass;
        r.rows.push(row);

        let blockers = r.spike_verdict().unwrap_err();
        assert!(blockers[0].contains("missing artifact path"));
    }
}
