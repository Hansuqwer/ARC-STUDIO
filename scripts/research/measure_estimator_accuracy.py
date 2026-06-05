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
from statistics import mean, median

# These imports assume the script runs from the python/ directory
from agent_runtime_cockpit.context.token_counter import estimate_tokens

try:
    from agent_runtime_cockpit.providers.anthropic_estimator import (
        AnthropicCountTokensEstimator,  # noqa: F401
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
    "cjk": lambda s: any("\u4e00" <= c <= "\u9fff" for c in s),
    "emoji": lambda s: any(0x1F300 <= ord(c) <= 0x1FAFF for c in s if isinstance(c, str)),
    "base64": lambda s: (
        "=" in s[-4:] and len(s) > 200 and all(c.isalnum() or c in "+/=\n" for c in s[:500])
    ),
    "code": lambda s: (
        "```" in s or any(kw in s for kw in ("def ", "function ", "class ", "import ", "const "))
    ),
    "json": lambda s: s.lstrip().startswith(("{", "[")) and s.rstrip().endswith(("}", "]")),
    "md_table": lambda s: "\n|" in s and "|---" in s,
    "prose": lambda s: True,  # fallback
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
    out: list[str] = []
    with jsonl_path.open() as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
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
    all_contents: list[str] = []
    for p in args.trace_files:
        if p.exists():
            all_contents.extend(extract_message_contents(p))

    if not all_contents:
        print("no trace corpus available; benchmark deferred to first R-01 dogfood week")
        return 0

    if len(all_contents) < args.samples:
        print(f"WARNING: only {len(all_contents)} samples found (wanted {args.samples})")

    sample = random.sample(all_contents, min(args.samples, len(all_contents)))

    if not TIKTOKEN_AVAILABLE:
        print("no ground-truth tokenizer (tiktoken) available; benchmark deferred")
        return 0

    # Measure
    rows = []
    for i, content in enumerate(sample):
        cat = categorize(content)
        heuristic = estimate_tokens(content)
        truth = tiktoken_count(content)
        if truth is None or truth == 0:
            continue
        abs_err = abs(heuristic - truth)
        rel_err = abs_err / truth
        rows.append(
            {
                "id": i,
                "category": cat,
                "length_chars": len(content),
                "tiktoken_truth": truth,
                "heuristic": heuristic,
                "abs_error": abs_err,
                "rel_error_pct": round(rel_err * 100, 2),
            }
        )

    # Aggregate
    by_cat: dict[str, list[float]] = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(r["rel_error_pct"])

    print("\nPer-category relative error (%):")
    print(f"  {'CATEGORY':<12} {'N':>4}  {'MEDIAN':>8}  {'MEAN':>8}  {'MAX':>8}")
    for cat in sorted(by_cat):
        vals = by_cat[cat]
        print(
            f"  {cat:<12} {len(vals):>4}  {median(vals):>7.1f}%  {mean(vals):>7.1f}%  {max(vals):>7.1f}%"
        )

    overall = [r["rel_error_pct"] for r in rows]
    if overall:
        print(
            f"\nOverall MAE: {mean(overall):.1f}% "
            f"(N={len(overall)}, median={median(overall):.1f}%, max={max(overall):.1f}%)"
        )

    # Write CSV
    with args.out.open("w") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"\nResults written to {args.out}")

    # ASCII scatter (heuristic vs truth)
    print("\nScatter (truth on X, heuristic on Y, diagonal = perfect):")
    _ascii_scatter([(r["tiktoken_truth"], r["heuristic"]) for r in rows])
    return 0


def _ascii_scatter(points: list[tuple[int, int]], width: int = 60, height: int = 20):
    if not points:
        print("(no data)")
        return
    max_x = max(p[0] for p in points)
    max_y = max(p[1] for p in points)
    scale = max(max_x, max_y) or 1
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
