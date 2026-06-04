"""CLI commands for A2A AgentCard management."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from ._subapps import a2a_app


@a2a_app.command("generate")
def a2a_generate(
    name: str = typer.Option("arc-studio", help="Agent name"),
    description: str = typer.Option("ARC Studio local agent", help="Description"),
    version: str = typer.Option("1.0.0", help="Agent version"),
    url: str = typer.Option("", help="Agent URL (loopback only)"),
    secret_key: str = typer.Option("", "--secret-key", help="HMAC signing key"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Generate and write an A2A AgentCard to .arc/a2a/agent-card.json."""
    from ..a2a.generator import generate_agent_card, write_agent_card

    card = generate_agent_card(
        name=name,
        description=description,
        version=version,
        url=url,
        secret_key=secret_key or None,
    )
    path = write_agent_card(card)
    if json_output:
        typer.echo(json.dumps({"ok": True, "path": str(path)}, indent=2))
    else:
        typer.echo(f"AgentCard written to {path}")


@a2a_app.command("list")
def a2a_list(
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """List known A2A agent cards."""
    from ..a2a.client import _load_approved

    arc_dir = Path.home() / ".arc"
    card_path = arc_dir / "a2a" / "agent-card.json"
    cards: list[dict] = []
    if card_path.exists():
        cards.append(json.loads(card_path.read_text()))
    approved = _load_approved(arc_dir)
    if json_output:
        typer.echo(json.dumps({"ok": True, "cards": cards, "approved": approved}, indent=2))
    else:
        if cards:
            for c in cards:
                typer.echo(f"  {c.get('name', '?')} v{c.get('version', '?')}")
        else:
            typer.echo("No agent cards found.")
        if approved:
            typer.echo(f"Approved: {', '.join(approved.keys())}")


@a2a_app.command("verify")
def a2a_verify(
    secret_key: str = typer.Option(..., "--secret-key", help="HMAC key for verification"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Verify the local agent card signature."""
    from ..a2a.generator import load_agent_card, verify_agent_card

    card = load_agent_card()
    if not card:
        msg = "No agent card found at ~/.arc/a2a/agent-card.json"
        if json_output:
            typer.echo(json.dumps({"ok": False, "error": msg}))
        else:
            typer.echo(msg, err=True)
        raise typer.Exit(1)
    valid = verify_agent_card(card, secret_key)
    if json_output:
        typer.echo(json.dumps({"ok": valid, "name": card.name, "valid": valid}))
    else:
        typer.echo(
            f"{'✓' if valid else '✗'} Signature {'valid' if valid else 'INVALID'} for {card.name}"
        )
    if not valid:
        raise typer.Exit(1)


@a2a_app.command("inspect")
def a2a_inspect(
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Inspect the local agent card."""
    from ..a2a.generator import load_agent_card

    card = load_agent_card()
    if not card:
        msg = "No agent card found"
        if json_output:
            typer.echo(json.dumps({"ok": False, "error": msg}))
        else:
            typer.echo(msg, err=True)
        raise typer.Exit(1)
    data = card.model_dump(mode="json")
    if json_output:
        typer.echo(json.dumps({"ok": True, "card": data}, indent=2))
    else:
        typer.echo(json.dumps(data, indent=2))


@a2a_app.command("approve")
def a2a_approve(
    name: str = typer.Argument(..., help="Card name to approve"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Approve an agent card for outbound invocations."""
    from ..a2a.client import approve_card
    from ..a2a.generator import load_agent_card

    card = load_agent_card()
    if not card or card.name != name:
        # Approve by name with minimal stub
        from ..a2a.models import AgentCard as _AC

        card = _AC(name=name)
    approve_card(card)
    if json_output:
        typer.echo(json.dumps({"ok": True, "approved": name}))
    else:
        typer.echo(f"Approved: {name}")


@a2a_app.command("invoke")
def a2a_invoke(
    url: str = typer.Option(..., help="Target agent URL (must be 127.0.0.1)"),
    payload: str = typer.Option("{}", help="JSON payload"),
    secret_key: str = typer.Option("", "--secret-key", help="HMAC key for verification"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Invoke a remote A2A agent (loopback only)."""
    from ..a2a.client import A2AClientError, invoke_sync
    from ..a2a.generator import load_agent_card

    card = load_agent_card()
    if not card:
        msg = "No agent card loaded"
        if json_output:
            typer.echo(json.dumps({"ok": False, "error": msg}))
        else:
            typer.echo(msg, err=True)
        raise typer.Exit(1)
    # Override URL for this invocation
    card.url = url
    try:
        body = json.loads(payload)
    except json.JSONDecodeError as e:
        typer.echo(json.dumps({"ok": False, "error": f"Invalid JSON: {e}"}))
        raise typer.Exit(1)
    try:
        result = invoke_sync(card, payload=body)
        if json_output:
            typer.echo(json.dumps({"ok": True, "result": result}, indent=2))
        else:
            typer.echo(json.dumps(result, indent=2))
    except A2AClientError as e:
        if json_output:
            typer.echo(json.dumps({"ok": False, "error": str(e)}))
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
