"""v0.6-alpha: /model-info slash command — detailed catalog data for one model."""

from __future__ import annotations

from datetime import date


def _lookup(vendor: str, model_id: str):
    """Return (vendor_cfg, CostRates) or (None, None)."""
    from ...providers.openai_compatible import VENDOR_CONFIGS

    cfg = VENDOR_CONFIGS.get(vendor)
    if cfg is None:
        return None, None
    rates = cfg.get("cost_rates", {}).get(model_id)
    return cfg, rates


def _all_by_id(query_id: str):
    """Find (vendor, model_id, rates) by '<vendor>/<model_id>' or bare '<model_id>'."""
    from ...providers.openai_compatible import VENDOR_CONFIGS

    if "/" in query_id:
        vendor, mid = query_id.split("/", 1)
        cfg, rates = _lookup(vendor, mid)
        if rates:
            return vendor, mid, rates
        return None, query_id, None

    # Bare model ID — search all vendors
    for vendor, cfg in VENDOR_CONFIGS.items():
        rates = cfg.get("cost_rates", {}).get(query_id)
        if rates:
            return vendor, query_id, rates
    return None, query_id, None


def run(arg: str) -> str:
    """Entry point called by cmd_model_info."""
    query = arg.strip()
    if not query or query in ("--help", "-h"):
        return "Usage: /model-info <vendor/model-id> or /model-info <model-id>"

    vendor, model_id, rates = _all_by_id(query)
    if rates is None:
        return f"[not found] No catalog entry for '{query}'. Run /models to list available models."

    lines = [f"Model: {vendor}/{model_id}" if vendor else f"Model: {model_id}"]
    lines.append("─" * 60)

    # Pricing
    if getattr(rates, "is_free_tier", False):
        lines.append("Pricing:    FREE TIER (via OpenRouter free tier; rate-limited)")
    else:
        lines.append(f"Input:      ${rates.input_per_million:.4f} / M tokens")
        lines.append(f"Output:     ${rates.output_per_million:.4f} / M tokens")
        if rates.cache_read_per_million:
            lines.append(f"Cache read: ${rates.cache_read_per_million:.4f} / M tokens")
        if getattr(rates, "cache_storage_usd_per_million_per_hour", None):
            lines.append(
                f"Cache store: ${rates.cache_storage_usd_per_million_per_hour:.4f} / M·hour"
            )

    # Modalities
    modalities = getattr(rates, "input_modalities", [])
    if modalities:
        lines.append(f"Modalities: {', '.join(modalities)}")
    else:
        lines.append("Modalities: text (assumed; no OpenRouter data)")

    # Capabilities
    params = getattr(rates, "supported_parameters", [])
    caps = []
    if "tools" in params:
        caps.append("tools")
    if "reasoning" in params or "include_reasoning" in params:
        caps.append("reasoning")
    if "response_format" in params:
        caps.append("structured-output")
    if caps:
        lines.append(f"Capabilities: {', '.join(caps)}")
    if params:
        lines.append(
            f"Parameters: {', '.join(sorted(params)[:8])}" + (" ..." if len(params) > 8 else "")
        )

    # Tokenizer
    tf = getattr(rates, "tokenizer_family", "cl100k_base")
    if tf != "cl100k_base":
        lines.append(f"Tokenizer:  {tf} (≈ cost estimate; heuristic may differ)")

    # Auto-route
    if route := getattr(rates, "auto_route_to", None):
        lines.append(f"Routes to:  {route}")

    # Deprecation
    if until := getattr(rates, "pricing_valid_until", None):
        try:
            until_date = date.fromisoformat(until)
            if until_date < date.today():
                lines.append(
                    f"⚠ DEPRECATED: pricing expired {until}. Use {route or 'a current model'}."
                )
            else:
                lines.append(f"⚠ Pricing valid until: {until}")
        except ValueError:
            pass

    return "\n".join(lines)
