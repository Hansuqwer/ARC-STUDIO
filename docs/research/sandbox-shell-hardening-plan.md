# Sandbox Shell-Escape Hardening — Verification & Coverage Plan (R-OPEN-SANDBOX)

**Status:** Executed 2026-06-06 | Prompt: `docs/prompts/sandbox-shell-hardening.md`

## Finding

The shell-escape hardening that `R-OPEN-SANDBOX` describes as open is **already
done** and was shipped during R-UX2. Verified against the live tree:

| Claim (stale roadmap) | Reality | Evidence |
|---|---|---|
| `subprocess.run(cmd, shell=True)` at `screen.py:271-291` bypasses sandbox | **REMOVED** | `grep "shell=True" src/` → only `allow_shell`/`requires_shell` config flags + a comment. Zero `subprocess(..., shell=True)`. |
| Shell escape not sandbox-aware | **Sandbox-gated** | `_handle_shell_escape` (screen.py:366-498): shlex.split → trust → `decide()` → approval → provider.execute(argv) → audit. |
| Fail-open on error | **Fail-closed** | `except Exception: _block(...)` around trust/policy/decision. |

## Secure pattern (research-grounded)

Python docs (`/python/cpython`) + real-world usage (vercel grep) both confirm the
implemented pattern: `shlex.split` → argv list → `subprocess` with `shell=False`.
`shell=True` is the only mode requiring manual `shlex.quote`; ARC does not use it.

## Branch coverage matrix

| Branch in `_handle_shell_escape` | Pre-existing test | This pass |
|---|---|---|
| read-only allowed → execute | ✅ | — |
| destructive denied | ✅ | — |
| untrusted workspace blocked | ✅ | — |
| network not silently run | ✅ | — |
| decide() raises → fail-closed | ✅ | — |
| allowed → argv (no shell) + audit | ✅ | — |
| **unparseable (shlex ValueError)** | ❌ | ✅ added |
| **empty command** | ❌ | ✅ added |
| **approval-required (distinct from denied)** | ❌ | ✅ added |
| **timeout (killed + kill_reason)** | ❌ | ✅ added |
| **provider.execute raises** | ❌ | ✅ added |
| **argv-oversized (ARGV_OVERSIZED)** | ❌ | ✅ added (decide-level) |

## Out of scope (verified safe)

`screen.py:610` `subprocess.run([pager, path])` — `/export` opens a tempfile in
`$PAGER`. List-argv, no shell, tempfile path. Not a shell-injection vector.

## Deliverables

- This plan + `docs/prompts/sandbox-shell-hardening.md`
- 6 added edge-case tests in `tests/tui/test_sandbox_shell_escape.py`
- `R-OPEN-SANDBOX` roadmap entry reconciled to Baseline Complete
