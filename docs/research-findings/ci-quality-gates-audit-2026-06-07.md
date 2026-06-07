# ARC Studio CI Guardrails, TestBench & Quality Gates Audit — 2026-06-07

> **Scope:** CI guardrails, TestBench, evals, local checks, private mode, policy verification, audit verification, release quality gates  
> **Source:** Synthesized from prior sessions + direct reads of cli/ci.py, docs/release/checklist.md, scripts/check-banned-claims.sh

---

## 1. Quality Gate Architecture Map

```
┌─────────────────────────────────────────────────────────────────────┐
│               ARC STUDIO QUALITY GATE ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 1 — BANNED CLAIMS CHECKER (scripts/check-banned-claims.sh)   │
│                                                                      │
│  23 banned phrases with suggested replacements                      │
│  Allowlisted: code blocks, ADR sections, "Banned Claims" headings   │
│  Skipped: docs/archive/, docs/adr/ (historical/planning only)       │
│  Table rows: always skipped (reference material)                    │
│  --fix: shows suggestions; without: shows file:line                 │
│  Exit: 0=clean, 1=violations found                                 │
│  CI gate: ✅ run on key docs in release_check.sh                    │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 2 — CI CHECK (arc ci check --json --private)                 │
│                                                                      │
│  4 checks, all ADVISORY (advisory: true in output):                 │
│  1. sandbox_audit: lists denied commands from sandbox.audit.jsonl   │
│     → status: pass (0 denied) / fail (>0 denied)                   │
│  2. policy: validates sandbox policy config, lists policy names      │
│     → status: pass / fail (validation errors present)               │
│  3. eval: counts goldens/.arc/goldens, .arc/eval, .arc/evals dirs   │
│     → status: pass (files found) / skip (no dirs)                   │
│  4. receipt: counts .arc/receipts/{.json,.jsonl,.md}                │
│     → status: pass (files found) / skip (no dir)                   │
│  overall: fail if any check fails; pass otherwise                   │
│  private: true always (no network calls)                            │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 3 — CI MATRIX (arc ci matrix)                                │
│                                                                      │
│  Detects local CI/test commands (same 17 scanners as testbench)     │
│  + includes GitHub Actions workflow detection (--include-workflows) │
│  Returns: CiMatrix { jobs: CiJob[], workflow_steps: [] }            │
│  Each CiJob: { id, command, cwd, runnable, blocked_reason }         │
│  Does NOT execute — detection only                                   │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 4 — CI RUN (arc ci run --job <id> / -- <cmd>)                │
│                                                                      │
│  Sandbox-policy-gated execution:                                    │
│  1. decide(command, policy) → SandboxDecision                       │
│  2. approve_decision_with_token() if --approval-token               │
│  3. validate_command_paths()                                        │
│  4. Denied → exit 3, audit event persisted                         │
│  5. Allowed → stream_subprocess_events() → JSONL stream or bulk    │
│  6. CiRunResult persisted to .arc/ci/{run_id}.json                 │
│  Exit codes: 0=pass, 3=denied, 124=timeout, 130=cancelled          │
│  Default policy: local-safe                                         │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 5 — CI SUMMARY (arc ci summary --format markdown|json)       │
│                                                                      │
│  Advisory PR summary from local audit/policy/eval/receipt data      │
│  No AI judgment claims in output (no_ai_judgment: true field)       │
│  Markdown comments: "Advisory Only; No AI Judgment Claims"          │
│  Deterministic, offline, no uploads                                 │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 6 — CI VERIFY-AUDIT (arc ci verify-audit --strict)           │
│                                                                      │
│  Verifies sandbox audit chain integrity via verify_sandbox_audit()  │
│  --strict: exit 1 if chain invalid or missing; otherwise exit 0     │
│  Without --strict: advisory (exit 0 even if failed)                 │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 7 — RELEASE GATE (scripts/release_check.sh)                  │
│                                                                      │
│  Gates: python:pytest, python:ruff, ts:test, ts:coverage,           │
│  pnpm:build, pnpm:typecheck, banned-claims, spec:citations,         │
│  policy:import-guards, policy:protocol-coverage, git:clean          │
│  3-day green window on main required before external tag            │
│  5609 tests collected, 5537 passed, 42 skipped, 7 xfailed, 0 failed │
└─────────────────────────────────────────────────────────────────────┘
```

### What `arc ci check --json --private` verifies

1. **sandbox_audit**: Reads `~/.arc/audit/sandbox.audit.jsonl` (last 100 events). Reports denied commands with classification + reason. Advisory: `fail` means denied events exist, not that any action is blocked.
2. **policy**: Validates sandbox policy config files. Lists active policy names.
3. **eval**: Scans for `.arc/goldens/`, `.arc/eval/`, `.arc/evals/` directories. Status `skip` if absent — no requirement to have evals.
4. **receipt**: Scans `.arc/receipts/`. Status `skip` if absent.

**All checks are advisory** (`advisory: true` in output). `arc ci check` never blocks a workflow — it reports status for human review.

**Private mode**: `--private` is default (`True`). The entire `ci_check()` function makes no network calls. Every data source is local filesystem only.

---

## 2. CLI / IDE Parity Matrix

| Feature | CLI | IDE (CiGuardrailsTab) | Gap |
|---|---|---|---|
| CI check status | ✅ `arc ci check --json` | ✅ `getCiCheckStatus()` | Minor: IDE shows pass/fail per check; CLI adds `denied_commands[]` detail |
| CI matrix detect | ✅ `arc ci matrix` | ❌ absent | **Full gap** — no IDE matrix view |
| CI run (sandbox-gated) | ✅ `arc ci run` | ❌ absent | **Full gap** — no Run button |
| CI summary (markdown) | ✅ `arc ci summary` | ❌ absent | **Full gap** |
| CI verify-audit | ✅ `arc ci verify-audit --strict` | ❌ absent | **Full gap** |
| Banned claims check | ✅ `scripts/check-banned-claims.sh` | ❌ absent | — |
| TestBench detect | ✅ `arc testbench detect` | ✅ TestBenchTab | Parity: identical detection |
| TestBench run | ✅ `arc testbench run --policy local-safe` | ❌ **no Run button** | **Critical gap** |
| TestBench streaming output | ✅ `--stream-json` | ❌ absent | — |
| Eval run | ✅ `arc eval run --batch` | ❌ absent | **Full gap** |
| Policy recommend-apply | ✅ `arc eval recommend-apply --dry-run` | ❌ absent | **Full gap** |
| Audit verify | ✅ `arc audit verify <run-id>` | ✅ AssuranceTab verify button | Parity: AssuranceTab covers run-level; `arc ci verify-audit` covers sandbox chain |
| Release checklist | ✅ Manual (`docs/release/checklist.md`) | ❌ absent | — |

**TestBenchTab is the most visible parity gap**: it shows detected tests but has no Run button. Users who discover the panel naturally expect to run the tests they see.

---

## 3. Release Verification Matrix

### Blocking checks (release gating)

| Check | Tool | Passes? | Notes |
|---|---|---|---|
| `pnpm install --frozen-lockfile` | pnpm | ✅ | Lockfile must not change |
| `pnpm build` | pnpm | ✅ | TypeScript + bundle |
| `arc --help` exits 0 | CLI | ✅ | |
| `arc runtimes --capabilities --json` honest output | CLI | ✅ | No false provider-backed claims |
| Banned claims clean on key docs | `check-banned-claims.sh` | ✅ | 23 banned phrases; runs on roadmap/phases/AGENTS/README/checklist |
| Python test suite: 0 failed | `uv run pytest -q` | ✅ | 5537 passed, 42 skipped, 7 xfailed |
| Extension test suite passes | `pnpm --filter arc-extension test` | ✅ | |
| No P0/P1 security issues open | GitHub issues | ✅ | |
| `.env` history scrubbed | git | ✅ | Done 2026-05-18 |
| Alpha/gated labels present | Manual review | ✅ | |

### Advisory checks (should be done)

| Check | Tool | Status | Notes |
|---|---|---|---|
| Browser app starts, loads ARC widget | Smoke test | ✅ | `pnpm start:browser:arc` + curl |
| 3-day CI green window on main | GitHub Actions | ⏳ | Required before external tag |
| All CI workflows green | `python`, `node`, `ARC Roadmap Gate` | ✅ | `real-runtime-smoke` is opt-in, non-gating |

### Private mode verification

`arc ci check --private` is the default and only mode. The `--private` flag is `default=True` — there is no `--no-private` to enable uploads. All data sources are:
- `~/.arc/audit/sandbox.audit.jsonl` (local)
- Sandbox policy config files (local)
- `.arc/goldens/`, `.arc/eval/`, `.arc/evals/` (local)
- `.arc/receipts/` (local)

**Confirmed: private mode uploads nothing.** There is no HTTP call anywhere in `ci_check()`.

---

## 4. UX Gap Analysis

### CiGuardrailsTab (IDE)

| Gap | Detail |
|---|---|
| Read-only display only | Shows pass/fail per check; no Run CI Job button |
| No `denied_commands[]` shown | CLI returns denied command details; IDE shows only count |
| No audit chain path | `arc ci verify-audit` output includes chain path; IDE doesn't |
| No trigger CI run | Most impactful gap: users can see CI status but can't run CI |
| No refresh interval | Manual Refresh button only; no auto-poll |
| No `advisory: true` label | CLI output has `advisory: true`; IDE doesn't communicate this to users |
| No eval file listing | Eval check shows file count but not which files |

### TestBenchTab (IDE)

| Gap | Detail |
|---|---|
| **No Run button** | Most critical gap — detect-only UX creates false affordance |
| No streaming output | Even if Run were added, no streaming output surface exists |
| No policy selector | Users can't choose sandbox policy before running |
| No cancellation | No way to stop a running test command |
| Linters mixed with test runners | ruff, mypy, pylint, flake8 appear alongside pytest/jest with no category distinction |
| No confidence filter | All entries shown at equal prominence regardless of confidence: "high"/"medium"/"explicit" |

### Evals (no IDE surface at all)

`arc eval run`, `arc eval recommend-apply`, `arc eval compare`, `arc eval report` — all CLI-only. No IDE tab or panel. The eval harness is entirely invisible from the IDE.

---

## 5. Test Gap Analysis

### Confirmed test coverage

| Area | Test file | Quality |
|---|---|---|
| `arc ci check` | `tests/cli/test_ci.py` | Covers sandbox_audit/policy/eval/receipt sections |
| `arc ci run` deny path | `tests/cli/test_ci.py` | exit 3 on sandbox deny |
| `arc ci run` allow path | `tests/cli/test_ci.py` | exit from subprocess |
| TestBench detect | `tests/cli/test_testbench.py` | 17 config scanners + 4 run paths |
| Eval consensus | `tests/evals/test_consensus_eval.py` | 5 protocols, deterministic |
| Eval golden | `tests/evals/test_golden.py` | score formula, status match |
| Eval early-stop | `tests/evals/test_consensus_earlystop.py` | mathematical certainty |
| Eval artifacts | `tests/evals/test_eval_artifacts.py` | CLI create/evaluate/show |
| Policy recommend | `tests/evals/test_apply.py` | apply_to_profile, YAML validation |
| Eval trending | `tests/evals/test_phase58_eval_trending.py` | delta_from_baseline |

### Gaps

| Gap | Severity | Detail |
|---|---|---|
| No test for `arc ci check --private` uploads nothing | **Medium** | Verify no HTTP call made; currently tested by structure review only |
| No test for `arc ci verify-audit --strict` exit code | **Medium** | exit 1 on invalid chain; exit 0 without `--strict` |
| TestBench: no `--stream-json` path tested | **Medium** | Only bulk mode tested; JSONL streaming path untested |
| TestBench: no `--approval-token` path tested | **Low** | Token approval path untested |
| `arc ci summary --format markdown` not tested | **Low** | Only implicit coverage through ci_check tests |
| Eval `quality_score` synthetic | **Low (known)** | quality_score is hard-coded formula, not real quality; `latency_ms == duration_ms` redundancy |
| Banned claims: no test that script itself passes on key docs in CI | **Low** | `release_check.sh` calls it but no unit test |
| `arc eval recommend-apply` profile mutation safety | **Medium** | `apply_to_profile()` writes YAML; no test for concurrent write safety |

---

## 6. Improved Implementation Prompt

**Target:** Add a Run button to TestBenchTab with safe policy routing — the single highest-value missing feature.

```
# Quality Gates Next Slice: TestBenchTab Run Button + CiGuardrailsTab Advisory Label

## Context

ARC Studio v0.8-r-ux2. Two UX gaps:

1. TestBenchTab shows detected test commands but has no Run button.
   The tab presents a list of runnable commands (pytest, jest, vitest,
   Makefile test, etc.) with no way to execute them. Users must drop
   to the CLI: arc testbench run --policy local-safe -- <command>.
   This is a false affordance — the tab implies runability it doesn't
   provide.

2. CiGuardrailsTab shows pass/fail per check but does not communicate
   that all checks are advisory (advisory: true in CLI output).
   Users may interpret a "fail" sandbox_audit as a blocking issue when
   it is informational only.

## Scope

### Slice A: TestBenchTab Run button

File: packages/arc-extension/src/browser/tabs/TestBenchTab.tsx

Add a Run button to each detected test entry that calls
`arcService.runTestbenchCommand(command, policy)`:

```tsx
interface TestbenchRunOptions {
    command: string[];
    policy?: 'local-safe' | 'local-paid';
    streamJson?: boolean;
}

// In each detection card:
<button
    className="arc-testbench__run-btn"
    onClick={() => this.runCommand(entry)}
    disabled={this.state.running === entry.command.join(' ')}
    aria-label={`Run: ${entry.command.join(' ')}`}
>
    {this.state.running === entry.command.join(' ') ? 'Running…' : 'Run'}
</button>
```

Add to arc-protocol.ts:
```typescript
runTestbenchCommand(options: TestbenchRunOptions): Promise<CiRunResult>;
```

Add to ArcBackendService:
```typescript
async runTestbenchCommand(options: TestbenchRunOptions): Promise<CiRunResult> {
    const args = ['testbench', 'run',
        '--policy', options.policy ?? 'local-safe',
        '--json', '--',
        ...options.command
    ];
    const output = await execFileAsync('arc', args, {
        timeout: 120000,
        encoding: 'utf-8',
        windowsHide: true,
        env: buildArcCliEnv(),
    });
    const parsed = JSON.parse(output);
    if (parsed.ok && parsed.data) return parsed.data;
    throw new ArcError(ArcErrorCode.RUN_FAILED, parsed?.error?.message || 'Test run failed');
}
```

Key constraints:
- Default policy: `local-safe` (deny network, destructive, privileged)
- Show exit code prominently (0 = pass, non-zero = fail, 3 = sandbox denied)
- Show stdout/stderr in an expandable section
- Add a "Stop" button that is a placeholder (CLI doesn't support cancel-in-flight yet)
- Show "Sandbox policy: local-safe" label near the Run button

State additions to TestBenchTab:
```typescript
interface State {
    running: string | null;
    lastResult: CiRunResult | null;
    runError: string | null;
}
```

CSS additions:
```css
.arc-testbench__run-btn {
    padding: 4px 12px;
    border: 1px solid var(--arc-color-primary);
    color: var(--arc-color-primary);
    background: transparent;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
}
.arc-testbench__run-btn:disabled {
    opacity: 0.5; cursor: not-allowed;
}
.arc-testbench__result {
    margin-top: 8px;
    padding: 8px;
    border-radius: 4px;
    font-size: 11px;
    font-family: var(--arc-font-family-mono);
}
.arc-testbench__result--pass { border-left: 3px solid var(--arc-color-success); }
.arc-testbench__result--fail { border-left: 3px solid var(--arc-color-error); }
.arc-testbench__result--denied { border-left: 3px solid var(--arc-color-warning); }
```

### Slice B: CiGuardrailsTab advisory label

File: packages/arc-extension/src/browser/tabs/CiGuardrailsTab.tsx

Add "Advisory only" badge near the header:

```tsx
<div className="arc-ci-guardrails__header">
    <h3>CI Guardrails</h3>
    <span
        className="arc-ci-guardrails__advisory-badge"
        aria-label="All checks are advisory — they do not block execution"
        title="All CI checks are informational only. A 'fail' status indicates a finding, not a blocked execution."
    >
        Advisory
    </span>
    <button onClick={refresh}>Refresh</button>
</div>
```

CSS:
```css
.arc-ci-guardrails__advisory-badge {
    padding: 2px 8px;
    border: 1px solid var(--arc-color-muted, #888);
    border-radius: 999px;
    font-size: 10px;
    color: var(--arc-color-muted, #888);
    text-transform: uppercase;
    font-weight: 600;
}
```

Also show `denied_commands[]` from the sandbox_audit check when status is `fail`:

```tsx
{check.key === 'sandbox_audit' && check.status === 'fail' && (
    <div className="arc-ci-guardrails__denied-list">
        <strong>Denied commands ({check.deniedCount}):</strong>
        {(check.deniedCommands || []).slice(0, 5).map((dc, i) => (
            <code key={i} className="arc-ci-guardrails__denied-cmd">
                {dc.command?.join(' ')} — {dc.classification}
            </code>
        ))}
    </div>
)}
```

### Slice C: Linters/runners category distinction in TestBenchTab

File: packages/arc-extension/src/browser/tabs/TestBenchTab.tsx

Add a `type` label to each detection card:

```tsx
const RUNNER_TYPES: Record<string, 'test' | 'lint'> = {
    pytest: 'test', tox: 'test', nox: 'test', jest: 'test',
    vitest: 'test', playwright: 'test', cypress: 'test', mocha: 'test',
    ava: 'test', make: 'test',
    ruff: 'lint', mypy: 'lint', pylint: 'lint', flake8: 'lint',
};

// In each card header:
<span className={`arc-testbench__type-badge arc-testbench__type-badge--${RUNNER_TYPES[entry.runner] ?? 'test'}`}>
    {RUNNER_TYPES[entry.runner] === 'lint' ? 'Linter' : 'Test Runner'}
</span>
```

This makes the linter/runner distinction visible without hiding linters entirely.

## Do NOT do in this slice

- Eval IDE surface (separate eval slice)
- Release checklist dashboard
- Fork/replay wizard
- Evidence provenance graph

## Tests to add

```typescript
// In studio-tabs.contract.test.ts, TestBenchTab section:
it('has Run button per detected command', () => {
    expect(source).toMatch(/Run/);
    expect(source).toMatch(/aria-label.*Run:/);
    expect(source).toMatch(/local-safe/); // policy shown near button
});

it('shows advisory label in CiGuardrailsTab', () => {
    expect(source).toMatch(/Advisory/i);
    expect(source).toMatch(/advisory-badge/);
    expect(source).toMatch(/informational|advisory/i); // in tooltip
});
```

## Verification

```bash
pnpm typecheck && pnpm build
pnpm --filter arc-extension test
```
```

---

## Appendix: Eval harness properties (confirmed deterministic)

| Property | Status | Evidence |
|---|---|---|
| consensus eval deterministic | ✅ | "All tests are deterministic — no random, no LLM, no network" in module docstring |
| quality_score synthetic | ⚠️ Known | Hard-coded formula, not real quality measurement |
| latency_ms == duration_ms | ⚠️ Known | Redundant field, identical value |
| early-stop logic never wired to dispatch | ✅ Documented | `can_stop_early()` is standalone utility; never called in worker loop |
| policy recommend-apply | ✅ | `apply_to_profile()` writes YAML with `--dry-run` protection |
| golden fixture orphaned | ⚠️ | `tests/integration/fixtures/swarmgraph.golden.jsonl` not read by any test |

## Appendix: `check-banned-claims.sh` banned phrases

23 banned phrases including: SwarmGraph adoption claims without proof, "live streaming" (vs SSE trace replay), "signed audit trails/chain" (unless HMAC is wired), "LM Arena live mode", "Production ready", "multi-user", "tenant-isolated", "100% stub" (for Arena), adapter adoption claims without test proof. Allowlisted: code blocks, `docs/archive/`, `docs/adr/`, sections headed "Banned Claims/Fiction List/Safe language".
