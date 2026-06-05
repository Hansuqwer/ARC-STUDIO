"""v0.6-alpha: /models slash command — catalog-driven model picker.

Reads committed CostRate data from VENDOR_CONFIGS (openai_compatible.py).
NO network fetch at runtime. Per local-first.md policy.
No LLM in decision path (CoSAI). Filters are deterministic lookups.
Catalog drives UI only — does NOT auto-route or change connection layer.
"""

from __future__ import annotations

import shlex
from typing import NamedTuple


class ModelRow(NamedTuple):
    vendor: str
    model_id: str
    input_per_million: float
    output_per_million: float
    is_free_tier: bool
    input_modalities: list
    supported_parameters: list
    pricing_valid_until: str | None


def _all_models() -> list[ModelRow]:
    """Return every model from every vendor in VENDOR_CONFIGS. No network."""
    from ...providers.openai_compatible import VENDOR_CONFIGS

    rows: list[ModelRow] = []
    for vendor, cfg in VENDOR_CONFIGS.items():
        cost_rates = cfg.get("cost_rates", {})
        for model_id, rates in cost_rates.items():
            rows.append(
                ModelRow(
                    vendor=vendor,
                    model_id=model_id,
                    input_per_million=getattr(rates, "input_per_million", 0.0),
                    output_per_million=getattr(rates, "output_per_million", 0.0),
                    is_free_tier=getattr(rates, "is_free_tier", False),
                    input_modalities=getattr(rates, "input_modalities", []),
                    supported_parameters=getattr(rates, "supported_parameters", []),
                    pricing_valid_until=getattr(rates, "pricing_valid_until", None),
                )
            )
    return rows


def _parse_args(arg: str) -> dict:
    """Parse /models arguments into filter dict."""
    opts: dict = {}
    try:
        tokens = shlex.split(arg)
    except ValueError:
        return opts
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == "--vendor" and i + 1 < len(tokens):
            opts["vendor"] = tokens[i + 1]
            i += 2
        elif t == "--has" and i + 1 < len(tokens):
            opts.setdefault("has", []).append(tokens[i + 1])
            i += 2
        elif t == "--free":
            opts["free"] = True
            i += 1
        elif t == "--max-input" and i + 1 < len(tokens):
            try:
                opts["max_input"] = float(tokens[i + 1])
            except ValueError:
                pass
            i += 2
        elif t == "--search" and i + 1 < len(tokens):
            opts["search"] = tokens[i + 1].lower()
            i += 2
        else:
            i += 1
    return opts


def _capability_tags(row: ModelRow) -> list[str]:
    tags = []
    if "image" in row.input_modalities or "video" in row.input_modalities:
        tags.append("vision")
    if "tools" in row.supported_parameters:
        tags.append("tools")
    if "reasoning" in row.supported_parameters or "include_reasoning" in row.supported_parameters:
        tags.append("reasoning")
    if row.is_free_tier:
        tags.append("free")
    if row.pricing_valid_until:
        tags.append("deprecated")
    return tags


def _apply_filters(rows: list[ModelRow], opts: dict) -> list[ModelRow]:
    if vendor := opts.get("vendor"):
        rows = [r for r in rows if r.vendor == vendor]
    if opts.get("free"):
        rows = [r for r in rows if r.is_free_tier]
    if max_input := opts.get("max_input"):
        rows = [r for r in rows if r.input_per_million <= max_input]
    for cap in opts.get("has", []):
        if cap == "vision":
            rows = [
                r for r in rows if "image" in r.input_modalities or "video" in r.input_modalities
            ]
        elif cap == "tools":
            rows = [r for r in rows if "tools" in r.supported_parameters]
        elif cap == "reasoning":
            rows = [
                r
                for r in rows
                if "reasoning" in r.supported_parameters
                or "include_reasoning" in r.supported_parameters
            ]
        else:
            rows = [r for r in rows if cap in r.input_modalities or cap in r.supported_parameters]
    if search := opts.get("search"):
        rows = [r for r in rows if search in r.model_id.lower() or search in r.vendor.lower()]
    return rows


def run(arg: str) -> str:
    """Entry point called by cmd_models in slash_commands.py."""
    if arg.strip() in ("--help", "-h", ""):
        return (
            "Usage: /models [--vendor <name>] [--has <capability>] [--free] "
            "[--max-input <$/M>] [--search <query>]\n"
            "Capabilities: vision, tools, reasoning\n"
            "Examples:\n"
            "  /models --vendor kimi\n"
            "  /models --has vision\n"
            "  /models --has tools --max-input 1.0\n"
            "  /models --free"
        )

    opts = _parse_args(arg)
    rows = _apply_filters(_all_models(), opts)

    if not rows:
        return "[/models] No models match the given filters."

    # Group by vendor, sort within vendor by input price
    from collections import defaultdict

    by_vendor: dict[str, list[ModelRow]] = defaultdict(list)
    for r in rows:
        by_vendor[r.vendor].append(r)
    for vendor in by_vendor:
        by_vendor[vendor].sort(key=lambda r: r.input_per_million)

    lines = [f"{'MODEL ID':<40} {'$/M in':>8} {'$/M out':>8}  TAGS"]
    lines.append("-" * 72)
    for vendor in sorted(by_vendor):
        lines.append(f"\n{vendor}:")
        for r in by_vendor[vendor]:
            tags = _capability_tags(r)
            tag_str = " ".join(f"[{t}]" for t in tags) if tags else ""
            price_in = "FREE" if r.is_free_tier else f"${r.input_per_million:.3f}"
            price_out = "FREE" if r.is_free_tier else f"${r.output_per_million:.3f}"
            lines.append(f"  {r.model_id:<38} {price_in:>8} {price_out:>8}  {tag_str}")

    lines.append(f"\n{len(rows)} model(s) listed.")
    return "\n".join(lines)
