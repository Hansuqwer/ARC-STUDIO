# Testing / Observability / Docs Review

## Current ARC Spec

### Testing (§6 CLI_IDE_REDESIGN_PLAN, §16 ARC_STUDIO_UX_SPEC, RELEASE_CHECKLIST)

ARC Studio specifies a three-layer test strategy:

**Python (pytest):** 550 passed, 10 skipped across adapters, storage, orchestration, security, isolation, audit, eval, CLI, and web endpoint tests. Real-runtime smoke is opt-in via `ARC_REAL_RUNTIME_SMOKE=1`. Conformance tests exist for SwarmGraph (8/8) and LangGraph (9/9).

**TypeScript (Jest):** 239 tests across 6 suites in `packages/arc-extension`. UI components use static source-pattern contract tests (not runtime jsdom). Coverage: 61.84% statements, 67.34% branches, 53.78% functions, 63.18% lines. Browser files show 0% coverage due to Theia runtime dependency.

**E2E (Playwright):** 12 smoke tests in `tests/e2e/arc-smoke.spec.ts`. Tests browser app load, ARC widget rendering, run timeline execution with local stub, runtime picker, run persistence across reload, event stream filtering, health monitor, and CLI integration (`arc inspect`, `arc adapter test`). CI workflow (`e2e.yml`) runs on every push/PR with stub backend.

**CI Gates:** Three workflows — `python` (pytest + ruff + mypy + pip-audit), `node` (build + workspace tests + PR hygiene), `e2e` (Playwright). A separate `real-runtime-smoke.yml` runs nightly/manual with opt-in real runtime tests. `arc-roadmap-gate.yml` enforces banned-claims checks.

### Observability (IMPLEMENTATION_PLAN P4, ARC_STUDIO_UX_SPEC §10.10)

**Trace Store:** JSONL canonical traces with SQLite index (ADR-003). `IndexedTraceStore` dual-writes. `arc runs search` uses SQLite index. `arc runs status/delete/export/backfill` for lifecycle management.

**Event Broker:** `EventBroker` with bounded queue pub/sub, SSE streaming, replay fallback. `JobSupervisor` manages run lifecycle, cancel, orphan recovery.

**Eval System:** `arc eval save/delete/run --batch/report` CLI. Golden trace comparison. 9 eval tests. `arc eval run --batch` evaluates against all saved golden traces.

**Diagnostics:** `arc doctor env/network/storage`, `arc bug-report` for support bundles. Redaction contract (§10.10) applies to all surfaces: CLI output, IDE chat, SSE events, Runs summaries, graph inspector, error cards, logs. Removes API keys, bearer tokens, passwords, provider secrets, cloud credentials, `.env` values.

**Audit:** HMAC-signed audit chain (vendored SwarmGraph), ARC SHA-256 hash chain. `arc audit verify/export/key *` CLI. HITL persistence with single-use tokens, expiry/TTL, replay-attack protection.

### Documentation (ARC_STUDIO_UX_SPEC §16, RELEASE_CHECKLIST)

**Specified deliverables:** Logo concepts (SVG/PNG/ICO/ICNS), Theia theme JSON, ANSI palette YAML, Cytoscape style JSON, font subsets (WOFF2), social card PNG, docs screenshots (dark/light/CLI), design spec markdown, slash command docs.

**Current docs:** `docs/TESTING.md` (78 lines, basic test commands), `docs/RELEASE_CHECKLIST.md` (259 lines, 13 gating items), `docs/IMPLEMENTATION_PLAN.md` (phased plan), `docs/QUICKSTART.md`, `docs/DEVELOPMENT.md`, `docs/ADAPTER_DEVELOPMENT.md`. No onboarding guide, no migration guide, no screenshot assets generated yet.

**Banned claims checker:** `scripts/check-banned-claims.sh` validates release docs don't overclaim adoption, live streaming, signed audit, or arena live mode.

### Accessibility Testing (§14 ARC_STUDIO_UX_SPEC)

WCAG AA target. Keyboard-only CLI and IDE flows specified. Screen reader live regions specified. Graph nodes expose spoken descriptions. Colour-blind support: every state has icon + text. Strings externalised via `arc.nls.json`. No accessibility tests currently exist in any test suite.

---

## Comparable Products / Research

| Area | VS Code | Cursor | LangGraph Studio | Temporal | Claude Code | OpenCode | ARC Studio (current) |
|---|---|---|---|---|---|---|---|
| **Unit test framework** | Mocha + assert | N/A (closed) | pytest | Go testing + testify | N/A (closed) | Go testing | Jest (TS) + pytest (Python) |
| **Extension testing** | @vscode/test-electron, API mocks | N/A | N/A | N/A | N/A | N/A | Jest source-pattern contracts |
| **E2E framework** | Playwright (official examples) | N/A | Playwright (graph/chat flows) | tctl + test server | N/A | N/A | Playwright (12 smoke tests) |
| **Contract tests** | Protocol schema validation | N/A | Graph schema validation | Workflow replay determinism | N/A | N/A | Web protocol contract tests |
| **Integration tests** | Extension host + language server | N/A | Real graph execution | Real workflow execution | N/A | N/A | Opt-in real-runtime smoke |
| **CLI testing** | N/A | N/A | CLI golden output tests | tctl golden output tests | N/A | CLI golden output tests | CLI smoke + conformance |
| **Security tests** | Dependency scanning, secret scanning | N/A | N/A | N/A | N/A | N/A | pip-audit, redaction tests, path validation |
| **Accessibility tests** | axe-core integration in E2E | N/A | N/A | N/A | N/A | N/A | None |
| **Test coverage target** | N/A (varies by extension) | N/A | N/A | ~80% | N/A | N/A | 61.84% statements (target 70%) |
| **CI split** | PR fast + nightly full | N/A | CI + manual integration | PR + nightly | N/A | CI | PR (python/node/e2e) + nightly (real-runtime) |
| **Screenshot generation** | Manual + extension marketplace | N/A | Manual docs | Manual docs | N/A | N/A | None automated |
| **Docs testing** | Link checker | N/A | N/A | Link checker | N/A | N/A | Banned claims checker |

**Key observations:**
- VS Code's extension testing pattern (`@vscode/test-electron`) is the closest analogue to ARC's Theia extension testing needs, but Theia doesn't have an equivalent test harness. Source-pattern contract tests are a pragmatic workaround.
- Temporal's integration test pattern (test server + deterministic replay) maps well to ARC's event broker + trace replay architecture. The `arc runs replay` command is the equivalent of Temporal's workflow replay tests.
- LangGraph Studio tests real graph execution with fake nodes — ARC's stub-backed SwarmGraph E2E tests follow the same pattern.
- No competitor publishes detailed test suite structure for closed products (Claude Code, Cursor). Claims about their testing are [needs verification].
- OpenCode's test structure is Go-native with golden output comparison. ARC's Python CLI tests follow a similar pattern with JSON envelope validation.

---

## Gaps

### Critical (v0.1 gating)

1. **No accessibility tests.** §14 specifies WCAG AA, keyboard flows, screen reader regions, colour-blind support. Zero accessibility tests exist in any suite. Axe-core integration in Playwright E2E would catch basic violations.

2. **No manifest validation tests.** Appendix A specifies runtime manifest format with required fields, versioning rules, validation in `/doctor`. No tests validate manifest parsing, version rejection, or field defaults.

3. **No redaction contract E2E verification.** §10.10 specifies redaction across all surfaces. Redaction unit tests exist (`test_security.py`, 12 tests) but no E2E test verifies redacted output in CLI, IDE chat, SSE events, or graph inspector simultaneously.

4. **No terminal UI test strategy.** CLI chat REPL (§7.1-7.2) is interactive. No test framework for TUI interaction (expect-like automation for REPL input/output). Current CLI tests are non-interactive (`arc inspect --json`, `arc adapter test`).

5. **No screenshot generation pipeline.** §16 specifies `docs/screenshots/*.png` (dark/light/CLI). No automated screenshot generation exists. Manual screenshots are error-prone and drift from actual UI.

6. **No onboarding docs.** No "getting started in 5 minutes" guide. `docs/QUICKSTART.md` exists but covers build/test, not user onboarding. New users face: install → configure provider key → trust workspace → run first workflow with no guided path.

7. **No migration docs.** CLI redesign (§2 CLI_IDE_REDESIGN_PLAN) changes command shape from 60+ nested to chat-first flat. No migration guide for existing `arc` users. `arc-studio advanced <cmd>` passthrough is specified but undocumented.

### High (v0.1 quality)

8. **Daemon lifecycle tests are thin.** `test_web_daemon.py` exists but daemon state machine tests (start/stop/crash/recovery) are not comprehensive. §7.14 specifies daemon lifecycle with explicit state machine.

9. **No session persistence E2E test.** Sessions specified with ULID, JSONL journaling, auto-resume (§7.14.1). No E2E test creates session → exits → resumes → verifies state continuity.

10. **Eval batch mode not E2E tested.** `arc eval run --batch` exists with 9 eval tests, but no E2E flow tests: run workflow → save golden trace → modify → eval batch → report diff.

11. **HITL flow only unit-tested.** HITL persistence, single-use tokens, expiry tested in `test_hitl.py` (6 tests). No E2E test triggers HITL prompt in IDE → approves → verifies run continues.

12. **No docs link checker.** No CI job checks for broken links in markdown files. External links in docs will rot silently.

13. **Coverage gap in browser files.** `arc-widget.tsx`, components show 0% coverage. Source-pattern contract tests verify structure but not runtime behavior. Theia dependency makes jsdom testing impractical.

14. **No performance/smoke benchmark.** No test measures: browser app startup time, graph render latency with 50+ nodes, SSE event throughput, trace file listing with 1000+ runs.

### Medium (v0.2)

15. **No chaos/resilience tests.** Event broker reconnect, daemon crash mid-run, network partition during SSE stream — not tested. §15 specifies offline/error states but tests don't exercise them.

16. **No cross-platform E2E.** E2E runs on Ubuntu CI only. macOS/Windows Theia behavior (native modules, keybindings, file paths) untested.

17. **No visual regression tests.** UI changes (colours, layout, graph rendering) have no pixel-comparison baseline. §2-3 specify precise colour/typography but nothing enforces them.

18. **No OTLP/telemetry tests.** `test_otlp_exporter.py` exists but telemetry integration (trace export to external backend) is not E2E tested.

---

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **Add axe-core to Playwright E2E** | §14 specifies WCAG AA but zero a11y tests exist. Axe-core catches missing labels, contrast, keyboard traps in 5 minutes of setup. | v0.1 | Low — adds ~2s per E2E test, no runtime dependency | §14: Add "E2E axe-core audit passes on Chat, Runs, Config panels" |
| **Add manifest validation tests** | Appendix A specifies runtime manifest format with versioning. `/doctor` validates manifests. No tests exist. | v0.1 | Low — pure Python unit tests | Appendix A: Add "manifest validation test matrix: valid v1, unknown major, missing required fields, extra unknown fields" |
| **Add redaction E2E contract test** | §10.10 redaction contract spans CLI, IDE, SSE, graph. Unit tests cover redaction logic but not surface integration. | v0.1 | Medium — requires injecting secret-like values into stub run output | §10.10: Add "E2E redaction verification: inject test key into stub output, verify `«REDACTED»` in CLI, IDE, SSE, graph inspector" |
| **Add expect-based CLI REPL tests** | Chat REPL is interactive. Current CLI tests use `--json` non-interactive mode. REPL interaction (type prompt, receive streaming response, slash commands) is untested. | v0.1 | Medium — pexpect or similar needed, flaky on slow CI | §7.1: Add "CLI REPL test: launch → type message → verify response → `/status` → verify output → `/exit` → verify session saved" |
| **Automated screenshot generation via Playwright** | §16 specifies `docs/screenshots/*.png`. Manual screenshots drift. Playwright can capture screenshots as part of E2E run. | v0.1 | Low — add `page.screenshot()` calls to existing E2E tests | §16: Add "Screenshots generated by `pnpm test:e2e:screenshots` from Playwright captures. Stored in `docs/screenshots/`. Regenerated on UI changes." |
| **Write onboarding guide** | No guided path from install → first run. Support churn from confused users. | v0.1 | Low — doc-only | §16: Add `docs/onboarding.md` to deliverables. 5-step guide: install → configure key → trust workspace → detect workflow → run. |
| **Write CLI migration guide** | CLI redesign changes command shape. Existing `arc` users need migration path. | v0.1 | Low — doc-only | §10.8: Add `docs/cli-migration.md` to deliverables. Maps old `arc <cmd>` to new `arc-studio` or `arc-studio advanced <cmd>`. |
| **Add daemon state machine tests** | §7.14 specifies daemon lifecycle. Current daemon tests are thin. | v0.1 | Low — Python unit tests with mocked aiohttp server | §7.14: Add "Daemon state machine test: start → healthy → crash → restart → recover orphan runs" |
| **Add session persistence E2E test** | Sessions specified with ULID, journaling, auto-resume. Not E2E tested. | v0.1 | Medium — requires CLI REPL + file system verification | §7.14.1: Add "E2E session test: create session → exit → `arc-studio -c` → verify transcript, runtime, mode restored" |
| **Add docs link checker to CI** | Broken links in docs erode trust. No CI check exists. | v0.1 | Low — `markdown-link-check` or similar, 1 minute CI addition | RELEASE_CHECKLIST: Add "Item 14: Docs link checker passes on `docs/*.md`" |
| **Add HITL E2E flow test** | HITL is a core differentiator. Only unit-tested. | v0.2 | Medium — requires stub adapter that triggers HITL prompt | §9 Card component: Add "E2E HITL test: stub run triggers HITL → IDE shows approval card → approve → run completes" |
| **Add eval batch E2E flow** | Eval system exists but not E2E tested end-to-end. | v0.2 | Medium — requires golden trace fixture + workflow modification | P4 eval: Add "E2E eval test: run → save golden → modify prompt → eval batch → verify report shows diff" |
| **Add visual regression via Playwright screenshots** | §2-3 specify precise colours/typography. No enforcement. | v0.2 | Medium — pixel comparison infrastructure, flaky on cross-platform | §2: Add "Visual regression: Playwright screenshot comparison against baseline for Chat, Graph, Runs panels" |
| **Add chaos/resilience tests** | §15 specifies error/offline states. Not exercised in tests. | v0.2 | Medium — requires daemon kill, network partition simulation | §15: Add "Resilience test matrix: daemon crash mid-run, SSE disconnect/reconnect, network timeout" |
| **Add performance smoke benchmarks** | No performance baselines exist. Graph with 50+ nodes, 1000+ runs listing untested. | v0.3 | Low — timing assertions in E2E tests | §11.4: Add "Performance: graph render < 500ms for 50 nodes, run list < 1s for 1000 runs" |
| **Add cross-platform E2E matrix** | CI runs Ubuntu only. macOS/Windows untested. | v0.3 | Medium — CI matrix expansion, 3x CI minutes | `.github/workflows/e2e.yml`: Add `strategy.matrix.os: [ubuntu-latest, macos-latest, windows-latest]` |

---

## Recommended Decisions

### Lock for v0.1

1. **Keep Jest + pytest.** Do not introduce new test frameworks. Source-pattern contract tests for UI are acceptable given Theia runtime dependency. Do not attempt jsdom-based Theia testing.

2. **Add axe-core to existing Playwright E2E.** No new test runner. Add `axe-core` accessibility audits to the 12 existing smoke tests. One `expect(await axe(page)).toHaveNoViolations()` per test.

3. **Automate screenshots via Playwright.** Add a `pnpm test:e2e:screenshots` script that runs E2E tests with `page.screenshot()` captures at key points (chat panel, runs list, graph, config). Output to `docs/screenshots/`. Commit screenshots to repo.

4. **CLI REPL testing via pexpect (Python).** Use `pexpect` for interactive CLI tests, not a Node.js PTY library. Python is the canonical CLI runtime. Gate REPL tests behind `ARC_E2E_CLI=1` to avoid CI flakiness.

5. **Manifest validation tests are Python unit tests.** Runtime manifests are YAML parsed by Python. Add tests in `python/tests/` for manifest loading, version validation, required fields, and `/doctor` integration.

6. **Redaction E2E: inject fake key into stub output.** Modify `swarmgraph-stub.sh` to emit a line containing a fake API key pattern. E2E test verifies `«REDACTED»` appears in IDE event stream detail (already partially tested at line 185 of `arc-smoke.spec.ts`).

7. **Onboarding guide is a single markdown file.** `docs/onboarding.md`, 5 steps, each with expected output. No screenshots required for v0.1 (use ASCII output examples). Screenshots added in v0.2 when UI stabilizes.

8. **CLI migration guide is a mapping table.** `docs/cli-migration.md`, single table: old command → new command → notes. Auto-generate from CLI help text where possible.

9. **Docs link checker: use `markdown-link-check`.** Add to `node.yml` CI workflow. Check only `docs/*.md` and `README.md`. Exclude `docs/archive/` (historical links may be intentionally stale).

10. **Daemon state machine tests: mock aiohttp.** Use `aiohttp.test_utils` for daemon lifecycle tests. Do not start real daemon in unit tests.

### Defer to v0.2

11. **Visual regression testing.** Defer until UI colours/layout stabilize post-redesign. Playwright screenshot comparison is useful but premature while §2-3 spec is still being implemented.

12. **Chaos/resilience tests.** Defer until daemon state machine and event broker are stable. Testing reconnect semantics requires stable SSE infrastructure.

13. **Cross-platform E2E matrix.** Defer until v0.1 release is stable on Ubuntu. macOS is the primary developer platform but CI cost/complexity is not justified for alpha.

14. **Performance benchmarks.** Defer until real user workload patterns are observed. Synthetic benchmarks without user data are misleading.

### Reject

15. **Do not add Cypress.** Playwright is already configured and working. Adding a second E2E framework duplicates infrastructure.

16. **Do not add coverage enforcement gate.** Coverage is 61.84% (target 70%). Enforcing a coverage gate now would block PRs without improving quality. Track coverage trend, don't gate.

17. **Do not add snapshot testing for React components.** Source-pattern contract tests are sufficient for Theia extension components. Snapshot tests would be brittle and Theia-version-dependent.

18. **Do not test terminal UI rendering pixel-perfectly.** Terminal rendering depends on terminal emulator, font, width. Test output content (JSON envelopes, text patterns), not pixel layout.

19. **Do not add mutation testing.** Mutation testing (e.g., mutmut, Stryker) is valuable but high CI cost. Revisit after coverage reaches 70%.

---

## Specific Spec Edits

### ARC_STUDIO_UX_SPEC.md

- **§14 (Accessibility):** Add paragraph: "Accessibility verification: E2E tests include axe-core audit on Chat, Runs, Workflows, and Config panels. Keyboard-only flow tested: launch → Tab to chat → type → Tab to mode → cycle → Enter to approve → exit. Screen reader live regions tested with NVDA/JAWS on Windows, VoiceOver on macOS. Colour-blind simulation tested with simulator tools for all state indicators."

- **§16 (Assets and deliverables):** Add rows:
  - `Onboarding guide | Markdown | 5-step getting started | docs/onboarding.md`
  - `CLI migration guide | Markdown | Old-to-new command mapping | docs/cli-migration.md`
  - `Screenshot generation script | Shell | Playwright-based capture | scripts/generate-screenshots.sh`

- **§10.10 (Redaction contract):** Add paragraph: "Redaction E2E verification: stub run output includes test patterns (`sk-test-00000000000000000000000000000000`, `Bearer test-token-12345`, `password=hunter2`). E2E test verifies `«REDACTED»` appears in: CLI stdout, IDE chat transcript, SSE event detail, graph node inspector, run summary, error cards. Failure to redact any pattern is a P0 release blocker."

- **§7.1 (CLI Chat):** Add paragraph: "CLI REPL testing: Interactive chat REPL tested via pexpect. Test matrix: (1) launch → welcome banner, (2) type message → agent response, (3) `/status` → status output, (4) `/runtime swarmgraph` → runtime switched, (5) `/exit` → session saved. Gate behind `ARC_E2E_CLI=1` env var to avoid CI flakiness."

- **§7.14.1 (Session Management):** Add paragraph: "Session persistence E2E test: Create session with runtime/model/mode → exit → `arc-studio -c` → verify session restored with same runtime, model, mode, and last 3 transcript messages. Session file exists at `~/.local/share/arc-studio/sessions/<ulid>/`."

- **Appendix A (Runtime Manifest):** Add paragraph: "Manifest validation tests: (1) valid v1 manifest loads, (2) unknown major version rejected with error, (3) missing required field produces validation error listing field name, (4) extra unknown fields ignored (forward compatibility), (5) `/doctor` reports manifest validation status."

### CLI_IDE_REDESIGN_PLAN.md

- **§6 (Testing Plan):** Add section "6.8 Accessibility Tests" with table:
  | Test | Description |
  |------|-------------|
  | axe-core audit | No WCAG AA violations in Chat, Runs, Workflows, Config panels |
  | Keyboard-only flow | All actions achievable without mouse |
  | Screen reader labels | All interactive elements have accessible names |
  | Colour contrast | All text meets 4.5:1 contrast ratio |
  | Focus management | Focus moves logically, no focus traps |

- **§6 (Testing Plan):** Add section "6.9 Documentation Tests" with table:
  | Test | Description |
  |------|-------------|
  | Link checker | No broken links in `docs/*.md` |
  | Banned claims | `check-banned-claims.sh` passes on release docs |
  | CLI help consistency | `arc-studio --help` matches docs |
  | Onboarding guide accuracy | Each step produces expected output |

### RELEASE_CHECKLIST.md

- Add **Item 14: Accessibility audit passes**
  ```bash
  pnpm test:e2e  # axe-core audits included
  # Expect: no WCAG AA violations in Chat, Runs, Workflows, Config panels
  ```

- Add **Item 15: Onboarding guide verified**
  ```bash
  # Follow docs/onboarding.md step by step on fresh machine
  # Expect: all 5 steps produce expected output
  ```

- Add **Item 16: Docs link checker passes**
  ```bash
  npx markdown-link-check README.md docs/*.md --skip 'docs/archive/'
  # Expect: all links valid (or explicitly ignored)
  ```

---

## Acceptance Criteria

### v0.1 Must-Have

- [ ] axe-core audit passes on all 4 IDE panels (Chat, Runs, Workflows, Config) in E2E tests
- [ ] Manifest validation tests cover: valid v1, unknown major, missing fields, extra fields, `/doctor` integration
- [ ] Redaction E2E test verifies `«REDACTED»` in CLI, IDE, SSE, graph inspector for injected fake secrets
- [ ] Automated screenshot generation script produces `docs/screenshots/*.png` for dark theme
- [ ] `docs/onboarding.md` exists with 5-step guide, verified on fresh environment
- [ ] `docs/cli-migration.md` exists with old→new command mapping table
- [ ] Daemon state machine tests cover: start, healthy, crash, restart, orphan recovery
- [ ] Docs link checker passes on `docs/*.md` and `README.md` (excluding `docs/archive/`)
- [ ] All existing tests continue to pass: 550 Python, 239 TypeScript, 12 E2E
- [ ] RELEASE_CHECKLIST.md updated with items 14-16

### v0.1 Should-Have

- [ ] CLI REPL pexpect tests for basic chat interaction (gated behind `ARC_E2E_CLI=1`)
- [ ] Session persistence E2E test (create → exit → resume → verify)
- [ ] Eval batch E2E flow test (run → save golden → modify → eval → report)
- [ ] HITL E2E flow test (stub triggers HITL → IDE shows card → approve → run completes)

### v0.2 Should-Have

- [ ] Visual regression tests via Playwright screenshot comparison
- [ ] Chaos/resilience tests (daemon crash, SSE reconnect, network timeout)
- [ ] Cross-platform E2E matrix (Ubuntu, macOS, Windows)
- [ ] Performance benchmarks (graph render, run list, SSE throughput)

### v0.3 Could-Have

- [ ] Mutation testing on core modules (storage, security, isolation)
- [ ] Fuzz testing for manifest parsing and protocol deserialization
- [ ] Load testing for event broker (concurrent SSE clients, high event rate)

---

## Reject / Do Not Build

| Idea | Reason |
|---|---|
| **Cypress E2E framework** | Playwright already configured and working. Second E2E framework is infrastructure duplication. |
| **Coverage enforcement gate** | 61.84% coverage, target 70%. Gating now blocks PRs without quality improvement. Track trend, don't gate. |
| **React component snapshot tests** | Source-pattern contract tests sufficient for Theia components. Snapshots would be brittle and Theia-version-dependent. |
| **Pixel-perfect terminal UI tests** | Terminal rendering depends on emulator, font, width. Test content (JSON, text), not pixels. |
| **Mutation testing (mutmut/Stryker)** | High CI cost, low ROI at current coverage. Revisit after 70% coverage. |
| **Full jsdom-based Theia testing** | Theia runtime cannot be adequately mocked in jsdom. Source-pattern contracts + Playwright E2E is the correct approach. |
| **Automated screenshot comparison on every PR** | Too flaky for CI. Run screenshot comparison nightly or manually before release. |
| **Real provider call E2E tests in CI** | Paid calls in CI are unacceptable cost/risk. Keep real-runtime tests opt-in (`ARC_REAL_RUNTIME_SMOKE=1`) and nightly/manual. |
| **Test coverage dashboard/monitoring** | Over-engineering for alpha. Jest/pytest coverage reports are sufficient. |
| **Separate test documentation site** | `docs/TESTING.md` is sufficient for alpha. No Docusaurus/GitBook needed. |
| **E2E tests for every adapter** | 5+ adapters × E2E = combinatorial explosion. Test SwarmGraph (default) + one adoption adapter in E2E. Other adapters covered by unit/conformance tests. |
| **Accessibility testing on CLI TUI** | CLI TUI accessibility is handled by the terminal emulator and screen reader. Test output content (labels, structure), not TUI rendering. |
