//! arc-plugin-host — Sprint-10 core, framework-free and headless-testable.
//!
//! SCOPE LABEL (honest): this crate implements the parts of the plugin
//! model that are ABI-independent and provable without a real extension:
//!
//! - engine budgets: fuel (CPU) + epoch deadline (wall clock), both kill
//!   deterministically (tests);
//! - the **guarded host-call policy** (review improvement #5): every host
//!   import goes through [`guarded_host_call`] — capability-checked
//!   (deny-by-default), time-bounded, audited-on-allow via a pluggable
//!   audit sink (daemon API in production), fail-closed when the audit
//!   write fails (review §9.2);
//! - manifest signature verification (minisign): unsigned/invalid refuse
//!   to load; the dev override is loud and audited.
//!
//! NOT here yet (lands with the first internal extension per ADR-0003):
//! the WASI Component Model ABI (`arc-ext/1` world), wasi ctx wiring, and
//! the real capability grant store. Wasm is NOT claimed as a VM boundary.

pub mod budget;
pub mod capability;
pub mod host_call;
pub mod manifest;

pub use budget::{BudgetKill, PluginEngine};
pub use capability::{Capability, CapabilitySet, DenialReason};
pub use host_call::{guarded_host_call, AuditSink, HostCallError, HostCtx, MemoryAuditSink};
pub use manifest::{verify_manifest, ManifestError, ManifestVerification};
