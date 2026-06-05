# Token Estimator Accuracy — Empirical Benchmark

> **Status:** ⏳ **DEFERRED (benchmark script shipped + run; corpus synthetic).**
> The runnable benchmark now exists (`scripts/research/measure_estimator_accuracy.py`)
> and was executed 2026-06-06 against the local corpus, but that corpus is
> SwarmGraph fake-deterministic test fixtures (1 distinct string), so a
> representative multi-category benchmark still awaits real dogfood traces.
> See §3 for the run outcome and the single honest data point.
> **Date:** 2026-06-04 (deferred) · 2026-06-06 (script run; corpus assessed)

---

## §1 — Why deferred

The benchmark requires real ARC Studio JSONL traces (location varies: macOS `~/Library/Application Support/arc-theia-studio/` or Linux `~/.local/share/arc-theia-studio/`). I have no access to your local clone or trace corpus. Per the brief's hard rule:

> "If no trace corpus is available, write 'no trace corpus available; benchmark deferred to first R-01 dogfood week' and STOP — do NOT fabricate numbers."

So this deliverable is a **runnable benchmark script** + **decision tree for R-01 wallet display semantics**. Once you run the script on real traces, fill in §3 with measured values.

---

## §2 — Runnable benchmark script (paste-ready)

Save as `scripts/research/measure_estimator_accuracy.py`:

```python
#!/usr/bin/env python3
"""
Measure ARC's heuristic token estimator accuracy vs ground truth.

Usage:
  cd python
  uv run python ../scripts/research/measure_estimator_accuracy.py \
      ~/.local/share/arc-theia-studio/traces/*.jsonl \
      --samples 100 \
      --out token-estimator-results.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path
from statistics import mean, median, stdev

# These imports assume the script runs from the python/ directory
from agent_runtime_cockpit.context.token_counter import estimate_tokens
try:
    from agent_runtime_cockpit.providers.anthropic_estimator import (
        AnthropicCountTokensEstimator,
    )
    GROUND_TRUTH_AVAILABLE = True
except ImportError:
    GROUND_TRUTH_AVAILABLE = False

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


CATEGORIES = {
    "cjk":      lambda s: any("\u4e00" <= c <= "\u9fff" for c in s),
    "emoji":    lambda s: any(0x1f300 <= ord(c) <= 0x1faff for c in s if isinstance(c, str)),
    "base64":   lambda s: ("=" in s[-4:] and len(s) > 200 and all(c.isalnum() or c in "+/=\n" for c in s[:500])),
    "code":     lambda s: "```" in s or any(kw in s for kw in ("def ", "function ", "class ", "import ", "const ")),
    "json":     lambda s: s.lstrip().startswith(("{", "[")) and s.rstrip().endswith(("}", "]")),
    "md_table": lambda s: "\n|" in s and "|---" in s,
    "prose":    lambda s: True,  # fallback
}


def categorize(content: str) -> str:
    for name, pred in CATEGORIES.items():
        try:
            if pred(content):
                return name
        except Exception:
            continue
    return "other"


def extract_message_contents(jsonl_path: Path, max_per_file: int = 50) -> list[str]:
    """Pull message content strings out of JSONL trace lines."""
    out = []
    with jsonl_path.open() as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Common shapes: { "messages": [{ "content": "..." }] },
            #                { "content": "..." },
            #                { "tool_result": { "output": "..." } },
            for content in _walk_for_content(obj):
                if isinstance(content, str) and len(content) >= 50:
                    out.append(content)
            if len(out) >= max_per_file:
                break
    return out


def _walk_for_content(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("content", "text", "output") and isinstance(v, str):
                yield v
            else:
                yield from _walk_for_content(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_for_content(v)


def tiktoken_count(content: str) -> int | None:
    if not TIKTOKEN_AVAILABLE:
        return None
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(content))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace_files", nargs="+", type=Path)
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--out", type=Path, default=Path("token-estimator-results.csv"))
    args = parser.parse_args()

    # Collect
    all_contents = []
    for p in args.trace_files:
        if p.exists():
            all_contents.extend(extract_message_contents(p))

    if len(all_contents) < args.samples:
        print(f"WARNING: only {len(all_contents)} samples found (wanted {args.samples})")

    sample = random.sample(all_contents, min(args.samples, len(all_contents)))

    # Measure
    rows = []
    for i, content in enumerate(sample):
        cat = categorize(content)
        heuristic = estimate_tokens(content)
        tt = tiktoken_count(content)
        truth = tt  # for non-Anthropic; if you have AnthropicCountTokens online, use it instead
        if truth is None or truth == 0:
            continue
        abs_err = abs(heuristic - truth)
        rel_err = abs_err / truth
        rows.append({
            "id": i,
            "category": cat,
            "length_chars": len(content),
            "tiktoken_truth": truth,
            "heuristic": heuristic,
            "abs_error": abs_err,
            "rel_error_pct": round(rel_err * 100, 2),
        })

    # Aggregate
    by_cat: dict[str, list[float]] = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(r["rel_error_pct"])

    print("\nPer-category relative error (%):")
    print(f"  {'CATEGORY':<12} {'N':>4}  {'MEDIAN':>8}  {'MEAN':>8}  {'MAX':>8}")
    for cat in sorted(by_cat):
        vals = by_cat[cat]
        print(f"  {cat:<12} {len(vals):>4}  {median(vals):>7.1f}%  {mean(vals):>7.1f}%  {max(vals):>7.1f}%")

    overall = [r["rel_error_pct"] for r in rows]
    print(f"\nOverall MAE: {mean(overall):.1f}% (N={len(overall)}, median={median(overall):.1f}%, max={max(overall):.1f}%)")

    # Write CSV
    with args.out.open("w") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
    print(f"\nResults written to {args.out}")

    # ASCII scatter (heuristic vs truth)
    print("\nScatter (truth on X, heuristic on Y, diagonal = perfect):")
    _ascii_scatter([(r["tiktoken_truth"], r["heuristic"]) for r in rows])


def _ascii_scatter(points: list[tuple[int, int]], width: int = 60, height: int = 20):
    if not points:
        print("(no data)")
        return
    max_x = max(p[0] for p in points)
    max_y = max(p[1] for p in points)
    scale = max(max_x, max_y)
    grid = [[" "] * width for _ in range(height)]
    # Diagonal
    for i in range(min(width, height)):
        x = int(i / min(width, height) * width)
        y = int(i / min(width, height) * height)
        if 0 <= x < width and 0 <= y < height:
            grid[height - 1 - y][x] = "."
    # Points
    for tx, hy in points:
        gx = int(tx / scale * (width - 1))
        gy = int(hy / scale * (height - 1))
        if 0 <= gx < width and 0 <= gy < height:
            grid[height - 1 - gy][gx] = "*"
    for row in grid:
        print("  " + "".join(row))


if __name__ == "__main__":
    sys.exit(main())
```

Run it:
```bash
cd python
uv run python ../scripts/research/measure_estimator_accuracy.py \
    ~/.local/share/arc-theia-studio/traces/*.jsonl \
    --samples 100
```

---

## §3 — Results (RUN 2026-06-06 against `python/.arc/traces/`)

**Outcome: benchmark script created + verified runnable; representative
multi-category benchmark still DEFERRED — the only available local corpus is
synthetic.**

The script (`scripts/research/measure_estimator_accuracy.py`) was run against
the local trace corpus (2,285 `*.jsonl` files, 8.9 MB). It executes end to end
and emits the per-category table, CSV, and ASCII scatter. However, corpus
inspection showed the traces are **SwarmGraph fake-deterministic test
fixtures**, not real model output:

```
total content strings (>=50 chars): 398   (per 500-file sample)
distinct content strings:           1
distinct lengths:                   1
most common (x398): "Fake deterministic response for: You are worker 1 of 1.
                     Provide your independent analysis. ..."  (1 string, 132 chars)
```

So the "300-sample" run measured the **same synthetic string 300 times** →
every row is category `prose` with identical error. That is not a representative
benchmark, so the §4 priors remain unverified and the verdict (§5) stays
**deferred to a real dogfood corpus**. Per the brief's hard rule, no
per-category numbers are reported as if representative.

**Single honest data point** (the fixture string, N=1 distinct):

```
content (132 chars):  "Fake deterministic response for: You are worker 1 of 1. …"
tiktoken (cl100k):     27 tokens   (ground truth)
ARC heuristic:         43 tokens   (default, no provider hint → _heuristic())
relative error:        +59%        (heuristic OVER-counts)
```

Notes:
- The default no-provider path (`estimate_tokens(text)` → `_heuristic`)
  over-counts this short English string by ~50–60%. Over-counting is the
  **wallet-safe** direction (you believe you spent more than you did, so you
  stop earlier), but the magnitude is larger than the §4 prose prior (±5–10%).
- A single synthetic sample cannot be generalised. **Re-run the script against
  real traces** once R-01 dogfooding accumulates diverse content
  (prose/code/json/cjk/base64). The script is ready and committed.
- When ground-truth accuracy matters, callers should pass `provider="openai"`
  (routes to tiktoken) or `provider="anthropic"` rather than the bare heuristic.

### Original blank template (fill after a real-corpus run)

```
CATEGORY      N    MEDIAN     MEAN      MAX
prose         __    __ %      __ %      __ %
code          __    __ %      __ %      __ %
json          __    __ %      __ %      __ %
md_table      __    __ %      __ %      __ %
cjk           __    __ %      __ %      __ %
emoji         __    __ %      __ %      __ %
base64        __    __ %      __ %      __ %
other         __    __ %      __ %      __ %

Overall MAE: __ % (N=__, median=__%, max=__%)
```

---

## §4 — Pre-research priors (verify or refute)

Based on tokenizer behavior published in OpenAI / Anthropic docs:

| Shape | Predicted heuristic error | Direction |
|---|---|---|
| Plain English prose | ±5–10% | Heuristic should be near-correct |
| Code (Python, TS) | ±10–15% | Slight over-count from symbol density |
| JSON deep nesting | +10–25% over-count | `{}[]"` count as 1 token each |
| Markdown tables | +20–40% over-count | Pipes are 1 token each |
| CJK text | -50% to -150% under-count | Multi-byte chars; heuristic sees N chars, tokenizer sees ~2N tokens |
| Emoji / ZWJ sequences | Wild ±200% | Unicode complexity; emoji can be 1 or 4+ tokens |
| Base64 blobs | -30% under-count | Heuristic divides chars by 4; base64 hits ~3 chars/token |
| URLs / file paths | ±15% | `/.` split aggressively |

If §3 results match these priors, the heuristic is "working as expected." If a category drifts >50%, that category needs a wallet-display qualifier.

---

## §5 — R-01 wallet display decision tree

Once §3 is filled in, pick the verdict:

### Verdict A — Heuristic accurate within ±10% across all categories

R-01 wallet displays `$X.XX remaining` without any qualifier. Single source of truth.

### Verdict B — Heuristic accurate except categories {X, Y, Z} with >25% MAE

R-01 wallet displays:
- `$X.XX remaining` for spend backed by AnthropicCountTokens or tiktoken (exact)
- `~$X.XX remaining` for spend backed by heuristic on a "safe" category
- `≈$X.XX remaining (heuristic, may drift by ±N%)` for spend backed by heuristic on a known-bad category

`/wallet` slash command shows the exact tier breakdown so users can audit.

### Verdict C — Heuristic >25% MAE overall

R-01 should bias toward calling the exact estimator (AnthropicCountTokens for Claude, tiktoken for OpenAI/Gemini-compatible) and only fall back to heuristic with a `~` prefix and a one-time `⚠ token estimator using fallback heuristic — accuracy degraded` warning.

This affects R-01's `TokenWallet` snapshot logic in `python/src/agent_runtime_cockpit/budget/wallet.py` (planned). Wire the wallet to read `CostRecord.source` (`"measured"` vs `"estimated"`) — that field already exists per `protocol/cost_record.py:31-37`.

---

## §6 — Open questions (resolvable only with run data)

- [ ] What's the actual MAE overall? (Need §3 data.)
- [ ] Which categories cross the 25% threshold? (Need §3 data.)
- [ ] How big is your trace corpus? If <100 samples, results are not reliable — extend the benchmark window to first 2 weeks of R-01 dogfooding.
- [ ] Does the heuristic behave differently on Anthropic vs OpenAI vs Gemini content? (Re-run with three tokenizers as ground truth.)
- [ ] Is there a single "wildcard" category that breaks everything (e.g., specific code-fence languages)? (Filter §3 by sub-category.)

---

## §7 — Cross-references

- P0-3 estimator code: `python/src/agent_runtime_cockpit/providers/anthropic_estimator.py`
- P0-3 commit: `6813c95`
- R-01 spec: `docs/spec/R-01-token-wallet.md` §4 Task 1 (wallet display logic depends on verdict)
- `CostRecord.source` field: `python/src/agent_runtime_cockpit/protocol/cost_record.py:31-37`
- Brief that asked for this: `docs/research/briefs/token-estimator-accuracy.md`
