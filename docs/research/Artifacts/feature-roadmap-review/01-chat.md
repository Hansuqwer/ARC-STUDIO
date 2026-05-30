# Chat Review

## Current ARC Spec

ARC Studio specifies chat as the **primary default surface** across both CLI and IDE.

### CLI Chat (§7.1-7.2, CLI_IDE_REDESIGN_PLAN §2.3)
- `arc-studio` launches directly into an interactive chat REPL — no arguments needed
- Welcome screen shows workspace, runtime, daemon, provider, and mode readiness
- Steady-state chat renders transcript with user/agent messages, tool call cards, paid-call confirmation cards
- Input area with `arc ›` prompt, multiline support (`Ctrl+J` for newline)
- Status line shows runtime, model, mode, daemon state, cost, and contextual commands
- Session lifecycle: ULID `session_id`, persisted to `~/.local/share/arc-studio/sessions/` (or platform equivalent), `transcript.jsonl` journaling, auto-resume on crash
- Streaming output with cursor `▌` blink animation (§6.2)

### IDE Chat Panel (§8.1)
- Chat is the default panel (60% width in 3-column layout)
- Transcript with messages, HITL cards, tool calls
- Input with slash hints and send button
- Mode toggle (Plan/Build/Auto), runtime/model selectors above input
- Keyboard: `Ctrl/Cmd+;` focus input, `Ctrl/Cmd+Enter` send
- Shared session lifecycle with CLI — both attach to same workspace session

### Slash Commands (§10.4, CLI_IDE_REDESIGN_PLAN §2.4)
- Flat namespace: `/config`, `/providers`, `/runtime`, `/model`, `/status`, `/run`, `/stop`, `/diff`, `/tasks`, `/runs`, `/workflows`, `/plan`, `/build`, `/auto`, `/doctor`, `/graph`, `/version`, `/help`, `/clear`, `/compact`, `/resume`, `/exit`
- Categorized: Session, Configuration, Workflow, Mode, Diagnostic
- Autocomplete via `combobox` role (§9 Input component)
- Advanced commands hidden behind `arc-studio advanced <cmd>`

### Mode System (§7.13)
- **Plan**: Read-only, no writes or paid calls
- **Build**: Can propose changes, asks before applying
- **Auto**: Follows approval policy (`.arc/policy.yaml`) — still denies `trust_changes` and `shell_exec` by default
- `Tab` cycles modes in CLI; button toggle in IDE

### HITL Prompts (§9 Card component, §7.2)
- HITL cards rendered in chat transcript with `state.info` tone
- Approval buttons: Approve, Reject, Edit First
- Single-use decision tokens (P4 hardening)
- Slides into transcript with 12px offset fade animation (§6.2)

### Paid-Call Cards (§9 Card component)
- Always display provider, model, estimated ceiling, approval buttons
- Warning tone (`state.warning.bg`)
- Confirmation copy includes session total and incremental cost (§10.3)

### Tool Call Cards (§7.2, §9 Card component)
- Rendered in `bg.sunken` with tool name header
- Status indicators: ✓ complete, ✗ failed
- Collapsible detail for output

### Transcript Rendering
- User messages labelled "you", agent messages labelled "agent"
- Tool cards and paid-call cards inline in transcript
- Streaming tokens append without layout animation
- Redaction contract (§10.10): API keys, bearer tokens, passwords, secrets, `.env` values never rendered

### Context Mentions
- **Not currently specified.** The spec mentions workspace path and file references in microcopy but does not define `@file`, `@folder`, or `@symbol` mention syntax.

### Session Management (§7.14.1)
- ULID session IDs, JSONL transcript journaling
- `metadata.yaml`, `transcript.jsonl`, `runs.jsonl` per session
- Auto-resume on crash via `/resume`
- CLI and IDE share session — concurrent attachment supported with `{N} clients attached` indicator
- `/new` creates new session, `/clear` starts fresh (previous transcript saved), `/compact` summarizes context

### What ARC Chat Does NOT Currently Specify
- `@file` / `@folder` / `@symbol` context mentions
- Image/multimodal input
- Message queueing while a run is active
- Web/URL context injection
- Copy/export/share conversation (beyond session resume)
- "Ask" vs "Run" intent disambiguation
- Chat history browsing (only resume of latest session)
- Compacting context implementation details

---

## Comparable Products / Research

| Feature | Claude Code | OpenCode | Codex CLI | Cursor | Windsurf | VS Code Copilot | Aider | ARC Studio (spec) |
|---|---|---|---|---|---|---|---|---|
| **Chat-first default** | ✅ `claude` launches chat | ✅ `opencode` launches TUI chat | ✅ `codex` launches TUI | ✅ Chat panel default | ✅ Cascade panel | ✅ Chat panel | ✅ `aider` launches REPL | ✅ `arc-studio` launches chat |
| **Install** | curl/brew/native | npm/bun/brew/binary | npm/brew | Desktop app | Desktop app | VS Code extension | pip | pip (npm wrapper planned) |
| **Session resume** | ✅ `-c`, `-r`, `--resume`, `--teleport` | ✅ `-c`, `-s`, share links | ✅ `resume`, `fork` | ✅ Conversation history | ✅ Session history | ✅ Chat history | ✅ `--restore-chat-history` | ✅ ULID sessions, `/resume`, auto-resume |
| **Slash commands** | ✅ 40+ built-in + custom skills | ✅ 6+ custom + `/init` | ✅ 30+ | ✅ `/` commands | ✅ Commands | ✅ `/` commands | ✅ 35+ in-chat commands | ✅ 20+ specified |
| **Permission modes** | ✅ 6 modes (default, acceptEdits, plan, auto, dontAsk, bypassPermissions) | ✅ Plan/Build (Tab toggle) | ✅ Approval + sandbox | ✅ Agent/Composer toggle | ✅ Code/Chat toggle | ✅ Chat/Agent/Edit | ✅ `--yes-always` | ✅ Plan/Build/Auto (Tab cycle) |
| **@file mentions** | ✅ `@file`, `@folder`, `@symbol`, `@git`, `@web` | ✅ `@` fuzzy file search | ❌ | ✅ `@file`, `@codebase`, `@docs` | ✅ `@file` mentions | ✅ `#file`, `#codebase` | ✅ `/add` file, auto-detect | ❌ Not specified |
| **Image input** | ✅ Drag & drop, paste | ✅ Drag & drop into terminal | ❌ | ✅ Paste/drop | ✅ Paste/drop | ✅ Paste | ✅ `/add` images | ❌ Not specified |
| **Web/URL context** | ✅ `@web` mention | ❌ | ❌ | ✅ `@web` | ✅ Cascade web search | ❌ | ❌ | ❌ Not specified |
| **Streaming output** | ✅ Token streaming | ✅ Streaming | ✅ Streaming | ✅ Streaming | ✅ Streaming | ✅ Streaming | ✅ Streaming | ✅ Specified (§6.2) |
| **Tool call rendering** | ✅ Tool use cards | ✅ Tool indicators | ✅ Tool calls | ✅ Agent steps feed | ✅ Cascade steps | ✅ Agent steps | ✅ Edit diffs inline | ✅ Tool call cards (§7.2) |
| **Paid-call gating** | ✅ Permission rules per tool | ✅ Permissions system | ✅ Sandbox | ❌ | ❌ | ❌ | ❌ | ✅ Paid-call cards with approval |
| **HITL prompts** | ✅ Permission prompts | ✅ Approval flow | ✅ Approval | ✅ Accept/Reject | ✅ Accept/Revert | ✅ Accept/Discard | ❌ | ✅ HITL cards with Approve/Reject/Edit |
| **Message queueing** | ✅ Queues while running | ❌ | ❌ | ✅ Queues | ✅ Queues | ✅ Queues | ❌ | ❌ Not specified |
| **Chat history** | ✅ Full history, search | ✅ Share links | ✅ History | ✅ Full history | ✅ History | ✅ Full history | ❌ | ✅ Session resume only (no browse) |
| **Context compacting** | ✅ Auto-compaction with skill carry-forward | `/undo`/`/redo` | ❌ | ✅ Context management | ❌ | ✅ Summarization | ❌ | ✅ `/compact` specified (no implementation) |
| **Copy/export/share** | ✅ `/share` | ✅ `/share` with links | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ Not specified |
| **Model switching** | ✅ `/model`, `--model`, per-skill override | ✅ `/connect`, 75+ models | ✅ `/model`, `-m` | ✅ Dropdown | ✅ Dropdown | ✅ Dropdown | ✅ `/model`, `--model` | ✅ `/model` specified |
| **Multi-session** | ✅ Background agents, subagents | ✅ Multi-session parallel | ❌ | ✅ Multiple tabs | ❌ | ❌ | ❌ | ❌ Not specified |
| **Ask vs Run distinction** | ❌ Implicit | ❌ Implicit | ❌ Implicit | ✅ Chat vs Agent mode | ❌ Implicit | ✅ Chat vs Agent | ❌ Implicit | ❌ Not specified |
| **Skills/custom commands** | ✅ SKILL.md system, Agent Skills standard | ✅ Custom commands | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ Not specified |

### What Competitors Do Better

**Claude Code** is the benchmark:
- **Skills system**: `SKILL.md` files with frontmatter, dynamic context injection (`!`command``), subagent execution, automatic discovery — this is the most extensible slash-command system in the market [source: docs.anthropic.com/en/docs/claude-code/slash-commands]
- **Permission modes**: 6 granular modes from `plan` (read-only) to `bypassPermissions` with managed settings for enterprise [source: docs.anthropic.com/en/docs/claude-code/permissions]
- **@-mentions**: `@file`, `@folder`, `@symbol`, `@git`, `@web` — comprehensive context injection
- **Session portability**: `--teleport` to move sessions between surfaces, Remote Control from mobile
- **Auto-compaction**: Skills carried forward in token budget after context summarization
- **Hooks**: PreToolUse/PostToolUse hooks for custom permission evaluation

**OpenCode**:
- **@file fuzzy search**: `@` key triggers fuzzy file search in project — simple and effective [source: docs.opencode.ai/docs]
- **Share links**: `/share` creates a shareable conversation link [source: opencode.ai/docs/share]
- **Multi-session**: Parallel agents on same project
- **Image drag-and-drop**: Direct image injection into terminal chat
- **Plan/Build toggle**: `Tab` key switches — identical to ARC's design
- **Undo/Redo**: `/undo` and `/redo` for reverting AI changes

**Cursor**:
- **Agent mode**: Distinct Agent mode vs Chat — clear "ask" vs "run" separation
- **Model dropdown**: Visible above input, one-click switch
- **Activity feed**: Real-time agent status ("Thought 7s", "Editing files")
- **Inline diffs**: Accept/Reject per-hunk in editor context

**Aider**:
- **File-centric chat**: `aider file1.py file2.py` adds specific files to chat — explicit context control
- **Model switching mid-session**: `/model` command with 75+ provider support
- **Repo map**: Automatic codebase context injection without explicit file adds
- **Git integration**: All changes auto-committed, `/undo` reverts via git

**Codex CLI**:
- **Sandbox mode**: OS-level isolation for tool execution
- **Resume/fork**: Session continuation with fork capability

---

## Gaps

1. **No @-mention system**: ARC has no `@file`, `@folder`, or `@symbol` syntax. Every competitor except Codex CLI supports context mentions. This is a critical gap for a chat-first tool.

2. **No image/multimodal support**: Not mentioned in spec. OpenCode, Cursor, Windsurf, and Claude Code all support image input. ARC's agent workflows could benefit from screenshot-based HITL evidence.

3. **No message queueing**: Spec does not address what happens when the user types a message while a run is active. Claude Code, Cursor, Windsurf, and Copilot all queue messages.

4. **No "ask" vs "run" distinction**: ARC has Plan/Build/Auto modes but no explicit intent routing. User types "explain this workflow" vs "run the reviewer workflow" — both go through the same path. Cursor separates Chat from Agent mode explicitly.

5. **No chat history browsing**: ARC supports session resume (`/resume`) but no history list, search, or browsing. Users cannot reference past conversations without knowing the session ID.

6. **No copy/export/share**: No way to share a conversation transcript. OpenCode has `/share` with shareable links. Claude Code has session teleport and channels.

7. **No context compacting implementation**: `/compact` is listed in help text (§10.4) but has no implementation spec. Claude Code has auto-compaction with skill carry-forward. OpenCode has `/undo`/`/redo`.

8. **No web/URL context**: No way to inject web content or URLs into chat context. Claude Code has `@web`, Cursor has `@web`.

9. **No skills/custom commands**: ARC's slash commands are hardcoded. Claude Code's `SKILL.md` system and OpenCode's custom commands allow user-extensible commands.

10. **No multi-session**: Only one session per workspace. OpenCode supports parallel sessions. Claude Code supports background agents.

11. **No explicit streaming protocol**: Spec mentions streaming animation (§6.2) but not the wire protocol (SSE, WebSocket, or polling). CLI_IDE_REDESIGN_PLAN §7.5 recommends SSE.

12. **No chat model specification**: §17 open question: "Chat model source?" — what LLM powers the chat agent? This is unresolved.

---

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **Add `@file` mention syntax** | Every competitor supports context mentions. Users expect to reference files in chat. Without it, ARC chat is strictly less capable than Claude Code, OpenCode, Cursor, and Aider. | v0.1 | Medium — needs file resolution, token budget management, and UI autocomplete | §9 Input component: add `mentions` prop; §10.4: document `@` syntax; new §10.11: Context Mentions |
| **Add `@folder` mention** | Users need to reference directories for broader context. Complements `@file`. | v0.1 | Low — extends `@file` resolver | Same as `@file` |
| **Defer `@symbol` to v0.2** | Symbol resolution requires LSP integration or AST parsing. Adds complexity to v0.1. | v0.2 | Low if deferred | §10.11: mark `@symbol` as reserved |
| **Reserve image input protocol** | Don't implement in v0.1, but reserve the event shape and input affordance so multimodal can be added without breaking changes. | v0.1 (reserve) / v0.2 (implement) | Low — reservation only | §9 Input component: add `attachments` prop (optional); §7.2: add image card mock in transcript |
| **Add message queueing** | Without queueing, user input during an active run is lost or blocks. Claude Code and Cursor queue. ARC should too. | v0.1 | Medium — needs queue state management and UI indicator | §7.2: add queue indicator in status line; §7.14: add queue to session state |
| **Add "ask" vs "run" intent routing** | Plan/Build/Auto modes control permissions but not intent. A natural-language message like "explain this" should not trigger workflow execution. Intent routing prevents accidental runs. | v0.1 | Medium — needs intent classifier (LLM-based or rule-based) | §7.2: add intent detection flow; §7.13: add intent to mode description |
| **Add chat history list** | Session resume is not enough. Users need to browse, search, and reference past conversations. | v0.2 | Low — session files already exist, just need listing UI | §7.14.1: add `/sessions` command; §8.1: add history panel reservation |
| **Add `/share` command** | Shareable transcripts are table stakes for collaboration. OpenCode and Claude Code both support this. | v0.2 | Medium — needs hosted viewer or markdown export | §10.4: add `/share` to Session commands |
| **Implement `/compact`** | Listed in help but has no spec. Context compaction is essential for long sessions. Claude Code's auto-compaction with skill carry-forward is the benchmark. | v0.1 | Medium — needs LLM summarization and skill preservation logic | §10.4: expand `/compact` description; new §10.12: Context Compaction |
| **Reserve web/URL context** | Don't implement in v0.1, but reserve `@url` mention for future web context injection. | v0.1 (reserve) / v0.3 (implement) | Low — reservation only | §10.11: add `@url` as reserved |
| **Add skills system scaffold** | Custom slash commands are a major differentiator for Claude Code. ARC should support user-extensible commands, but a full SKILL.md system is v0.2 scope. | v0.1 (reserve) / v0.2 (implement) | Low if scaffolded | §10.8: add "Custom" tier to command tiers; §10.4: add `/skills` as reserved |
| **Specify streaming protocol** | SSE is recommended in CLI_IDE_REDESIGN_PLAN §7.5 but not locked in spec. Lock it now. | v0.1 | Low — decision only | §7.2: add streaming protocol note; §8.1: add SSE to IDE chat |
| **Resolve chat model question** | §17 lists "Chat model source?" as open. This must be resolved before implementation. | v0.1 | Low — decision only | §17: resolve to "Provider LLM via configured model" |
| **Add copy-to-clipboard for messages** | Basic UX. Users need to copy agent responses. | v0.1 | Low | §9 Card component: add copy action to message cards |
| **Defer multi-session to v0.2** | Parallel sessions add significant complexity to session lifecycle. Defer until v0.1 session model is stable. | v0.2 | Low if deferred | §7.14.1: add multi-session as reserved |

---

## Recommended Decisions

### 1. Support `@file` and `@folder` in v0.1
**Decision**: Yes. This is table stakes for a chat-first tool.

Implementation:
- `@` triggers autocomplete popup (already specified as `combobox` in §9 Input)
- `@filename` resolves to file path in workspace, reads content, injects into context
- `@folder/` resolves to directory, lists files, injects tree + selected file contents
- Token budget: max 16K tokens per mention, truncates with warning
- UI: autocomplete shows file path, size, and line count
- CLI: `@` autocomplete uses fuzzy match (like OpenCode)
- IDE: `@` autocomplete shows file icon, path, and size

### 2. Defer `@symbol` to v0.2
**Decision**: Yes. Symbol resolution requires LSP or AST parsing. Not worth the v0.1 complexity.

### 3. Reserve image input, don't implement in v0.1
**Decision**: Yes. Reserve the protocol shape but don't build image handling.

Reservation:
- Input component accepts optional `attachments` array
- Transcript can render `image` card type
- Event schema reserves `attachment` field
- Implementation deferred to v0.2 when HITL evidence workflows need screenshots

### 4. Support queued messages while run is active
**Decision**: Yes. Losing user input during active runs is unacceptable.

Implementation:
- Messages typed during active run are queued (FIFO)
- Status line shows `(1 queued)` indicator
- Queue processes after current run completes or is cancelled
- Max queue depth: 5 messages (warn at 3, block at 5)
- `/stop` cancels current run and clears queue (with confirmation)

### 5. Add intent routing (ask vs run) in v0.1
**Decision**: Yes, but keep it simple.

Implementation:
- Default: chat messages go to LLM for response (ask)
- Messages that match workflow execution patterns (e.g., "run X", "execute Y", "start Z") trigger run
- Plan mode: all messages are "ask" (no runs)
- Build mode: intent detection suggests run, asks for confirmation
- Auto mode: intent detection auto-runs matching patterns
- User can override with explicit `/run` command
- Intent classifier: simple keyword/pattern matching in v0.1, LLM-based in v0.2

### 6. Defer chat history browsing to v0.2
**Decision**: Yes. Session resume is sufficient for v0.1. History browsing adds UI complexity.

### 7. Defer `/share` to v0.2
**Decision**: Yes. Requires hosted viewer or export format. Not critical for v0.1.

### 8. Implement `/compact` in v0.1
**Decision**: Yes. It's already listed in help text. Must deliver.

Implementation:
- `/compact` sends conversation to LLM for summarization
- Summary replaces full transcript in context
- Invoked skills are carried forward (first 5K tokens each, max 25K total — matching Claude Code)
- Original transcript preserved in session file
- User sees: "Context compacted. {N} tokens → {M} tokens. {K} skills preserved."

### 9. Resolve chat model: use configured provider model
**Decision**: Chat uses the same model configured for workflow execution. No separate chat model.

Rationale:
- Simpler configuration
- Consistent behavior across chat and runs
- User controls model via `/model` command
- If user wants a cheaper model for chat, they can switch before chatting

### 10. Lock streaming protocol to SSE
**Decision**: SSE for both CLI and IDE streaming.

Rationale:
- Already recommended in CLI_IDE_REDESIGN_PLAN §7.5
- Existing event broker infrastructure uses SSE
- Simple, HTTP-based, works through proxies
- Reconnect semantics well-understood

---

## Specific Spec Edits

### §7.2 Steady-State Chat
- Add: "Messages typed during an active run are queued. Status line shows `(N queued)`. Queue processes after run completes. Max depth: 5."
- Add: "Input supports `@` mentions for files and folders. Typing `@` opens autocomplete popup with fuzzy file search."
- Add: "Intent detection classifies messages as 'ask' (LLM response) or 'run' (workflow execution). Plan mode forces 'ask'. Build mode asks for confirmation on 'run'. Auto mode auto-executes 'run'."

### §7.13 Plan / Build / Auto Chip
- Add to Plan: "All messages treated as 'ask'. No workflow execution."
- Add to Build: "Intent detection suggests 'run' actions. User confirms before execution."
- Add to Auto: "Intent detection auto-executes 'run' actions matching policy."

### §7.14 Status Line
- Add segment: `queue` — shows `(N queued)` when messages are queued
- Add segment: `intent` — shows `[ask]` or `[run]` when intent is detected (Build mode only)

### §7.14.1 Session Lifecycle Contract
- Add to per-session files: `queue.jsonl` — queued messages pending processing
- Add: "Multi-session reserved for v0.2. Single session per workspace in v0.1."

### §8.1 Default Workspace (IDE)
- Add: "Chat input supports `@` mentions with autocomplete dropdown."
- Add: "Messages during active run are queued with indicator in input area."
- Add: "SSE streaming from daemon event broker. Reconnect on disconnect."

### §9 Input Component
- Add to `InputProps`: `mentions?: Mention[]` where `Mention = { type: 'file' | 'folder'; path: string; content?: string; tokenCount?: number }`
- Add to `InputProps`: `attachments?: Attachment[]` where `Attachment = { type: 'image'; data: string; name: string }` (reserved, v0.2)
- Add to `InputProps`: `queueDepth?: number`
- Update placeholder: "Ask ARC Studio or @mention files..."

### §9 Card Component
- Add variant: `'image'` (reserved v0.2)
- Add to message cards: `onCopy?: () => void` action

### §10.4 Help Text
- Add to Session section:
  ```
  /sessions   list past sessions (reserved v0.2)
  /share      share conversation link (reserved v0.2)
  ```
- Expand `/compact` entry:
  ```
  /compact    summarise conversation to free tokens; skills carried forward
  ```

### New §10.11 Context Mentions
```
## 10.11 Context Mentions

| Mention | Resolves to | Token budget | v0.1 status |
|---|---|---|---|
| `@file.ext` | File content | 16K tokens max | Ships |
| `@folder/` | Directory tree + file contents | 32K tokens max | Ships |
| `@symbol` | Symbol definition (LSP) | 8K tokens max | Reserved v0.2 |
| `@url` | Web page content | 16K tokens max | Reserved v0.3 |

Mention autocomplete triggers on `@` key. Fuzzy match against workspace files.
Selected mention injects content into message context before sending.
Token budget exceeded: shows warning, truncates with ellipsis, user can remove mention.
CLI: autocomplete uses terminal popup. IDE: autocomplete uses dropdown (elevation.3).
```

### New §10.12 Context Compaction
```
## 10.12 Context Compaction

`/compact` triggers LLM summarization of current transcript.

Rules:
- Original transcript preserved in `transcript.jsonl` (not deleted)
- Summary replaces context for subsequent turns
- Invoked skills carried forward: first 5K tokens per skill, max 25K total
- User sees: "Context compacted. {N} tokens → {M} tokens. {K} skills preserved."
- Auto-compaction reserved for v0.2 (triggered when context reaches 80% capacity)
```

### §17 Open Questions
- Resolve "Chat model source?": **"Provider LLM via configured model. Chat uses the same model as workflow execution. Switch with `/model`."**
- Add: "Image input reserved for v0.2. Protocol shape reserved in §9 Input component."
- Add: "Multi-session reserved for v0.2. Single session per workspace in v0.1."
- Add: "Skills/custom commands reserved for v0.2. Hardcoded slash commands in v0.1."

---

## Acceptance Criteria

### v0.1 Chat Core
- [ ] `arc-studio` launches into chat REPL with no arguments
- [ ] Chat input accepts text and Enter submits
- [ ] `Ctrl+J` inserts newline in multiline input
- [ ] Streaming output renders token-by-token with cursor animation
- [ ] Tool call cards render in transcript with status indicators
- [ ] Paid-call cards render with provider, model, ceiling, and approval buttons
- [ ] HITL cards render with Approve/Reject/Edit actions
- [ ] Plan mode blocks all writes and paid calls
- [ ] Build mode asks for confirmation on destructive actions
- [ ] Auto mode follows `.arc/policy.yaml` approval policy
- [ ] Mode toggle (Tab in CLI, button in IDE) switches Plan/Build/Auto
- [ ] Session persists to platform-specific path with ULID ID
- [ ] `/resume` restores previous session
- [ ] Auto-resume offered when journal has unrendered turns
- [ ] `/compact` summarizes conversation and carries forward invoked skills
- [ ] Redaction contract enforced: no secrets in any chat surface
- [ ] All 20+ slash commands work
- [ ] `arc-studio advanced <cmd>` passes through to legacy `arc` commands

### v0.1 Context Mentions
- [ ] `@` triggers file/folder autocomplete in CLI and IDE
- [ ] `@filename` resolves and injects file content (max 16K tokens)
- [ ] `@folder/` resolves and injects directory tree + contents (max 32K tokens)
- [ ] Token budget exceeded shows warning and truncates
- [ ] Mentioned files appear as chips/tags in input before send
- [ ] User can remove mentions before sending

### v0.1 Message Queueing
- [ ] Messages typed during active run are queued
- [ ] Status line shows `(N queued)` indicator
- [ ] Queue processes in FIFO order after run completes
- [ ] Max queue depth: 5 (warn at 3, block at 5)
- [ ] `/stop` cancels run and clears queue with confirmation

### v0.1 Intent Routing
- [ ] Natural messages default to "ask" (LLM response)
- [ ] Messages matching run patterns ("run X", "execute Y") detected as "run" intent
- [ ] Plan mode: all messages forced to "ask"
- [ ] Build mode: "run" intent asks for confirmation
- [ ] Auto mode: "run" intent auto-executes per policy
- [ ] `/run` command bypasses intent detection

### v0.1 IDE Chat Panel
- [ ] Chat panel is default active tab in ARC Studio widget
- [ ] Chat input with send button and slash hints
- [ ] Runtime and model dropdowns above input
- [ ] Mode toggle in chat panel header
- [ ] `Ctrl/Cmd+;` focuses chat input
- [ ] `Ctrl/Cmd+Enter` sends message
- [ ] SSE streaming from daemon event broker
- [ ] @-mention autocomplete dropdown in IDE input

### v0.1 Protocol
- [ ] Streaming uses SSE for both CLI and IDE
- [ ] Chat model uses configured provider model (no separate chat model)
- [ ] Session schema includes `queue.jsonl` for pending messages
- [ ] Image attachment shape reserved in Input component (not implemented)
- [ ] `@symbol` and `@url` mentions reserved (not implemented)
- [ ] Multi-session reserved (not implemented)

---

## Reject / Do Not Build

### Rejected for v0.1

| Feature | Why rejected | Reconsider when |
|---|---|---|
| **`@symbol` mentions** | Requires LSP integration or AST parsing. Too complex for v0.1. | v0.2 when LSP infrastructure exists |
| **Image/multimodal input** | Requires image handling, base64 encoding, provider multimodal support. No v0.1 workflow needs it. | v0.2 when HITL evidence workflows need screenshots |
| **Web/URL context (`@url`)** | Requires web fetching, HTML-to-text conversion, token management. Not core to agent workflow cockpit. | v0.3 if users request web context injection |
| **Chat history browsing** | Session resume is sufficient for v0.1. History UI adds panel complexity. | v0.2 when session count grows and users need search |
| **`/share` conversation** | Requires hosted viewer or export format. Not critical for v0.1 local-first tool. | v0.2 when collaboration workflows are defined |
| **Multi-session (parallel)** | Significant session lifecycle complexity. Single session per workspace is sufficient for v0.1. | v0.2 when users need parallel agent workflows |
| **Skills/custom commands** | Claude Code's SKILL.md system is powerful but requires directory watching, frontmatter parsing, dynamic context injection, and subagent execution. Too large for v0.1. | v0.2 when slash command set is stable and users request extensibility |
| **Auto-compaction** | Manual `/compact` is sufficient for v0.1. Auto-compaction requires context monitoring and trigger logic. | v0.2 when long sessions become common |
| **Separate chat model** | Adds configuration complexity with marginal benefit. Users can switch model via `/model` if needed. | Reconsider if users consistently want cheap chat + expensive runs |
| **Message editing** | Editing sent messages adds transcript mutation complexity. Users can re-prompt instead. | v0.3 if users request it |
| **Chat search** | Full-text search across sessions is v0.2+ scope. | v0.2 when history browsing exists |
| **Voice input** | Out of scope for v0.1 agent cockpit. | Never, unless explicitly requested |
| **Emoji reactions on messages** | Cosmetic. Not aligned with honest/observable brand attributes. | Never |
| **Chat themes per session** | Global theme is sufficient. Per-session themes add unnecessary complexity. | Never |

### Explicitly Keeping

| Feature | Why keep |
|---|---|
| **Chat-first CLI default** | Core product differentiator. Every competitor does this. ARC must too. |
| **SwarmGraph default and bundled** | Core runtime. Not negotiable. |
| **Plan/Build/Auto modes** | Matches market pattern (Claude Code, OpenCode, Cursor). Well-specified in ARC. |
| **Paid-call gating** | Unique ARC strength. No competitor has per-call cost confirmation with policy. |
| **HITL cards** | Core to high-assurance workflows. Differentiates from generic chat tools. |
| **Session sharing between CLI and IDE** | Unique ARC capability. No competitor supports shared CLI/IDE sessions. |
| **Redaction contract** | Security requirement. Non-negotiable. |
| **Advanced command passthrough** | Preserves backward compatibility with 60+ existing `arc` commands. |
