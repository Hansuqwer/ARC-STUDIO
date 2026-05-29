# CLI Parity Priority Research

Date: 2026-05-29

Status: Phase 97 research gate complete. This is not an OpenCode/Claude Code parity claim.

## Research Notes

| Source | Link/query | What was learned | Implementation consequence | Confidence | Unresolved questions |
|---|---|---|---|---|---|
| Context7 | Required: Typer/Rich/Textual/Pydantic/subprocess/git/diff/provider/microVM docs | No Context7 MCP tool is exposed in this runtime. | Recorded tool gap; used official docs/web fetch plus local repo patterns. | High for tool availability | Re-run Context7 before broad parity/security sign-off. |
| Vercel Grep/code search | Required: OpenCode/Claude Code style command palette, repair loops, undo/redo, IDE diff, provider shell, VM wrappers, CI UX | No Vercel Grep/code-search tool is exposed in this runtime. | Recorded blocker; implementation remains conservative/local-test based. | High for tool availability | Run Vercel Grep externally before security sign-off. |
| Typer docs | https://typer.tiangolo.com/tutorial/testing/ | `CliRunner.invoke(app, args, input=...)` is documented for CLI tests; subcommands are regular Typer apps. | Added CLI regressions using existing Typer runner style. | High | None. |
| Pydantic docs | https://docs.pydantic.dev/latest/concepts/models/ | `BaseModel`, `model_validate_json()`, `model_dump()`, and `ConfigDict(extra='forbid')` support stable local envelopes. | New result/transaction/repair models use Pydantic serialization. | High | Full TS schema generation remains future work. |
| Python subprocess docs | https://docs.python.org/3/library/subprocess.html | Prefer argv list; `shell=False` avoids shell injection; timeout paths must kill/drain; `wait()` can deadlock with pipes. | Existing sandbox subprocess provider remains argv-only, bounded-output, process-group timeout kill. | High | Async streaming UX deferred to Phase 102. |
| Git diff docs | https://git-scm.com/docs/git-diff | `git diff` exposes machine-friendly `--name-status`, `--numstat`, `--check`; patch output is separate review material. | IDE diff bridge uses saved unified diff sidecar and keeps apply through Python gates. | High | Rich Monaco side-by-side editor remains UI polish. |
| Claude Code permissions | https://docs.anthropic.com/en/docs/claude-code/permissions | Permission order is deny -> ask -> allow; read-only commands can run without prompt; symlink checks include link and target; sandboxing is distinct OS enforcement. | ARC keeps conservative command classification, symlink/path guard, approval gates, and explicit sandbox truth labels. | High | Exact Claude sandbox internals remain external. |
| Claude Code checkpoints/sessions/tools | https://docs.anthropic.com/en/docs/claude-code/permissions and linked docs | File-edit checkpointing does not imply Bash rollback; tool outputs/timeouts are capped; JSON/headless modes matter for CI. | ARC transaction undo/redo covers only ARC-made edit records, not arbitrary subprocess writes. | High | Conversation/session rewind remains out of scope. |
| OpenCode permissions | https://opencode.ai/docs/permissions | Permissions resolve to allow/ask/deny; granular wildcard rules exist; external-directory access is a separate permission; defaults are more permissive. | ARC defaults stay stricter: deny network/install/destructive/privileged unless policy/gate allows. | High | OpenCode internal command parser not audited. |
| OpenCode commands/docs | https://opencode.ai/docs/commands/ | Custom commands can inject shell output and file references. | ARC provider/runtime shell must route tool proposals through sandbox policy before execution. | Medium | Full command marketplace parity not attempted. |
| Firecracker docs | https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md | Firecracker requires Linux/KVM, `/dev/kvm`, kernel/rootfs, and explicit networking setup. | MicroVM execution stays blocked/preflight-only until ADR-024 proofs pass. | High | Real Linux host proof still missing. |
| Lima docs | https://lima-vm.io/docs/ | Lima provides lightweight Linux VMs on macOS using VZ, but default/user networking remains network-present. | Lima remains low-security developer harness/design path, not strict no-network microVM execution. | High | Strict macOS no-network proof unresolved. |
| Cloud Hypervisor docs | https://www.cloudhypervisor.org/docs/ | Lightweight Linux hypervisor uses KVM; networking is explicit but boot/image lifecycle still required. | Secondary Linux candidate after Firecracker; no public execution claim. | Medium | Workspace mount/guest command channel unimplemented. |
| Theia JSON-RPC/services docs | https://theia-ide.org/docs/json_rpc/ | Shared protocol + backend service + frontend proxy are the normal extension pattern. | Phase 100 extends existing `ArcService` edit-plan bridge rather than adding a parallel RPC service. | High | Runtime e2e remains environment-sensitive. |

## Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| Phase 98 repair scope | Deterministic bounded edit/test/repair loop | LLM autonomous repair, live provider loop | Proves loop semantics without paid/network calls or unsafe runtime broadening. | `security/repair_loop.py`, `cli/edit.py`, tests | High |
| Phase 99 transactions | ARC-owned file snapshots + transaction log; no `git reset/checkout` | Stash/reset/checkout, whole-worktree snapshot | Restores only ARC-recorded files and preserves unrelated user work. | `security/transactions.py`, `security/edit_loop.py`, tests | High |
| Phase 100 IDE diff | Saved diff sidecar + capped bridge + apply through Python gates | Persist replacement bodies in IDE, direct TS file writes, Monaco-only mock | Real diff review without storing replacement content; Python remains security authority. | `edit_loop.py`, `cli/edit.py`, `arc-protocol.ts`, `edit-plan-bridge-service.ts`, `EditPlansTab.tsx` | Medium |
| Phase 101 provider shell | Dry-run default, live path delegates to existing gated provider action, tool proposal policy surfaced | Default live provider shell, direct model-to-shell exec | Preserves no default paid/network calls; tool calls are policy-visible before execution. | `cli/providers.py`, tests | Medium |
| MicroVM in this track | Keep preflight/doctor/design-only unless ADR-024 proofs exist | Public `arc sandbox run --provider microvm` | No real create/run/destroy proof in this session. | Docs only | High |

## OpenCode / Claude Code Comparison

| Area | OpenCode/Claude behavior researched | ARC current result | Gap |
|---|---|---|---|
| Permission model | allow/ask/deny, read-only auto-allow, external-dir controls | Sandbox policy/classifier exists; Phase 98-101 reuse it | Full wildcard permission grammar absent. |
| Plan/edit/test loop | Agent can plan, edit, test, retry with approvals | Deterministic bounded repair loop exists for local fixtures | No LLM diagnosis/autonomous general repair claim. |
| Undo/redo/checkpoints | Claude checkpoints file edits; OpenCode has `/undo`/`/redo` UX | ARC transaction undo/redo for ARC edit applies | Does not rollback arbitrary Bash/subprocess writes or conversation state. |
| Diff review | Rich IDE/CLI diff review before apply | IDE can load real saved unified diff and apply through backend bridge | Not a full Monaco side-by-side editor/e2e proof yet. |
| Provider shell/tool loop | Provider proposes tool use, approvals gate execution | Dry-run provider shell contract + gated live provider action path + tool decision payload | No multi-turn provider runtime shell parity. |
| Streaming terminal/events | Incremental stdout/stderr/events, cancel | Existing sandbox returns capped result; Phase 102 still required | No new streaming implementation in this slice. |
| MicroVM/sandbox | OS sandbox/microVM/container isolated execution | Subprocess sandbox foundation; microVM preflight only | No public microVM execution. |
| CI orchestration | Headless JSON modes, max turns/timeouts | Existing CI/testbench basics; broad Phase 103 pending | No broad CI matrix orchestration here. |

## Acceptance Matrix

| Capability | Required proof | Status | Evidence | Gaps |
|---|---|---|---|---|
| OpenCode/Claude Code parity | Feature-by-feature checklist vs current docs | Not Started | This matrix only | Full parity unclaimed. |
| Edit -> test -> repair | Bounded loop, fail/repair/pass, audit, denial stop | Baseline Complete | `test_phase_98_101_cli_parity.py` targeted tests | Deterministic repair only; no LLM diagnosis. |
| Git undo/redo | Transaction log, restore, dirty-worktree tests | Baseline Complete | `edit undo/redo` tests | Only ARC edit transactions; not Bash rollback. |
| IDE diff review/apply | Real diff UI, apply/deny/stale tests | Baseline Complete | TS bridge/UI contract tests plus Python diff/apply tests | Full side-by-side Monaco/e2e polish pending. |
| Provider-backed shell | Gated runtime, tool proposals, audit, no default paid calls | Baseline Complete | Dry-run/gate tests; live delegates to existing gated provider action | No broad multi-turn provider shell. |
| Live terminal/event UX | Incremental stdout/stderr/events/cancel | Not Started | Existing capped sandbox result only | Phase 102. |
| CLI CI orchestration | Detect/run matrix, artifacts, summaries | Not Started | Existing CI/testbench commands only | Phase 103. |
| macOS microVM | Lima/VZ run + strict no-network proof | Blocked | ADR-024; `sandbox-and-microvm.md` | Lima network posture; no strict proof. |
| Linux Firecracker | Boot/run/destroy proof | Blocked | ADR-024; preflight/harness docs | Requires Linux/KVM/kernel/rootfs/guest proof channel. |

## Dependency Order

1. Phase 97 research/matrix.
2. Phase 98 deterministic repair loop using existing edit/sandbox gates.
3. Phase 99 transactions around edit applies.
4. Phase 100 IDE diff/apply bridge using transaction layer.
5. Phase 101 provider shell contract/gates.
6. Phase 102 streaming.
7. Phase 103 CI orchestration.
8. Phase 104/105 real microVM proofs only on eligible hosts.
