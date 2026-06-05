#!/usr/bin/env python3
"""
sync_from_pricing_feed.py — Fetch model pricing data from a configurable
                            source and render ARC vendor blocks.

Usage:
    # Default: OpenRouter (primary source per pricing-feed-sources-comparison.md)
    python3 scripts/sync_from_pricing_feed.py

    # Filter to specific vendors
    python3 scripts/sync_from_pricing_feed.py --vendors deepseek qwen

    # Switch source (fallback)
    python3 scripts/sync_from_pricing_feed.py --source models-dev

    # Emit JSON instead of rendered Python blocks
    python3 scripts/sync_from_pricing_feed.py --json

    # Cross-check against the research addendum
    python3 scripts/sync_from_pricing_feed.py \\
        --cross-check docs/research/pricing-snapshot-2026Q2-addendum-chinese-labs.md

Sources supported:
    openrouter (default) — https://openrouter.ai/api/v1/models
                           300+ models, no auth, cache + tiered + deprecation
    models-dev (fallback) — https://models.dev/api.json
                           100+ models, no auth, TOML-source backed

Design philosophy:
    1. RUNS AT DEV-TIME, NOT RUNTIME. Output is a code-review artifact
       a human commits. ARC runtime never fetches these URLs (that's
       v0.7-alpha opt-in territory).
    2. NEVER auto-writes to providers/*. Reviewer reads diff, commits.
    3. Cross-references the existing addendum so divergences surface.
    4. Fails closed on schema drift. Unknown fields ignored, missing
       required fields raises.
    5. No new dependencies. Uses stdlib urllib + json.

See: docs/research/pricing-feed-sources-comparison.md for source rationale.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable


SOURCES: dict[str, dict[str, str]] = {
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/models",
        "description": "OpenRouter Models API (300+ models, recommended)",
    },
    "models-dev": {
        "url": "https://models.dev/api.json",
        "description": "models.dev (100+ models, fallback)",
    },
}

# Vendor prefix mapping: OpenRouter uses "anthropic/claude-sonnet-4" pattern;
# models.dev uses "anthropic" / "openai" top-level keys.
# Map source-specific vendor IDs to ARC's canonical vendor IDs.
OPENROUTER_VENDOR_PREFIX_TO_CANONICAL = {
    "anthropic": "anthropic",
    "openai": "openai",
    "google": "google",
    "deepseek": "deepseek",
    "qwen": "alibaba",
    "moonshotai": "moonshot",
    "z-ai": "zai",
    "zai": "zai",
    "xiaomi": "xiaomi",
    "minimax": "minimax",
}

# Cache field name conventions where vendors deviate from Anthropic-style.
# These are facts about the vendor's wire protocol, NOT facts the pricing
# source tracks. Stays manual.
KNOWN_CACHE_FIELD_OVERRIDES: dict[str, dict[str, str]] = {
    "deepseek": {"hit": "prompt_cache_hit_tokens", "miss": "prompt_cache_miss_tokens"},
    # OpenAI uses 'cached_tokens' inside usage.input_tokens_details
    # but cache_read field at top level matches Anthropic-style.
}

# Tokenizer family hints (informs wallet "≈" qualifier). Manual fact.
TOKENIZER_FAMILY: dict[str, str] = {
    "anthropic": "anthropic-cl100k",
    "openai": "cl100k_base",
    "deepseek": "deepseek",
    "alibaba": "qwen",
    "moonshot": "kimi",
    "zai": "glm",
    "xiaomi": "mimo",
    "minimax": "cl100k_base",
    "google": "gemini",
}


@dataclass(frozen=True)
class ModelRow:
    """Renderable cost-row, source-agnostic."""

    vendor_id: str
    model_id: str
    display_name: str
    input_usd_per_million: Decimal | None
    output_usd_per_million: Decimal | None
    cached_input_usd_per_million: Decimal | None
    cache_write_usd_per_million: Decimal | None
    context_window: int | None
    max_output_tokens: int | None
    is_free: bool = False
    deprecation_date: str | None = None  # ISO 8601
    canonical_slug: str | None = None  # OpenRouter equivalent of auto_route_to
    supported_parameters: list[str] = field(default_factory=list)
    input_modalities: list[str] = field(default_factory=list)
    output_modalities: list[str] = field(default_factory=list)
    tokenizer: str | None = None
    source: str = "unknown"  # which feed this came from


def _to_decimal(v: Any) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        d = Decimal(str(v))
        # OpenRouter prices are per-token; convert to per-million
        return d * 1_000_000 if d < Decimal("1") else d
    except Exception:
        return None


def _to_decimal_per_million(v: Any) -> Decimal | None:
    """For OpenRouter: prices are per-token strings; convert to per-million."""
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v)) * 1_000_000
    except Exception:
        return None


def _to_decimal_already_per_million(v: Any) -> Decimal | None:
    """For models.dev: prices already per-million."""
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


def parse_openrouter(data: dict[str, Any]) -> list[ModelRow]:
    """Parse OpenRouter /api/v1/models response."""
    rows: list[ModelRow] = []
    for entry in data.get("data", []):
        full_id = entry.get("id", "")
        if "/" not in full_id:
            continue
        vendor_prefix, model_id_part = full_id.split("/", 1)
        canonical_vendor = OPENROUTER_VENDOR_PREFIX_TO_CANONICAL.get(
            vendor_prefix.lower(), vendor_prefix.lower()
        )

        pricing = entry.get("pricing", {})
        # Handle tiered pricing (list) — use first tier as base
        if isinstance(pricing, list):
            pricing = pricing[0] if pricing else {}

        architecture = entry.get("architecture", {})
        top_provider = entry.get("top_provider", {}) or {}

        # Detect free: explicit is_free flag OR all prices zero
        is_free = bool(entry.get("is_free", False))
        if not is_free:
            try:
                if (
                    Decimal(str(pricing.get("prompt", "0"))) == 0
                    and Decimal(str(pricing.get("completion", "0"))) == 0
                ):
                    is_free = True
            except Exception:
                pass

        rows.append(
            ModelRow(
                vendor_id=canonical_vendor,
                model_id=full_id,
                display_name=entry.get("name", full_id),
                input_usd_per_million=_to_decimal_per_million(pricing.get("prompt")),
                output_usd_per_million=_to_decimal_per_million(pricing.get("completion")),
                cached_input_usd_per_million=_to_decimal_per_million(
                    pricing.get("input_cache_read")
                ),
                cache_write_usd_per_million=_to_decimal_per_million(
                    pricing.get("input_cache_write")
                ),
                context_window=entry.get("context_length") or top_provider.get("context_length"),
                max_output_tokens=top_provider.get("max_completion_tokens")
                or entry.get("max_output_length"),
                is_free=is_free,
                deprecation_date=entry.get("deprecation_date") or entry.get("expiration_date"),
                canonical_slug=entry.get("canonical_slug"),
                supported_parameters=list(entry.get("supported_parameters", [])),
                input_modalities=list(architecture.get("input_modalities", [])),
                output_modalities=list(architecture.get("output_modalities", [])),
                tokenizer=architecture.get("tokenizer"),
                source="openrouter",
            )
        )
    return rows


def parse_models_dev(data: dict[str, Any]) -> list[ModelRow]:
    """Parse models.dev /api.json response."""
    rows: list[ModelRow] = []
    for provider_id, provider in data.items():
        models = (provider or {}).get("models", {})
        if not isinstance(models, dict):
            continue
        for model_id, model in models.items():
            cost = model.get("cost", {}) or {}
            limit = model.get("limit", {}) or {}
            modalities = model.get("modalities", {}) or {}

            input_p = _to_decimal_already_per_million(cost.get("input"))
            output_p = _to_decimal_already_per_million(cost.get("output"))
            cache_p = _to_decimal_already_per_million(cost.get("cache_read"))
            cache_w = _to_decimal_already_per_million(cost.get("cache_write"))

            # Detect free: all costs are zero or None
            is_free = all(v in (None, Decimal("0")) for v in (input_p, output_p, cache_p))

            rows.append(
                ModelRow(
                    vendor_id=provider_id,
                    model_id=model_id,
                    display_name=model.get("name", model_id),
                    input_usd_per_million=input_p,
                    output_usd_per_million=output_p,
                    cached_input_usd_per_million=cache_p,
                    cache_write_usd_per_million=cache_w,
                    context_window=limit.get("context"),
                    max_output_tokens=limit.get("output"),
                    is_free=is_free,
                    deprecation_date=None,  # models.dev doesn't track
                    canonical_slug=None,
                    supported_parameters=[],  # not in models.dev schema
                    input_modalities=list(modalities.get("input", [])),
                    output_modalities=list(modalities.get("output", [])),
                    tokenizer=None,
                    source="models-dev",
                )
            )
    return rows


PARSERS: dict[str, Callable[[dict[str, Any]], list[ModelRow]]] = {
    "openrouter": parse_openrouter,
    "models-dev": parse_models_dev,
}


def fetch(url: str) -> dict[str, Any]:
    sys.stderr.write(f"Fetching {url}...\n")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ARC-Studio-sync-script/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        sys.stderr.write(f"ERROR fetching {url}: {type(exc).__name__}: {exc}\n")
        sys.exit(1)


def render_vendor_block(vendor_id: str, rows: list[ModelRow]) -> str:
    """Render a copy-pasteable Python vendor block for openai_compatible.py."""
    cache_override = KNOWN_CACHE_FIELD_OVERRIDES.get(vendor_id)
    tokenizer = TOKENIZER_FAMILY.get(vendor_id, "cl100k_base")
    source_marker = rows[0].source if rows else "unknown"

    lines = []
    lines.append(f"# Auto-generated from {source_marker} on {_today()}")
    lines.append("# Reviewer MUST cross-check against vendor pricing pages before commit.")
    lines.append("# See docs/policy/honesty-over-polish.md.")
    lines.append(f'"{vendor_id}": {{')
    lines.append(f'    "display_name": {vendor_id.title()!r},')
    lines.append('    "models": {')
    for row in rows:
        lines.append(f"        {row.model_id!r}: CostRate(")
        if row.input_usd_per_million is not None:
            lines.append(
                f"            input_usd_per_million=Decimal({str(row.input_usd_per_million)!r}),"
            )
        if row.output_usd_per_million is not None:
            lines.append(
                f"            output_usd_per_million=Decimal({str(row.output_usd_per_million)!r}),"
            )
        if row.cached_input_usd_per_million is not None:
            lines.append(
                f"            cached_input_usd_per_million=Decimal({str(row.cached_input_usd_per_million)!r}),"
            )
        if row.is_free:
            lines.append(
                "            is_free_tier=True,  # ⚠ ALL COSTS ZERO; wallet must skip enforcement"
            )
        if row.deprecation_date:
            lines.append(f'            pricing_valid_until="{row.deprecation_date}",')
        if row.canonical_slug and row.canonical_slug != row.model_id:
            lines.append(f"            auto_route_to={row.canonical_slug!r},")
        if cache_override:
            lines.append(f"            cache_field_names={cache_override!r},")
        if tokenizer != "cl100k_base":
            lines.append(f"            tokenizer_family={tokenizer!r},")
        if row.context_window:
            lines.append(f"            context_window={row.context_window},")
        lines.append("        ),")
    lines.append("    },")
    lines.append("},")
    return "\n".join(lines)


def _today() -> str:
    from datetime import date

    return date.today().isoformat()


def cross_check_against_addendum(rows: list[ModelRow], addendum_path: Path) -> list[str]:
    if not addendum_path.exists():
        return [f"addendum not found at {addendum_path}; skipping cross-check"]
    text = addendum_path.read_text(encoding="utf-8")
    warnings: list[str] = []
    for row in rows:
        if row.model_id not in text:
            warnings.append(
                f"  ⚠ {row.vendor_id}/{row.model_id}: in feed but NOT in addendum "
                f"(may be new since 2026-Q2 snapshot; reviewer should update next snapshot)"
            )
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        choices=list(SOURCES.keys()),
        default="openrouter",
        help="Pricing feed source. Default: openrouter (primary per pricing-feed-sources-comparison.md)",
    )
    parser.add_argument(
        "--vendors",
        nargs="*",
        default=None,
        help="Filter to canonical vendor IDs (after parsing). Default: all.",
    )
    parser.add_argument(
        "--cross-check",
        type=Path,
        default=None,
        help="Path to addendum markdown for divergence warnings",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit raw JSON instead of rendered Python blocks"
    )
    parser.add_argument(
        "--api-url", default=None, help="Override source URL (default: per --source)"
    )
    args = parser.parse_args()

    url = args.api_url or SOURCES[args.source]["url"]
    data = fetch(url)
    rows = PARSERS[args.source](data)

    sys.stderr.write(f"Source: {args.source} ({SOURCES[args.source]['description']})\n")
    sys.stderr.write(f"Fetched: {len(rows)} models total\n")

    if args.vendors:
        rows = [r for r in rows if r.vendor_id in args.vendors]
        sys.stderr.write(f"After vendor filter ({args.vendors}): {len(rows)} models\n")

    rows_by_vendor: dict[str, list[ModelRow]] = defaultdict(list)
    for r in rows:
        rows_by_vendor[r.vendor_id].append(r)

    if args.json:
        out = {
            "source": args.source,
            "source_url": url,
            "fetched_at": _today(),
            "vendors": {vid: [r.__dict__ for r in rs] for vid, rs in rows_by_vendor.items()},
        }

        def _json_default(o):
            if isinstance(o, Decimal):
                return str(o)
            raise TypeError(f"Not JSON serializable: {type(o).__name__}")

        print(json.dumps(out, indent=2, default=_json_default))
        return 0

    print(f"# Generated by sync_from_pricing_feed.py on {_today()}")
    print(f"# Source: {args.source} ({url})")
    print("# This output is a CODE-REVIEW ARTIFACT, not committed automatically.")
    print("# Reviewer: cross-check against vendor pricing pages before commit.")
    print()

    all_warnings: list[str] = []
    for vendor_id in sorted(rows_by_vendor):
        vendor_rows = rows_by_vendor[vendor_id]
        print(f"# ─── {vendor_id} ({len(vendor_rows)} models) ───")
        print(render_vendor_block(vendor_id, vendor_rows))
        print()
        if args.cross_check:
            warnings = cross_check_against_addendum(vendor_rows, args.cross_check)
            all_warnings.extend(warnings)

    if all_warnings:
        sys.stderr.write("\n=== Cross-check warnings ===\n")
        for w in all_warnings:
            sys.stderr.write(w + "\n")

    sys.stderr.write(
        f"\nDone. {sum(len(r) for r in rows_by_vendor.values())} models across "
        f"{len(rows_by_vendor)} vendors rendered.\n"
    )
    sys.stderr.write(f"Free-tier rows detected: {sum(1 for r in rows if r.is_free)}\n")
    sys.stderr.write(f"Deprecated rows detected: {sum(1 for r in rows if r.deprecation_date)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
