# Token-Saving Plan for ARC Studio v0.3.0-alpha

**Author:** Staff Engineering Research  
**Date:** 2026-06-04  
**Branch:** `research/token-saving-plan`  
**Status:** Research Complete — Ready for Sprint Planning

---

## Executive Summary — Top 3 Wins by ROI

| Rank | Strategy | Estimated Savings | Effort | Risk |
|------|----------|-------------------|--------|------|
| 1 | **Tool Result Trimming (Microcompact)** — Clear stale tool outputs before each request; no LLM call needed | 40–70% of per-request token bloat | ≤1 day | None — additive, deterministic |
| 2 | **Prompt Cache Breakpoints** — Structure requests to maximise OpenAI/Anthropic prefix cache hits; system prompt + tools first, dynamic content last | 50% cost reduction on cached prefix (per OpenAI/Anthropic pricing) | 1–2 days | None — transparent to user |
| 3 | **Context Compaction (`/compact`)** — Tiered: microcompact → session-memory summary → full LLM summarization when threshold exceeded | Extends session lifespan 3–5× before context overflow | 3–5 days | Medium — requires quality-guarded summarization prompt |

Combined, these three strategies should reduce **per-session token costs by 50–75%** and extend sessions from ~30 turns (current) to 100+ turns before any quality degradation.

---

## 1. Per-Track Findings

### Track 1 — Context-Window Management

| Source | What Learned | Implementation Consequence | Confidence |
|--------|-------------|---------------------------|------------|
| `tui/data.py` — `DataStore` | `total_tokens: int = 0`, `context_limit: int = 0` (0 = unknown). `entries: list[TranscriptEntry]` holds full chat history in memory. No trimming, no eviction, no compaction. | ARC currently sends the **entire transcript** on every request. Token growth is linear and unbounded until the context window errors. Must add eviction/compaction. | High |
| `tui/screen.py` — `_handle_chat_message()` | Appends user entry, then calls SwarmGraphAdapter.run_workflow(). No message history assembly — the adapter gets the raw prompt text only. The TUI sends thinking-indicator then replaces it. `is_streaming` flag for interrupt. | The "agent loop" is minimal today — effectively single-turn. Multi-turn context growth is the next bottleneck once real providers are wired in (ChatSession). | High |
| `adapters/swarmgraph.py` — message assembly | CLI subprocess path passes `--prompt` (single string). Native path passes a single `prompt` arg to SwarmGraphRunner. No multi-turn message array constructed. Env filtered to allowlist. | Today's architecture is single-turn. Token savings matter most once `ChatSession` + provider-backed multi-turn is live. System prompt + tool schemas are the current fixed overhead. | High |
| [Context Compaction in Codex, Claude Code, OpenCode](https://justin3go.com/en/posts/2026/04/09-context-compaction-in-codex-claude-code-and-opencode) | Three industry approaches: Codex = single handoff summary; Claude Code = 3-tier (tool-result trim → cache-aware → 9-section LLM summary); OpenCode = timestamp-hide + 5-heading LLM summary. Claude Code's Layer 1 (tool result trimming) is **zero LLM cost** and removes 81% of token bloat (tool outputs). | ARC should implement Layer 1 (deterministic tool-result clearing) immediately. Layer 2 (cache-aware trimming) pairs with prompt caching. Layer 3 (LLM summarization) is P1. | High |
| [Claude Code Deep Dive — oldeucryptoboi](https://oldeucryptoboi.substack.com/p/context-compaction-deep-dive) | Claude Code: auto-compact fires at `effectiveWindow - 13,000 tokens`. Token counting uses `length/4` heuristic plus 33% buffer. Microcompact clears tool results for: file reads, shell output, grep, glob, web fetch/search, edits/writes. Keeps last 5 results. Replaces older with `[Old tool result content cleared]`. | ARC's tool-result messages (from MCP tools, shell escapes, file reads) are prime targets. Keep last N results, replace older with stub. Estimated token reduction: 60–80% of accumulated tool output. | High |
| [DAG-Based Structurally Lossless Trimming (arXiv 2602.22402)](https://arxiv.org/html/2602.22402v1) | Three-pass algorithm: preserves user/assistant verbatim, strips mechanical bloat (raw tool outputs, base64, metadata). Mean 20% reduction, up to 86% for tool-heavy sessions. | Validates our approach: strip tool outputs, keep human messages. ARC's audit entries are metadata that can be excluded from LLM context without loss. | High |
| [Efficient LLM Agent Deployment (emergentmind.com)](https://api.emergentmind.com/topics/cost-efficient-llm-agent-deployment) | "Rolling-window observation masking (M=10) halves per-instance cost compared to unbounded history while maintaining solve rate, outperforming LLM-based summarization." | For ARC's agent loop: keep last 10 tool-result turns, mask older ones. Simpler than summarization, equally effective for coding tasks. | Medium–High |

### Track 2 — Prompt Caching

| Source | What Learned | Implementation Consequence | Confidence |
|--------|-------------|---------------------------|------------|
| [OpenAI Prompt Caching](https://openai.com/index/api-prompt-caching/) | OpenAI caches automatically. Prefix ≥1024 tokens, increments of 128. The longest matching prefix is cached. Cached tokens get 50% discount. No opt-in needed — just structure requests correctly. | ARC must ensure system prompt + tool definitions are a stable prefix. Dynamic content (conversation history) goes after. This is **free** — just message ordering. | High |
| [Anthropic SDK — cache_control ephemeral](https://github.com/anthropics/anthropic-sdk-python) | Anthropic requires explicit `cache_control: {"type": "ephemeral"}` on system blocks and tool definitions. TTL configurable (5m default). Cache write costs 25% more; cache read costs 90% less. Up to 4 breakpoints. | ARC's `AnthropicClient` already lists `ProviderFeature.PROMPT_CACHING` but doesn't set `cache_control` breakpoints on system/tools. Add breakpoints at: (1) end of system prompt, (2) end of tool definitions. | High |
| `providers/base.py` — `CacheBreakpoint` model | `CacheBreakpoint(position: "system"|"tools"|"messages", index: int, ttl_seconds: int|None)` already defined! The base model supports it. | ARC already has the data model. Need to wire `CacheBreakpoint` through to Anthropic API calls and ensure OpenAI message ordering maximises auto-cache. | High |
| `providers/anthropic.py` — capabilities | `features=[...PROMPT_CACHING...]`, `CostRates(cache_write_per_million=3.75, cache_read_per_million=0.30)`. Already modeled. | Provider knows cache rates. BudgetEnforcer can track cache hits vs misses. Implementation gap: actually SENDING cache_control in API calls. | High |
| Stable prefix surfaces in ARC | System prompt (~800 tokens), tool schemas (MCP: 8 tools × ~200 tokens = ~1,600 tokens), AGENTS.md context injection (varies). Total stable prefix: ~2,400–4,000 tokens. | Above 1,024 token threshold for both providers. Caching the stable prefix saves 50–90% on repeated calls. For a 10-turn session, this saves 20,000–36,000 cached input tokens. | High |

### Track 3 — Tool Schema Compression

| Source | What Learned | Implementation Consequence | Confidence |
|--------|-------------|---------------------------|------------|
| `mcp/server.py` — tool count | 8 MCP tools defined: `arc_doctor`, `arc_runtime_capabilities`, `arc_run_status`, `arc_trace_search`, `arc_trace_read`, `arc_audit_verify`, `arc_hitl_list`, `arc_task_create/status/cancel/result`. ~11 tools total. | ~11 tools × ~200 tokens per schema = ~2,200 tokens per request for tool definitions. Not enormous, but cacheable. | High |
| `mcp/manifests.py` — `McpToolRisk` | Schema structure tracks risk per tool. Descriptions are verbose (include full docstrings). `inputSchema` sent as full JSON Schema. | Can compress tool descriptions in the LLM context: short one-liner + parameter list. Keep full schema for execution but send abbreviated version for context. Saves ~30–50% of tool token overhead. | Medium |
| Claude Code's approach | Claude Code clears tool_use block inputs for write-like tools; keeps tool names in schema. Post-compact re-announces full tool set. | ARC could lazily load tool schemas: send abbreviated schemas, expand on demand via `tool_details` tool. Risky — model may not know when to expand. Safer: keep full schemas but cache them. | Medium |

### Track 4 — BudgetEnforcer Streaming Integration

| Source | What Learned | Implementation Consequence | Confidence |
|--------|-------------|---------------------------|------------|
| `budget.py` — `BudgetEnforcer` | `check_and_update(tokens, cost, latency_ms)` — checks all dimensions atomically. `check_and_warn()` emits `QuotaWarning` at 80%. `exhausted` property. `reset()` for fork/replay. Already event-bus-integrated. | BudgetEnforcer is **pre-call** enforcement (checks before each model call). Streaming interruption requires **mid-stream** monitoring — different hook point. | High |
| `tui/screen.py` — streaming | `is_streaming` flag; Ctrl+C/Escape sets it False. Worker thread calls adapter. No token counting during stream. | Can wire: accumulate streamed tokens during generation; if `BudgetEnforcer.exhausted` becomes True mid-stream, set `is_streaming = False` (graceful interrupt). Audit implication: partial response must still be recorded. | High |
| Audit chain integrity | `audit/` module writes HMAC-chain entries per event. A mid-stream interruption creates a partial response. | **Safe if**: interrupted response is recorded as `INTERRUPTED` status with truncation flag. The audit chain appends the interruption event. No chain break. CoSAI rule satisfied: BudgetEnforcer is deterministic arithmetic, not LLM-based decision. | High |

**Decision: Yes, BudgetEnforcer can interrupt streaming without breaking audit**, provided the interruption event is recorded with `status=interrupted, tokens_at_interrupt=N, budget_dimension_hit=X`.

### Track 5 — /fork and /rewind

| Source | What Learned | Implementation Consequence | Confidence |
|--------|-------------|---------------------------|------------|
| [Context Forking (HumanLayer)](https://www.humanlayer.dev/blog/context-forking-to-save-time-trouble-and-tokens) | Context forking = pop messages off the end of context window stack. Saves tokens by discarding failed/unnecessary exploration. Allows parallel design exploration from a common "good context" checkpoint. | ARC can implement `/fork` as: snapshot DataStore.entries at index N; create new session branch from that point; discard entries[N:]. Token savings: all tokens after fork point are freed. | High |
| [Claude Code /fork, /rewind, /btw](https://medium.com/@richardhightower/mastering-claude-codes-btw-fork-and-rewind-the-context-hygiene-toolkit-5ceefa59623d) | `/fork` creates new session from current point. `/rewind` pops last turn. `/btw` inserts side-context without advancing the main conversation. Combined = "context hygiene toolkit". Token savings: 30–60% for exploratory sessions. | Implement `/rewind` first (simplest — pop last entry pair). Then `/fork` (snapshot + new session). `/btw` is lower priority (injects one-off context). | High |
| `tui/data.py` — DataStore state | Fields to snapshot for fork: `entries`, `total_tokens`, `total_cost_usd`, `session_id`, `mode`, `current_provider`, `current_model`. All in one dataclass — easy to deepcopy. | Fork = `copy.deepcopy(data_store)` + new session_id + truncate entries. Store parent reference for branch tree. | High |
| `storage/jsonl.py` — trace storage | `JsonlTraceStore.save(run)` — one JSONL file per run_id. `list_runs()`, `load()`. Thread-safe with `_lock`. | Fork must persist branch metadata (parent_session_id, fork_index). Can add `fork_metadata.json` alongside trace files. Or extend `RunRecord.metadata` with fork info. | High |
| `BudgetEnforcer.reset()` | Already has `reset()` method "for fork/replay scenarios". | Fork naturally resets budget from fork point. The saved budget state at fork time becomes the starting state for the new branch. | High |

### Track 6 — Eval-Driven Prompt Optimization

| Source | What Learned | Implementation Consequence | Confidence |
|--------|-------------|---------------------------|------------|
| `evals/golden.py` — GoldenTrace | Compare RunRecord against expected: status match, event types present, output contains text. `score = sum(checks)/len(checks)`. | Can add token-efficiency metric to eval: `tokens_used / expected_baseline_tokens`. If a prompt optimization produces same quality with fewer tokens, it scores higher. | Medium |
| `evals/policy_recommend.py` — PolicyRecommendationReport | Aggregates eval failures → recommendations (consensus, HITL, tool gates). Never auto-applies; dry-run only. | Can extend with `TokenEfficiencyRecommendation`: "System prompt section X contributes Y tokens but Z% of eval failures reference it → candidate for compression". Safe because recommendations are advisory, not auto-applied. | Medium |
| Eval-driven optimization general | Pattern: run evals with original prompt → measure tokens + quality. Modify prompt → re-run evals → compare. Accept only if quality ≥ threshold AND tokens decrease. | ARC can ship a `arc eval token-efficiency` command that: (1) runs golden traces with current prompts, (2) runs with compressed prompts, (3) reports delta. This is the safe, auditable way to optimize prompts. | Medium |

---

## 2. Decision Table

| Decision | Chosen Approach | Alternatives Considered | Reason | Files Affected | Confidence |
|----------|----------------|------------------------|--------|----------------|------------|
| Context trimming strategy | Three-tier: microcompact → session notes → LLM summary | Single handoff summary (Codex style); sliding window only; no trimming | Claude Code's three-tier proven at scale; each tier is independently valuable; microcompact is free | `tui/data.py`, `tui/screen.py`, new `context/compaction.py` | High |
| Tool result eviction | Keep last N=5 tool results verbatim; replace older with `[content cleared]` stub | Keep all; summarize all; keep last N=10 | N=5 matches Claude Code default; balances recoverability vs token savings | new `context/microcompact.py`, `tui/data.py` | High |
| Prompt caching — Anthropic | Add `cache_control: {type: ephemeral}` on system prompt and last tool definition | Cache on every message; no caching; cache only system | Anthropic limit is 4 breakpoints; system+tools covers stable prefix; Claude Code does same | `providers/anthropic.py` | High |
| Prompt caching — OpenAI | Ensure system prompt + tools sent first in messages array (already standard) | Explicit cache API (doesn't exist); no action | OpenAI auto-caches prefix; just need correct ordering which is standard | `providers/openai_compatible.py` | High |
| Budget mid-stream interrupt | Monitor token accumulation during stream; interrupt at budget threshold; record audit event | No interruption (let budget exceed); interrupt without audit event | BudgetEnforcer already has `exhausted` property; audit must record partial response for chain integrity | `tui/screen.py`, `budget.py` | High |
| /fork implementation | Deepcopy DataStore + new session_id + persist fork metadata in JSONL store | Git-style branching; database-backed tree; no fork support | Simplest that works; DataStore is one dataclass; JSONL already has per-run storage | `tui/data.py`, `storage/jsonl.py`, new `cli_repl/commands/fork.py` | High |
| /rewind implementation | Pop last user+assistant entry pair from DataStore.entries | Pop only assistant; pop entire turn sequence including tool calls | Popping the pair matches "undo last turn" mental model; tool calls between are included | `tui/data.py`, new slash command | High |
| /compact implementation | Slash command that triggers microcompact immediately; full compact at threshold | Auto-only; manual-only | Both manual and auto are needed; manual gives user control; auto prevents overflow | new `context/compaction.py`, slash command | High |
| Tool schema compression | Cache full schemas; no runtime compression | Abbreviate descriptions; lazy-load schemas; remove unused tools | Caching achieves same cost savings without risking model confusion from missing schema details | `providers/anthropic.py`, message ordering | High |
| Token counting method | `len(text) / 4` heuristic with 33% buffer (matches Claude Code) | tiktoken library; provider count-tokens API; exact per-model tokenizer | Heuristic is fast, no external dep, 80% accurate. Can upgrade to tiktoken later. ARC already has `AnthropicCountTokensEstimator`. | new `context/token_counter.py` | Medium–High |

---

## 3. P0 Quick Wins (≤1 day each, no new deps, no security-surface changes)

### P0-1: Message Ordering for Auto-Cache (0.5 day)

**What:** Ensure all provider request builders put messages in order: system prompt → tool definitions → conversation history.

**Why:** OpenAI auto-caches the longest matching prefix. Current message ordering isn't verified. A single reordering bug destroys cache hits across all subsequent calls.

**Files:** `providers/openai_compatible.py`, `providers/anthropic.py`

**Token savings:** 50% reduction on the stable prefix (~2,000–4,000 tokens) for every request after the first.

**Safety:** Zero risk. Message ordering is a standard OpenAI/Anthropic best practice.

### P0-2: Anthropic cache_control Breakpoints (0.5 day)

**What:** Add `cache_control: {"type": "ephemeral"}` to the system prompt block and the last tool definition block in Anthropic API calls.

**Why:** ARC already has `CacheBreakpoint` model and the `AnthropicClient` lists `PROMPT_CACHING` as a feature. The only gap is actually sending the cache control in API calls.

**Files:** `providers/anthropic.py` (complete method)

**Token savings:** 90% cost reduction on cached prefix for Anthropic calls (cache read: $0.30/M vs input: $3.00/M for Sonnet).

**Safety:** Zero risk. Cache misses fall back to normal pricing.

### P0-3: Token Counter Utility (0.5 day)

**What:** Add `context/token_counter.py` with `estimate_tokens(messages: list[TranscriptEntry]) -> int` using `len(content)/4 * 1.33` heuristic.

**Why:** Prerequisite for all threshold-based decisions. Must know current context size to trigger compaction, display usage, enforce budget.

**Files:** new `context/token_counter.py`, `tui/data.py` (wire `total_tokens` update)

**Safety:** Additive only. Heuristic can't break anything.

### P0-4: Context Meter in Status Bar (0.5 day)

**What:** Show `tokens_used / context_limit` in the TUI status bar. Already have `context_limit` field (UX R-002 note in data.py). Just need to populate and display.

**Why:** Users can't optimize what they can't see. Visibility drives behavior.

**Files:** `tui/data.py`, `tui/widgets/status_bar.py`

**Safety:** Read-only display. Zero risk.

---

## 4. P1 Wins (2–5 days each)

### P1-1: Microcompact — Tool Result Trimming (2 days)

**What:** Before each provider request, scan `DataStore.entries` for tool-role entries. Keep the last 5 tool results verbatim. Replace older tool results with `[Tool output cleared — re-run if needed]`. Preserve tool call metadata (tool name, timestamp, status).

**Why:** Tool results are 60–81% of token accumulation in agent sessions (empirically validated by Claude Code, DAG paper, and our own MCP server output analysis). Clearing them is deterministic, zero-cost, and preserves the agent's "memory" of what it did without retaining the bulky output.

**Implementation:**
```python
# context/microcompact.py
COMPACTABLE_ROLES = {"tool"}
KEEP_RECENT = 5
CLEARED_STUB = "[Tool output cleared — re-run command if needed]"

def microcompact(entries: list[TranscriptEntry]) -> list[TranscriptEntry]:
    """Clear old tool results in-place. Returns modified list."""
    tool_indices = [i for i, e in enumerate(entries) if e.role == "tool"]
    if len(tool_indices) <= KEEP_RECENT:
        return entries
    to_clear = tool_indices[:-KEEP_RECENT]
    for idx in to_clear:
        entry = entries[idx]
        original_len = len(entry.content)
        entry.content = CLEARED_STUB
        entry.metadata["_compacted"] = True
        entry.metadata["_original_bytes"] = original_len
    return entries
```

**Files:** new `context/microcompact.py`, `tui/screen.py` (call before provider request)

**Token savings:** 40–70% of accumulated tool output.

**Safety:** Deterministic. No LLM call. No security surface change. Audit chain unaffected (audit records original execution, not trimmed context).

### P1-2: /compact Slash Command with Session-Memory Summary (3 days)

**What:** Implement `/compact` slash command:
1. Run microcompact first (free)
2. If still above threshold (80% of context_limit): generate structured summary using current provider
3. Replace all entries before a boundary marker with the summary
4. Preserve last 3 user messages verbatim (Codex pattern)

**Summary prompt structure (5 sections):**
1. Task objective and user intent
2. Key decisions and constraints
3. Files examined/modified
4. Current state and pending work
5. Errors resolved

**Files:** new `context/compaction.py`, new `tui/commands/compact.py`, `tui/screen.py`

**Token savings:** Extends sessions from ~30 turns to 100+ turns.

**Safety:** Summary is advisory context only. No security decisions use summarized content. Audit chain records the compaction event as a boundary marker. CoSAI compliant: LLM generates the summary text, but no enforcement decisions are based on it.

### P1-3: /rewind and /fork (3 days)

**What:**
- `/rewind` — Pop the last user+assistant turn pair. Reset `total_tokens` by the estimated tokens of removed entries.
- `/fork` — Snapshot current DataStore state. Create new session with entries up to current point. Original session continues independently.

**Implementation:**
- `/rewind`: remove last entries where role matches `[user, assistant]` sequence from tail. Update counters.
- `/fork`: `deepcopy(data_store)`, assign new `session_id`, persist fork metadata (`parent_id`, `fork_index`, `fork_timestamp`), call `BudgetEnforcer.reset()` with forked budget state.

**Files:** `tui/data.py` (fork/rewind methods), `tui/screen.py` (slash commands), `storage/jsonl.py` (fork metadata)

**Token savings:** 30–60% for exploratory sessions. User can fork before risky operations, rewind if they go badly, saving all the tokens from the failed path.

**Safety:** Additive only. Original session data preserved. Fork metadata is append-only to storage.

### P1-4: BudgetEnforcer Streaming Interrupt (2 days)

**What:** During streaming responses, accumulate token count (character-based estimate). If `BudgetEnforcer.exhausted` becomes True mid-stream, gracefully interrupt:
1. Set `is_streaming = False`
2. Append `[Response truncated — budget limit reached]` to partial response
3. Emit audit event: `BUDGET_STREAM_INTERRUPTED` with dimensions

**Files:** `tui/screen.py` (streaming worker), `budget.py` (no changes needed — already has `exhausted`), `events/types.py` (new event type)

**Safety:** Audit chain records interruption event. Partial response preserved. No security surface change. BudgetEnforcer is deterministic arithmetic.

### P1-5: Auto-Compact at Threshold (2 days)

**What:** Before each provider request, check `estimate_tokens(entries) > auto_compact_threshold`. If exceeded:
1. Run microcompact
2. Re-check. If still exceeded: run full compact (P1-2)
3. Circuit breaker: after 3 consecutive failures, stop auto-compacting and warn user

**Threshold:** `context_limit - max(20_000, context_limit * 0.1)` (reserve 10% or 20K tokens for response generation).

**Files:** `context/compaction.py` (add auto-compact orchestrator), `tui/screen.py` (pre-request hook)

**Safety:** Same as P1-2. Circuit breaker prevents runaway costs.

---

## 5. What NOT to Do (Audit/Security Traps)

### ❌ Do NOT use LLM to decide what to trim from security context

The CoSAI rule is non-negotiable: **no LLM in security decisions**. `EnforcementContext` is frozen. If an LLM summarizes away a security constraint (trust level, workspace boundary, denied command), the enforcement layer could make wrong decisions.

**Safe boundary:** LLM summarization applies only to `DataStore.entries` (chat transcript). `EnforcementContext`, `TrustState`, `SandboxPolicy`, and `BudgetVector` are **never** summarized, compressed, or LLM-processed.

### ❌ Do NOT compact audit chain events

The HMAC audit chain (`~/.arc/audit/sandbox.audit.jsonl`) is append-only and hash-linked. Compacting, rewriting, or summarizing audit events would break chain verification. Audit events are separate from the LLM context — they are written to disk, not sent to the model.

**Safe boundary:** Audit trail is a side-channel write-only log. Token savings apply to the provider request context, not the audit store.

### ❌ Do NOT invalidate cache by reordering messages mid-session

If the system prompt or tool definitions change order between requests in the same session, all cached prefixes are invalidated. This wastes cache-write tokens already spent.

**Rule:** System prompt and tool definitions must be structurally identical across all requests within a session. If tools are added/removed mid-session (e.g., MCP server connects), append new tools at the end of the tool list — never reorder existing ones.

### ❌ Do NOT summarize user messages without verbatim preservation option

User messages contain corrections ("no, I meant X"), preferences ("always use TypeScript"), and implicit constraints. Generic summarization smooths these away, leading to task drift.

**Safe approach:** Codex pattern — preserve all user messages verbatim in the summary. Only compress assistant responses and tool outputs.

### ❌ Do NOT use BudgetEnforcer to suppress audit event emission

If budget is exhausted, the system must still emit audit events for the interruption itself. Budget enforcement gates expensive LLM calls, not cheap local I/O. An `INTERRUPTED` audit event costs ~0 tokens and ~0 latency.

### ❌ Do NOT fork/rewind across trust boundaries

If user runs `/workspace trust` during a session, forking back to before that point could create a branch where the workspace is untrusted but the user expects it to be trusted. Trust state must be resolved fresh from disk on each branch, not inherited from the fork snapshot.

**Safe approach:** Fork snapshots DataStore (chat state) only. Trust, profiles, and enforcement state are always resolved fresh from `security/trust.py`.

### ❌ Do NOT send redacted secrets back to the model

If `Redactor.redact_string()` replaces a token/key with `[REDACTED]` in tool output, and that output is later summarized, the summary might reference the redacted value. This is fine — but ensure the redaction happens BEFORE the content enters `DataStore.entries`, not after. Current code already does this correctly (`_redactor.redact_string(stderr[-2000:])` in swarmgraph adapter).

### ❌ Do NOT use /compact as a substitute for proper session boundaries

Compacting 500 turns into a 2-page summary and continuing creates a fragile "house of cards" where the model operates on degraded context. Better: encourage users to start new sessions for new tasks. Compact is for extending long single-task sessions, not for infinite general-purpose memory.

---

## 6. Implementation Sequence

```
Week 1 (P0 — Foundation)
├── P0-1: Message ordering verification
├── P0-2: Anthropic cache_control breakpoints
├── P0-3: Token counter utility
└── P0-4: Context meter in status bar

Week 2 (P1 — Core Token Savings)
├── P1-1: Microcompact (tool result trimming)
├── P1-4: BudgetEnforcer streaming interrupt
└── Tests for P0 + P1-1 + P1-4

Week 3 (P1 — Session Management)
├── P1-2: /compact slash command
├── P1-3: /rewind and /fork
├── P1-5: Auto-compact at threshold
└── Integration tests for full compaction flow
```

---

## 7. Measurement Plan

| Metric | Baseline (current) | Target | How to Measure |
|--------|--------------------|---------|-|
| Tokens per turn (avg) | Unbounded growth | Capped at context_limit × 80% | `DataStore.total_tokens` / turn count |
| Cache hit rate (Anthropic) | 0% (no breakpoints) | >80% after turn 2 | `usage.cache_read_input_tokens / usage.input_tokens` |
| Cache hit rate (OpenAI) | Unknown (auto) | >60% after turn 2 | `usage.prompt_tokens_details.cached_tokens / usage.prompt_tokens` |
| Session lifespan (turns before overflow) | ~30 (at 200K limit) | 100+ | Count turns before auto-compact fires |
| Cost per session (avg) | $X (measure baseline) | 50–75% reduction | `DataStore.total_cost_usd` comparison |
| Compaction quality (eval) | N/A | ≥0.8 golden trace score post-compact | Run eval suite before/after compact |

---

## 8. Unresolved Questions

| Question | Impact | Resolution Path |
|----------|--------|-----------------|
| Should microcompact run synchronously (blocking) or in a background task? | UX latency vs correctness | Start synchronous (simpler); profile; move to background if >50ms |
| What's the right KEEP_RECENT value for tool results? | Too low = re-reads; too high = wasted tokens | Start at 5 (Claude Code default); tune via eval metrics |
| Should /fork persist to disk immediately or lazily? | Data loss risk vs write latency | Persist fork metadata immediately; lazy-persist the full entry snapshot |
| How to handle compaction when the summary itself is too long? | Recursive compaction risk | Implement PTL retry loop (Claude Code pattern): truncate oldest 20% of entries per retry, max 3 retries |
| Should auto-compact fire during streaming or wait until stream completes? | Mid-stream compaction would confuse the model | Wait until stream completes; only compact before the NEXT request |
| How to handle provider switch mid-session (context_limit changes)? | Different providers have different windows | Re-evaluate threshold on provider switch; compact if now over new limit |

---

## 9. Dependencies and Risks

| Risk | Mitigation |
|------|-----------|
| Summary quality degrades over many compactions | Track "compaction depth" counter; warn user at depth >3; suggest new session |
| Token counter heuristic inaccurate for non-English | Allow pluggable estimator (tiktoken for OpenAI, Anthropic count_tokens API) as P2 upgrade |
| Auto-compact triggers during time-sensitive operations | Circuit breaker + user override (`/compact off`) |
| Fork creates inconsistent state if plugins have side effects | Fork only snapshots DataStore (pure data); all side-effect state (trust, files, git) resolved fresh |
| Microcompact clears a tool result the model needs to reference | Model can re-run the tool; cleared stub says "re-run if needed" |

---

## 10. References

1. [Context Compaction in Codex, Claude Code, and OpenCode](https://justin3go.com/en/posts/2026/04/09-context-compaction-in-codex-claude-code-and-opencode) — Comparative analysis of three approaches
2. [Claude Code Compaction Deep Dive](https://oldeucryptoboi.substack.com/p/context-compaction-deep-dive) — Detailed reverse engineering of Claude Code's three-tier system
3. [DAG-Based Structurally Lossless Trimming (arXiv 2602.22402)](https://arxiv.org/html/2602.22402v1) — Academic validation of tool-result stripping approach
4. [Efficient LLM Agent Deployment](https://api.emergentmind.com/topics/cost-efficient-llm-agent-deployment) — Rolling-window masking research
5. [OpenAI Prompt Caching](https://openai.com/index/api-prompt-caching/) — Automatic prefix caching documentation
6. [Anthropic SDK — Prompt Caching](https://github.com/anthropics/anthropic-sdk-python) — cache_control API
7. [Context Forking (HumanLayer)](https://www.humanlayer.dev/blog/context-forking-to-save-time-trouble-and-tokens) — Fork/rewind patterns for token savings
8. [Claude Code /fork, /rewind, /btw](https://medium.com/@richardhightower/mastering-claude-codes-btw-fork-and-rewind-the-context-hygiene-toolkit-5ceefa59623d) — Context hygiene toolkit
9. [Session Memory Compaction Cookbook (Anthropic)](https://platform.claude.com/cookbook/misc-session-memory-compaction) — Official Anthropic guidance
10. [Demand Paging for LLM Context Windows (arXiv 2603.09023)](https://arxiv.org/html/2603.09023v1) — OS-inspired context management
11. [Codex CLI reduce token usage (GitHub #14879)](https://github.com/openai/codex/issues/14879) — Community discussion on verbose output trimming

---

## 11. Alignment with ARC Constraints

| Constraint | How This Plan Complies |
|-----------|----------------------|
| **No LLM in security decisions (CoSAI)** | All token-saving strategies operate on chat transcript only. EnforcementContext, TrustState, and SandboxPolicy are never summarized or compressed. Compaction is context-engineering, not security logic. |
| **EnforcementContext is frozen** | Not touched. Token savings happen upstream of enforcement — in the provider request assembly path. |
| **Additive protocol only** | All new modules (`context/microcompact.py`, `context/compaction.py`, `context/token_counter.py`) are additive. No existing APIs are removed or changed. Existing `CacheBreakpoint` model is used as-is. |
| **Local-first single-user** | All compaction runs locally. No cloud summarization service. Session memory stored in `~/.arc/` or workspace `.arc/`. Fork/rewind state is per-user, per-machine. |
| **Audit chain integrity** | Compaction events are recorded in the audit chain. Audit events themselves are never compacted. Partial responses from budget interruption are recorded with appropriate status flags. |

---

*End of research document. No code was implemented. Ready for sprint planning.*
