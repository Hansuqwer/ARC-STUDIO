# v0.5.0-alpha Merge Notes

## What ships

**R-02 + QW-4 — first behavior-changing token-saving release.**

Two paired features bundled because R-02's eviction target is QW-4's handle store:

### QW-4 — MCP output handle virtualization

Tool outputs > 8KB stored as `arc://output/sha256/<hex>` handles in SQLiteWAL DB (new `handles` table, same `budget.db` file). Model receives a resource_link with head/tail preview instead of the full payload. `/expand <prefix>` re-injects on demand.

- `context/handles.py` — `HandleStore`: content-addressed, SHA computed post-redaction, LRU eviction cap (default 1GB), fail-closed on corrupt/missing
- `context/tool_interceptor.py` — `virtualize_tool_outputs()`: byte-size comparison only, no LLM
- `/expand` slash command registered in `context` category
- `ToolOutputVirtualized` typed event (3 Python sites + TS mirror)

### R-02 — Deterministic context compaction

When context usage ≥ 0.85 × context_limit: evict middle user/assistant pairs (Lost-in-the-Middle informed) until usage < 0.70. System prompt + first 2 pairs + last 4 pairs + current user message always preserved. No LLM in decision path (CoSAI).

- `context/compaction.py` — `compact()`: trigger/stop hysteresis, positional eviction order, deterministic
- Hooked in `anthropic.py` + `openai_compatible.py` before `_request_kwargs()` via `_maybe_compact()`; `ARC_COMPACTION_ENABLED=0` to disable
- `ContextCompacted` typed event (3 Python sites + TS mirror)

## Token savings — measured on three workloads

```
Workload 1 (18KB grep result):         4758 → 162 tokens    (96% saved)
Workload 2 (3 × 9KB tool calls):       6755 → 466 tokens    (93% saved)
Workload 3 (12-pair session, compact):  2405 → 1804 tokens   (24% saved)
```

W1 and W2 are tool-virtualization savings; W3 is pure message-compaction. The 96%/93% figures match the upper range predicted by `docs/research/QW-4-mcp-handle-design.md`. The 24% on W3 is expected for a 12-pair session at 87% context utilization — longer sessions will see higher savings.

## New interceptor seam

v0.5.0-alpha ships the first version of `context/tool_interceptor.py` as a clean intercept layer. Prior to this sprint, `anthropic_estimator.py:201` was the only tool-result handling site. Future provider work can hook the same seam without scattering changes across providers.

## Test delta

Python: 4937 → 4979 (+42). TS: 143 → 147 (+4).

Pre-existing acceptable failures (unchanged from baseline):
- `test_provider_statuses_fallback_to_stored_creds` — env-specific credential flake
- `test_concurrent_task_execution` — kvm/openai env flake
- `test_concurrent_accumulation` — SQLite lock under concurrent threads (env-specific)
- 5 xfailed: 2 CLI doctor exit-code, 1 CLI runs mode, 2 TUI snapshot SVG-hash nondeterminism

## CoSAI compliance

- `test_no_llm_in_path` (compaction): `openai.OpenAI` + `anthropic.Anthropic` mock assert 0 calls ✅
- `test_no_llm_in_virtualization_path`: `openai.OpenAI` mock assert 0 calls ✅

## Branch

`spec/v0.5.0-r02-and-qw4` — 8 commits — ready to merge to `main`.
