# Architecture Decision Records

**Project:** ARC Studio  
**Version:** 0.6.0-alpha  
**Last Updated:** 2026-05-13

---

## ADR-001: Theia Framework Selection

**Status:** Accepted  
**Date:** Phase 2 (Research)

**Context:**  
Need an extensible IDE framework for building agent workflow tooling with:
- Browser and desktop deployment
- Extension system for custom widgets
- VS Code compatibility for familiarity
- Multi-language support

**Decision:**  
Use Eclipse Theia as the IDE framework.

**Consequences:**
- ✅ VS Code extension compatibility
- ✅ Multi-language support via LSP
- ✅ Browser and Electron deployment options
- ✅ Active community and documentation
- ⚠️ Larger bundle size than custom solution
- ⚠️ Learning curve for Theia-specific patterns

---

## ADR-002: Security-First Subprocess Execution

**Status:** Accepted  
**Date:** Phase 4 (Independent Fixes)

**Context:**  
Need to execute user-provided prompts as CLI commands (swarmgraph swarm --json "prompt").
This creates command injection risk if not handled properly.

**Decision:**  
Use list-form argv with shell disabled (shell:false in TypeScript, shell=False in Python)
as the primary defence. Add input validation (metacharacter rejection) as defence-in-depth.
Use environment allow-list to prevent unbounded inheritance.

**Consequences:**
- ✅ Command injection impossible via classical shell injection
- ✅ Path traversal prevented via workspace isolation
- ✅ Environment leakage prevented via allow-list
- ⚠️ Cannot use shell features (pipes, redirects, variable expansion)
- ⚠️ Prompts with shell metacharacters are rejected (intentional)

---

## ADR-003: JSONL Trace Format

**Status:** Accepted  
**Date:** Phase 2 (Research)

**Context:**  
Need to store and stream execution traces from workflow runs.
Options considered: JSON, JSONL, Protocol Buffers, custom binary format.

**Decision:**  
Use JSONL (JSON Lines) format — one JSON object per line.

**Consequences:**
- ✅ Easy streaming (line-by-line reading)
- ✅ Human-readable and debuggable
- ✅ Simple parsing (JSON.parse per line)
- ✅ Handles large files efficiently (no need to load entire file)
- ⚠️ No built-in schema validation
- ⚠️ Larger file size than binary formats

---

## ADR-004: Monaco ESM Integration

**Status:** Accepted  
**Date:** Phase 5 (Integration Fixes)

**Context:**  
Monaco editor migrated to ESM modules in Theia 1.45+.
The generated webpack config uses resolvePackagePath for monaco-editor-core,
which returns null when it's only a transitive dependency.

**Decision:**  
Add @theia/monaco-editor-core as a direct dependency of arc-browser-app
to make resolvePackagePath work correctly.

**Consequences:**
- ✅ Webpack build succeeds
- ✅ Monaco editor works correctly
- ⚠️ Larger dependency tree
- ⚠️ Direct dependency on a transitive package

---

## ADR-005: Production Source Map Exclusion

**Status:** Accepted  
**Date:** Phase 6 (Alpha Acceptance)

**Context:**  
Source maps add 70+ MB to the production bundle and 356 MB for stats.json.
This makes the production bundle impractically large for deployment.

**Decision:**  
Exclude source maps from production builds (devtool: false).
Remove .map files and stats.json via RemoveSourceMapsPlugin.

**Consequences:**
- ✅ Production bundle: 38 MB (vs 521 MB dev)
- ✅ 93% size reduction
- ⚠️ Harder to debug production errors
- ⚠️ Stack traces less useful in production

---

## ADR-006: Environment Allow-List for Child Processes

**Status:** Accepted  
**Date:** Phase 5 P1 (Security Fixes)

**Context:**  
Child processes inherit the full parent environment by default ({ ...process.env }).
This can leak sensitive variables (tokens, keys, credentials) to subprocesses.

**Decision:**  
Define an explicit allow-list of 12 environment variables that child processes may inherit.
All other variables are stripped.

**Consequences:**
- ✅ No environment variable leakage
- ✅ Explicit control over what subprocesses see
- ⚠️ New env vars must be explicitly added to allow-list
- ⚠️ May break if subprocess needs unexpected env var

---

## ADR-007: Gated Workspace Launcher

**Status:** Accepted  
**Date:** Phase 5 P1 (Security Fixes)

**Context:**  
The findExecutable method checks workspace-local executables before system PATH.
In a Theia IDE that opens user workspaces, any file named "swarmgraph" in the
workspace root would be preferred over the system installation — a foot-gun.

**Decision:**  
Change priority to: ARC_SWARMGRAPH_CLI env var → system PATH → workspace local
(only if ARC_TRUST_WORKSPACE_LAUNCHER=1).

**Consequences:**
- ✅ System executables preferred by default
- ✅ Workspace executables require explicit opt-in
- ⚠️ Users must set env var to use workspace-local CLI
- ⚠️ Slightly more complex configuration

---

## ADR-008: Defence-in-Depth Security Model

**Status:** Accepted  
**Date:** Phase 5 P0 (Security Fixes)

**Context:**  
Security review identified that security-utils.ts validators were not wired into
the backend service — the class used private stubs instead. The primary mitigation
(shell:false) is sufficient, but the validators provide defence-in-depth.

**Decision:**  
Wire shared security-utils into backend service, replacing private stubs.
Both layers (shell:false + input validation) are active simultaneously.

**Consequences:**
- ✅ Two independent security layers
- ✅ Metacharacter rejection even if shell:false is accidentally removed
- ⚠️ Slightly more complex code
- ⚠️ Validators may reject valid prompts with shell metacharacters

---

## ADR-009: Test Coverage Strategy

**Status:** Accepted  
**Date:** Phase 6 (Alpha Acceptance)

**Context:**  
Widget tests cannot easily achieve runtime coverage because importing the widget
requires Theia browser dependencies (ReactWidget, MessageService, jsdom).
Setting up a full jsdom test harness with mocked Theia DI is complex.

**Decision:**  
Use source-code analysis for widget tests (reading .tsx file and validating patterns).
Focus runtime test coverage on backend service and security utilities.
Accept 63.86% overall coverage for alpha, target 70%+ for beta.

**Consequences:**
- ✅ Backend and security well-tested (67.74% and 96.61%)
- ✅ Widget logic validated via source analysis
- ⚠️ Widget not tested at runtime
- ⚠️ Coverage below 70% target

---

## ADR-010: Dual Backend Architecture

**Status:** Accepted  
**Date:** Phase 4 (Independent Fixes)

**Context:**  
Project has both a TypeScript backend (Theia JSON-RPC) and a Python backend (FastAPI REST).
Both can execute SwarmGraph workflows, creating redundancy.

**Decision:**  
Keep both backends for now. TypeScript backend is primary (integrated with Theia UI).
Python backend serves as a standalone API for external integrations.
Plan to collapse into single canonical backend in future phase.

**Consequences:**
- ✅ Flexibility for different use cases
- ✅ Python backend accessible without Theia
- ⚠️ Code duplication between backends
- ⚠️ Maintenance burden of two implementations

---

## ADR-011: SwarmGraph Runner Canonical Path

**Status:** Accepted  
**Date:** 2026-05-14

**Context:**  
Two parallel SwarmGraph implementations existed with divergent security, gating, and event streaming behavior. The CLI subprocess path had a P0 security vulnerability ([#10](https://github.com/Hansuqwer/arc-theia-studio/issues/10)).

**Decision:**  
Modular `SwarmGraphRunner` is canonical. CLI subprocess path is deprecated. Cost gating unified via `require_dual_gate()`. Workspace-rooted launchers permanently removed.

**Consequences:**
- ✅ Security: no executable from untrusted workspaces
- ✅ Gating: single source of truth (`require_dual_gate`)
- ✅ Streaming: real-time AG-UI events for all backends
- ✅ 23 security-focused and gating tests added
- ⚠️ Breaking change: users must configure `ARC_SWARMGRAPH_CLI`
- ⚠️ Monolithic path emits deprecation warning

---

**Last Reviewed:** 2026-05-14  
**Next Review:** When major architecture changes are made
