# Policy: No LLM in Decision Path (CoSAI Interpretation)

> **Status:** Authoritative for ARC Studio token-saving and budget work.
> **Owner:** Sprint planning + spec authors.
> **Last updated:** 2026-06-04
> **Origin:** Coalition for Secure AI (CoSAI) principle that security and
> budget enforcement decisions must not depend on LLM output. ARC's
> interpretation locked here to prevent re-litigation per sprint.

---

## The rule

**No decision that affects security, cost enforcement, eviction, or
compaction may depend on the output of a Large Language Model at decision
time.**

This applies to all code paths in `budget/`, `security/`, `context/`
(compaction + handles), and any new module that gates spend, access, or
context preservation.

---

## What "decision time" means

A decision is "at decision time" if its outcome — execute / deny /
evict / compact / virtualize / approve — is computed within the path
that produces the outcome. If an LLM's output influences that outcome,
the LLM is **in the path**, even if the model call happens "elsewhere."

| Scenario | LLM in path? |
|---|---|
| `BudgetEnforcer.preflight()` reads a hardcoded $cap → approves/denies | ✗ No |
| `TokenWallet.snapshot()` reads `BudgetEnforcer` state → returns balance | ✗ No |
| `compact()` evicts the middle 3 messages because position 3-5 are middle | ✗ No |
| `handles.store()` SHA-hashes content and stores blob | ✗ No |
| `compact()` asks Claude "which messages can I safely evict?" then evicts | ✓ **YES — forbidden** |
| `BudgetEnforcer` lets a future call go ahead because GPT said the project is "important" | ✓ **YES — forbidden** |
| Token-counting via `tiktoken.encode(content)` (pure CPU, no remote model) | ✗ No |
| Token-counting via `AnthropicCountTokensEstimator` (network call to count_tokens endpoint) | ✗ No — counts, doesn't decide |
| Heuristic `len(content) / 4 * 1.33` | ✗ No |
| LLMLingua-2 small-LM perplexity scoring → drops low-perplexity tokens | ✓ **YES — small LM is in the path** |
| LLMLingua-2 run offline once, hardcoded threshold lookup table at runtime | ✗ No (the LM ran at build time, not decision time) |
| Embedding model produces vector → kNN top-K → keep top-K | **Borderline** — see §"Borderline cases" |
| Classical IR (BM25, TF-IDF) ranks messages → evict bottom | ✗ No |
| Regex / pattern match decides whether to redact | ✗ No |
| User confirms via TUI prompt → ARC executes | ✗ No (human in the loop, not LLM) |

---

## What this rule does NOT prohibit

The rule prohibits **LLMs deciding**. It does not prohibit:

- **LLMs informing.** A model can describe what it would evict, the user can choose. The user is the decider; the LLM provides advisory output that is rendered to the screen, not consumed by the decision code.
- **LLMs counting.** Token-counting endpoints (Anthropic `count_tokens`, OpenAI estimators) produce numbers; ARC's deterministic threshold compares those numbers to a cap. The LLM doesn't decide; the comparison does.
- **LLMs at build time.** A research script that runs LLMLingua-2 to compile a small lookup table (e.g., "these tokens are usually low-perplexity in code") and ships the lookup table is fine. The LM ran offline; the production decision path consults a static table.
- **LLMs in non-decision UX surfaces.** Suggested completions in the chat panel, autocomplete in the editor, summaries of search results — none of these gate spend or eviction. Fine.

---

## Borderline cases (require written ruling per case)

These are genuinely ambiguous. Each requires an explicit ruling in this document before adoption, with rationale recorded.

### B1 — Small-LM perplexity scoring (LLMLingua family)

**Status:** RULED OUT for ARC v0.5.0-alpha and prior. May be reconsidered after v0.6.0-alpha.

**Reasoning:**
1. LLMLingua-2 runs a BERT-class model (~278M params) at decision time to score tokens.
2. Scoring is non-deterministic across GPU/CUDA versions (per `openreview.net/pdf?id=lbFVTPv4s6` §A).
3. Latency: ~42s per prompt (per same source) — kills interactive UX.
4. Performance: 80% accuracy at 50% savings vs TSCG's 93% at 75% savings on tool schemas. Loses on ARC's primary workload.

**What would change the ruling:**
- A future LLMLingua release ships a fully deterministic, sub-100ms mode
- ARC adds a server-side opt-in flag the user toggles per request
- Production benchmarks show competitive accuracy on ARC-shaped content

### B2 — Embedding-model retrieval (RAG, semantic search over message history)

**Status:** **ALLOWED with conditions** for non-decision UX (search panel, "find similar past messages"). **RULED OUT** for compaction eviction.

**Reasoning:**
- Embedding-then-kNN is a learned representation, not a learned decision. The decision (return top-K) is deterministic given the vectors.
- However, if eviction policy *depends* on those K results ("evict messages NOT in top-K"), the embedding model is materially shaping the decision. Under strict reading: forbidden.
- For non-eviction UX where the user picks from results, the human is the decider.

**Conditions for the allowed use:**
- Must use a locally-runnable embedding model (no remote service)
- Must be deterministic given input + model weights (no temperature)
- Must not gate any spend or eviction directly

### B3 — LLM-based confirmation flows

**Status:** ALLOWED for inform-then-confirm UX. FORBIDDEN for silent gating.

**Examples:**
- ✓ "Claude estimates this run will cost $5.20. Approve? [y/n]" — LLM provided estimate; human decides; allowed.
- ✗ "Claude reviewed the proposed spend and approved it." — LLM decided; forbidden.

---

## How to check compliance

### Code review checklist

For any PR touching `budget/`, `security/`, `context/compaction*`, or `context/handles*`:

- [ ] Does this file import from `providers/`, `anthropic`, `openai`, `google.generativeai`, or any vendor SDK? → If yes, justify or refactor.
- [ ] Does this file call any function whose name contains `complete`, `chat`, `messages`, `generate`, `predict`, `infer`? → Same.
- [ ] Does the decision outcome depend on a model response? → Same.
- [ ] Is there a deterministic equivalent? → If yes, prefer it.

### Import-guard test pattern

Each module covered by this rule SHOULD have an automated test that asserts no LLM provider is imported:

```python
# tests/<module>/test_no_llm_imports.py
import ast
from pathlib import Path

FORBIDDEN_IMPORTS = {
    "anthropic", "openai", "google.generativeai",
    "agent_runtime_cockpit.providers",  # any vendor adapter
}

def test_budget_wallet_does_not_import_llm():
    module_path = Path(__file__).parent.parent.parent / "src" / \
        "agent_runtime_cockpit" / "budget" / "wallet.py"
    tree = ast.parse(module_path.read_text())
    imports = {
        node.module for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    forbidden = imports & FORBIDDEN_IMPORTS
    assert not forbidden, f"Forbidden LLM imports: {forbidden}"
```

Apply the same pattern to `context/compaction.py`, `context/handles.py`, and any future enforcement module.

### Runtime mock-and-assert pattern

For functions that *could* call an LLM but shouldn't:

```python
def test_compact_does_not_call_llm(monkeypatch):
    call_count = 0
    def fail_on_call(*a, **kw):
        nonlocal call_count
        call_count += 1
        raise AssertionError("LLM call from compaction path")
    monkeypatch.setattr("agent_runtime_cockpit.providers.anthropic.AnthropicProvider.complete", fail_on_call)
    monkeypatch.setattr("agent_runtime_cockpit.providers.openai_compatible.OpenAICompatibleProvider.complete", fail_on_call)
    result = compact(sample_messages, context_limit=100, context_used=95)
    assert call_count == 0
```

---

## Resolution procedure for new ambiguous cases

When a new strategy/library arrives that *might* be in-path:

1. **Author proposes** in a sprint spec (`docs/spec/<sprint>.md`) with one of: ALLOWED, FORBIDDEN, BORDERLINE.
2. If BORDERLINE, the spec MUST include:
   - One paragraph stating why ambiguous
   - The deterministic alternative being considered
   - What evidence would shift the ruling
3. Sprint review either ratifies (adds to this document's §"Borderline cases") or rejects.
4. Once ruled, the result is recorded here. Future sprints inherit the ruling — no re-litigation.

---

## Cross-references

- Origin discussion: token-saving sprint preamble (v0.3.0-alpha through v0.5.0-alpha specs)
- Research that prompted this memo: `docs/research/R-02-compaction-options.md` §4 (LLMLingua exclusion analysis)
- First enforcement: `python/src/agent_runtime_cockpit/context/compaction.py` (v0.5.0-alpha; ships with import-guard + runtime mock test)
- CoSAI source: Coalition for Secure AI principles (2024); ARC-specific interpretation captured here as the local authoritative reading.
