"""Capability Card CLI commands — generate, inspect, validate, diff, list, explain.

These commands are read-only analysis: they read IR graphs, MCP registries, and
adapter metadata to generate and inspect Capability Cards. They never execute
workflows, call tools/models, open network connections, or launch MCP servers.
"""

from __future__ import annotations

import json
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
    cards_from_mcp_registry,
    card_hash,
    validate_card,
    sign_card_file,
    verify_card_file,
    generate_secret_key,
    generate_ecdsa_keypair,
)


def _load_card(path: Path) -> Optional[CapabilityCard]:
    """Load a CapabilityCard from a JSON file."""
    try:
        text = path.read_text(encoding="utf-8")
        card_dict = json.loads(text)
        return CapabilityCard.model_validate(card_dict)
    except Exception:
        return None


def _save_card(card: CapabilityCard, out_dir: Path) -> Path:
    """Save a CapabilityCard to a JSON file."""
    # Ensure hash is computed
    if not card.card_hash:
        card.card_hash = card_hash(card)

    # Redact secrets
    from ..capabilities.redaction import redact_card

    redacted = redact_card(card)

    # Save
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{card.card_hash[:16]}_{card.id.replace('/', '_')}.json"
    content = (
        redacted.model_dump_json(indent=2)
        if hasattr(redacted, "model_dump_json")
        else json.dumps(redacted, indent=2)
    )
    path.write_text(content, encoding="utf-8")
    return path


# ── generate command ──────────────────────────────────────────────────────────


@capabilities_app.command("generate")
def capabilities_generate(
    from_ir: Optional[str] = typer.Option(
        None,
        "--from-ir",
        help="Path to a compiled IR JSON file to generate cards from.",
    ),
    from_mcp: bool = typer.Option(
        False,
        "--from-mcp",
        help="Generate cards from local MCP registry (reads workspace registry).",
    ),
    out: Optional[str] = typer.Option(
        None,
        "--out",
        "-o",
        help="Output directory for generated cards (default: .arc/capabilities/cards/).",
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate Capability Cards from IR graphs or MCP registry.

    Examples:
        arc capabilities generate --from-ir workflow.ir.json --out .arc/capabilities/cards/
        arc capabilities generate --from-mcp --workspace /path/to/workspace
    """
    _setup_logging(debug)
    ws = _workspace(workspace)

    cards: list[CapabilityCard] = []
    sources: list[str] = []

    # Generate from IR
    if from_ir:
        from ..swarmgraph_ir import from_json

        ir_path = Path(from_ir)
        if not ir_path.is_file():
            _out(err(ArcErrorCode.INVALID_INPUT, f"IR file not found: {from_ir}"), json_output)
            raise typer.Exit(1)

        try:
            graph = from_json(ir_path.read_text(encoding="utf-8"))
            ir_cards = cards_from_ir_graph(graph)
            cards.extend(ir_cards)
            sources.append(f"IR graph: {graph.id}")
        except Exception as exc:
            _out(err(ArcErrorCode.INVALID_INPUT, f"Failed to parse IR: {exc}"), json_output)
            raise typer.Exit(1) from exc

    # Generate from MCP registry
    if from_mcp:
        try:
            mcp_cards = cards_from_mcp_registry(workspace=ws)
            cards.extend(mcp_cards)
            sources.append(f"MCP registry: {len(mcp_cards)} cards")
        except Exception as exc:
            _out(
                err(ArcErrorCode.INTERNAL_ERROR, f"Failed to read MCP registry: {exc}"), json_output
            )
            raise typer.Exit(1) from exc

    if not cards:
        _out(
            err(ArcErrorCode.INVALID_INPUT, "No cards generated. Provide --from-ir or --from-mcp."),
            json_output,
        )
        raise typer.Exit(1)

    # Save cards
    out_dir = Path(out) if out else ws / ".arc" / "capabilities" / "cards"
    saved_paths: list[str] = []

    for card in cards:
        path = _save_card(card, out_dir)
        # Use relative path if possible, otherwise absolute
        try:
            rel_path = path.relative_to(ws)
            saved_paths.append(str(rel_path))
        except ValueError:
            saved_paths.append(str(path))

    payload = {
        "cards_generated": len(cards),
        "sources": sources,
        "output_dir": str(out_dir.relative_to(ws)) if out_dir.is_relative_to(ws) else str(out_dir),
        "saved_cards": saved_paths,
    }

    _out(ok(payload, workspace=str(ws)), json_output)


# ── inspect command ───────────────────────────────────────────────────────────


@capabilities_app.command("inspect")
def capabilities_inspect(
    card_path: Optional[str] = typer.Argument(
        None,
        help="Path to a Capability Card JSON file, or card ID to look up in registry.",
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Inspect a Capability Card and display its capabilities.

    Examples:
        arc capabilities inspect .arc/capabilities/cards/abc123_ir-graph-xyz.json
        arc capabilities inspect ir-node-wf-min-agent --workspace /path/to/workspace
    """
    _setup_logging(debug)
    ws = _workspace(workspace)

    if not card_path:
        _out(err(ArcErrorCode.INVALID_INPUT, "Card path or ID is required."), json_output)
        raise typer.Exit(1)

    # Try to load from path first
    card: Optional[CapabilityCard] = None

    path = Path(card_path)
    if path.is_file():
        card = _load_card(path)
    else:
        # Try registry lookup
        from ..capabilities.registry import CardRegistry

        registry = CardRegistry(workspace=ws)
        card = registry.load(card_path)

    if not card:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Card not found: {card_path}"), json_output)
        raise typer.Exit(1)

    # Build inspection report
    caps = card.capabilities
    trust = card.trust
    audit = card.audit

    payload = {
        "id": card.id,
        "name": card.name,
        "entity_type": card.entity_type.value
        if hasattr(card.entity_type, "value")
        else str(card.entity_type),
        "description": card.description,
        "schema_version": card.schema_version,
        "card_hash": card.card_hash,
        "risk_level": card.risk_level.value
        if hasattr(card.risk_level, "value")
        else str(card.risk_level),
        "opaque": card.opaque,
        "requires_review": card.requires_review,
        "capabilities": {
            "can_read": caps.can_read,
            "can_write": caps.can_write,
            "can_delete": caps.can_delete,
            "can_execute": caps.can_execute,
            "can_network": caps.can_network,
            "can_call_tools": caps.can_call_tools,
            "can_call_mcp": caps.can_call_mcp,
            "can_call_models": caps.can_call_models,
            "can_read_secrets": caps.can_read_secrets,
            "can_make_paid_calls": caps.can_make_paid_calls,
            "can_request_hitl": caps.can_request_hitl,
            "can_replay": caps.can_replay,
        },
        "trust": {
            "requires_workspace_trust": trust.requires_workspace_trust,
            "trust_level": trust.trust_level.value
            if hasattr(trust.trust_level, "value")
            else str(trust.trust_level),
            "hitl_requirement": trust.hitl_requirement.value
            if hasattr(trust.hitl_requirement, "value")
            else str(trust.hitl_requirement),
            "approval_mode": trust.approval_mode.value
            if hasattr(trust.approval_mode, "value")
            else str(trust.approval_mode),
        },
        "audit": {
            "audit_required": audit.audit_required,
            "audit_level": audit.audit_level.value
            if hasattr(audit.audit_level, "value")
            else str(audit.audit_level),
            "receipt_required": audit.receipt_required,
        },
        "provenance": card.provenance.model_dump()
        if hasattr(card.provenance, "model_dump")
        else {},
        "mcp": card.mcp.model_dump() if card.mcp and hasattr(card.mcp, "model_dump") else None,
        "cost": card.cost.model_dump() if card.cost and hasattr(card.cost, "model_dump") else None,
        "permissions_count": len(card.permissions),
        "side_effects_count": len(card.side_effects),
    }

    _out(ok(payload, workspace=str(ws)), json_output)


# ── validate command ──────────────────────────────────────────────────────────


@capabilities_app.command("validate")
def capabilities_validate(
    card_path: str = typer.Argument(
        ...,
        help="Path to a Capability Card JSON file to validate.",
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Validate a Capability Card against the schema and rules.

    Exit code: 0 if valid, 1 if card not found, 2 if validation errors.

    Examples:
        arc capabilities validate .arc/capabilities/cards/abc123_ir-node-xyz.json
    """
    _setup_logging(debug)

    path = Path(card_path)
    if not path.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Card file not found: {card_path}"), json_output)
        raise typer.Exit(1)

    try:
        text = path.read_text(encoding="utf-8")
        card_dict = json.loads(text)
        card = CapabilityCard.model_validate(card_dict)
    except Exception as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Failed to parse card: {exc}"), json_output)
        raise typer.Exit(1) from exc

    report = validate_card(card)
    payload = {
        "ok": report.ok,
        "errors": [{"field": e.field, "message": e.message} for e in report.errors],
        "warnings": [{"field": w.field, "message": w.message} for w in report.warnings],
        "error_count": report.error_count,
        "warning_count": report.warning_count,
    }

    if not report.ok:
        _out(
            err(ArcErrorCode.INVALID_INPUT, "Card validation failed.", details=payload), json_output
        )
        raise typer.Exit(2)

    _out(ok(payload), json_output)


# ── diff command ──────────────────────────────────────────────────────────────


@capabilities_app.command("diff")
def capabilities_diff(
    old_card: str = typer.Argument(..., help="Path to the old card JSON file."),
    new_card: str = typer.Argument(..., help="Path to the new card JSON file."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Compare two Capability Cards and show differences.

    Examples:
        arc capabilities diff old.card.json new.card.json
    """
    _setup_logging(debug)

    old_path = Path(old_card)
    new_path = Path(new_card)

    if not old_path.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Old card not found: {old_card}"), json_output)
        raise typer.Exit(1)
    if not new_path.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"New card not found: {new_card}"), json_output)
        raise typer.Exit(1)

    try:
        old_card_obj = CapabilityCard.model_validate_json(old_path.read_text())
        new_card_obj = CapabilityCard.model_validate_json(new_path.read_text())
    except Exception as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Failed to parse cards: {exc}"), json_output)
        raise typer.Exit(1) from exc

    # Compute differences
    changes: dict = {}
    old_dict = old_card_obj.model_dump()
    new_dict = new_card_obj.model_dump()

    for key in set(list(old_dict.keys()) + list(new_dict.keys())):
        old_val = old_dict.get(key)
        new_val = new_dict.get(key)
        if old_val != new_val:
            changes[key] = {"old": old_val, "new": new_val}

    payload = {
        "old_id": old_card_obj.id,
        "new_id": new_card_obj.id,
        "old_hash": old_card_obj.card_hash,
        "new_hash": new_card_obj.card_hash,
        "hash_changed": old_card_obj.card_hash != new_card_obj.card_hash,
        "changes": changes,
        "change_count": len(changes),
    }

    _out(ok(payload), json_output)


# ── list command ──────────────────────────────────────────────────────────────


@capabilities_app.command("list")
def capabilities_list(
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
        help="Filter by entity type (e.g. ir_node, mcp_tool, mcp_server).",
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List all Capability Cards in a directory or registry.

    Examples:
        arc capabilities list --workspace /path/to/workspace
        arc capabilities list --path .arc/capabilities/cards/ --entity-type ir_node
    """
    _setup_logging(debug)
    ws = _workspace(workspace)

    if path:
        cards_dir = Path(path)
    else:
        cards_dir = ws / ".arc" / "capabilities" / "cards"

    if not cards_dir.is_dir():
        _out(
            err(ArcErrorCode.INVALID_INPUT, f"Cards directory not found: {cards_dir}"), json_output
        )
        raise typer.Exit(1)

    cards: list[CapabilityCard] = []
    for card_file in sorted(cards_dir.glob("*.json")):
        try:
            card = CapabilityCard.model_validate_json(card_file.read_text())
            if entity_type and card.entity_type.value != entity_type:
                continue
            cards.append(card)
        except Exception:
            continue

    payload = {
        "cards": [
            {
                "id": c.id,
                "name": c.name,
                "entity_type": c.entity_type.value
                if hasattr(c.entity_type, "value")
                else str(c.entity_type),
                "card_hash": c.card_hash,
                "risk_level": c.risk_level.value
                if hasattr(c.risk_level, "value")
                else str(c.risk_level),
                "requires_review": c.requires_review,
                "file": card_file.name,
            }
            for c in cards
        ],
        "count": len(cards),
        "directory": str(cards_dir.relative_to(ws))
        if cards_dir.is_relative_to(ws)
        else str(cards_dir),
    }

    _out(ok(payload, workspace=str(ws)), json_output)


# ── explain command ───────────────────────────────────────────────────────────


@capabilities_app.command("explain")
def capabilities_explain(
    card_path: str = typer.Argument(
        ...,
        help="Path to a Capability Card JSON file to explain.",
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Explain a Capability Card in human-readable format.

    Shows what the card allows, what it requires, and why.

    Examples:
        arc capabilities explain .arc/capabilities/cards/abc123_ir-node-xyz.json
    """
    _setup_logging(debug)

    path = Path(card_path)
    if not path.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Card file not found: {card_path}"), json_output)
        raise typer.Exit(1)

    try:
        card = CapabilityCard.model_validate_json(path.read_text())
    except Exception as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Failed to parse card: {exc}"), json_output)
        raise typer.Exit(1) from exc

    # Build explanation
    caps = card.capabilities

    can_do: list[str] = []
    requirements: list[str] = []

    if caps.can_read:
        can_do.append("Read data from workspace or environment")
    if caps.can_write:
        can_do.append("Write data to workspace or filesystem")
        requirements.append("Requires workspace trust")
    if caps.can_delete:
        can_do.append("Delete files or data")
        requirements.append("Requires explicit approval")
    if caps.can_execute:
        can_do.append("Execute tool commands or scripts")
        requirements.append("Requires HITL approval")
    if caps.can_network:
        can_do.append("Make network requests")
        requirements.append("Requires workspace trust")
    if caps.can_call_tools:
        can_do.append("Call tools or functions")
    if caps.can_call_mcp:
        can_do.append("Invoke MCP tools")
        if card.mcp:
            requirements.append(f"MCP server: {card.mcp.server_id}")
    if caps.can_call_models:
        can_do.append("Call model APIs")
        if card.cost and card.cost.paid:
            requirements.append("Requires paid call budget")
    if caps.can_read_secrets:
        can_do.append("Access secrets, tokens, or credentials")
        requirements.append("Requires secret scope or explicit approval")
    if caps.can_make_paid_calls:
        requirements.append("Requires paid call gate")

    hitl_req_str = (
        card.trust.hitl_requirement.value
        if hasattr(card.trust.hitl_requirement, "value")
        else str(card.trust.hitl_requirement)
    )
    if hitl_req_str != "none":
        requirements.append("Requires human-in-the-loop approval")

    if card.audit.audit_required:
        audit_level_str = (
            card.audit.audit_level.value if hasattr(card.audit.audit_level, "value") else "default"
        )
        requirements.append(f"Requires audit trail ({audit_level_str})")

    # Determine overall verdict
    risk_level_str = card.risk_level.value if hasattr(card.risk_level, "value") else "unknown"
    if card.opaque:
        verdict = "REQUIRES REVIEW - Card has unknown entity type"
    elif card.requires_review:
        verdict = f"REQUIRES REVIEW - High risk ({risk_level_str})"
    elif card.mcp and (card.mcp.blocked or card.mcp.drifted):
        status = "BLOCKED" if card.mcp.blocked else "DRIFTED"
        verdict = f"{status} - MCP tool is not approved or manifest has changed"
    else:
        verdict = "APPROVED - All requirements satisfied"

    payload = {
        "id": card.id,
        "name": card.name,
        "entity_type": card.entity_type.value
        if hasattr(card.entity_type, "value")
        else str(card.entity_type),
        "verdict": verdict,
        "can_do": can_do,
        "requirements": requirements,
        "risk_level": risk_level_str,
        "trust_level": card.trust.trust_level.value
        if hasattr(card.trust.trust_level, "value")
        else str(card.trust.trust_level),
        "mcp_server": card.mcp.server_id if card.mcp else None,
        "mcp_tool": card.mcp.tool_name if card.mcp else None,
        "manifest_hash": card.mcp.manifest_hash if card.mcp else None,
        "is_approved": card.mcp.approved if card.mcp else True,
        "is_blocked": card.mcp.blocked if card.mcp else False,
        "is_drifted": card.mcp.drifted if card.mcp else False,
        "cost_paid": card.cost.paid if card.cost else False,
        "card_hash": card.card_hash,
    }

    _out(ok(payload), json_output)


# ── signing commands ──────────────────────────────────────────────────────────


@capabilities_app.command("sign")
def capabilities_sign(
    card_path: str = typer.Argument(
        ..., exists=True, readable=True, help="Path to the card JSON file"
    ),
    output: Optional[str] = typer.Option(
        None, "--out", "-o", help="Output path for signed card (default: <input>.signed.json)"
    ),
    signer_id: str = typer.Option("arc-runtime", "--signer", "-s", help="Identity of the signer"),
    algorithm: str = typer.Option(
        "hmac", "--algorithm", "-a", help="Signing algorithm: 'hmac' or 'ecdsa'"
    ),
    secret_key: Optional[str] = typer.Option(
        None, "--secret", help="HMAC secret key (if algorithm=hmac)"
    ),
    private_key: Optional[str] = typer.Option(
        None, "--private-key", help="ECDSA private key file (if algorithm=ecdsa)"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Sign a Capability Card.

    Examples:
        arc capabilities sign card.json --secret "my-secret-key"
        arc capabilities sign card.json --algorithm ecdsa --private-key key.pem
    """
    _setup_logging(debug)

    import secrets

    # Determine signing parameters
    if algorithm == "hmac":
        if secret_key is None:
            # Generate a new secret key for the user
            secret_key = secrets.token_hex(32)
            typer.echo(
                "[yellow]No secret key provided. Generated new key (save this!):[/yellow]", err=True
            )
            typer.echo(f"[cyan]{secret_key}[/cyan]", err=True)
    elif algorithm == "ecdsa":
        if private_key is None:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "ECDSA requires --private-key pointing to a valid PEM file",
                ),
                json_output,
            )
            raise typer.Exit(1)
        priv_path = Path(private_key)
        if not priv_path.is_file():
            _out(
                err(ArcErrorCode.INVALID_INPUT, f"Private key file not found: {private_key}"),
                json_output,
            )
            raise typer.Exit(1)
    else:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Unknown algorithm '{algorithm}'. Use 'hmac' or 'ecdsa'",
            ),
            json_output,
        )
        raise typer.Exit(1)

    # Sign the card
    try:
        output_path = Path(output) if output else None
        private_key_pem = Path(private_key).read_text() if private_key else None

        signed_path = sign_card_file(
            Path(card_path),
            output_path,
            signer_id=signer_id,
            secret_key=secret_key,
            private_key_pem=private_key_pem,
        )

        payload = {
            "signed_card": str(signed_path),
            "algorithm": algorithm,
            "signer_id": signer_id,
        }
        _out(ok(payload), json_output)

    except Exception as exc:
        _out(err(ArcErrorCode.INTERNAL_ERROR, f"Error signing card: {exc}"), json_output)
        raise typer.Exit(1)


@capabilities_app.command("verify")
def capabilities_verify(
    signed_path: str = typer.Argument(
        ..., exists=True, readable=True, help="Path to the signed card JSON file"
    ),
    secret_key: Optional[str] = typer.Option(
        None, "--secret", help="HMAC secret key (if signed with HMAC)"
    ),
    public_key: Optional[str] = typer.Option(
        None, "--public-key", help="ECDSA public key file (if signed with ECDSA)"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Verify a signed Capability Card.

    Examples:
        arc capabilities verify signed-card.json --secret "my-secret-key"
        arc capabilities verify signed-card.json --public-key pubkey.pem
    """
    _setup_logging(debug)

    path = Path(signed_path)

    # Load the signed card to check algorithm
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Failed to read signed card: {exc}"), json_output)
        raise typer.Exit(1)

    algorithm = data.get("signature", {}).get("algorithm", "hmac_sha256")

    if algorithm == "ecdsa_p256" and public_key is None:
        # Try to use embedded public key
        if not data.get("signature", {}).get("public_key_pem"):
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "ECDSA signature without embedded public key requires --public-key",
                ),
                json_output,
            )
            raise typer.Exit(1)

    # Verify the signature
    try:
        public_key_pem = Path(public_key).read_text() if public_key else None

        is_valid = verify_card_file(
            Path(signed_path),
            secret_key=secret_key,
            public_key_pem=public_key_pem,
        )

        if is_valid:
            payload = {
                "valid": True,
                "card_id": data.get("card", {}).get("id", "unknown"),
                "algorithm": algorithm,
                "signer_id": data.get("signature", {}).get("signer_id", "unknown"),
                "signed_at": data.get("signature", {}).get("signed_at", "unknown"),
            }
            _out(ok(payload), json_output)
        else:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "Signature is INVALID - card may have been tampered with",
                ),
                json_output,
            )
            raise typer.Exit(1)

    except Exception as exc:
        _out(err(ArcErrorCode.INTERNAL_ERROR, f"Error verifying card: {exc}"), json_output)
        raise typer.Exit(1)


@capabilities_app.command("generate-key")
def capabilities_generate_key(
    algorithm: str = typer.Argument("hmac", help="Key type: 'hmac' or 'ecdsa'"),
    output: Optional[str] = typer.Option(
        None, "--out", "-o", help="Output file for the key (stdout if not specified)"
    ),
    include_public: bool = typer.Option(
        False, "--include-public", help="Include public key (for ECDSA)"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate a signing key.

    Examples:
        arc capabilities generate-key hmac
        arc capabilities generate-key ecdsa --out private_key.pem
    """
    _setup_logging(debug)

    if algorithm == "hmac":
        key = generate_secret_key()
        output_text = f"# HMAC-SHA256 Secret Key\n{key}\n"

    elif algorithm == "ecdsa":
        private_key, public_key = generate_ecdsa_keypair()

        if include_public:
            output_text = f"# ECDSA-P256 Key Pair\n\n{private_key}\n\n{public_key}\n"
        else:
            output_text = private_key
            typer.echo(
                "[yellow]Note: Store the private key securely. Public key will be embedded in signatures.[/yellow]",
                err=True,
            )

    else:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Unknown algorithm '{algorithm}'. Use 'hmac' or 'ecdsa'",
            ),
            json_output,
        )
        raise typer.Exit(1)

    if output:
        Path(output).write_text(output_text)
        payload = {"key_file": output, "algorithm": algorithm}
        _out(ok(payload), json_output)
    else:
        typer.echo(output_text)
