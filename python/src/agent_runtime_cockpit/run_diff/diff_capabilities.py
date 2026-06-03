"""Capability card diff - compare two CapabilityCard lists."""

from __future__ import annotations

from .models import CapabilityDiff, DiffSubject, DiffSubjectKind, DiffSummary, RunDiffReport


def diff_capability_cards(left_cards, right_cards):
    left_map = {c.id: c for c in left_cards}
    right_map = {c.id: c for c in right_cards}
    cards_added = [cid for cid in right_map if cid not in left_map]
    cards_removed = [cid for cid in left_map if cid not in right_map]
    cards_changed = []
    caps_added = []
    caps_removed = []
    risk_level_changed = []
    for cid in set(left_map) & set(right_map):
        lc = left_map[cid]
        rc = right_map[cid]
        if lc.risk_level != rc.risk_level:
            risk_level_changed.append(
                {
                    "card_id": cid,
                    "left_level": lc.risk_level.value,
                    "right_level": rc.risk_level.value,
                }
            )
        l_caps = {p.kind for p in lc.permissions}
        r_caps = {p.kind for p in rc.permissions}
        new_caps = r_caps - l_caps
        rem_caps = l_caps - r_caps
        if new_caps:
            caps_added.extend(sorted(new_caps))
        if rem_caps:
            caps_removed.extend(sorted(rem_caps))
        mcp_drift = (lc.mcp and rc.mcp and lc.mcp.drifted != rc.mcp.drifted) or (
            (lc.mcp and not rc.mcp) or (not lc.mcp and rc.mcp)
        )
        if mcp_drift:
            cards_changed.append({"card_id": cid, "changes": {}, "mcp_drift": mcp_drift})
    cap_diff = CapabilityDiff(
        cards_added=cards_added,
        cards_removed=cards_removed,
        cards_changed=cards_changed,
        capabilities_added=caps_added,
        capabilities_removed=caps_removed,
        risk_level_changed=risk_level_changed,
        mcp_drift_detected=any(c.get("mcp_drift") for c in cards_changed),
        trust_regression=False,
    )
    summary = DiffSummary()
    summary.compute_total()
    report = RunDiffReport(
        left=DiffSubject(
            kind=DiffSubjectKind.CAPABILITY_CARD,
            id="capabilities-left",
            metadata={"card_count": len(left_cards)},
        ),
        right=DiffSubject(
            kind=DiffSubjectKind.CAPABILITY_CARD,
            id="capabilities-right",
            metadata={"card_count": len(right_cards)},
        ),
        mode="capability_vs_capability",
        summary=summary,
        capability_diff=cap_diff,
        warnings=["MCP drift detected in capability cards"] if cap_diff.mcp_drift_detected else [],
    )
    return report.with_hash()


def diff_capability_cards_from_paths(path_a, path_b):
    import json

    errors = []
    warnings = []
    left_cards = []
    right_cards = []
    for path, target in [(path_a, "left"), (path_b, "right")]:
        try:
            from agent_runtime_cockpit.capabilities.models import CapabilityCard

            data = json.loads(open(path).read())
            cards = [CapabilityCard.model_validate(item) for item in data]
            if target == "left":
                left_cards = cards
            else:
                right_cards = cards
        except FileNotFoundError:
            errors.append(f"File not found: {path}")
        except json.JSONDecodeError:
            errors.append(f"Invalid JSON: {path}")
        except Exception as exc:
            errors.append(f"Failed to parse {path}: {exc}")
    if errors:
        report = RunDiffReport(
            left=DiffSubject(kind=DiffSubjectKind.CAPABILITY_CARD, id=path_a, path=path_a),
            right=DiffSubject(kind=DiffSubjectKind.CAPABILITY_CARD, id=path_b, path=path_b),
            mode="capability_vs_capability",
            errors=errors,
        )
        return report.with_hash(), errors, warnings
    return diff_capability_cards(left_cards, right_cards), errors, warnings
