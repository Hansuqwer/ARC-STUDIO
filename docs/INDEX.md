# ARC Studio Documentation Index

## Architecture Decision Records (ADR)

These are proposed architectural decisions for ARC Studio. They become authoritative only after review acceptance and implementation-plan integration.

| ADR | Title | Status |
|-----|-------|--------|
| [000](adr/000-execution-core-contract.md) | Execution Core Contract Specification | Proposed |
| [001](adr/001-config-model.md) | Configuration Model and Precedence | Proposed |
| [002](adr/002-run-lifecycle-state-machine.md) | Run Lifecycle State Machine and Background Job Supervisor | Proposed |
| [003](adr/003-storage-strategy.md) | Storage Strategy — JSONL Traces + SQLite Index | Proposed |
| [004](adr/004-event-schema-versioning.md) | Event Schema Versioning Contract | Proposed |
| [005](adr/005-audit-key-management.md) | Audit HMAC Key Management and Rotation | Proposed |
| [006](adr/006-workspace-trust-isolation.md) | Workspace Trust, Filesystem, and Network Isolation Policies | Proposed |
| [007](adr/007-provider-routing-unification.md) | Provider Routing Unification | Proposed |
| [008](adr/008-daemon-bundling.md) | Python Daemon Bundling for Electron/Desktop | Proposed |

## Current Reference Documents

These documents are **current and maintained** as reference material.

| Document | Description |
|----------|-------------|
| [REALITY_AUDIT.md](REALITY_AUDIT.md) | Repo-grounded audit of what's real, fiction, and underclaimed |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Phased P0-P5 implementation roadmap |
| [CLI_IDE_GAP_ANALYSIS.md](CLI_IDE_GAP_ANALYSIS.md) | Market-comparative CLI/IDE capability analysis |
| [ADAPTER_DEVELOPMENT.md](ADAPTER_DEVELOPMENT.md) | Guide for developing runtime adapters |
| [SECURITY.md](SECURITY.md) | Security policy and threat model |
| [MOCK_POLICY.md](MOCK_POLICY.md) | Policy for mock/fixture usage in tests |
| [TESTING.md](TESTING.md) | Testing strategy and conventions |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Development setup and workflow guide |
| [QUICKSTART.md](QUICKSTART.md) | Quick start guide for new developers |
| [RUNTIMES.md](RUNTIMES.md) | Runtime support matrix and adapter status |

## Archived Documents

These documents are **historical** and preserved for reference. They are NOT current guidance.

### Phase Completion Reports
- [PHASE_1_COMPLETE.md](archive/PHASE_1_COMPLETE.md)
- [PHASE_2_COMPLETE.md](archive/PHASE_2_COMPLETE.md)
- [PHASE_3_COMPLETE_SUMMARY.md](archive/PHASE_3_COMPLETE_SUMMARY.md)
- [PHASE_4_COMPLETE.md](archive/PHASE_4_COMPLETE.md)
- [PHASE_5_COMPLETE.md](archive/PHASE_5_COMPLETE.md)
- [PHASE_6_COMPLETE.md](archive/PHASE_6_COMPLETE.md)
- [PHASE_7_COMPLETE.md](archive/PHASE_7_COMPLETE.md)

### Phase Execution Prompts
- [PHASE_2_EXECUTION_PROMPT.md](archive/PHASE_2_EXECUTION_PROMPT.md)
- [PHASE_2_EXECUTION_SUMMARY.md](archive/PHASE_2_EXECUTION_SUMMARY.md)
- [PHASE_2_STATUS.md](archive/PHASE_2_STATUS.md)
- [PHASE_3_DISCOVERY.md](archive/PHASE_3_DISCOVERY.md)
- [PHASE_3_EXECUTION_PROMPT.md](archive/PHASE_3_EXECUTION_PROMPT.md)
- [PHASE_5_EXECUTION_PROMPT.md](archive/PHASE_5_EXECUTION_PROMPT.md)
- [PHASE_5_E2E_ISSUES.md](archive/PHASE_5_E2E_ISSUES.md)
- [PHASE_6_EXECUTION_PROMPT.md](archive/PHASE_6_EXECUTION_PROMPT.md)
- [PHASE_7_EXECUTION_PROMPT.md](archive/PHASE_7_EXECUTION_PROMPT.md)

### Handover Documents
- [FINAL_HANDOVER.md](archive/FINAL_HANDOVER.md)
- [FINAL_STATUS.md](archive/FINAL_STATUS.md)
- [HANDOFF.md](archive/HANDOFF.md)
- [KNOWLEDGE_TRANSFER.md](archive/KNOWLEDGE_TRANSFER.md)
- [ORCHESTRATOR_HANDOVER_PROMPT.md](archive/ORCHESTRATOR_HANDOVER_PROMPT.md)

### Superseded Architecture
- [ARCHITECTURE.md](archive/ARCHITECTURE.md) — Superseded by ADR series
- [ADR.md](archive/ADR.md) — Superseded by `docs/adr/` directory
- [DECISIONS/](archive/DECISIONS/) — Superseded by ADR series
- [IMPLEMENTATION_DECISIONS.md](archive/IMPLEMENTATION_DECISIONS.md) — Superseded by IMPLEMENTATION_PLAN.md
- [U1-U2_DECISIONS.md](archive/U1-U2_DECISIONS.md) — Historical decisions

### Superseded Roadmaps
- [ROADMAP.md](archive/ROADMAP.md) — Superseded by IMPLEMENTATION_PLAN.md
- [ROADMAP_PHASE3.md](archive/ROADMAP_PHASE3.md) — Historical
- [NEXT_STEPS.md](archive/NEXT_STEPS.md) — Superseded by IMPLEMENTATION_PLAN.md

### Audit and Review Reports
- [SECURITY_AUDIT_REPORT.md](archive/SECURITY_AUDIT_REPORT.md) — Historical audit
- [SECURITY_REVIEW.md](archive/SECURITY_REVIEW.md) — Historical review
- [SECURITY_QUICK_REFERENCE.md](archive/SECURITY_QUICK_REFERENCE.md) — Superseded by SECURITY.md
- [BUG_BASH_REPORT.md](archive/BUG_BASH_REPORT.md) — Historical bug bash
- [UAT_REPORT.md](archive/UAT_REPORT.md) — Historical UAT

### Operational Documents
- [DEPLOYMENT.md](archive/DEPLOYMENT.md) — Not yet updated for current architecture
- [MONITORING.md](archive/MONITORING.md) — Not yet updated for current architecture
- [RUNBOOK.md](archive/RUNBOOK.md) — Not yet updated for current architecture
- [RELEASE_CHECKLIST.md](archive/RELEASE_CHECKLIST.md) — Not yet updated for current architecture
- [RELEASE.md](archive/RELEASE.md) — Not yet updated for current architecture
- [PACKAGING.md](archive/PACKAGING.md) — Superseded by ADR-008
- [MAINTENANCE.md](archive/MAINTENANCE.md) — Historical
- [ONBOARDING.md](archive/ONBOARDING.md) — Superseded by QUICKSTART.md + DEVELOPMENT.md
- [WALKTHROUGH.md](archive/WALKTHROUGH.md) — Historical
- [TROUBLESHOOTING.md](archive/TROUBLESHOOTING.md) — May contain useful tips but not current
- [USER_GUIDE.md](archive/USER_GUIDE.md) — Not yet updated for current UI
- [API.md](archive/API.md) — Not yet updated for current daemon API
- [VERIFICATION.md](archive/VERIFICATION.md) — Historical
- [SOURCES.md](archive/SOURCES.md) — Historical source references
- [RESEARCH_NOTES.md](archive/RESEARCH_NOTES.md) — Historical research
- [PRODUCTION_BUILD_REPORT.md](archive/PRODUCTION_BUILD_REPORT.md) — Historical build report
- [MOCKS_AND_BLOCKERS.md](archive/MOCKS_AND_BLOCKERS.md) — Superseded by MOCK_POLICY.md
- [PLUGIN_POLICY.md](archive/PLUGIN_POLICY.md) — Not yet updated for current architecture
- [PR_ACCEPTANCE.md](archive/PR_ACCEPTANCE.md) — Historical PR policy
- [mypy-expansion.md](archive/mypy-expansion.md) — Historical mypy work
- [branch-cleanup.md](archive/branch-cleanup.md) — Historical branch cleanup

### Handover Archive
- [handover/](archive/handover/) — Previous handover documents
- [history/](archive/history/) — Historical context documents

## Research Documents

Active research and analysis documents:

| Document | Description |
|----------|-------------|
| [research/](research/) | Active research notes and analysis |
| [audits/](audits/) | Audit reports and findings |
| [context-packs/](context-packs/) | Context pack definitions |
| [schemas/](schemas/) | Schema definitions |

## How to Use This Index

1. **For architectural decisions**: Read the ADR series (`docs/adr/`)
2. **For current state**: Read `REALITY_AUDIT.md` and `IMPLEMENTATION_PLAN.md`
3. **For market context**: Read `CLI_IDE_GAP_ANALYSIS.md`
4. **For development**: Read `QUICKSTART.md` and `DEVELOPMENT.md`
5. **For adapter development**: Read `ADAPTER_DEVELOPMENT.md`
6. **For security**: Read `SECURITY.md` and `MOCK_POLICY.md`
7. **For historical context**: Browse `archive/` directory

## Document Status Legend

| Status | Meaning |
|--------|---------|
| **Current** | Actively maintained, reflects current architecture |
| **Proposed** | Drafted for review, not yet implemented |
| **Archived** | Historical, preserved for reference, NOT current guidance |
| **Superseded** | Replaced by a newer document |
