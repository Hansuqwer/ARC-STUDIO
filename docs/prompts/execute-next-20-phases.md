# ARC Studio — 20-Phase Execution Prompt (Phases 316–335)

> Paste this entire prompt into a new opencode session to execute the next 20 phases.
> Each phase follows: **Research → Implement → Test → Commit → Docs → Next**.

---

## Master Prompt

```
You are executing ARC Studio Phases 316–335 (20 phases). You MUST complete all 20
phases sequentially in this session. Do not stop, ask for permission, or skip a
phase unless tests fail irrecoverably after 3 fix attempts.

## Charter Constraints (from AGENTS.md — read before starting)
- Single-user, loopback-only alpha. No production-grade, multi-user, or shared-host claims.
- Deterministic security. No LLM-based security decisions.
- Additive protocol only. Do not remove existing CLI commands, events, or public APIs.
- No commits unless asked — WAIT, this prompt explicitly asks you to commit after each phase.
- Finish each phase 1→100% before the next.

## Phase Execution Loop (repeat for EACH of the 20 phases)

### Step 0 — Research (BEFORE writing any code)

For each phase, gather context using ALL three tools:

1. **Context7** — Resolve the library ID for any framework/library used in the phase,
   then query docs for relevant patterns:
   - Use `resolve-library-id` with the library name
   - Use `query-docs` with the specific API/pattern needed
   - Example: for R92 (daemon tasks), look up `asyncio`, `sched`, or `celery` patterns
   - Example: for R99 (DAP debugger), look up `debugpy` or VS Code DAP protocol

2. **GitHub Code Search (grep)** — Find real-world implementations:
   - Search for similar features in comparable projects
   - Example: for R98 (visual graph builder), search for `ReactFlow` + `dagre` usage
   - Example: for R100 (notebook format), search for `.ipynb` schema patterns
   - Use `language` filters matching the target file (Python/TypeScript)

3. **WebFetch** — Fetch specification docs, API references, or design patterns:
   - Fetch protocol specs (DAP, MCP, etc.) when relevant
   - Fetch design pattern documentation for new subsystems
   - Fetch Theia extension docs for IDE widget patterns

### Step 1 — Read Existing Context

Before implementing each phase:
```bash
# Read the roadmap item details
# Read docs/roadmap.md section for the target R-item
# Read docs/research/IMPLEMENTATION_RESEARCH.md for scaffolds
# Read relevant ADRs in docs/adr/
# Read existing code that the phase touches or extends
```

### Step 2 — Implement

- Follow existing code conventions (check neighboring files)
- Use existing libraries/utilities already in the project (check package.json / pyproject.toml)
- New Python modules go under `python/src/agent_runtime_cockpit/`
- New CLI subcommands go under `python/src/agent_runtime_cockpit/cli/`
- New TS components go under `packages/arc-extension/src/browser/components/`
- New TS backend services go under `packages/arc-extension/src/node/services/`
- Wire new CLI subcommands into `cli/_app.py` or `cli/_subapps.py`
- Every user-visible surface needs: loading, empty, error, degraded, success states
- Security decisions must be deterministic (regex, allowlist, policy — never LLM)

### Step 3 — Test

Run ALL verification commands after each phase:
```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
pnpm typecheck && pnpm build
```

Write NEW tests for every phase:
- Python tests go under `python/tests/`
- TS tests go alongside source or under `packages/arc-extension/src/`
- Minimum: 3 unit tests per new module, 1 integration test per CLI command
- Tests must be deterministic, offline, no provider calls unless gated

If tests fail: fix and re-run. Do not proceed until green. Max 3 fix attempts.

### Step 4 — Commit

After tests pass:
```bash
git add -A
git commit -m "feat(<R-ID>): <phase title> — Phase <N>"
```

### Step 5 — Update Locked Docs

In the SAME commit or an immediate follow-up:
- Update `docs/roadmap.md`: change the R-item status from `Not Started` → `Baseline Complete`
- Update `docs/phases.md`: append the phase entry under the latest section
- Run `bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md` to verify

---

## Phase Assignments (316–335)

| Phase | Roadmap ID | Title | Primary Language | Key Research Targets |
|---|---|---|---|---|
| 316 | R91 | ARC Hub — local-first assistant/config sharing | Python | Context7: `pydantic` serialization; GitHub: config-sharing CLIs; WebFetch: local-first sync patterns |
| 317 | R92 | ARC Daemon Tasks — local background task runner | Python | Context7: `asyncio` task queues; GitHub: `background task runner python CLI`; WebFetch: daemon process patterns |
| 318 | R93 | ARC Vision — local browser/desktop automation (HITL-gated) | Python+TS | Context7: `playwright`; GitHub: `browser automation CLI`; WebFetch: Playwright Python API |
| 319 | R94 | ARC Advisor — token cost optimization advisor | Python | Context7: `tiktoken`; GitHub: `token cost analyzer`; WebFetch: OpenAI/Anthropic pricing APIs |
| 320 | R95 | ARC Dashboard — multi-workspace control center | TS | Context7: `@theia/core`; GitHub: `theia dashboard widget`; WebFetch: Theia widget API |
| 321 | R96 | ARC Voice — local voice-to-command interface | Python | Context7: `speech_recognition`; GitHub: `voice command CLI python`; WebFetch: Web Speech API / Vosk |
| 322 | R97 | ARC Policies — sandbox policy template library | Python | Context7: `pydantic`; GitHub: `policy template engine python`; WebFetch: OPA/Rego patterns |
| 323 | R98 | ARC Composer — visual SwarmGraph builder | TS | Context7: `reactflow`; GitHub: `react flow dagre graph builder`; WebFetch: ReactFlow docs |
| 324 | R99 | ARC Debug — inline debugger & REPL via DAP | Python+TS | Context7: `debugpy`; GitHub: `DAP debug adapter python`; WebFetch: DAP specification |
| 325 | R100 | ARC Notebook — agent workbook `.arcnb` | Python+TS | Context7: `pydantic`; GitHub: `.ipynb notebook format json schema`; WebFetch: Jupyter notebook spec |
| 326 | R101 | ARC Time Travel — run replay & diff debugger | Python+TS | Context7: `deepdiff`; GitHub: `time travel debugger event replay`; WebFetch: event sourcing patterns |
| 327 | R102 | ARC Migrate — cross-adapter migration assistant | Python | Context7: `pydantic`; GitHub: `adapter migration tool python`; WebFetch: LangChain↔LangGraph migration guides |
| 328 | R-PERF7 | Incremental workspace index (< 1s per file change) | Python | Context7: `watchdog`; GitHub: `incremental file watcher FTS index`; WebFetch: inotify/FSEvents docs |
| 329 | R-PERF9 | WASM trace parser (~10× large-trace speedup) | Python+Rust/WASM | Context7: `wasmtime`; GitHub: `WASM JSON parser rust`; WebFetch: wasmtime Python bindings |
| 330 | R-PROC1 | Auto-generate release intelligence from CI | Python+Bash | Context7: `pygithub`; GitHub: `release notes generator CI`; WebFetch: GitHub Releases API |
| 331 | R-PROC2 | `docs/RELEASE_SNAPSHOTS/` — dated, locked snapshots | Bash+Python | Context7: `jinja2`; GitHub: `release snapshot markdown generator`; WebFetch: semantic-release patterns |
| 332 | R91-polish | R91 DoD elevation — UX states, a11y, parity, perf | Python+TS | Review R91 baseline; run DoD gate checklist |
| 333 | R92-polish | R92 DoD elevation — UX states, a11y, parity, perf | Python+TS | Review R92 baseline; run DoD gate checklist |
| 334 | R93-polish | R93 DoD elevation — UX states, a11y, parity, perf | Python+TS | Review R93 baseline; run DoD gate checklist |
| 335 | Final sweep | Roadmap/phases update + release snapshot + banned-claims | Bash | Run all verification scripts; update locked docs |

---

## Execution Rules

1. **One phase at a time.** Complete Steps 0–5 fully before moving to the next phase.
2. **Research first.** ALWAYS run Context7 + GitHub grep + WebFetch BEFORE writing code.
3. **Mimic conventions.** Check neighboring files for style, imports, error handling patterns.
4. **Minimum viable tests.** 3+ unit tests per module, 1+ integration test per CLI command.
5. **No overclaiming.** Label everything as Baseline Complete until DoD elevation phases.
   - Use "stub", "heuristic", "research-grade", "gated" where appropriate.
   - Never claim "production-ready", "multi-user", or "tenant-isolated".
6. **Bounded scope.** Each feature is local-first, single-user, loopback-only.
   - R93 (Vision): HITL-gated, no unattended automation.
   - R96 (Voice): local STT only, no cloud APIs.
   - R98 (Composer): local Theia widget, no remote collaboration.
   - R99 (Debug): local DAP, no remote debug server.
7. **Green gate.** If `ruff`, `pytest`, `typecheck`, or `build` fails, fix before committing.
8. **Docs in same commit.** Roadmap + phases update must accompany the implementation commit.
9. **Continue automatically.** After committing phase N, immediately begin phase N+1.
10. **Final summary.** After Phase 335, output a summary table:
    | Phase | R-ID | Status | Tests Added | Commit |

---

## Quick-Start Checklist (before pasting this prompt)

- [ ] Working tree is clean (`git status` shows no uncommitted changes)
- [ ] On the correct branch
- [ ] `pnpm install` and `cd python && uv sync` are up to date
- [ ] You have internet access (for Context7, GitHub grep, WebFetch)

---

## Resume Prompt (if session is interrupted)

If the session stops mid-phase, resume with:

```
Resume ARC Studio phase execution. Last completed phase: <N>.
Read docs/phases.md tail to confirm, then continue from Phase <N+1>.
Follow the same loop: Context7 + GitHub grep + WebFetch research,
implement, test (ruff + pytest + typecheck + build), commit, update
docs/roadmap.md + docs/phases.md, then next phase. Continue through
Phase 335.
```
```
