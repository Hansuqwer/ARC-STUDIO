# Path to 1.0 — Phase Review Prompt

**Purpose:** Systematic review gate for each phase (Phase 1-5) in the path to 1.0 roadmap.  
**Related:** ADR-020 (desktop-first decision), docs/roadmap.md, docs/phases.md  
**Last Updated:** 2026-05-21

## Review Framework

Each phase review produces one of three outcomes:

- **APPROVE:** Phase meets all acceptance criteria. Proceed to next phase.
- **APPROVE_WITH_FOLLOWUPS:** Phase meets minimum bar but has identified gaps. Document followups explicitly; proceed to next phase with followup tracking.
- **REJECT:** Phase has blocking gaps. Do not proceed until gaps are closed.

## Universal Checks (All Phases)

These checks apply to every phase review regardless of phase-specific scope.

### 1. Verification Baseline

```bash
# Python tests
cd python && uv run pytest -q
# Expected: all pass (or documented pre-existing failures only)

# TypeScript builds
pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build
# Expected: clean build, no errors

# PR hygiene
bash scripts/check-pr.sh
# Expected: pass

# If browser/IDE touched:
pnpm --filter @arc-studio/browser build
pnpm --filter @arc-studio/e2e-tests test
# Expected: pass
```

**Gate:** All verification commands pass. If any fail, REJECT.

### 2. Documentation Completeness

- [ ] Every new public API has docstrings/JSDoc
- [ ] Every new CLI command has `--help` text
- [ ] Every new slash command has discoverable help
- [ ] CHANGELOG.md updated with user-facing changes
- [ ] README.md updated if installation/setup changed
- [ ] ADRs referenced where architectural decisions were made

**Gate:** If user-facing features lack documentation, APPROVE_WITH_FOLLOWUPS (document in next phase). If architectural decisions lack ADRs, REJECT.

### 3. Deprecation Policy Adherence (ADR-020)

- [ ] Breaking changes announced in CHANGELOG with migration path
- [ ] Deprecated features have removal timeline (one minor version + one patch cycle)
- [ ] Shims for deprecated features include deprecation warnings
- [ ] No silent breaking changes

**Gate:** If breaking changes lack migration path or timeline, REJECT.

### 4. Schema/API Stability

- [ ] Cross-language schemas (Python ↔ TypeScript) have migration tests
- [ ] New schemas include `tenant_id` or `principal_id` fields (default `"local"`) per ADR-020 guardrails
- [ ] SQLite queries avoid SQLite-specific syntax unless behind interface
- [ ] HTTP API endpoints designed for future remote use (no client-trusts-server assumptions)

**Gate:** If schemas break future SaaS optionality without justification, APPROVE_WITH_FOLLOWUPS. If cross-language schemas lack migration tests, REJECT.

### 5. Security & Privacy

- [ ] No secrets logged in error output
- [ ] No secrets persisted in plaintext (env-var references only)
- [ ] Sensitive data (API keys, file paths, prompts) redacted in logs
- [ ] New HTTP endpoints respect loopback-only binding default

**Gate:** If secrets are logged or persisted, REJECT.

### 6. Test Coverage

- [ ] New features have unit tests
- [ ] New CLI commands have integration tests
- [ ] New HTTP endpoints have web tests
- [ ] Paid/live provider paths are in `@pytest.mark.paid` taxonomy (excluded by default)
- [ ] No `--deselect` debt added to CI

**Gate:** If new features lack tests, APPROVE_WITH_FOLLOWUPS. If paid tests are not properly marked, REJECT.

---

## Phase-Specific Checks

### Phase 1 — Polish (v0.2-v0.5)

**Scope:** Documentation, error messages, empty/degraded states, performance, accessibility, test taxonomy, EU AI Act audit chain foundation.

#### 1.1 Documentation (Diátaxis Framework)

- [ ] **Tutorials:** Getting Started guide exists, takes <5 minutes from install to first `/run`
- [ ] **How-tos:** Task-oriented guides for common workflows (configure provider, run workflow, inspect trace, respond to HITL)
- [ ] **Reference:** 100% CLI command coverage in `arc --help` and `arc <subcommand> --help`
- [ ] **Explanation:** Architecture overview for contributors exists

**Gate:** If Getting Started guide is missing or broken, REJECT. If CLI coverage <100%, APPROVE_WITH_FOLLOWUPS.

#### 1.2 Error Messages

- [ ] Every error path has human-readable message with concrete next action
- [ ] Errors include stable `error_code` for documentation lookup
- [ ] Degraded states (missing data, partial responses, cancelled turns) have distinct messages from hard errors
- [ ] Sensitive data never logged in error output

**Gate:** If errors lack actionable messages or leak sensitive data, REJECT.

#### 1.3 Empty & Degraded States

- [ ] Every IDE tab has defined empty state with onboarding guidance
- [ ] Every list view has defined zero-results state
- [ ] Every operation has defined cancelled state
- [ ] Every async operation has defined loading state
- [ ] Degraded cost records render with explicit "estimated" badges

**Gate:** If any IDE surface fabricates data instead of showing empty/degraded state, REJECT.

#### 1.4 Performance Budgets

- [ ] REPL prompt latency < 50ms (p50)
- [ ] First-token streaming latency < 500ms (p50)
- [ ] `arc --help` cold start < 200ms
- [ ] IDE tab switch < 100ms
- [ ] Performance regression tests added to CI

**Gate:** If budgets are not measured or documented, APPROVE_WITH_FOLLOWUPS. If budgets are exceeded by >2x, REJECT.

#### 1.5 Accessibility

- [ ] Keyboard navigation for all IDE flows
- [ ] ARIA labels on interactive elements
- [ ] Screen reader compatibility verified with at least one screen reader (NVDA or VoiceOver)
- [ ] Colorblind-friendly palette for cost/budget visualizations
- [ ] Respects `prefers-reduced-motion`
- [ ] CLI output supports `NO_COLOR` env var

**Gate:** If keyboard navigation is broken or screen reader compatibility is not verified, APPROVE_WITH_FOLLOWUPS. If ARIA labels are missing on critical elements, REJECT.

#### 1.6 Test Taxonomy Cleanup

- [ ] Paid-smoke tests moved to `@pytest.mark.paid` taxonomy
- [ ] Full `pytest` run requires no flags to pass
- [ ] CI runs paid taxonomy on schedule, not per-commit
- [ ] No `--deselect` debt remains

**Gate:** If `--deselect` debt remains, APPROVE_WITH_FOLLOWUPS. If paid tests run in default CI, REJECT.

#### 1.7 EU AI Act Audit Chain Foundation

- [ ] ADR-021 (audit chain architecture) drafted and accepted
- [ ] HMAC-SHA256 audit chain implementation started
- [ ] Audit chain schema includes `principal` field (default `"local"`)
- [ ] Audit chain key derivation is parameterizable for future per-tenant keys

**Gate:** If ADR-021 is not drafted by end of Phase 1, REJECT (Aug 2 deadline is 73 days from v0.1.0-alpha release).

#### 1.8 Org/Legal Track (Parallel)

- [ ] Apple Developer Program enrollment initiated ($99/year)
- [ ] D-U-N-S number obtained (if organizational)
- [ ] Windows EV certificate business verification initiated (~2-4 weeks)
- [ ] Privacy policy and terms of service drafting started

**Gate:** If org/legal track has not started by end of Phase 1, APPROVE_WITH_FOLLOWUPS (but flag as high risk for Phase 4).

---

### Phase 2 — Provider Expansion (v0.6-v0.8)

**Scope:** OpenAI provider, provider abstraction generalization, retry/failover, prompt caching, additional providers, real-time budget enforcement, MCP tool transport, OpenTelemetry GenAI conventions.

#### 2.1 OpenAI Provider Client

- [ ] Full `ProviderClient` implementation (streaming, tool use, vision, structured output)
- [ ] Cost extraction from OpenAI usage block
- [ ] Model alias mapping (gpt-4.1, gpt-5, etc.)
- [ ] Azure OpenAI variant support
- [ ] Tests cover all features

**Gate:** If OpenAI provider lacks feature parity with Anthropic, APPROVE_WITH_FOLLOWUPS. If cost extraction is broken, REJECT.

#### 2.2 Provider Abstraction Generalization

- [ ] ADR-014, ADR-019, cache breakpoint contract are provider-agnostic
- [ ] Provider-specific logic (Anthropic cache-control, OpenAI structured output) behind capability flags
- [ ] Tool-call shape normalization (canonical internal format)
- [ ] `ProviderCapability` schema supports per-provider capabilities

**Gate:** If provider-specific logic leaks into shared code, REJECT.

#### 2.3 Retry, Failover, Circuit Breaking

- [ ] Per-provider circuit breakers (open/half-open/closed states)
- [ ] Cross-provider failover policy (e.g., OpenAI → Anthropic → local)
- [ ] Exponential backoff with jitter
- [ ] Shared retry budget
- [ ] Honor `Retry-After` headers
- [ ] Distinguish retryable from non-retryable errors per provider

**Gate:** If retry logic is missing or circuit breakers are not implemented, APPROVE_WITH_FOLLOWUPS. If failover causes cascading failures, REJECT.

#### 2.4 Prompt Caching Across Providers

- [ ] `CacheStrategy` per provider (explicit_breakpoints, automatic, none)
- [ ] Anthropic explicit cache-control preserved
- [ ] OpenAI automatic caching documented
- [ ] Cost extraction handles both strategies

**Gate:** If cache strategy is not abstracted, APPROVE_WITH_FOLLOWUPS.

#### 2.5 Additional Providers

- [ ] At least 3 of: Gemini, Mistral, Bedrock, local OpenAI-compatible (vLLM, Ollama, LM Studio)
- [ ] Each provider has full `ProviderClient` implementation
- [ ] Each provider has cost extraction (or documented as "not available")
- [ ] Each provider has tests

**Gate:** If <3 additional providers are implemented, APPROVE_WITH_FOLLOWUPS. If any provider lacks tests, REJECT.

#### 2.6 Real-Time Budget Enforcement

- [ ] Hierarchical budgets (run < workflow < session < provider-day < global)
- [ ] Budget evaluated before request reaches provider
- [ ] Per-user throttling
- [ ] Budget exhaustion produces structured event
- [ ] IDE renders budget exhaustion as live banner

**Gate:** If budget enforcement is not real-time (only post-hoc), APPROVE_WITH_FOLLOWUPS. If budget exhaustion is silent, REJECT.

#### 2.7 OpenTelemetry GenAI Conventions

- [ ] Full adoption of `gen_ai.*` attributes (system, request.model, response.id, usage.input_tokens, etc.)
- [ ] OTLP exporter for traces
- [ ] Example dashboards for Grafana and Datadog
- [ ] Structured logging uses OTel semantic conventions

**Gate:** If OTel conventions are not adopted, APPROVE_WITH_FOLLOWUPS. If traces are not exportable, REJECT.

#### 2.8 MCP Tool Transport

- [ ] MCP client implemented
- [ ] External tool servers can be registered as `ToolHandler` implementations
- [ ] MCP transport support (stdio, HTTP+SSE, streamable HTTP)
- [ ] MCP results trust-tagged as `untrusted` by default per ADR-019

**Gate:** If MCP client is not implemented, APPROVE_WITH_FOLLOWUPS (but flag as high priority for enterprise adoption).

---

### Phase 3 — Compliance & Observability (v0.9)

**Scope:** EU AI Act audit chain completion, OpenTelemetry observability, deprecation policy enforcement, external security audit.

#### 3.1 EU AI Act Audit Chain Completion

- [ ] HMAC-SHA256 audit chain implemented for all adapters
- [ ] Every agent decision, tool call, LLM interaction logged to verifiable chain
- [ ] SIEM integration via OTel
- [ ] Documented compliance posture for "limited risk" tier
- [ ] Transparency obligations satisfied (users know they're interacting with AI)
- [ ] Incident reporting capability exists

**Gate:** If audit chain is not complete by Aug 2, 2026, REJECT (regulatory deadline). If any adapter lacks audit chain, REJECT.

#### 3.2 OpenTelemetry Observability

- [ ] Users can integrate desktop daemon with their own monitoring stack
- [ ] OTel exporter configuration documented
- [ ] Example integrations (Grafana, Datadog, OpenObserve) provided
- [ ] Structured logging complete

**Gate:** If OTel integration is not documented, APPROVE_WITH_FOLLOWUPS.

#### 3.3 Deprecation Policy Enforcement

- [ ] All deprecated features from Phase 1-2 have removal timeline
- [ ] Shims emit deprecation warnings
- [ ] CHANGELOG documents all deprecations
- [ ] No silent removals

**Gate:** If deprecation policy is not enforced, REJECT.

#### 3.4 External Security Audit

- [ ] Security audit scheduled (4-6 weeks lead time)
- [ ] Audit scope covers ADR-014 (security architecture), ADR-019 (tool trust boundaries), prompt injection defenses, audit chain integrity, secret handling
- [ ] Audit findings documented
- [ ] Critical findings remediated before 1.0

**Gate:** If security audit is not scheduled by end of Phase 3, REJECT. If critical findings are not remediated, REJECT.

---

### Phase 4 — Distribution (v0.10-v1.0)

**Scope:** Electron packaging, code signing, notarization, auto-update, distribution channels, installation guides.

#### 4.1 Electron Packaging

- [ ] PyInstaller daemon embedded as resource
- [ ] Electron app bundles daemon + UI
- [ ] Tested on clean VMs for macOS, Windows, Linux

**Gate:** If packaging is broken on any platform, REJECT.

#### 4.2 Code Signing

- [ ] macOS: signed with Apple Developer ID certificate
- [ ] macOS: notarized via `notarytool`
- [ ] Windows: signed with EV certificate
- [ ] Windows: no SmartScreen warnings on first install
- [ ] Signing in CI using cloud HSM (Azure Key Vault, AWS CloudHSM)

**Gate:** If code signing is not working on any platform, REJECT.

#### 4.3 Auto-Update

- [ ] `electron-updater` integrated
- [ ] Hosted update endpoint (S3 + CloudFront or GitHub Releases)
- [ ] Staged rollout capability (release to 10% first)
- [ ] Rollback mechanism
- [ ] Update notifications in UI

**Gate:** If auto-update is not working, APPROVE_WITH_FOLLOWUPS. If rollback is not possible, REJECT.

#### 4.4 Distribution Channels

- [ ] GitHub Releases with checksums
- [ ] Homebrew tap for macOS
- [ ] winget for Windows
- [ ] AUR or Flathub for Linux
- [ ] Direct download page with installation instructions

**Gate:** If <3 distribution channels are available, APPROVE_WITH_FOLLOWUPS.

#### 4.5 Installation Guides

- [ ] Per-platform installation guide (macOS, Windows, Linux)
- [ ] Migration guide for users upgrading from v0.1 alpha
- [ ] Troubleshooting guide
- [ ] Uninstall instructions

**Gate:** If installation guides are missing, REJECT.

#### 4.6 Distribution-Readiness Gates

- [ ] Install/uninstall flows tested on clean VMs
- [ ] First-run experience tested (onboarding, default config)
- [ ] Upgrade path from v0.1 alpha tested
- [ ] Privacy policy and terms of service finalized
- [ ] Release notes template ready

**Gate:** If any distribution-readiness gate fails, REJECT.

---

### Phase 5 — LM Arena Decision (v1.0-rc)

**Scope:** Decide whether to commit LM Arena to v1.1 or remove gated stub.

#### 5.1 LM Arena Decision

- [ ] ADR-022 drafted (LM Arena status decision)
- [ ] Decision is either:
  - **Commit:** Full scope defined (real model battles, scoring, provider integration, safety gates, tests/docs), timeline estimated, resources allocated
  - **Remove:** Gated stub removed from codebase, no maintenance tax

**Gate:** If decision is not made, REJECT. If decision is "commit" but scope/timeline/resources are not defined, REJECT.

---

## Review Execution

### Before Review

1. Run all verification commands (Universal Checks #1)
2. Collect evidence:
   - Test results (pytest output, jest output)
   - Build logs
   - Performance measurements (if Phase 1)
   - Security audit report (if Phase 3)
   - Distribution test results (if Phase 4)

### During Review

1. Go through Universal Checks (all phases)
2. Go through Phase-Specific Checks (current phase only)
3. For each check:
   - Mark as ✅ (pass), ⚠️ (pass with followups), or ❌ (fail)
   - Document evidence or gap
4. Determine outcome:
   - **APPROVE:** All checks ✅, no ❌
   - **APPROVE_WITH_FOLLOWUPS:** Some ⚠️, no ❌, followups documented
   - **REJECT:** Any ❌

### After Review

1. Document outcome in `docs/phases.md` (update phase status)
2. If APPROVE_WITH_FOLLOWUPS, create followup tracking (GitHub issues or next phase checklist)
3. If REJECT, document blocking gaps and remediation plan
4. Update `docs/roadmap.md` with current status

---

## Example Review Output

```markdown
# Phase 1 Review — 2026-08-15

## Outcome: APPROVE_WITH_FOLLOWUPS

## Universal Checks
- ✅ Verification baseline: all tests pass
- ✅ Documentation completeness: CHANGELOG updated, ADRs referenced
- ✅ Deprecation policy: no breaking changes in Phase 1
- ✅ Schema/API stability: tenant_id fields added per ADR-020
- ✅ Security & privacy: no secrets logged
- ✅ Test coverage: 1450 Python tests, 820 TS tests

## Phase 1 Checks
- ✅ Documentation (Diátaxis): Getting Started guide complete, <5min
- ✅ Error messages: stable error codes, actionable messages
- ✅ Empty/degraded states: all IDE tabs have empty states
- ⚠️ Performance budgets: measured but not in CI yet (followup: add regression tests)
- ⚠️ Accessibility: keyboard nav works, screen reader not yet verified (followup: test with NVDA)
- ✅ Test taxonomy: paid tests in @pytest.mark.paid, no --deselect debt
- ✅ EU AI Act foundation: ADR-021 drafted, HMAC implementation started
- ✅ Org/legal track: Apple enrollment initiated, EV cert in progress

## Followups for Phase 2
1. Add performance regression tests to CI (owner: @eng, deadline: Phase 2 week 1)
2. Verify screen reader compatibility with NVDA (owner: @eng, deadline: Phase 2 week 2)

## Evidence
- Python tests: 1450 passed, 22 skipped
- TS tests: 820 passed
- Performance: REPL 42ms p50, first-token 380ms p50, arc --help 150ms
- ADR-021: docs/adr/021-audit-chain-architecture.md (status: Proposed)
```

---

## Notes

- This review prompt is a living document. Update it as new checks are identified or existing checks become obsolete.
- The review is not a bureaucratic gate; it's a quality gate. If a check is consistently irrelevant, remove it.
- The review should take 1-2 hours per phase, not days. If it takes longer, the checks are too detailed or the phase scope is too large.
- The review is done by the implementer(s) with optional peer review. It's not an external audit.
