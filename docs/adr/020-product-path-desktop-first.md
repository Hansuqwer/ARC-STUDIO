# ADR-020: Product Path — Desktop-First, SaaS-Later

**Status:** Proposed (draft 2026-05-21)
**Context:** Path to 1.0 planning, post-v0.1.0-alpha
**Related:** ADR-011 (full-parity framing), ADR-014 (security architecture), the deferred-items list in v0.1.0-alpha

## Context

The path-to-1.0 roadmap has a fork: 1.0 can mean a polished single-user desktop product, or a production SaaS platform with multi-tenancy, authentication, and remote deployment. The two products have fundamentally different scopes (10-13 months versus 16-20 months from v0.1.0-alpha), different risk profiles, different team sizing requirements, and different regulatory exposure under the EU AI Act enforcing August 2, 2026.

The deferred-items list from v0.1.0-alpha treats this as undecided: "Production/Tenant Isolation - Not Claimed" and "Multi-user support - Needed for 1.0" coexist in the same document. The lack of decision has allowed both possibilities to remain plausible, which is unsustainable when phases 3 and 4 of the path-to-1.0 plan depend on which product is being built.

ARC Studio's positioning in the broader ecosystem is also relevant. The LLM gateway and AI agent platform space is crowded with SaaS competitors (LiteLLM, Bifrost, OpenRouter, agentgateway, Maxim, Inworld, Truefoundry) competing on similar axes: provider routing, cost tracking, budget enforcement, gateway-style deployment. A "local-first AI agent cockpit" positioning is differentiated; a "yet another LLM gateway SaaS" positioning is not.

## Decision

ARC Studio 1.0 ships as a desktop-first product. Multi-tenancy, authentication, and remote deployment are explicitly out of scope for 1.0 and are reconsidered as a 1.5 or 2.0 transition after product-market fit is established in the desktop form factor.

"Desktop-first" means:

- The product runs as a local daemon plus optional Electron UI on the user's own machine. Sessions, audit chains, configuration, and provider credentials live on the local filesystem. The daemon binds to loopback only by default; remote binding requires explicit configuration and is documented as "use at your own risk" — not a supported deployment topology.

- There is exactly one trust principal per installation: the user running the daemon. Filesystem ACLs and OS-level user accounts are the isolation boundary. The product does not implement application-level authentication, authorization, or tenant isolation.

- The product can be used in shared environments (a developer's workstation that they sometimes let a colleague use, or a single-team server reachable on a private network) but those topologies are user-managed, not product-managed. Documentation explicitly states that the security model assumes a single trusted user.

- Data never leaves the user's machine except to the LLM provider(s) the user has explicitly configured. There is no telemetry-by-default, no usage reporting, no centralized analytics. Opt-in error reporting may be added in a future version.

## What Changes in the Path-to-1.0 Plan

Phase 3 (Production Features) shrinks substantially. Multi-user support, authentication, authorization, tenant isolation, and remote deployment all move out of 1.0 scope. What remains in Phase 3:

- The EU AI Act compliance work (tamper-evident audit chains, transparency obligations, documented compliance posture for the "limited risk" tier). This is non-negotiable regardless of product path because the August 2 2026 deadline applies to the product's existence, not its deployment topology.

- The deprecation policy (ADR candidate) and the deferred "adapter-wide keyed audit" item, which is naturally subsumed by the EU AI Act audit chain work.

- Observability (OpenTelemetry GenAI conventions) for users who want to integrate the desktop daemon with their own monitoring stack.

Phase 3 becomes roughly half its previous size. The freed timeline either accelerates 1.0 (target ~10 months instead of 13) or absorbs into a more thorough Phase 1 polish pass.

Phase 4 (Distribution) is unchanged in scope but is now the most critical phase. A desktop-first product that doesn't distribute well to its users is a failed product. The Electron packaging, code signing, notarization, auto-update, and distribution channel work all proceed as planned. The org/legal track (Apple Developer enrollment, Windows EV certificate, privacy policy, terms of service) starts on day 1 of Phase 1 in parallel since certificates take weeks to obtain.

Phase 2 (Provider Expansion) is unchanged. Multiple providers, retry/failover, real-time budget enforcement, MCP tool transport, OpenTelemetry conventions — all of this matters for the desktop product just as much as it would have for SaaS.

Phase 1 (Polish) gains accessibility and offline-first considerations that matter more for desktop than for SaaS. Keyboard navigation, screen reader support, respect for OS conventions (dark mode, system fonts, native window controls), graceful handling of network outages (since the product is now expected to run on laptops in transit).

## Conditions for Revisiting

The decision is revisited if, after 1.0 ships and the product has been in users' hands for at least 3 months, any of the following are true:

- **Validated enterprise demand exists:** at least 3 pilot customers with signed LOIs requesting SaaS deployment, with budget allocated and integration requirements documented.

- **The team has scaled to support the SaaS work:** minimum 3-4 engineers plus dedicated DevOps capacity, with budget allocated for a security audit and compliance review covering the broader AI Act surface area that SaaS implicates.

- **Product-market fit is demonstrated in the desktop form factor:** the desktop product has measurable adoption (user count, retention, NPS or equivalent) sufficient to justify investing 6-9 months into a SaaS transition that may displace existing desktop users' workflows.

A SaaS transition without these conditions is a speculative product pivot, not a roadmap expansion. The default answer to "should we add SaaS to 1.0?" is no.

## Architectural Guardrails to Preserve Future Optionality

Even though SaaS is out of scope for 1.0, decisions made between now and 1.0 should not actively foreclose the SaaS transition path. Specifically:

- **Schema designs should not assume single-user.** Where it costs little, include `tenant_id` or `principal_id` fields with a default value of `"local"` so future migrations are additive rather than restructuring. The `CostRecord`, `EventEnvelope`, and audit chain schemas should all be reviewed for this.

- **The daemon HTTP API should be designed as if it might one day be remote.** No client-trusts-server assumptions; authentication can be a no-op middleware in 1.0 that's swapped for real auth later. Loopback-only binding is enforced by configuration, not by API design.

- **The SQLite storage layer should isolate query construction** in a way that allows swapping for Postgres later. ORM use is fine; raw SQL with SQLite-specific syntax (e.g., `INSERT OR REPLACE`) should be avoided unless contained behind an interface.

- **The audit chain (built in Phase 3 for EU AI Act compliance) should support a "principal" field** even if all entries are signed by the same principal in 1.0. The HMAC key derivation should be parameterizable so a future per-tenant key isn't a schema change.

These are not "build SaaS, just don't enable it" decisions. They're "don't paint yourself into a corner" decisions. Total cost is low (estimated < 2% of total Phase 1-4 work); future option value is high.

## Consequences

### Positive

- **Faster path to 1.0:** ~10-13 months versus 16-20 months. Ship sooner, learn from real users sooner.

- **Lower risk:** the cited 92% of SaaS breaches from tenant isolation failures don't apply to a product that doesn't have tenants. The security audit before 1.0 has a much smaller surface area, costs less, and finishes faster.

- **Cleaner positioning:** "local-first AI agent cockpit" is differentiated in a crowded market. Marketing has a story to tell that the SaaS competitors can't tell.

- **Lower compliance overhead:** the EU AI Act work still needs to happen, but a desktop developer tool's compliance posture is "limited risk" with primarily transparency obligations, not the "high risk" obligations that some SaaS deployments of AI agents may trigger.

- **Smaller team viable:** a 1-2 engineer team can plausibly ship desktop 1.0 in the proposed timeline. SaaS 1.0 would have required 3-4 engineers plus DevOps.

### Negative

- **Some users who would prefer a hosted SaaS will not be served by 1.0.** This is acceptable: those users are not the target market for the desktop-first positioning, and the SaaS transition path remains open for 1.5 or 2.0.

- **Distribution becomes more critical and more painful:** signing certificates, notarization, auto-update infrastructure, and per-OS installer flows are all real engineering work that a SaaS product would have avoided. This is accepted as the cost of desktop-first positioning.

- **Some architectural guardrails** (multi-principal-aware schemas, swappable storage layer) require minor upfront investment that wouldn't pay back until the SaaS transition happens. Estimated <2% overhead; worth it for option value.

### Open

- Whether the daemon's HTTP API should support optional remote binding in 1.0 as a "use at your own risk" feature, or whether loopback-only should be enforced at the binding layer with no escape hatch. **Lean:** optional remote with prominent warnings, since some users will run the daemon on a private homelab server and that's a reasonable use case the product shouldn't actively prevent.

- Whether the audit chain key should be per-installation (single key, derived from a machine-bound secret) or per-session (rotating keys signed by a root key). **Lean:** per-installation for 1.0 simplicity; revisit if compliance review surfaces a requirement.

## Updated Roadmap Summary (Desktop-First Path)

With ADR-020 locked, here's the tightened roadmap:

**Phase 1 — Polish (v0.2-v0.5, ~3 months):** documentation completion, error messages, empty/degraded states, performance budgets, accessibility (now elevated in priority), test taxonomy cleanup, schema/API stability sweep, deprecation policy ADR, EU AI Act audit chain work starts here in parallel. Org/legal track for distribution (Apple Developer enrollment, Windows EV cert business verification, privacy policy drafting) starts day 1.

**Phase 2 — Provider Expansion (v0.6-v0.8, ~4 months):** OpenAI provider client with full feature parity, provider abstraction generalization (ADR-014/019/cache contract become provider-agnostic), retry/failover/circuit breaking, prompt caching strategy abstraction, 2-3 additional providers (Gemini/Mistral/Bedrock/local), real-time budget enforcement at gateway boundary, MCP tool transport, OpenTelemetry GenAI conventions fully adopted.

**Phase 3 — Compliance & Observability (v0.9, ~2 months):** EU AI Act audit chain completion (HMAC-SHA256, SIEM integration, transparency obligations), OpenTelemetry observability for user integration, deprecation policy enforcement, external security audit scheduled during this phase, ADR-021 (AI Act compliance posture). No multi-tenancy work.

**Phase 4 — Distribution (v0.10-v1.0, ~3 months including org/legal lead time absorbed from Phase 1):** Electron packaging, code signing (macOS + Windows EV), notarization, auto-update with staged rollout and rollback, distribution channels (GitHub Releases, Homebrew, winget, AUR/Flathub), per-platform installation guides, migration guide from v0.1 alpha.

**Phase 5 — LM Arena Decision (v1.0-rc, 2 weeks):** ADR-022 either commits LM Arena to v1.1 with full scope or removes the gated stub.

**Total timeline:** ~10-11 months from v0.1.0-alpha to v1.0, targeting roughly Q1 2027.

**EU AI Act enforcement (Aug 2, 2026)** lands during Phase 2, which is why audit chain work starts in Phase 1 in parallel — it has to be done before enforcement regardless of phase plan.
