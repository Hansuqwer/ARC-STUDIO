//! arc-index — Sprint-5 shell-local latency index (ADR-0005 two-tier rule).
//!
//! This index exists for UI latency ONLY. AI-reasoning memory/context stays
//! daemon-owned. Rules encoded:
//! - corruption REBUILDS, never crashes (`open_or_rebuild` swallows a corrupt
//!   index dir by recreating it and reports `rebuilt: true`);
//! - full rebuild is a COMMAND (`rebuild()`), never a side effect;
//! - redaction-aware (review §9.6): pattern-matched secrets are excluded
//!   from indexed bodies BEFORE write.

pub mod search;
pub mod symbols;

pub use search::{RebuildOutcome, SearchHit, SearchIndex};
pub use symbols::{Symbol, SymbolStore};
