# MCP / ACP Integrations Review

## Current ARC Spec

**MCP (Model Context Protocol) and ACP (Agent Client Protocol) are not addressed in the ARC Studio UX spec.** Neither protocol appears in `ARC_STUDIO_UX_SPEC.md`, `CLI_IDE_REDESIGN_PLAN.md`, or `IMPLEMENTATION_PLAN.md` as a planned feature.

The only MCP/ACP references in the codebase are:

| Location | Content |
|---|---|
| `docs/research/feature-roadmap-review/04-handoff-protocol.md:78-79` | Brief comparison rows noting MCP is a tool-calling protocol (not workflow orchestrator) and ACP is a draft agent-to-agent message spec. No ARC implementation. |
| `docs/IMPLEMENTATION_PLAN.md:148,157` | Mobile framework roadmap mentions "MCP tools" as a future mobile agent concept; maps to "Worker tools gated by permission manifest." Not ARC Studio scope. |
| `docs/SECURITY.md:33-35` | Generic warning: "Only install plugins and MCP/tool servers from trusted sources." No implementation. |
| `docs/archive/RESEARCH_NOTES.md:606` | Historical reference to `mcp-toolbox` for SwarmGraph + Flutter workflows. Not productized. |
| Python codebase | Zero MCP server or client code. No `mcp` package dependency. |
| TypeScript codebase | Zero MCP server or client code. No `@modelcontextprotocol` dependency. |

**What the spec reserves that is tangentially related:**

- `handoff` event kind (Appendix B): Inter-runtime phase boundary transfer — conceptually adjacent to ACP agent delegation, but different scope. Handoff is about runtime-to-runtime state transfer within ARC; ACP is about editor-to-agent communication.
- Tool cards in Chat (§7.2, §9): The spec defines tool call rendering in chat transcripts. MCP tools would slot into this same rendering path if consumed.
- Plan/Build/Auto permission modes (§7.13): MCP tool permissions would need to map to these modes.
- Workspace trust (§7.18): MCP servers execute arbitrary code; trust gates are relevant.
- `/config` panel (§7.3, §8.6): MCP server configuration would need a tab or section here.

**Bottom line:** The spec is silent on MCP/ACP. This is correct for v0.1 — the spec focuses on SwarmGraph orchestration, runtime adoption, and core cockpit UX. MCP consumption and ACP compatibility are expansion features that depend on a stable chat/session/tool-card foundation.

---

## Comparable Products / Research

### MCP Integration

| Product | MCP Server Config | MCP Tools in Chat | MCP Permissions | Tool Cards | OAuth/Auth | Sandboxing | Source |
|---|---|---|---|---|---|---|---|
| **Claude Code** | `claude mcp add` CLI, `.mcp.json` (local/project/user scope), JSON add, Claude Desktop import, plugin-bundled servers, managed enterprise config | Tools auto-available in chat; tool search defers schemas to reduce context; `@` resource mentions; MCP prompts as `/` commands | Per-server trust dialog; `permissions.deny` for specific tools; managed allowlists/denylists; `alwaysLoad` per server | Tool calls rendered as cards in chat; output warnings at 10K tokens; configurable `MAX_MCP_OUTPUT_TOKENS` | OAuth 2.0 with DCR, pre-registered clients, fixed callback ports, dynamic headers, scope pinning | No process sandbox; trust-based; `headersHelper` for custom auth; workspace trust gate for arbitrary commands | [docs.anthropic.com](https://docs.anthropic.com/en/docs/claude-code/mcp) |
| **VS Code Copilot** | `mcp.json` (workspace/user profile), Extensions view `@mcp` gallery, CLI `--add-mcp`, Dev Container integration, settings sync | Tools available in agent chat; "Configure Tools" button to toggle per-server; MCP resources as `@` context; MCP prompts; MCP Apps (interactive UI) | Trust dialog on first start; per-server enable/disable; enterprise GitHub policies; auto-approve for sandboxed servers | Tool invocations shown in chat; inline confirmation prompts | Not documented for OAuth in VS Code layer (relies on server-side auth) | **Sandbox mode** on macOS/Linux: filesystem + network restrictions; auto-approve for sandboxed tools | [code.visualstudio.com](https://code.visualstudio.com/docs/copilot/chat/mcp-servers) |
| **OpenCode** | `opencode.jsonc` with `mcp` section; local (`type: "local"`) and remote (`type: "remote"`); env vars; per-agent tool enable/disable | MCP tools auto-available alongside built-in tools; referenced by server name in prompts; AGENTS.md rules can direct tool usage | Global tool enable/disable via `tools` config; per-agent tool scoping; glob patterns for bulk control (`"my-mcp*": false`) | Not explicitly documented; tools appear in chat transcript | OAuth 2.0 with DCR; `opencode mcp auth`; token storage in `~/.local/share/opencode/mcp-auth.json`; `mcp logout`; manual trigger | No process sandbox documented; trust-based | [opencode.ai/docs/mcp-servers](https://opencode.ai/docs/mcp-servers) |
| **Cursor** | `.cursor/mcp.json` (workspace); UI settings for server management | Tools available in agent chat; MCP server management in settings | Trust-based; per-server enable/disable | Not documented in detail | Not documented | Not documented | [cursor.com/docs](https://cursor.com/docs/context/mcp) [needs verification] |
| **Codex CLI** | No documented MCP support as of research date | N/A | N/A | N/A | N/A | N/A | [needs verification] |
| **MCP Ecosystem** | Protocol: JSON-RPC over stdio/SSE/HTTP; `tools/list`, `resources/list`, `prompts/list`; `tool_reference` for deferred loading; `list_changed` notifications; elicitation for interactive input | Client-side rendering is implementation-specific; MCP spec defines the wire protocol, not the UI | Server-side trust; client-side permissioning is implementation-specific; spec does not mandate permissions | N/A (protocol-level) | OAuth 2.0 via RFC 7591 DCR; spec-agnostic to auth implementation | No sandboxing in spec; implementation-specific | [modelcontextprotocol.io](https://modelcontextprotocol.io/introduction) |

### ACP Integration

| Product | ACP Support | How It Works | Editor Support | Source |
|---|---|---|---|---|
| **OpenCode** | Yes — `opencode acp` subcommand | Starts OpenCode as ACP-compatible subprocess; JSON-RPC over stdio; all features work (tools, MCP, rules, agents); `/undo` and `/redo` currently unsupported | Zed, JetBrains IDEs, Avante.nvim, CodeCompanion.nvim | [opencode.ai/docs/acp](https://opencode.ai/docs/acp) |
| **Zed** | Yes — ACP client | `agent_servers` config with `command` + `args`; external agent threads | N/A (is the client) | [zed.dev/blog/acp-progress-report](https://zed.dev/blog/acp-progress-report) |
| **JetBrains** | Yes — ACP client | `acp.json` with `agent_servers` config; AI Chat agent selector | N/A (is the client) | [jetbrains.com/help/ai-assistant/acp.html](https://www.jetbrains.com/help/ai-assistant/acp.html) |
| **Claude Code** | No documented ACP support | N/A | N/A | [needs verification] |
| **VS Code Copilot** | No documented ACP support | Uses native Copilot protocol, not ACP | N/A | [needs verification] |
| **ACP Spec** | Open protocol at [agentclientprotocol.com](https://agentclientprotocol.com) | Standardizes editor↔agent communication via JSON-RPC over stdio; defines session management, tool calling, streaming, cancellation | Growing editor support: Zed, JetBrains, Neovim plugins | [agentclientprotocol.com](https://agentclientprotocol.com) |

### Key Observations

1. **MCP consumption is now table stakes for coding agents.** Claude Code, VS Code Copilot, OpenCode, and Cursor all support MCP server configuration and tool consumption. Not supporting MCP puts ARC at a competitive disadvantage for users who want external tool integration.

2. **MCP permission models are converging on trust + granularity.** All products require a trust confirmation on first server start. Claude Code and VS Code add per-tool deny lists. OpenCode adds per-agent tool scoping. The pattern: trust the server, then control which tools are available where.

3. **Tool search / deferral is critical for context management.** Claude Code's `ENABLE_TOOL_SEARCH` defers tool schemas until needed, reducing context window pressure. VS Code Copilot uses a similar approach. This matters when users connect multiple MCP servers.

4. **Sandboxing is emerging as a differentiator.** VS Code Copilot supports filesystem + network sandboxing for stdio MCP servers on macOS/Linux. Claude Code relies on trust only. ARC's existing isolation provider architecture (§P1a-P3) could support MCP sandboxing naturally.

5. **ACP is an editor-side protocol, not an agent-side feature.** ACP defines how editors talk to agents. OpenCode implements `opencode acp` as a subcommand that starts the agent in ACP-compatible mode. For ARC Studio (which IS the IDE), ACP support would mean either:
   - Exposing ARC as an ACP server so external editors (Zed, JetBrains) can use ARC as their agent backend
   - Consuming ACP-compatible agents within ARC's IDE surface
   The first is more aligned with ARC's positioning as a cockpit.

6. **No product combines MCP + SwarmGraph-style adoption.** MCP tools are consumed directly by the LLM in all products examined. ARC's unique positioning — wrapping external runtimes in SwarmGraph queen/worker/consensus orchestration — could extend to MCP tools: MCP servers become typed workers under SwarmGraph coordination, with audit, HITL, and cost controls applied uniformly.

7. **OAuth for MCP is maturing.** Claude Code and OpenCode both support OAuth 2.0 with Dynamic Client Registration. This is relevant for remote MCP servers (Sentry, GitHub, Notion). ARC would need OAuth support if it consumes remote MCP servers.

---

## Gaps

### No MCP Server Configuration

ARC has no way to configure, start, stop, or manage MCP servers. No CLI commands, no IDE UI, no config schema entries, no protocol types. Users cannot connect external tools.

### No MCP Tool Consumption

Even if MCP servers were configured, ARC has no mechanism to:
- Discover tools from MCP servers (`tools/list`)
- Inject MCP tool schemas into the LLM's tool set
- Route tool calls from the LLM to MCP servers (`tools/call`)
- Render MCP tool results in chat tool cards
- Handle MCP tool errors, timeouts, or large outputs

### No MCP Permission Model

The existing Plan/Build/Auto modes (§7.13) have no MCP-specific rules. Questions unanswered:
- Should Plan mode block all MCP tool calls? (Probably yes — MCP tools can write files, call APIs.)
- Should Build mode require per-tool approval for MCP tools? Or per-server?
- Should Auto mode auto-approve specific MCP servers?
- How do MCP permissions interact with workspace trust?
- How do MCP permissions interact with paid-call gating?

### No MCP Context Management

MCP tools consume context window tokens. ARC has no:
- Tool deferral/search mechanism (like Claude Code's `ENABLE_TOOL_SEARCH`)
- Context budget warnings for MCP tool schemas
- Per-server context limits
- Tool output size warnings (Claude Code warns at 10K tokens)

### No MCP Sandboxing

ARC's isolation provider architecture supports subprocess and Docker isolation, but MCP servers are not routed through it. A malicious or compromised MCP server could:
- Read workspace files
- Execute arbitrary commands
- Exfiltrate data via network calls
- Inject prompt-injection payloads

VS Code Copilot's sandbox model (filesystem + network restrictions) is a good reference. ARC's existing isolation infrastructure could support this.

### No ACP Server Mode

ARC cannot act as an ACP-compatible agent server. External editors (Zed, JetBrains, Neovim) cannot use ARC as their agent backend. This limits ARC's reach beyond its own IDE surface.

### No ACP Client Mode

ARC's IDE cannot connect to external ACP-compatible agents. This is less critical since ARC is itself the cockpit, but it means ARC cannot delegate to external agents via ACP.

### No MCP/ACP in Protocol Types

`arc-protocol-types.ts` has no MCP or ACP-related types. No `McpServer`, `McpTool`, `McpToolCall`, `AcpSession`, or related interfaces.

### No MCP/ACP in Config Schema

The ADR-001 config model (`ArcConfig`) has no MCP or ACP sections. No `mcp.servers`, `mcp.enabled`, `acp.enabled`, or related fields.

### No MCP/ACP in CLI

No `arc mcp *` or `arc acp *` commands. No server management, auth, debugging, or status commands.

### No MCP/ACP in IDE

No MCP server management UI, no tool configuration panel, no ACP connection status, no MCP tool cards distinct from built-in tool cards.

### Naming Collision Risk

The spec reserves `handoff` for inter-runtime phase transfer. ACP also uses "handoff" terminology for agent delegation. If ARC implements both, naming must be explicit (the handoff protocol review already flagged this for intra-runtime vs inter-runtime; ACP adds a third concept).

---

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **Reserve MCP config schema in ArcConfig** | Future-proof the config model; define `mcp.servers` structure now so it doesn't conflict later | v0.1 (reservation only) | Low. Additive schema change; no behavior. | ADR-001: add `mcp` section skeleton. §8.6 Config: add MCP tab placeholder. |
| **Reserve MCP tab in IDE Config panel** | MCP server management needs a home in the IDE. Reserve the tab slot in v0.1 with an empty/coming-soon state. | v0.1 (reservation only) | Low. One tab entry in Config panel spec. | §8.6: add MCP tab to config panel list. §9: add McpServerList component reservation. |
| **Define MCP permission mapping to Plan/Build/Auto** | MCP tools need explicit permission rules per mode. Plan should block MCP calls; Build should ask; Auto should follow policy. | v0.2 (before MCP consumption) | Medium. Permission model must be designed before any MCP tool routing. | §7.13: add MCP permission rows to `/auto` policy table. §10.7: add MCP permission microcopy. |
| **Add MCP server configuration CLI** | `arc mcp add/list/remove/get/status/debug` commands for server management. Matches Claude Code/OpenCode patterns. | v0.2 | Medium. CLI commands need config schema + server lifecycle management. | New CLI section in spec. §7.10 `/doctor`: add MCP server health checks. |
| **Add MCP tool consumption in chat** | Wire MCP tools into the LLM tool set; route `tools/call` to MCP servers; render results in existing tool cards. | v0.2 | High. Requires chat agent architecture, tool routing, MCP SDK integration, error handling. | §7.2: add MCP tool card variant. §9: extend ToolCard props for MCP metadata. |
| **Add MCP tool deferral/search** | Prevent context window exhaustion from multiple MCP servers. Defer tool schemas until needed. | v0.2 (with MCP consumption) | Medium. Requires model support for deferred tool references (Sonnet 4+, Opus 4+). | §7.2: add tool search behavior description. |
| **Add MCP sandboxing via isolation providers** | Route stdio MCP servers through existing isolation infrastructure. Apply filesystem + network restrictions. | v0.2 (with MCP consumption) | High. Requires isolation provider integration with MCP server lifecycle. | §8.6: add MCP sandbox config. P1a isolation docs: add MCP server routing. |
| **Add MCP OAuth support** | Remote MCP servers need OAuth. Reuse existing keychain infrastructure. | v0.2 (with remote MCP) | Medium. OAuth flow requires browser redirect, token storage, refresh logic. | §7.4 `/providers`: add OAuth flow for MCP. §8.6: add MCP auth config. |
| **Add ACP server mode (`arc acp serve`)** | Expose ARC as an ACP-compatible agent server. External editors can use ARC as backend. | v0.3 | High. ACP spec compliance, JSON-RPC over stdio, session management, tool mapping. | New ACP section in spec. CLI: add `arc acp serve`. |
| **Add MCP output size warnings** | MCP tools can produce large outputs that consume context. Warn at threshold, configurable limit. | v0.2 (with MCP consumption) | Low. Simple token count check + warning UI. | §7.2: add MCP output warning microcopy. §9: add ToolCard overflow state. |
| **Add MCP server health monitoring** | MCP servers can crash, disconnect, or become unresponsive. Show status in IDE and CLI. | v0.2 | Low. Health check is a simple `ping` or `tools/list` probe. | §7.10 `/doctor`: add MCP server health. §8.5: add MCP server status indicator. |
| **Add per-agent MCP tool scoping** | Like OpenCode, allow MCP tools to be enabled per agent/runtime. SwarmGraph queen might need different tools than workers. | v0.3 | Medium. Requires agent-level tool configuration. | §8.6: add per-agent MCP config. §9: add agent tool scoping UI. |
| **Add MCP elicitation support** | MCP servers can request interactive input mid-task (forms, URLs). ARC needs to render elicitation dialogs. | v0.2 (with MCP consumption) | Medium. Elicitation requires interactive UI in chat flow. | §9: add McpElicitationCard component. §7.2: add elicitation flow. |
| **Add MCP resources as `@` context** | MCP resources (data, docs, tables) can be attached to prompts via `@` mentions. | v0.2 (with MCP consumption) | Low. `@` autocomplete already exists conceptually; add MCP resource source. | §7.2: add `@` MCP resource mention. §9: extend autocomplete for MCP resources. |
| **Add MCP prompts as slash commands** | MCP servers can expose prompt templates that become `/` commands. | v0.2 (with MCP consumption) | Low. Dynamic slash command registration from MCP prompts. | §2.4: add MCP prompt slash command pattern. |

---

## Recommended Decisions

### Decision 1: MCP consumption is v0.2, not v0.1

**Rationale:** v0.1 scope is already tight: chat-first CLI, runtime selection, SwarmGraph execution, provider keys, workspace trust, sessions, daemon lifecycle, basic graph, runs panel, review/apply. Adding MCP server management, tool routing, OAuth, sandboxing, and context management would blow v0.1 scope and delay release. MCP is a force multiplier that depends on a stable chat/tool-card foundation. Build the foundation first.

**Action:** Mark MCP as "Reserved v0.2" in the spec. Add schema reservations but no behavior.

### Decision 2: ACP server mode is v0.3

**Rationale:** ACP server mode exposes ARC as an agent backend for external editors. This is valuable for ecosystem reach but depends on:
1. A stable chat agent architecture (v0.2)
2. MCP consumption working (v0.2)
3. ACP spec compliance testing against Zed, JetBrains, Neovim

This is a distribution play, not a core product feature. Defer to v0.3.

**Action:** Note ACP server mode in the spec as "Reserved v0.3." No code in v0.1 or v0.2.

### Decision 3: MCP permissions map to Plan/Build/Auto as follows

| Mode | MCP Tools | Rationale |
|---|---|---|
| **Plan** | Blocked entirely | Plan mode is read-only. MCP tools can write files, call APIs, execute commands. Block all MCP tool calls in Plan mode. |
| **Build** | Ask per tool call | Build mode requires approval for destructive actions. MCP tool calls should require per-call approval, matching built-in tool behavior. |
| **Auto** | Follow policy | Auto mode follows `/auto` policy. Add `mcp_tools: ask/auto/deny` to policy YAML. Default: `ask`. Users can auto-approve specific servers via config. |

**Action:** Add MCP permission rows to §7.13 `/auto` policy table.

### Decision 4: MCP servers are configured via `.arc/mcp.json` (not in `.arc/config.yaml`)

**Rationale:** MCP server configuration is a distinct concern from runtime/model/provider config. Separating it:
- Matches industry convention (`.mcp.json` in Claude Code, VS Code, Cursor)
- Allows project-scoped MCP config to be committed to git without mixing with user-specific config
- Simplifies config schema; MCP config has its own structure (command, args, env, url, headers, oauth)

Config precedence: workspace `.arc/mcp.json` > user `~/.config/arc-studio/mcp.json` > built-in defaults.

**Action:** Define in v0.2 MCP spec. Reference in §8.6 Config.

### Decision 5: MCP sandboxing uses existing isolation provider infrastructure

**Rationale:** ARC already has `IsolationProvider` architecture with `none`, `subprocess`, and `docker` providers. MCP servers should route through the same infrastructure:
- `sandboxEnabled: true` → route through `subprocess` or `docker` isolation
- Filesystem restrictions map to isolation provider's env/path filtering
- Network restrictions map to isolation provider's network policy

This avoids duplicating sandbox logic and leverages existing tested infrastructure.

**Action:** Define in v0.2 MCP spec. Update isolation provider docs to include MCP server routing.

### Decision 6: MCP tool cards reuse existing ToolCard component

**Rationale:** The spec already defines tool card rendering in chat (§7.2, §9). MCP tools should use the same visual treatment with additional metadata:
- Server name badge
- Tool name
- Execution status (running, completed, failed)
- Output (truncated if large)
- Warning for large outputs

No new component needed; extend existing `ToolCard` props with MCP-specific fields.

**Action:** Extend ToolCard spec in §9 with MCP metadata fields.

### Decision 7: ARC should NOT consume MCP tools in the SwarmGraph adoption layer (v0.2)

**Rationale:** MCP tools are LLM-facing tools, not runtime-facing workers. In v0.2, MCP tools should be consumed directly by the chat agent (like Claude Code/OpenCode), not wrapped as SwarmGraph workers. SwarmGraph wrapping of MCP tools is a v0.3+ feature that requires:
- Stable MCP consumption
- Typed worker interfaces
- Audit chain integration
- Consensus over tool outputs

Start simple: MCP tools are direct LLM tools in v0.2. Consider SwarmGraph wrapping in v0.3 if there's a clear use case for consensus over MCP tool outputs.

**Action:** Document this decision in v0.2 MCP implementation plan.

### Decision 8: Reserve `mcp` and `acp` sections in protocol types

**Rationale:** TypeScript protocol types need reserved slots for MCP and ACP to avoid future breaking changes. Add empty interfaces or type stubs in v0.1 so future additions are additive.

**Action:** Add `McpServerConfig`, `McpTool`, `McpToolCall` interfaces as reserved/empty in `arc-protocol-types.ts`. Add `AcpSession` stub.

---

## Specific Spec Edits

### §0.5 v0.1 Scope — Add MCP/ACP to "Out Of Scope" table

**Add rows:**

| Area | Deferred |
|---|---|
| MCP server configuration | No MCP server management in v0.1. Reserved for v0.2. |
| MCP tool consumption | MCP tools not consumed in v0.1. Reserved for v0.2. |
| ACP server mode | ARC as ACP agent server deferred to v0.3. |

### §0.5 Reserved In v0.1 Protocol — Add MCP/ACP reservations

**Add rows:**

| Reservation | Purpose |
|---|---|
| `mcp` config section | MCP server configuration schema (`.arc/mcp.json`); no v0.1 behavior. |
| `mcp` tool card metadata | MCP server name, tool name, output size warnings; rendered via existing ToolCard. |
| `acp` protocol types | ACP session types for future editor integration; no v0.1 behavior. |

### §7.13 `/auto` Policy — Add MCP permission rows

**Add to policy YAML:**

```yaml
approvals:
  paid_calls: ask
  destructive_writes: ask
  trust_changes: deny
  shell_exec: deny
  phase_advance: ask
  mcp_tools: ask          # v0.2: MCP tool call approval policy
  mcp_server_start: ask   # v0.2: MCP server start approval (trust gate)
```

**Add microcopy:**

| Policy | Plan | Build | Auto (default) |
|---|---|---|---|
| `mcp_tools` | deny (hardcoded) | ask | ask |
| `mcp_server_start` | deny (hardcoded) | ask | ask |

### §8.6 Config — Add MCP tab reservation

**Add to Config tabs list:**

| Tab | v0.1 | v0.2 |
|---|---|---|
| MCP | Hidden/reserved | Server list, add/remove, enable/disable, sandbox config, OAuth status |

### §9 Component Library — Add MCP component reservations

**Add:**

| Component | v0.1 Status | Props (reserved) |
|---|---|---|
| `McpServerList` | Reserved v0.2 | `servers: McpServerConfig[]`, `onAdd`, `onRemove`, `onToggle`, `onDebug` |
| `McpServerCard` | Reserved v0.2 | `server: McpServerConfig`, `status: 'connected'/'disconnected'/'error'`, `toolCount: number`, `sandboxed: boolean` |
| `McpElicitationCard` | Reserved v0.2 | `serverName: string`, `formFields: ElicitationField[]`, `onSubmit`, `onCancel` |

**Extend `ToolCard` props:**

```ts
interface ToolCardProps {
  // Existing props...
  toolName: string;
  status: 'running' | 'completed' | 'failed';
  output?: string;
  // NEW: MCP metadata (v0.2)
  mcpServerName?: string;       // undefined for built-in tools
  mcpToolOutputTokens?: number; // for output size warnings
  mcpOutputWarning?: string;    // "Output exceeds 10K tokens"
  mcpSandboxed?: boolean;       // true if server runs in sandbox
}
```

### §7.2 Steady-State Chat — Add MCP tool card example

**Add after existing tool card example:**

```text
┌ tool: sentry__list_issues (MCP) ────────────────────────────────────────────────────────────────┐
│ ✓ found 12 unresolved issues in project/my-project                                              │
│ Server: sentry | Output: 3.2K tokens                                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Add MCP output warning card:**

```text
┌ tool: postgres__query (MCP) ────────────────────────────────────────────────────────────────────┐
│ ! Output exceeds 10K tokens (18.4K). Truncated.                                                 │
│ Server: postgres | Full output persisted to disk.                                                │
│ [View full output] [Increase limit]                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### §7.10 `/doctor` — Add MCP server health checks

**Add:**

```text
✓ MCP: github connected (14 tools)
✓ MCP: sentry connected (8 tools, OAuth authenticated)
! MCP: postgres disconnected (connection refused)
  Fix: Check PostgreSQL is running or remove server from .arc/mcp.json
✗ MCP: untrusted-server blocked (untrusted source)
  Fix: Run arc mcp trust untrusted-server to allow.
```

### §10.7 Content — Add MCP microcopy

**Add:**

| Context | Copy |
|---|---|
| MCP server trust prompt | `This MCP server will run locally and can access files and execute commands. Only add servers from trusted sources.` |
| MCP OAuth prompt | `{server} requires authentication. Open browser to authorize?` |
| MCP tool blocked (Plan) | `MCP tools are disabled in Plan mode. Switch to Build to use external tools.` |
| MCP server start failed | `MCP server {name} failed to start: {reason}. Run arc mcp debug {name} for details.` |
| MCP output warning | `MCP tool output exceeds 10K tokens ({actual}K). Truncated to preserve context.` |
| MCP sandbox info | `This MCP server runs in a sandbox with restricted filesystem and network access.` |

### `arc-protocol-types.ts` — Add reserved MCP/ACP types

**Add:**

```ts
// ── MCP (reserved v0.2) ─────────────────────────────────────────────────────
export interface McpServerConfig {
  type: 'local' | 'remote';
  command?: string[];       // local: command + args
  url?: string;             // remote: server URL
  environment?: Record<string, string>;
  headers?: Record<string, string>;
  enabled?: boolean;
  sandboxEnabled?: boolean;
  timeout?: number;
  oauth?: {
    clientId?: string;
    clientSecret?: string;
    scope?: string;
  };
}

export interface McpTool {
  name: string;
  description: string;
  serverName: string;
  inputSchema: Record<string, unknown>;
}

export interface McpToolCall {
  toolName: string;
  serverName: string;
  arguments: Record<string, unknown>;
  status: 'running' | 'completed' | 'failed';
  output?: string;
  outputTokens?: number;
  error?: string;
}

// ── ACP (reserved v0.3) ─────────────────────────────────────────────────────
export interface AcpSession {
  sessionId: string;
  status: 'active' | 'closed' | 'error';
}
```

---

## Acceptance Criteria

### v0.1 Reservations

- [ ] MCP listed as "Out Of Scope" in §0.5 with explicit deferral to v0.2
- [ ] ACP listed as "Out Of Scope" in §0.5 with explicit deferral to v0.3
- [ ] `mcp` config section reserved in §0.5 protocol reservations
- [ ] `acp` protocol types reserved in §0.5 protocol reservations
- [ ] MCP tab reserved in §8.6 Config panel (hidden in v0.1)
- [ ] MCP component reservations added to §9 (McpServerList, McpServerCard, McpElicitationCard)
- [ ] ToolCard props extended with optional MCP metadata fields
- [ ] `arc-protocol-types.ts` includes reserved McpServerConfig, McpTool, McpToolCall, AcpSession interfaces
- [ ] No MCP/ACP behavior ships in v0.1 (no code, no commands, no UI)

### v0.2 MCP Consumption (future)

- [ ] `arc mcp add/list/remove/get/status/debug` CLI commands exist
- [ ] `.arc/mcp.json` config file format defined and parsed
- [ ] MCP servers can be configured as local (stdio) and remote (HTTP/SSE)
- [ ] MCP server lifecycle: start, stop, reconnect, health check
- [ ] MCP tools discovered via `tools/list` and injected into LLM tool set
- [ ] MCP tool calls routed via `tools/call` to correct server
- [ ] MCP tool results rendered in existing ToolCard component with MCP metadata
- [ ] MCP tool output warnings at 10K token threshold
- [ ] MCP permissions mapped to Plan/Build/Auto modes
- [ ] Plan mode blocks all MCP tool calls (hardcoded deny)
- [ ] Build mode asks per MCP tool call
- [ ] Auto mode follows `mcp_tools` policy
- [ ] MCP server trust confirmation on first start
- [ ] OAuth 2.0 support for remote MCP servers (DCR + pre-registered)
- [ ] MCP sandboxing via isolation providers (filesystem + network restrictions)
- [ ] MCP resources available as `@` context mentions
- [ ] MCP prompts available as slash commands
- [ ] MCP elicitation dialogs rendered in chat
- [ ] MCP server health checks in `arc doctor`
- [ ] MCP server status visible in IDE Config > MCP tab
- [ ] Python tests for MCP server lifecycle, tool routing, error handling
- [ ] TypeScript tests for MCP config parsing, tool card rendering

### v0.3 ACP Server Mode (future)

- [ ] `arc acp serve` command starts ACP-compatible JSON-RPC server over stdio
- [ ] ACP session management (create, close, list)
- [ ] ACP tool mapping: ARC tools exposed to ACP clients
- [ ] ACP streaming responses
- [ ] ACP cancellation support
- [ ] Tested against Zed, JetBrains IDEs, Avante.nvim
- [ ] ACP documentation for editor configuration

---

## Reject / Do Not Build

### Rejected: MCP as SwarmGraph workers in v0.2

**Considered:** Wrapping MCP tools as SwarmGraph workers under queen/worker orchestration, applying consensus and audit to MCP tool outputs.

**Rejected for v0.2:** MCP tools are LLM-facing tools, not runtime workers. Wrapping them as SwarmGraph workers adds complexity without clear user benefit in v0.2. The LLM already decides when to call MCP tools; adding a queen coordination layer on top would add latency and complexity. Revisit in v0.3 if there's a clear use case for consensus over MCP tool outputs (e.g., multiple MCP tools queried and consensus needed on the result).

### Rejected: ACP client mode in ARC IDE

**Considered:** ARC IDE connects to external ACP-compatible agents as a client.

**Rejected:** ARC IS the agent cockpit. Its value proposition is orchestrating runtimes, not delegating to external agents via ACP. If users want to use external agents, they should use those agents' native interfaces. ACP client mode would dilute ARC's positioning and add maintenance burden for a feature that competes with ARC's core value.

### Rejected: MCP server marketplace in v0.2

**Considered:** A curated gallery of MCP servers with one-click install, similar to VS Code's Extensions view `@mcp` gallery.

**Rejected for v0.2:** A marketplace requires curation, security review, publisher verification, and ongoing maintenance. v0.2 should focus on the mechanics of MCP consumption. Users can configure servers manually via `.arc/mcp.json`. A marketplace is a v0.3+ feature after MCP consumption is stable and there's data on which servers are commonly used.

### Rejected: MCP server auto-discovery from Claude Desktop / VS Code configs

**Considered:** Automatically import MCP server configurations from Claude Desktop's `claude_desktop_config.json` or VS Code's `mcp.json`.

**Rejected for v0.2:** Import logic adds complexity and creates maintenance burden as those formats evolve. v0.2 should focus on ARC's own MCP config format. Users can manually copy configs. Auto-import can be added in v0.3 if there's demand.

### Rejected: MCP as a replacement for built-in tools

**Considered:** Replace ARC's built-in tools (file operations, shell execution, code search) with MCP servers.

**Rejected:** Built-in tools are tightly integrated with ARC's permission model, workspace trust, cost controls, and audit chain. MCP servers are external and untrusted. Built-in tools should remain first-class citizens with full integration. MCP tools are supplementary, not replacements.

### Rejected: ACP as the primary chat protocol

**Considered:** Use ACP as the internal protocol between ARC's CLI and IDE, replacing the current JSON-RPC/SSE architecture.

**Rejected:** ARC already has a working protocol architecture (JSON-RPC over Theia connection, SSE for events). ACP is designed for editor-to-agent communication, not internal IDE architecture. Migrating to ACP internally would be a massive refactor with no user-visible benefit. ACP should only be used for external editor integration.

### Do Not Build: MCP server hosting platform

**Deferred indefinitely:** ARC should not become a platform for hosting or publishing MCP servers. ARC is a cockpit for running and observing agent workflows, not an MCP server marketplace or hosting provider. If users want to build MCP servers, they should use the MCP SDK and publish to existing directories (Anthropic Directory, MCPJam, etc.).

### Do Not Build: MCP-to-SwarmGraph tool adapter

**Deferred to v0.3+:** An adapter that converts MCP tool schemas into SwarmGraph worker tool definitions would enable SwarmGraph queens to call MCP tools as workers. This is architecturally interesting but premature. v0.2 should prove MCP consumption in the chat agent first. Only add SwarmGraph wrapping if there's a demonstrated need for consensus/audit over MCP tool outputs.
