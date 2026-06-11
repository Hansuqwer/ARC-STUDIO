//! spike-harness — the one measurement code path every Sprint-3 candidate uses.
//!
//! Design rule: the candidates (gpui / gpui-ce / floem / bespoke+masonry) differ
//! only in *rendering*; sampling, percentile math, report format, and pass-bar
//! evaluation live here so the numbers are comparable by construction.
//! Vsync-awareness per review report §10.2: every report records the display
//! refresh rate and reports latency both in ms and in frames.

pub mod gates;
pub mod percentile;
pub mod report;
pub mod runner;
pub mod script;
pub mod views;
pub mod workloads;

pub use gates::{Gate, GateOutcome, GateRow, PassBar};
pub use percentile::Percentiles;
pub use report::{MachineIdentity, SpikeReport};
pub use runner::{assemble_report, RunConfig};
pub use script::{Action, FrameScript, ScriptPlan, ScriptResults};
pub use views::{
    bidi_sample_lines, DiffDoc, DiffLineKind, EventRow, EventTable, TextDoc, TypeBox,
    VIEWPORT_LINES,
};
