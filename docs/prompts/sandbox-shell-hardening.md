# Prompt — Sandbox Shell-Escape Hardening (R-OPEN-SANDBOX)

> **Status note (2026-06-06):** The core hardening is **already implemented**.
> This prompt is retained for the verification + coverage-completion pass, not a
> from-scratch fix. Verify-don't-trust: confirm the code state before changing it.

## Context

The TUI `!<cmd>` shell escape (`tui/screen.py::_handle_shell_escape`) historically
fell through to `subprocess.run(cmd, shell=True)` on any error, bypassing the
sandbox. That path was removed during R-UX2. This prompt covers locking in the
guarantee with tests and reconciling the stale roadmap entry.

## Verified secure pattern (research-grounded)

- **Python docs (`/python/cpython` subprocess + shlex):** tokenize with
  `shlex.split`, pass the resulting **argv list** to `subprocess` with
  `shell=False` (the default). "The subprocess library does not implicitly choose
  to call a system shell." `shell=True` is the only mode that requires manual
  `shlex.quote` escaping — avoid it.
- **Real-world (vercel grep):** the common secure idiom is
  `cmd_parts = shlex.split(cmd); subprocess.run(cmd_parts)` — exactly ARC's path.

## What the code already does (to verify, not rebuild)

1. `shlex.split(cmd)` — **fail-closed** on `ValueError` (unparseable) and empty argv.
2. `resolve_trust(workspace)` — blocks `TrustLevel.UNTRUSTED`.
3. `decide(argv, policy)` — deterministic classification (no LLM); privileged +
   destructive always denied; network/install/unknown gated by policy + approval;
   argv size bounds → `ARGV_OVERSIZED`.
4. Approval-required commands are blocked unless approved.
5. Allowed commands execute the **exact argv** via the isolation provider —
   no shell, workspace cwd, env allowlist (secrets stripped), policy timeout.
6. Outcome audited on **both** allow (with exit code) and deny.
7. Any exception in trust/policy/decision **fails closed** to `_block`.

## Task

1. Confirm there is no `shell=True` anywhere in `src/` (grep).
2. Close the test-coverage gaps for the branches not yet exercised:
   unparseable command, empty command, approval-required (distinct from denied),
   timeout, provider-execute error, argv-oversized.
3. Reconcile the `R-OPEN-SANDBOX` roadmap entry (still "Research Intake", citing
   the removed `shell=True`) to **Baseline Complete** with evidence.

## Acceptance

- Grep proves zero `shell=True` in `src/`.
- Every branch of `_handle_shell_escape` has a test.
- Roadmap entry reflects reality; banned-claims gate passes.
- `ruff` + full `pytest` green. No production-grade / multi-tenant claims.
