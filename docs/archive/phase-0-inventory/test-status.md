# Phase 0 — Test Status Snapshot

Status: DRAFT (Phase 0 inventory, non-destructive)
Scope: full test inventory + current pass/fail/skip counts.
Output: baseline that Phase 7 release gate compares against.

## How to fill this file

1. Run:
   - `cd python && uv run pytest --collect-only -q > /tmp/py-collect.txt`
   - `cd python && uv run pytest -q > /tmp/py-run.txt` (capture exit code)
   - `pnpm --filter arc-extension test --listTests > /tmp/ts-collect.txt`
   - `pnpm --filter arc-extension test > /tmp/ts-run.txt` (capture exit code)
2. Paste summary counts below (not full output).
3. Classify every test file by taxonomy.

## Taxonomy (locked)

| Category | Definition | Allowed in default CI? |
|---|---|---|
| unit | pure function, no I/O | yes |
| contract | schema/envelope snapshot | yes |
| integration | subprocess/daemon, no network | yes |
| smoke | clean-checkout bootstrap, no paid calls | yes |
| paid | explicit opt-in, real provider calls | NO (opt-in only) |

## Python snapshot

Date taken: 2026-05-19 (latest run)
Command: `cd python && uv run pytest -q`
Exit code: 1

| Counter | Value |
|---|---|
| Collected | 1010 |
| Passed | 990 |
| Failed | 1 |
| Skipped | 19 |
| Errors | 0 |
| xfail | 0 |
| xpass | 0 |

### Python test file classification

| File | Category | Touches network? | Touches ~/.arc? | Notes |
|---|---|---|---|---|
| tests/test_cli_studio.py | integration | no | no (uses tmp_path/monkeypatch) | legacy cli_studio REPL tests |
| tests/test_cli_repl.py | integration | no | no (uses tmp_path) | cli_repl/ chat REPL tests |
| tests/swarmgraph/test_runner.py | unit | no | no | part of 57-test SwarmGraph suite |
| tests/swarmgraph/test_*.py | unit | no | no | SwarmGraph native runtime tests (57 total) |
| tests/adapters/swarmgraph/test_security.py | unit | no | no | adapter security tests |
| tests/test_swarmgraph_topology.py | unit | no | no | topology event tests |
| tests/test_cli_providers.py | integration | dry-run: no; live smoke: yes (1 test, gated) | no (tmp quota/config) | 1 failing test attempts live provider call |
| tests/test_providers.py | integration | dry-run: no (mocked); live: mocked | no (tmp_path) | gated provider action tests |
| tests/test_trust_resolver.py | integration | no | no (tmp_path for DB) | workspace trust resolver tests |
| tests/test_runtime_router.py | integration | no | no (tmp traces dir) | runtime resolution tests |
| tests/test_cli_runs.py | integration | no | no (tmp traces dir) | CLI runs commands tests |
| tests/test_adoption_protocol.py | unit/integration | no (mocked) | no (tmp_path) | adoption protocol tests |
| tests/test_budget_enforcer.py | unit | no | no | BudgetVector enforcer tests (130 lines) |
| tests/test_adapter_status.py | unit | no | no | adapter status tracking tests (165 lines) |
| tests/web/test_*.py | integration/web | no (offline SSE stubs) | no | web/SSE endpoint tests |
| tests/test_cli_doctor.py | integration | network check: yes (reachable); env: no | no (tmp traces) | doctor CLI tests (76 tests total across companions) |
| tests/test_cli_discoverability.py | integration | no | no | CLI discoverability tests |

### Failing / skipped tests

| File::test | Category | Reason | Phase to fix |
|---|---|---|---|
| `tests/test_cli_providers.py::test_providers_action_all_gates_pass_closed_smoke` | integration | live provider smoke attempted with invalid `sk-test` OpenAI-compatible key and returned HTTP 401; gated behind `ARC_ALLOW_LIVE_PROVIDER_TESTS` env | 0/next fix: skip in CI default run; preserve as opt-in smoke |
| `tests/test_trust_resolver.py::TestTrustCLI::test_untrust` | integration | previously reported `ExceptionGroup`/socket `ResourceWarning`; passed in 2026-05-19 run | resolved/monitor |

## TypeScript snapshot

Date taken: 2026-05-19 (latest run)
Command: `pnpm --filter arc-extension test`
Exit code: 0

| Counter | Value |
|---|---|
| Test files | 16 passed / 16 total |
| Tests | 762 passed / 762 total |
| Passed | 762 |
| Failed | 0 |
| Skipped | 0 |

### TS test file classification

| File (suite) | Category | Touches subprocess? | Notes |
|---|---|---|---|
| `src/node/__tests__/arc-service.integration.test.ts` | integration | yes (CLI spawn via Theia service) | 762 total tests across 16 suites |
| (remaining 15 suites are smaller helper/component tests) | unit/contract | no | component-level tests |

## Build status

| Command | Exit code | Date |
|---|---|---|---|
| `pnpm --filter @arc-studio/protocol build` | 0 | 2026-05-19 |
| `pnpm --filter arc-extension build` | 0 | 2026-05-19 |
| `bash scripts/check-pr.sh` | 0 | 2026-05-19 |
| `bash scripts/check-banned-claims.sh <files>` | 0 | 2026-05-19 |

## Verification Plan For This Patch

Requested commands after docs-only patch:

1. `git diff --stat`
2. `bash scripts/check-pr.sh`
3. `cd python && uv run pytest -q`
4. `pnpm --filter arc-extension test`

Counts above were updated from command output. Existing Python provider smoke failure is preserved instead of claiming green.

## Default-test-suite invariants (locked)

- No test in the default suite makes a real provider call.
- No test in the default suite writes to `~/.arc/sessions/` outside a tmp dir.
- No test in the default suite requires network egress.
- Any violation found above is recorded in the Failing / skipped table with Phase to fix.

## Acceptance for this file

- Counts filled for Python and TS.
- Every test file classified by taxonomy.
- Every failing/skipped test has a Phase to fix.
- Invariant violations explicitly listed (or "none found").
