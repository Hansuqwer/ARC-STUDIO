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
pub mod workloads;

pub use gates::{Gate, GateOutcome, GateRow, PassBar};
pub use percentile::Percentiles;
pub use report::SpikeReport;
