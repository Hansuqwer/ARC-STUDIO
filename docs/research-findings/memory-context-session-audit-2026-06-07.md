# Memory / Context / Session Audit — 2026-06-07

> **Scope:** AGENTS.md ingestion, SKILL.md catalog, workspace context, session persistence, compaction, file/folder mentions, memory boundaries, safe context injection  
> **Agent count:** 12 parallel sub-agents

---

## 1. Context / Memory Truth Map

```
DISCOVERED
  AGENTS.md    rglob scan, SHA256, over_cap(32KB), LLM heuristic
               → CapabilityCard(entity=AGENTS_MD, risk=LOW/MEDIUM)
               ✗ Content NOT parsed (charter rules invisible)
               ✗ NOT injected into ContextEngine

  SKILL.md     rglob scan, YAML frontmatter (name, description)
               → CapabilityCard(entity=SKILL, risk=LOW)
               ✗ Content NOT injected into ContextEngine

  Workspace    files(1k/10MB) + git + traces + MCP + symbols
  Inventory    symbols: Python=AST, TS/JS=regex (fragile)
               ✗ No AGENTS.md/SKILL.md section in payload
               ✗ NOT auto-injected into context window

  Memory       extract from traces → MemoryNode(kind,text,conf)
  Graph        redaction-at-extraction, workspace-scoped
               ✗ runtime_injection=False HARDCODED everywhere
               ✗ No TTL/retention policy, no wipe command

PERSISTED
  Session       ~/.arc/sessions/{id}/session.json (schema v4)
                id, mode, runtime_mode, profile_id, isolation_id,
                allow_paid_calls, tools_enabled, history[{role,content,ts}]
                ✗ NO model, provider, workspace, token_usage fields
                Atomic write (fcntl.flock + rename), latest symlink
                Export bundle: SHA256 integrity + Redactor() wrap

  REPL history  ~/.arc/repl_history.txt (last 500 lines)
  Memory graph  ~/.arc/memory/graph.json (workspace-local)
  AGENTS.md pin → .arc/agents-md/index.json
  Handles       SQLiteWAL (~/.arc/handles/ or workspace/.arc/)

AUTOMATICALLY INJECTED
  ✅ LocalRepoProvider   keyword-scored workspace files (top 20)
     ✗ SECURITY: .env / *.key files NOT excluded
  ✅ VercelGrepProvider  grep.app scrape
     ✗ UNGATED: unconditional network call (no env var gate)
  ✅ GitHubCodeSearchProvider  gated: GITHUB_TOKEN required
  ✅ Context7Provider           gated: ARC_CONTEXT7_API_KEY
  ✅ WebSearchProvider          gated: ARC_SEARCH_API_KEY
  ✗ AGENTS.md content   NOT injected
  ✗ SKILL.md content    NOT injected
  ✗ Memory graph        NOT injected (hardcoded blocked)
  ✗ @file/@folder       NOT IMPLEMENTED anywhere
  ✗ Workspace symbols   NOT injected into context window
```

---

## 2. Session Lifecycle Map

```
arc (TUI) / arc chat
         │
         ▼
  ChatSession.load(id)?  ─── no id ──→  ChatSession.create()
         │
  session.history → transcript replay
         │
  ┌─── REPL Turn Loop ─────────────────────────────────────────┐
  │  /compact  → MT-1 + MT-5 (deterministic, no LLM)           │
  │  /sessions resume <id>  → in-place session swap            │
  │  /context pack <task>  → ContextEngine.retrieve()          │
  │  bare text → TurnManager.run_turn()                        │
  │    ├─ BudgetEnforcer.preflight()                           │
  │    ├─ context injection (5 providers, no AGENTS/SKILL)     │
  │    │   ⚠ no auto-compact on overflow                      │
  │    ├─ LLM call (streaming)                                 │
  │    ├─ tool calls → MT-1 virtualize if >8KB                │
  │    └─ session.add_message() + metadata update              │
  │                                                             │
  │  ContextMeter: shows total_tokens / context_limit (64k)   │
  │  R-02 auto-compact: 85% of 200k threshold (MISMATCH ⚠️)   │
  └─────────────────────────────────────────────────────────────┘
         │  on exit / Ctrl-C
         ▼
  session.save() → ~/.arc/sessions/{id}/session.json
```

### IDE Session Bridge (Phase 46 + 52)

| Method | Daemon path | CLI fallback |
|---|---|---|
| `importSession(payload)` | `POST /api/sessions/write` | `arc studio sessions write` |
| `deleteSession(id)` | `DELETE /api/sessions/{id}` | `arc studio sessions delete` |
| `updateSessionField(id, field, value)` | `PATCH /api/sessions/{id}` | `arc studio sessions update` |
| `listChatSessions()` | — (no daemon path) | `arc studio sessions --json` |

SSE `session_changed` events — no reconnect on drop.

### Session resume / fork reliability

- **Resume:** Reliable — `ChatSession.load(id)`, `ChatSession.latest()`, full history persisted
- **Fork (TUI [f] key):** Best-effort — wrapped in `except Exception: pass`; fork exists in-memory only if save fails
- **No `/fork` slash command** in REPL or IDE

---

## 3. AGENTS / SKILL Feature Map

| Feature | AGENTS.md | SKILL.md |
|---|---|---|
| Discovery (rglob) | ✅ | ✅ |
| SHA-256 per file | ✅ | ✅ |
| LLM-generated heuristic | ✅ (3-of-4 signals) | ❌ |
| Content parsing | ❌ **charter text invisible** | ✅ YAML frontmatter only |
| CapabilityCard generation | ✅ | ✅ |
| Auto-inject into ContextEngine | ❌ | ❌ |
| CLI discover | ✅ `arc agents-md discover` | ✅ `arc skills discover` |
| IDE surface | ❌ (R-AUDIT16 stub) | ❌ |
| TUI surface | ❌ | ❌ |

**Critical:** The AGENTS.md file governing agents (including ARC itself) is visible as path+hash only. Charter rules and active-track constraints are never parsed or presented to any running agent.

---

## 4. CLI / TUI / IDE Parity Matrix

| Capability | CLI | TUI | IDE |
|---|---|---|---|
| Session list | ✅ | ✅ `/sessions list` | ✅ CommandCentre (read-only) |
| Session resume | ✅ `--session-id` | ✅ `/sessions resume` | ❌ |
| Session fork | ❌ | ✅ TUI [f] (best-effort) | ❌ |
| Session export/import | ✅ | ❌ | ❌ |
| Context budget meter | ❌ | ✅ ContextMeter (stale 64k limit) | ❌ absent |
| AGENTS.md discovery | ✅ `arc agents-md discover` | ❌ | ❌ (R-AUDIT16 stub) |
| Context pack | ✅ `arc context pack` | ✅ `/context pack` | ❌ |
| Memory query | ✅ `arc memory query` | ❌ no /memory cmd | ❌ |
| Compaction | ✅ | ✅ `/compact` | ❌ |
| @file mention | ❌ | ❌ | ❌ |
| Token usage view | ❌ | ✅ status bar | ❌ |

---

## 5. Safety Review

### Strong properties ✅

- Memory injection `memory_runtime_injection=False` hardcoded in 4 classes, 3 assertion tests
- Redaction at memory extraction — `Redactor.redact_dict()` before any text analysis
- Session export bundle: SHA256 + Redactor scrub; schema version gate on import
- Handle content addressed post-redaction; tamper detection on expand
- `EnforcementContext` immutability (`frozen=True`); `dry_run` overrides all flags
- Memory workspace-scoped: `privacy_mode="local_workspace_only"` Literal type

### Gaps ⚠️

| Severity | Gap |
|---|---|
| **HIGH** | `LocalRepoProvider` does NOT exclude `.env`, `*.key`, credential files from context injection |
| **HIGH** | `tool_interceptor.py` calls `HandleStore.store()` with no `redactor` — tool outputs stored unredacted |
| **MEDIUM** | `VercelGrepProvider` makes unconditional outbound HTTP (no env var gate) |
| **MEDIUM** | No `arc memory wipe` / full graph clear command |
| **MEDIUM** | Redaction patterns miss env-style assignments (`DEEPSEEK_API_KEY=sk-xxx`), JWTs |
| **MEDIUM** | Session history capped at 200 on IDE write (`slice(-200)`) — old messages permanently lost |
| **MEDIUM** | Fork persistence in TUI is `except Exception: pass` |
| **LOW** | Memory graph has no TTL/retention policy — residual data accumulation |
| **LOW** | `session_changed` SSE events excluded from HMAC audit chain |

---

## 6. Next-Slice Implementation Prompt

**Target:** AGENTS.md content injection + LocalRepoProvider secret exclusion + VercelGrep gate

### 1. Sensitive file exclusion in `iter_workspace_files()` and `LocalRepoProvider`

```python
_SENSITIVE_FILENAMES = frozenset({
    ".env", ".env.local", ".env.production", ".env.staging",
    "id_rsa", "id_ed25519", ".netrc", ".npmrc", ".pypirc",
})
_SENSITIVE_SUFFIXES = frozenset({".key", ".pem", ".p12", ".pfx", ".cer", ".crt"})
_SENSITIVE_PATTERNS = frozenset({"credentials", "secrets"})
```

Skip in `iter_workspace_files()` and in `LocalRepoProvider.retrieve()` before `read_text()`.

### 2. `AgentsMdProvider` in ContextEngine

New file `context/providers/agents_md_provider.py`:
```python
class AgentsMdProvider(BaseContextProvider):
    source_type = "AGENTS_MD"
    def retrieve(self, task, workspace):
        entries = discovery(Path(workspace))
        # return ContextEntry per file, 4KB cap on over_cap files
```
Wire as first provider in `ContextEngine.__init__`.

### 3. Gate `VercelGrepProvider` on `ARC_VERCEL_GREP_ENABLED=1`

```python
self._offline = os.environ.get("ARC_VERCEL_GREP_ENABLED", "") != "1"
if self._offline:
    return []
```

### 4. Fix `tool_interceptor` redactor pass-through

Ensure `HandleStore` is always initialized with a `redactor` argument in `virtualize_tool_outputs()`.

### 5. Add `/memory` TUI slash command

```
/memory query <text>  — keyword search over memory nodes
/memory show          — snapshot metadata
```

### 6. Fix ContextMeter default limit

`_DEFAULT_CONTEXT_LIMIT = 64_000` → `200_000` (matches R-02 auto-compact default).

### Do NOT do

- Automatic memory injection (officially deferred, hardcoded blocked)
- @file/@folder mention parsing
- IDE context drawer wiring (R-AUDIT16 follow-on)
- JWT redaction patterns

---

## Key Findings Summary

**Three biggest gaps:**

1. **AGENTS.md/SKILL.md content is invisible to agents** — discovered as path+hash only, never parsed or injected. Governance charter is inaccessible to running agents.

2. **`LocalRepoProvider` leaks secrets** — `.env`, `*.key`, and credential files are not excluded from context injection.

3. **IDE is a UI stub** — `ChatTab` is ephemeral local state with no session management, no context visibility, no streaming, and no mention support.
