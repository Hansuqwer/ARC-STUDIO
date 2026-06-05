"""v0.6-alpha: Capability-aware UI state from catalog CostRate data.

Deterministic lookup — no LLM in decision path (CoSAI).
Catalog drives UI only — does NOT affect connection layer.
Fail-closed: unknown model → all gates return False.
"""

from __future__ import annotations

_ALL_GATES = ("vision", "tools", "reasoning", "audio", "video", "structured_output")


def get_capabilities(model_id: str, vendor: str | None = None) -> dict[str, bool]:
    """Return {feature: bool} dict for the given model.

    Fail-closed: unknown model or missing CostRate entry → all False.
    Never raises.
    """
    result = {gate: False for gate in _ALL_GATES}
    try:
        from agent_runtime_cockpit.providers.openai_compatible import VENDOR_CONFIGS

        rates = None
        if vendor:
            cfg = VENDOR_CONFIGS.get(vendor)
            if cfg:
                rates = cfg.get("cost_rates", {}).get(model_id)
            else:
                return result  # vendor hint given but vendor unknown → fail-closed

        if rates is None:
            # Search all vendors — prefer entry with non-empty capability data
            best: object = None
            for cfg in VENDOR_CONFIGS.values():
                r = cfg.get("cost_rates", {}).get(model_id)
                if r is not None:
                    if best is None:
                        best = r
                    # Upgrade to this entry if it has actual capability data
                    if getattr(r, "supported_parameters", []) or getattr(r, "input_modalities", []):
                        best = r
                        break
            rates = best

        if rates is None:
            return result  # fail-closed

        modalities = getattr(rates, "input_modalities", [])
        params = getattr(rates, "supported_parameters", [])

        result["vision"] = "image" in modalities
        result["audio"] = "audio" in modalities
        result["video"] = "video" in modalities
        result["tools"] = "tools" in params
        result["reasoning"] = "reasoning" in params or "include_reasoning" in params
        result["structured_output"] = "response_format" in params

    except Exception:
        pass  # always fail-closed

    return result


def is_capability_enabled(model_id: str, capability: str, vendor: str | None = None) -> bool:
    """Convenience single-capability lookup. Returns False on any error."""
    return get_capabilities(model_id, vendor).get(capability, False)
