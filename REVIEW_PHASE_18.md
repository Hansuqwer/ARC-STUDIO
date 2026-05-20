# Review Phase 18 — CLI Consolidation

**Verdict:** REJECT

## Top 3 Strengths

- `cli_studio.py` duplicate implementation was substantially removed and now delegates to `cli_repl.chat_repl.run_chat_repl()` (`python/src/agent_runtime_cockpit/cli_studio.py:23-55`).
- Targeted CLI tests were expanded and stable across two runs: `57 passed` twice for `tests/test_cli_repl.py tests/test_cli_studio.py`.
- PR hygiene, banned-claims, `pnpm -w build`, and `pnpm -w test` passed during independent review.

## 1. Scope Conformance — BLOCKER

Diff vs `main` shows changes in CLI/session/test/docs files plus an unrelated docs file: `docs/ENV_HISTORY_SCRUB_PLAN.md` is modified but does not map to any Phase 18 CLI deliverable (`git diff --stat`, report lines 87-98 also admits it is pre-existing). More importantly, the Phase 0 inventory contract for CLI consolidation includes more than the implemented subset: every slash command should have a non-interactive sibling (`docs/archive/phase-0-inventory/cli-commands.md:149-150`), and the target inventory includes `/new`, `/resume`, `/continue`, `/fork`, `/graph`, `/providers`, `/quota`, `/budget`, `/audit`, `/hitl`, `/context`, `/memory`, `/receipt`, `/contract`, and more (`docs/archive/phase-0-inventory/slash-commands.md:72-127`). The implementation only registers 14 commands in `_build_registry()` (`python/src/agent_runtime_cockpit/cli_repl/slash_commands.py:18-110`), so multiple deliverables from the locked Phase 0 inventory have no corresponding changes.

## 2. Acceptance Criteria — BLOCKER

The added `docs/phases.md` Phase 18 section narrows acceptance after implementation (`docs/phases.md:580-616`) rather than reflecting the broader Phase 0 inventory it cites as contract. Several locked acceptance points are unmet: explicit migration command must be `arc studio sessions migrate` (`docs/archive/phase-0-inventory/sessions.md:130-140`), but the implementation exposes only `arc studio sessions-migrate` (`python/src/agent_runtime_cockpit/cli.py:2616-2620`), and `uv run arc studio sessions migrate --help` only displays the `sessions` command help. Canonical session schema required many top-level fields (`runtime_id`, `runtime_mode`, `profile_id`, `isolation_id`, `allow_paid_calls`, `cwd`, `project_id`, etc.) (`docs/archive/phase-0-inventory/sessions.md:61-85`), but `ChatSession` only has `version`, `id`, `mode`, timestamps, `history`, and `metadata` (`python/src/agent_runtime_cockpit/cli_repl/session.py:119-128`). `ARC_STUDIO_HISTORY_FILE` and `ARC_STUDIO_DEFAULT_SCOPE` are listed as Phase 2 env vars (`docs/archive/phase-0-inventory/sessions.md:90-97`), but `chat_repl.py` still hardcodes `HISTORY_FILE = Path.home() / ".arc" / "repl_history.txt"` (`python/src/agent_runtime_cockpit/cli_repl/chat_repl.py:9`).

## 3. Test Quality — CONCERN

New/changed tests are mostly integration-style CLI/session tests. They cover some happy/failure paths for registry duplication, legacy migration, and bare `arc` non-TTY behavior (`python/tests/test_cli_repl.py:237-496`, `python/tests/test_cli_repl.py:499-525`). However, they do not test the locked command path `arc studio sessions migrate`, do not test that all registry entries have required `trust_required`/`privileged`/`renders` fields populated according to the final registry shape, and do not test missing Phase 2 slash inventory items. Full `cd python && uv run pytest -q` fails because `tests/test_cli_providers.py::test_providers_action_all_gates_pass_closed_smoke` attempts a live provider call with an invalid key; this appears to be a known baseline issue and was separately verified with a deselect (`1002 passed, 19 skipped, 1 deselected`), but the requested command does not pass as written.

## 4. Schema And Contract — BLOCKER

The report says no schema bumps are needed, but the implementation changes the persisted session schema by adding `version` and `mode` while only partially implementing the locked canonical session schema. The Phase 0 session inventory explicitly defines `version=1` plus required fields including runtime/profile/isolation/cwd/project metadata (`docs/archive/phase-0-inventory/sessions.md:61-85`) and migration rules (`docs/archive/phase-0-inventory/sessions.md:166-175`). The writer emits only the partial Pydantic model (`python/src/agent_runtime_cockpit/cli_repl/session.py:119-146`) and no fixture/contract snapshot demonstrates canonical compatibility. This is not a RuntimeCapability/event/receipt schema bump issue, but it is still a session-contract miss for this phase.

## 5. Trust And Security (ADR-014) — CONCERN

The implementation reads legacy session JSON files directly (`python/src/agent_runtime_cockpit/cli_repl/session.py:27-67`, `python/src/agent_runtime_cockpit/cli_repl/session.py:159-206`) and returns legacy message content in `ChatSession` without tagging it as workspace or untrusted input. ADR-014 requires external content, including file content read mid-session, to be tagged as lower-trust data (`docs/adr/ADR-014-security-architecture.md:21-39`). This phase does not concatenate those messages into a system prompt directly in the changed code, but the session history is later used by REPL execution paths, so the trust boundary is under-specified.

## 6. SwarmGraph Integrity (ADR-013) — PASS

The changed code does not modify SwarmGraph orchestration, worker spawning, fan-out, checkpoints, or worker context isolation. `/run` still constructs `SwarmGraphRunner` directly (`python/src/agent_runtime_cockpit/cli_repl/slash_commands.py:132-142`), but that behavior existed before this phase and is not a new ADR-013 structural change.

## 7. IDE / Audit (ADR-015) — PASS

No IDE AssuranceTab, receipt v2, audit chain, or compliance-mode code paths were touched. ADR-015 is not applicable to these changes.

## 8. CLI/UX Lock — BLOCKER

Registry entries include `category`, `renders`, `requires_events`, `gates_required`, `trust_required`, and `privileged` fields at the dataclass level (`python/src/agent_runtime_cockpit/cli_repl/commands/__init__.py:15-31`), but most registered commands rely on empty/default values (`python/src/agent_runtime_cockpit/cli_repl/slash_commands.py:18-110`). The final registry shape requires `privileged` and trust-aware/gate-aware metadata (`docs/archive/phase-0-inventory/slash-commands.md:235-253`), while Phase 2 commands such as `/run`, `/plan`, `/build`, `/auto`, and provider-related commands should carry gate/mode semantics (`docs/archive/phase-0-inventory/slash-commands.md:90-125`). `/run` remains ungated and directly invokes `SwarmGraphRunner` (`python/src/agent_runtime_cockpit/cli_repl/slash_commands.py:132-142`), and no cancellation token exists for the potentially long-running run call. This fails the CLI/UX lock.

## 9. Docs And Banned Claims — CONCERN

`bash scripts/check-banned-claims.sh docs/agents.md docs/roadmap.md docs/phases.md docs/release/checklist.md README.md` passed. However, docs overstate completion: `docs/phases.md` claims “All existing slash commands from both implementations work identically” and “Complete” (`docs/phases.md:580-616`), while `cli_studio.py` no longer preserves the previous local-shell echo semantics for non-slash one-shot messages; it now routes them through SwarmGraph execution via `run_chat_repl()` (`python/src/agent_runtime_cockpit/cli_studio.py:52-55`, `python/src/agent_runtime_cockpit/cli_repl/chat_repl.py:92-101`). The report is also untracked (`PHASE_18_REPORT.md`), and the review found an unrelated modified docs file (`docs/ENV_HISTORY_SCRUB_PLAN.md`) in the worktree.

## 10. Build And CI — CONCERN

`bash scripts/check-pr.sh`, banned-claims, `pnpm -w build`, and `pnpm -w test` passed. Full `cd python && uv run pytest -q` failed due the pre-existing provider smoke test, so the implementer’s deselected run is reasonable for comparison but does not satisfy the requested command literally. The targeted test suite ran twice and passed both times.

## 11. Regression Sweep — CONCERN

There are no new `TODO`/`FIXME`/`XXX` markers in the changed files. `git log --stat main...phase-2-cli-consolidation` shows no commits because the work is uncommitted; this complicates review against the requested `BRANCH_OR_PR` and means the diff is the working tree rather than a reviewable branch commit set. Behavioral regression risk remains: `arc-studio <message>` previously echoed a local shell response with no agent execution (`docs/archive/phase-0-inventory/slash-commands.md:206-208`), but now executes prompt flow through `SwarmGraphRunner` (`python/src/agent_runtime_cockpit/cli_repl/chat_repl.py:92-101`) without explicit compatibility note or tests proving this changed behavior is intended.

## Blockers

- `docs/archive/phase-0-inventory/cli-commands.md:149-150` and `docs/archive/phase-0-inventory/slash-commands.md:72-127`: locked Phase 2 target inventory not implemented. Add the missing slash commands and non-interactive siblings, or file an ADR/phase-scope correction before marking Complete.
- `docs/archive/phase-0-inventory/sessions.md:130-140` vs `python/src/agent_runtime_cockpit/cli.py:2616`: locked migration command is `arc studio sessions migrate`; implementation exposes `arc studio sessions-migrate`. Implement nested `sessions migrate` or update the lock through an ADR.
- `docs/archive/phase-0-inventory/sessions.md:61-85` vs `python/src/agent_runtime_cockpit/cli_repl/session.py:119-128`: canonical session schema is incomplete. Add required fields/defaults or formally narrow the schema through an ADR.
- `docs/archive/phase-0-inventory/slash-commands.md:235-253` vs `python/src/agent_runtime_cockpit/cli_repl/slash_commands.py:18-110`: registry metadata defaults leave gate/trust/privilege/rendering semantics mostly unpopulated. Populate per command and add contract tests.
- `python/src/agent_runtime_cockpit/cli_repl/slash_commands.py:132-142`: `/run` remains ungated, has no cancellation path, and directly invokes a potentially long-running runner. Add gate/mode/cancellation handling or keep `/run` out of the “Complete” claim.

## Concerns

- `docs/ENV_HISTORY_SCRUB_PLAN.md` is modified outside CLI consolidation scope.
- `python/src/agent_runtime_cockpit/cli_repl/chat_repl.py:9`: `ARC_STUDIO_HISTORY_FILE` from the Phase 0 session inventory remains unimplemented.
- `python/src/agent_runtime_cockpit/cli_studio.py:52-55`: `arc-studio <message>` behavior changed from local shell/no-agent echo to SwarmGraph execution without an explicit acceptance note.
- `python/src/agent_runtime_cockpit/cli_repl/session.py:27-67`: legacy file content is read without ADR-014 trust tagging; safe only if never injected into privileged prompts.

## Follow-ups

- Split “thin shim + basic registry” from “full CLI consolidation” if the team wants a smaller mergeable slice; otherwise implement the full Phase 0 inventory before approval.
- Add a real command-registry contract snapshot asserting each locked command exists, with category/gates/trust/privileged/renders/requires_events populated.
- Add session-schema fixture tests for canonical v1 including runtime/profile/isolation/cwd/project fields and legacy migration outputs.

## Evidence Appendix

### git diff --stat
```
CHANGELOG.md                                       |  15 +
docs/ENV_HISTORY_SCRUB_PLAN.md                     |   4 +-
docs/phases.md                                     |  40 +++
python/src/agent_runtime_cockpit/cli.py            |  82 ++++-
python/src/agent_runtime_cockpit/cli_repl/__init__.py |   5 -
python/src/agent_runtime_cockpit/cli_repl/session.py  | 175 ++++++++++-
python/src/agent_runtime_cockpit/cli_repl/slash_commands.py | 337 +++++++++++++++-----
python/src/agent_runtime_cockpit/cli_studio.py     | 270 ++--------------
python/tests/test_cli_repl.py                      | 350 +++++++++++++++++++++
python/tests/test_cli_studio.py                    | 242 +++++++-------
10 files changed, 1033 insertions(+), 487 deletions(-)
```

### check-pr.sh
```
Checking PR hygiene...
Checking for accidental generated artifacts...
Artifact check passed. No prohibited files tracked.
License check passed. Workspace packages declare licenses or are private.
PR hygiene check passed.
```

### banned claims
```
OK: No banned claims found.
```

### pytest summary
```
cd python && uv run pytest -q
1 failed, 1002 passed, 19 skipped
FAILED tests/test_cli_providers.py::test_providers_action_all_gates_pass_closed_smoke

cd python && uv run pytest -q --deselect tests/test_cli_providers.py::test_providers_action_all_gates_pass_closed_smoke
1002 passed, 19 skipped, 1 deselected

cd python && uv run pytest tests/test_cli_repl.py tests/test_cli_studio.py -q
57 passed
Repeated: 57 passed
```

### pnpm test summary
```
pnpm -w test
exit=0
tests/e2e test: 4 skipped
tests/e2e test: 11 passed
applications/browser test: no unit tests for app shell
applications/electron test: no unit tests for app shell
```

### pnpm build summary
```
pnpm -w build
exit=0
packages build passed; applications/browser and applications/electron webpack builds completed successfully.
```
