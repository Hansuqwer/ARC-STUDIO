"""Capability Card policy CLI commands.

These commands use the card-aware policy linter to analyze capability cards
and produce policy reports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import DEBUG_FLAG, JSON_FLAG, WORKSPACE_FLAG, _out, _setup_logging, _workspace
from ._subapps import capabilities_app

# Import capabilities module
from ..capabilities import (
    CapabilityCard,
    cards_from_ir_graph,
    lint_cards,
)


# ── policy command ─────────────────────────────────────────────────────────────


@capabilities_app.command("policy")
def capabilities_policy(
    from_ir: Optional[str] = typer.Option(
        None,
        "--from-ir",
        help="Path to a compiled IR JSON file to lint cards from.",
    ),
    from_cards: Optional[str] = typer.Option(
        None,
        "--from-cards",
        help="Path to a directory of Capability Card JSON files to lint.",
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Run the card-aware policy linter against Capability Cards.

    This command analyzes Capability Cards and reports policy issues like:
    - Missing trust requirements for dangerous capabilities
    - Unapproved or blocked MCP tools
    - Drifted MCP manifests
    - Missing HITL requirements
    - Unpaid paid calls
    - Network access without audit

    Examples:
        arc capabilities policy --from-ir workflow.ir.json
        arc capabilities policy --from-cards .arc/capabilities/cards/
    """
    _setup_logging(debug)
    ws = _workspace(workspace)

    cards: list[CapabilityCard] = []
    source: str = ""

    # Generate cards from IR
    if from_ir:
        from ..swarmgraph_ir import from_json

        ir_path = Path(from_ir)
        if not ir_path.is_file():
            _out(err(ArcErrorCode.INVALID_INPUT, f"IR file not found: {from_ir}"), json_output)
            raise typer.Exit(1)

        try:
            graph = from_json(ir_path.read_text(encoding="utf-8"))
            cards = cards_from_ir_graph(graph)
            source = f"IR graph: {graph.id}"
        except Exception as exc:
            _out(err(ArcErrorCode.INVALID_INPUT, f"Failed to parse IR: {exc}"), json_output)
            raise typer.Exit(1) from exc

    # Load cards from directory
    elif from_cards:
        cards_dir = Path(from_cards)
        if not cards_dir.is_dir():
            _out(
                err(ArcErrorCode.INVALID_INPUT, f"Cards directory not found: {from_cards}"),
                json_output,
            )
            raise typer.Exit(1)

        for card_file in sorted(cards_dir.glob("*.json")):
            try:
                card = CapabilityCard.model_validate_json(card_file.read_text())
                cards.append(card)
            except Exception:
                continue

        source = f"Card directory: {cards_dir}"

    else:
        _out(
            err(ArcErrorCode.INVALID_INPUT, "Provide --from-ir or --from-cards."),
            json_output,
        )
        raise typer.Exit(1)

    if not cards:
        _out(err(ArcErrorCode.INVALID_INPUT, "No valid cards found."), json_output)
        raise typer.Exit(1)

    # Run policy linting
    try:
        report = lint_cards(cards, workspace_root=ws)
    except Exception as exc:
        _out(err(ArcErrorCode.INTERNAL_ERROR, f"Policy lint failed: {exc}"), json_output)
        raise typer.Exit(1) from exc

    # Build response
    payload = {
        "workflow_id": report.workflow_id,
        "workflow_name": report.workflow_name,
        "card_count": report.card_count,
        "high_risk_cards": report.high_risk_cards,
        "can_run": report.can_run,
        "requires_review": report.requires_review,
        "source": source,
        "issues": [
            {
                "rule": i.rule,
                "severity": i.severity,
                "card_id": i.card_id,
                "message": i.message,
                "remediation": i.remediation,
                "capability_affected": i.capability_affected,
            }
            for i in report.issues
        ],
        "issue_count": len(report.issues),
        "error_count": len(report.errors),
        "warning_count": len(report.warnings),
    }

    _out(ok(payload, workspace=str(ws)), json_output)


# ── policy registry command ───────────────────────────────────────────────────


@capabilities_app.command("policy-registry")
def capabilities_policy_registry(
    path: Optional[str] = typer.Option(
        None,
        "--path",
        "-p",
        help="Path to the cards directory (default: workspace .arc/capabilities/cards/).",
    ),
    entity_type: Optional[str] = typer.Option(
        None,
        "--entity-type",
        "-t",
        help="Filter by entity type (e.g. ir_node, mcp_tool).",
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Run the card-aware policy linter against all cards in a registry.

    This scans all Capability Cards in a directory or the workspace registry
    and produces a policy report for each workflow/graph.

    Examples:
        arc capabilities policy-registry
        arc capabilities policy-registry --path .arc/capabilities/cards/
        arc capabilities policy-registry --entity-type ir_node
    """
    _setup_logging(debug)
    ws = _workspace(workspace)

    # Determine cards directory
    if path:
        cards_dir = Path(path)
        if not cards_dir.is_dir():
            _out(err(ArcErrorCode.INVALID_INPUT, f"Cards directory not found: {path}"), json_output)
            raise typer.Exit(1)
    else:
        cards_dir = ws / ".arc" / "capabilities" / "cards"
        if not cards_dir.is_dir():
            _out(
                err(ArcErrorCode.INVALID_INPUT, f"Cards directory not found: {cards_dir}"),
                json_output,
            )
            raise typer.Exit(1)

    # Load all cards
    cards: list[CapabilityCard] = []
    for card_file in sorted(cards_dir.glob("*.json")):
        try:
            card = CapabilityCard.model_validate_json(card_file.read_text())
            if entity_type and card.entity_type.value != entity_type:
                continue
            cards.append(card)
        except Exception:
            continue

    if not cards:
        _out(err(ArcErrorCode.INVALID_INPUT, "No valid cards found."), json_output)
        raise typer.Exit(1)

    # Group by workflow and lint
    from ..capabilities import CardPolicyReport

    workflows: dict[str, list[CapabilityCard]] = {}
    for card in cards:
        if card.entity_type.value == "ir_graph":
            workflow_id = card.id
        elif card.entity_type.value == "ir_node":
            parts = card.id.split("-")
            if len(parts) >= 3:
                workflow_id = f"ir-graph-{parts[2]}"
            else:
                workflow_id = "unknown"
        else:
            workflow_id = f"other-{card.entity_type.value}"

        if workflow_id not in workflows:
            workflows[workflow_id] = []
        workflows[workflow_id].append(card)

    reports: list[CardPolicyReport] = []
    total_issues = 0
    total_errors = 0

    for workflow_id, workflow_cards in workflows.items():
        graph_card = next((c for c in workflow_cards if c.entity_type.value == "ir_graph"), None)
        workflow_name = graph_card.name if graph_card else workflow_id

        report = lint_cards(
            workflow_cards,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            workspace_root=ws,
        )
        reports.append(report)
        total_issues += len(report.issues)
        total_errors += len(report.errors)

    # Build response
    can_run_all = all(r.can_run for r in reports)
    requires_review_any = any(r.requires_review for r in reports)

    payload = {
        "workflow_count": len(reports),
        "total_cards": len(cards),
        "total_issues": total_issues,
        "total_errors": total_errors,
        "can_run_all": can_run_all,
        "requires_review_any": requires_review_any,
        "reports": [
            {
                "workflow_id": r.workflow_id,
                "workflow_name": r.workflow_name,
                "card_count": r.card_count,
                "high_risk_cards": r.high_risk_cards,
                "can_run": r.can_run,
                "requires_review": r.requires_review,
                "issue_count": len(r.issues),
                "error_count": len(r.errors),
                "warning_count": len(r.warnings),
            }
            for r in reports
        ],
    }

    _out(ok(payload, workspace=str(ws)), json_output)
