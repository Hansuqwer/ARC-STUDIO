# CLI Edit Loop Next Research

Date: 2026-05-28

## Source Notes

| Source | Link/query | What was learned | Implementation consequence | Confidence | Unresolved questions |
|---|---|---|---|---|---|
| Context7 | Requested: Typer subcommands/testing, Pydantic v2 nested models, Python unified diff/patch handling | Context7 tool was not available in this execution environment. | Used existing repo Typer/Pydantic patterns and Python stdlib `difflib`; documented limitation instead of claiming external research. | High for tool availability; medium for implementation pattern. | Re-run with Context7 available before expanding patch parser beyond narrow mode. |
| Vercel Grep/code search | Requested: multi-file edit plans, approval UX, patch apply safety, provenance links | Vercel Grep/code-search tool was not available in this execution environment. | Used local Grep over ARC code for plan/apply/review/sandbox patterns; no external-code claims. | High for tool availability; medium for broader industry comparison. | Re-run Vercel Grep before broad IDE UI work. |
| Local code search | `security/edit_loop.py`, `security/plan.py`, `security/sandbox.py`, `cli/review.py`, `cli_repl/slash_commands.py` | Existing safe primitives: workspace path guard, plan audit events, sandbox classification, atomic writes, stable CLI envelopes, review provenance model. | Extended existing edit-loop helper; did not introduce shell `patch`; persisted metadata only. | High | Need IDE protocol review before wiring UI. |
| Python stdlib docs memory | `difflib.unified_diff` / narrow line-oriented parsing | Robust patch application is complex; narrow parser should fail closed for unsupported/ambiguous diffs. | Implemented single-file narrow unified diff parser; malformed/ambiguous patch denied. | Medium | Multi-hunk/no-newline/binary patches need explicit future design. |

## Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| Multi-file edit representation | `EditPlan.files[]` with per-file hashes and decisions | Separate bundle type only | Preserves current stable single-file shape while adding bundle metadata. | `security/edit_loop.py`, tests | High |
| Plan persistence | Store metadata/hashes only; no replacement content/diff in records | Store full content for easier apply | Avoids persisting potentially secret replacement text. | `.arc/edit-plans/*.json` | High |
| Patch mode | Narrow stdlib parser, fail closed | Shell out to `patch`; full parser | Avoids shell execution and ambiguous broad runtime behavior. | `security/edit_loop.py` | Medium |
| Approval UX | Scoped token hash bound to edit-plan metadata hash | Reuse generic sandbox approval directly | Edit plans are metadata objects, not raw argv; scoped approval is simpler and explicit. | `security/edit_loop.py`, `cli/edit.py`, REPL | High |
| IDE bridge | CLI `edit list/show` stable envelopes | Full IDE UI now | Provides real integration surface without mock UI claims. | `cli/edit.py` | High |
| Review provenance | Add `edit_plan` source and summarize saved plan records | Fabricate test/sandbox links | Existing producers only; missing producers remain explicit. | `security/review.py`, `cli/review.py` | High |

## Current Scope Truth

- Real: local CLI/REPL edit bundle planning/apply, saved plan records, scoped approval tokens, narrow patch mode, review provenance from saved edit plans.
- Not real: full Claude Code/OpenCode parity, autonomous multi-file agent editing, robust general patch engine, IDE UI for edit plans, collaborative approval server.
