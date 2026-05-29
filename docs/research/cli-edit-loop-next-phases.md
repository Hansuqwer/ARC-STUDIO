# CLI Edit Loop Next Phases Research

Date: 2026-05-29

## Source Notes

| Source | Link/query | What was learned | Implementation consequence | Confidence | Unresolved questions |
|---|---|---|---|---|---|
| Context7 | Requested: Typer testing, Pydantic v2 models, Theia services, unified diff parsing | Context7 tool is not available in this execution environment. | Used upstream docs via web fetch plus existing repo patterns; did not claim Context7 coverage. | High for tool availability; medium for coverage. | Re-run with Context7 before broadening patch parser beyond text hunks. |
| Vercel Grep/code search | Requested: edit plan approval UX, IDE patch bridge, sandboxed test loop examples | Vercel Grep/code-search tool is not available in this execution environment. | Used local code search/subagents and public docs; no external-code pattern claims. | High for tool availability; medium for broader industry comparison. | Re-run Vercel Grep before larger IDE UX. |
| Typer docs | https://typer.tiangolo.com/tutorial/testing/ | `CliRunner.invoke(app, args)` is the documented path for CLI tests; input prompts can be tested with `input=...`; exit codes/output assertions are first-class. | Continue existing `CliRunner` regression style for edit/test workflow commands. | High | None for current CLI scope. |
| Pydantic v2 docs | https://docs.pydantic.dev/latest/concepts/models/ | `BaseModel` validates untrusted data; `model_dump()` is the stable serialization path; nested models are supported; `model_validate_json()` is appropriate for JSON payloads. | Keep edit/test evidence as Pydantic models or validated dicts; use `model_dump(mode="json")`; avoid `model_construct()` for untrusted local files. | High | Whether strict models should be added later for saved artifacts. |
| Theia services/contributions docs | https://theia-ide.org/docs/services_and_contributions/ | Theia services are DI-bound via Inversify; contributions should depend on interfaces and be bound in modules. | Add a small backend bridge service and bind it through existing ARC backend module; frontend consumes existing `ArcService`. | High | Exact app-specific tab placement follows repo conventions. |
| Theia JSON-RPC docs | https://theia-ide.org/docs/json_rpc/ | Backend services are exposed via RPC connection handlers and frontend proxies; interfaces live in common protocol. | Extend existing `ArcService` protocol instead of adding a new RPC path. | High | None for P91 bridge. |
| Python difflib docs | https://docs.python.org/3/library/difflib.html | `unified_diff` format uses `---`, `+++`, and `@@`; line sequences should preserve newline behavior; difflib can produce diffs but does not provide safe patch apply. | Keep custom apply parser fail-closed; parse unified hunk headers explicitly; support only text lines and reject unsupported markers. | High | Full Git patch semantics remain out of scope. |
| GNU diffutils unified format | https://www.gnu.org/software/diffutils/manual/html_node/Detailed-Unified.html | Unified hunk headers carry old/new line ranges in `@@ -l,c +l,c @@` form. | Parse and validate hunk ranges so multi-hunk patches cannot silently drift. | Medium | Page fetch returned minimal content; use Python docs and tests as primary guard. |
| Claude Code workflows | https://docs.anthropic.com/en/docs/claude-code/common-workflows | Common agent workflows emphasize plan-before-edit, tests after changes, and delegating research to subagents. | Implement `/diff`, `/apply`, `/test` as explicit local workflow commands, not autonomous parity. | Medium | No direct OpenCode docs available in this environment. |
| Local code search/subagents | `arc-protocol.ts`, `arc-backend-service.ts`, `SessionBridgeService`, `studio-tabs.contract.test.ts`, `security/edit_loop.py`, `cli_repl/adapters.py`, `cli/testbench.py` | Existing patterns cover ARC JSON-RPC, CLI bridge spawning with no shell, static UI contract tests, sandbox/testbench paths, edit bundle helpers. | Minimal implementation should extend existing service/protocol/tabs and Python helpers; avoid new parallel systems. | High | Large Theia UI runtime e2e may expose unrelated environment issues. |

## Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| IDE bridge scope | CLI-backed `ArcService` methods for edit list/show/approve/apply | New daemon routes; direct file reads from TS | Reuses Python as security authority and stable envelopes; smallest P91 slice. | `arc-protocol.ts`, backend service/module, new bridge service, tab | High |
| IDE UI | Metadata-only `EditPlansTab` | Full diff viewer/editor | Saved plans intentionally omit replacement content/diffs; UI must not imply content review parity. | Browser tab files/tests | High |
| REPL workflow | Add `/diff`, `/apply`, `/test` adapters over existing edit/testbench helpers | Autonomous repair loop | Gives explicit user-controlled workflow without parity overclaim. | `cli_repl/adapters.py`, `slash_commands.py`, tests | High |
| Test loop | Route `/test` through existing sandbox/testbench command path | Raw subprocess; live CI/network | Preserves deny-by-default policy and output caps. | Python REPL adapters/tests | High |
| Patch hardening | Explicit multi-hunk parser with range validation, fail closed | Shell out to `patch`; accept broad Git patches | Avoids unsafe shell/runtime behavior; keeps text-only local scope. | `security/edit_loop.py`, tests | Medium |
| Evidence/status docs | Add R62-R64/Phases 91-93 only after implementation evidence | Plan-only docs now | User asked to complete phases; docs should reflect actual completed status only after tests. | `docs/roadmap.md`, `docs/phases.md` | High |

## Scope Truth

- Real target: IDE metadata bridge, explicit CLI/REPL diff/apply/test workflow commands, safer multi-hunk text patch support.
- Not target: autonomous coding-agent parity, general Git patch engine, collaborative approval server, signed reviewer identity, live network CI orchestration.
