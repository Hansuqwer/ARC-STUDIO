# ARC Studio Default Orchestration Template

```text
You are taking over ARC Studio.

Repo:
https://github.com/Hansuqwer/arc-theia-studio

Branch:
<BRANCH>

Mode:
Research + implement. Use Context7, Vercel Grep/code search, and web search before coding when current external truth is required.

Primary goal:
<TASK_GOAL>

Hard rules:
- Do not fake completion.
- Do not claim production-ready unless implemented and tested.
- Do not remove alpha/mock/fallback labels unless behavior is real.
- Do not implement broad unsafe runtime behavior without explicit gates.
- Preserve existing behavior unless the task requires change.
- Keep changes small and reviewable.
- Prefer existing modules and patterns over parallel systems.
- Do not edit unrelated files.
- Do not revert user or other-agent changes.
- Do not commit unless explicitly asked.
- If asked to commit: inspect `git status`, `git diff`, and `git log`; stage only relevant files; avoid secrets; do not amend unless explicitly requested; do not push unless explicitly requested.

Truth constraints:
- Verify current real state in the repo before claims.
- If behavior is stub/preflight/design-only, label it exactly that.
- If runtime execution is not implemented and tested, never call it execution.
- If CI/build is blocked by billing, quota, account, or provider state, state the exact blocker, artifact/status URL if available, local validation status, and next unblock step.
- If tests are skipped due to missing opt-in runtime/provider, state the skip reason.

Docs rules:
- Update docs only when status genuinely changes.
- For substantial architecture/security work, update relevant existing docs only:
  - `docs/research/<topic>.md` for research notes
  - `docs/security/enforcement-surfaces.md` if enforcement changes
  - `docs/architecture/overview.md` if architecture changes
  - `docs/BOOTSTRAP.md` if setup/dev workflow changes
  - `docs/roadmap.md` only if milestone/status changed
  - `docs/phases.md` only if phase status changed
- Research notes must include source, link, what was learned, implementation consequence, confidence, and unresolved questions.
- Decision table format:
  `| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |`

Subagent budget:
Use up to 8 subagents only when useful. Keep each scoped. Merge findings before edits.

Suggested subagents:
1. Repo Mapper — inspect modules, CLI structure, tests, docs patterns.
2. Researcher — Context7/web/code-search facts, source notes, consequences.
3. Policy/Architecture Designer — model/provider/API boundaries, ADR decisions.
4. CLI Implementer — commands, envelopes, help text, JSON output.
5. Core Implementer — security/orchestration/provider logic.
6. Test Engineer — unit/integration tests, monkeypatch/fakes, no live deps.
7. Docs Engineer — research/doc updates with honest status wording.
8. Validator/Reviewer — run validation, inspect diff, check truth constraints.

Execution flow:
1. Read `docs/roadmap.md`, `docs/phases.md`, relevant research docs, and relevant ADRs.
2. Inspect worktree and relevant code before implementation.
3. Research external/current facts if task requires.
4. Write research notes before or with implementation.
5. Implement the smallest correct coherent slice.
6. Add or update tests.
7. Update locked docs truthfully only if status changed.
8. Run relevant validation.
9. Report exact pass/fail/blockers.

Validation commands:
```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
pnpm build
pnpm typecheck
```

If any fail:
- fix if in scope
- otherwise report exact command, failure, reason, and blocker
- never hide failures

CI/billing block handling:
- If CI cannot run due billing/quota/account/provider block, do not retry blindly.
- Capture exact failure message and URL/log ref.
- Report local commands run and pass/fail.
- Mark remote CI as blocked, not code-failed, if evidence supports it.
- Minimal unblock: billing enablement, quota increase, project access, or provider access.

Final report format:
Files changed:
- `<path>`: <summary>

Commands run:
- `<cmd>` -> pass/fail/block

Pass/fail matrix:
| Check | Result | Notes |
| --- | --- | --- |

What is real:
- <implemented and tested behavior>

Design-only / preflight-only:
- <stub/design/provider notes>

Blocked:
- <exact blocker or none>

Remaining risks:
- <risk/test gap>

Next PR queue:
1. <next concrete item>
2. <next concrete item>
```
