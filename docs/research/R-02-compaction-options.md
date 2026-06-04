# R-02 — Deterministic Compaction Strategies

> **Date:** 2026-06-04
> **Constraint:** CoSAI rule prohibits LLM-in-the-decision-path. Strategies
> must be deterministic functions of message history + config. No model
> calls, no learned scorers requiring GPU inference at decision time.
> **For consumer:** v0.5.0-alpha R-02 spec author.

---

## §1 — Executive summary

1. **LLMLingua family is OUT under our CoSAI interpretation.** It uses a small LM (GPT-2 small, BERT, LLaMA-7B) for perplexity-based token scoring at decision time. Even LLMLingua-2 (BERT-class, "task-agnostic") runs a model on the prompt to decide what to evict. Per the strict reading of "no LLM in decision path," this is forbidden. **Requires written ARC ruling** before reconsideration.
2. **Recommended P0:** Attachment/tool-output virtualization (QW-4 — already designed) + oldest-first message eviction + "Lost in the Middle"–informed preservation of prompt head + tail. These three together deliver 60–90% savings on tool-heavy traces with zero LLM in the decision path.
3. **Bonus:** TSCG (Tool-Schema Compilation Grammar, 2024) achieves 93.3% accuracy at 74.8% savings on tool schemas in <1 ms pure deterministic. Drop-in win for ARC's tool registry, separate from message compaction.

---

## §2 — Strategy table

| # | Name | Mechanism | Expected savings | Quality cost | LOC est | CoSAI status |
|---|---|---|---|---|---|---|
| 1 | **Oldest-first message eviction** | FIFO drop of oldest user/assistant turn pairs when context approaches `context_limit × threshold` (default 0.85) | 30–60% on long sessions; depends on session length | Quality cost grows past ~5 evicted pairs (loses earlier reasoning); mitigate by keeping system prompt + first user message pinned | ~60 | ✓ deterministic |
| 2 | **Attachment virtualization (QW-4)** | Replace large tool outputs with `resource_link` handles; `/expand` on demand | 40–95% on tool-heavy traces; headroom@8006293 reports 90.6% on JSON arrays specifically | Near-zero if previews are well-chosen (head+tail) | ~250 (see QW-4 spec) | ✓ deterministic |
| 3 | **Tool-result truncation with handle** | For tool outputs >N tokens: keep first M lines + last K lines + handle for full | 70–90% on grep / list / large file reads | Small — typical tool consumers care about head/tail not middle | ~80 | ✓ deterministic |
| 4 | **System-prompt deduplication** | If multi-turn re-sends identical system, the cache breakpoint placement (R-04) already handles. No additional eviction needed. | Already realized via R-04 | — | 0 (no new code) | ✓ already shipped |
| 5 | **"Lost in the Middle"–informed eviction** | When evicting, drop middle turns first; preserve first N + last M | Same as #1 in savings; potentially better quality retention per Liu et al. 2023 | Better than naive FIFO based on published priors | +20 over #1 | ✓ deterministic |
| 6 | **BM25 / TF-IDF relevance ranking** | Index past turns; surface top-K most relevant to current user prompt; evict bottom | 50–70% in theory; little production data | Risk of dropping subtly-relevant context | ~150 | ✓ deterministic (classical IR) |
| 7 | **TSCG tool-schema compilation** | Pre-compile tool JSON schemas to a compressed grammar at registration time; deterministic, sub-ms, no GPU | 74.8% on tool schemas (paper-published, openreview.net/pdf?id=lbFVTPv4s6 §A) | ~7% accuracy drop (93.3% vs 100% baseline) | ~120 | ✓ pure deterministic |
| 8 | **LLMLingua / LongLLMLingua / LLMLingua-2** | Small LM (GPT-2/BERT/LLaMA-7B) computes perplexity; drops low-perplexity tokens | 4–20× compression per paper; LongLLMLingua reports 17.1% accuracy improvement *and* 4× compression on RAG | Negligible per paper (Jiang et al. 2023, 2024; Pan et al. 2024) | ~80 (lib wrapper) | ⚠ **borderline — requires written ruling** |
| 9 | **Selective Context** (Li et al. 2023) | Self-information based; smaller external LM scores tokens | Worse than LLMLingua per published benchmarks | Similar to LLMLingua | ~80 | ⚠ same — LM in path |
| 10 | **KV-cache truncation server-side** | Provider-side trick: model has a long KV-cache, truncate input on the wire | Provider-dependent; not in ARC's control | Variable | n/a (vendor) | ✗ not user-controllable |

---

## §3 — Recommended P0 for v0.5.0-alpha

Ship **three deterministic strategies in priority order**:

### 3a. Attachment virtualization (QW-4) — biggest ROI

Already designed in `docs/research/QW-4-mcp-handle-design.md`. ~250 LOC. Returns ~90% savings on tool-heavy workloads per [chopratejas/headroom](https://github.com/chopratejas/headroom) production data cited in `TOKEN_SAVING_PLAN-2.md`.

Eliminates the largest single source of context bloat in agent workflows.

### 3b. "Lost in the Middle"–informed oldest-first eviction

Trigger: `context_used / context_limit >= 0.85` (configurable threshold).

Algorithm:
1. Identify all message pairs (user + assistant turn).
2. Sort by position: keep first N=2 pairs (early context typically anchors the task) and last M=4 pairs (recent context drives current response).
3. Evict middle pairs until `context_used / context_limit < 0.70` (configurable hysteresis).
4. Never evict: system prompt, current user message, pinned attachments.
5. Log every eviction to `events.QuotaWarning`-adjacent typed event so user sees it.

~80 LOC + 8 tests. Based on Liu et al. 2023 [arxiv.org/abs/2307.03172](https://arxiv.org/abs/2307.03172) which shows LLMs are more accurate on first-and-last content than middle content — so evict middle first.

### 3c. Tool-result truncation with handle (overlaps with 3a)

Even before full QW-4 lands, ARC can do truncation:

```python
# Pseudo
if len(tool_output_str) > TOOL_OUTPUT_TRUNCATE_THRESHOLD:  # default 8KB
    head = tool_output_str[:2000]
    tail = tool_output_str[-1000:]
    handle = store(tool_output_str)
    return f"{head}\n\n[... {len(tool_output_str) - 3000} bytes truncated; handle={handle} ...]\n\n{tail}"
```

~40 LOC + 5 tests. Ship as a fast path if QW-4 slips.

**Total for R-02 P0:** ~370 LOC, ~20 tests, all deterministic, all CoSAI-compliant.

---

## §4 — Why LLMLingua is excluded (and what would change that)

The published numbers are strong:

| Method | Tokens (compressed) | 1/τ | Latency | Speedup | Source |
|---|---|---|---|---|---|
| Original prompt | 9,788 | 1× | 12.2s | — | Jiang et al. 2024 (LongLLMLingua) |
| Selective Context | 1,865 | 5× | 47.5s | 0.3× | same |
| LLMLingua | 1,862 | 5× | 4.8s | **0.3× (slower)** | same |
| LongLLMLingua | 1,826 | 6× | 5.2s | **2.3× (faster)** | same |
| Zero-shot | 32 | 306× | 1.0s | 12.2× | same (no compression at all, terrible accuracy) |

LongLLMLingua hits 6× compression with *better* downstream accuracy than zero-shot AND 2.3× speedup. It's genuinely good.

**But:** Quote from [openreview.net/pdf?id=lbFVTPv4s6](https://openreview.net/pdf?id=lbFVTPv4s6) (TSCG paper, Jan 2024, §A — re-applying LLMLingua-2 to tool schemas): "LLMLingua-2 yields 80.0% accuracy at 50.8% token savings vs. TSCG's 93.3% at 74.8% savings... Both require GPU model inference, produce non-deterministic output... LLMLingua-2 requires 42.5s on the same prompts (~40,000× slower [than TSCG])."

So:
1. **Non-deterministic** — same input may produce different compressed output on different runs (varies with GPU/CUDA versions, batch size).
2. **Requires GPU model inference at decision time** — clear LLM-in-path under literal CoSAI reading.
3. **Slow** (LLMLingua-2 reported at 42.5s per prompt) — incompatible with interactive TUI use.
4. **Worse than TSCG on tool schemas specifically** (80% vs 93%) — so for ARC's primary use case (agent tool workloads), it's not even the winner.

**Reconsider if:**
- ARC issues a written CoSAI ruling that "deterministic small-model perplexity scoring with seed pinning" is allowed for content compression (separable from "model chooses what to do").
- OR a future LLMLingua release ships a pure-deterministic mode.
- OR ARC adds a server-side mode where the user explicitly opts in per request.

Until any of those, LLMLingua family stays at #8 with the ⚠ marker.

---

## §5 — Sources

| Source | URL | Accessed |
|---|---|---|
| LLMLingua (Jiang et al. 2023, EMNLP) | [arxiv.org/abs/2310.05736](https://arxiv.org/abs/2310.05736) / [microsoft/LLMLingua repo](https://github.com/microsoft/LLMLingua) | 2026-06-04 |
| LongLLMLingua (Jiang et al. 2024, ACL) | [arxiv.org/html/2310.06839v2](https://arxiv.org/html/2310.06839v2) | 2026-06-04 |
| LLMLingua-2 (Pan et al. 2024) | [microsoft/LLMLingua README §LLMLingua-2](https://github.com/microsoft/LLMLingua) | 2026-06-04 |
| Empirical comparison of compression methods | [openreview.net/pdf?id=lbFVTPv4s6](https://openreview.net/pdf?id=lbFVTPv4s6) (TSCG paper, Jan 2024) | 2026-06-04 |
| Prompt Compression Survey (Oct 2024) | [arxiv.org/html/2410.12388v2](https://arxiv.org/html/2410.12388v2) | 2026-06-04 |
| "Lost in the Middle" (Liu et al. 2023) | [arxiv.org/abs/2307.03172](https://arxiv.org/abs/2307.03172) | 2026-06-04 (cited from prior knowledge — not re-fetched this round) |
| Microsoft LLMLingua research blog | [microsoft.com/en-us/research/blog/llmlingua-innovating-llm-efficiency-with-prompt-compression](https://www.microsoft.com/en-us/research/blog/llmlingua-innovating-llm-efficiency-with-prompt-compression/) | 2026-06-04 |
| Headroom production data (90.6% on JSON arrays) | `chopratejas/headroom@8006293` (cited via TOKEN_SAVING_PLAN-2.md) | not re-fetched |

---

## §6 — Open questions

| Q | Resolution path |
|---|---|
| Should ARC write a formal CoSAI ruling on "small-LM perplexity scoring at content-compression time"? | Author a 1-page memo `docs/policy/cosai-llm-in-path.md` defining boundaries. Land in v0.4.0-alpha or earlier. |
| What's the right threshold for "approaching context limit"? | 0.85 in §3b is a guess. Run with default, log eviction events, calibrate per dogfooding feedback. |
| Should attachment virtualization (QW-4) ship BEFORE R-02 message eviction, or together? | Recommend together in v0.5.0-alpha. QW-4 handles tool outputs; R-02 §3b handles message bloat. Different attack surfaces. |
| Does BM25/TF-IDF relevance ranking (#6) beat oldest-first in practice? | No production data found. Ship oldest-first first; consider BM25 as v0.6.0-alpha experiment. |
| TSCG (#7) — is the tool-schema compression real for ARC? | Yes, drop-in. ARC's tool registry already lives at `protocol/` — a TSCG pass at registration time is ~120 LOC. Worth a separate spec. |

---

## §7 — Cross-references

- v0.5.0-alpha spec (to be written): `docs/spec/R-02-compaction-triage.md`
- Sibling brief: `docs/research/QW-4-mcp-handle-design.md`
- Sibling brief: `docs/research/pricing-snapshot-2026Q2.md` (cache discounts amplify compaction wins)
- R-04 ship (already prevents some duplication): `python/src/agent_runtime_cockpit/providers/anthropic.py:237-366`
- TUI surface: `python/src/agent_runtime_cockpit/tui/data.py:context_limit`
- Project rule: CoSAI — see `AGENTS.md` (or write `docs/policy/cosai-llm-in-path.md`)
