"""Audit commands: verify, export, key init/show/delete (Phase 25.4)."""

from __future__ import annotations

from pathlib import Path

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok

from ._helpers import (
    DEBUG_FLAG,
    JSON_FLAG,
    _out,
    _setup_logging,
)
from ._subapps import audit_app, key_app


@audit_app.command("verify")
def audit_verify(
    run_id: str = typer.Argument(..., help="Run ID to verify audit chain for"),
    chain_path: str = typer.Option("", "--chain", "-c", help="Path to audit chain file"),
    mode: str = typer.Option(
        "auto", "--mode", "-m", help="Verification mode: sha256, hmac, or auto"
    ),
    max_memory_mb: int = typer.Option(500, "--max-memory-mb", help="Maximum memory budget in MB"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Verify audit chain integrity with streaming verification (Phase 21)."""
    _setup_logging(debug)
    from ..audit.key_manager import AuditKeyManager
    from ..audit.streaming_verifier import StreamingAuditVerifier

    if mode not in ("auto", "sha256", "hmac"):
        _out(
            err(
                ArcErrorCode.INVALID_INPUT, f"Invalid mode: {mode}. Must be auto, sha256, or hmac."
            ),
            json_output,
        )
        raise typer.Exit(1)
    try:
        verifier = StreamingAuditVerifier(max_memory_mb=max_memory_mb)
    except ValueError as e:
        _out(err(ArcErrorCode.INVALID_INPUT, str(e)), json_output)
        raise typer.Exit(1)
    key = None
    key_status = None
    if mode in ("hmac", "auto"):
        mgr = AuditKeyManager()
        key, key_status = mgr.get_key()
        if mode == "hmac" and not key_status.available:
            _out(err(ArcErrorCode.INVALID_INPUT, key_status.warning), json_output)
            raise typer.Exit(1)
    ws = Path.cwd()
    audit_dir = ws / ".arc" / "audit"
    if chain_path:
        chain = Path(chain_path)
    else:
        new_chain = audit_dir / f"{run_id}.audit.jsonl"
        old_chain = audit_dir / f"{run_id}.jsonl"
        if new_chain.exists():
            chain = new_chain
        elif old_chain.exists():
            chain = old_chain
        else:
            _out(
                err(ArcErrorCode.RUN_NOT_FOUND, f"Audit chain not found for run {run_id}"),
                json_output,
            )
            raise typer.Exit(1)
    if mode == "auto":
        result = verifier.verify_auto(chain, key)
    elif mode == "hmac":
        result = verifier.verify_hmac(chain, key)
    else:
        result = verifier.verify_sha256(chain)
    payload = {
        "ok": result.ok,
        "mode": result.mode,
        "records_checked": result.records_checked,
        "reason": result.reason,
        "duration_ms": result.duration_ms,
        "run_id": run_id,
        "chain_path": str(chain),
    }
    if result.file_size_bytes is not None:
        payload["file_size_bytes"] = result.file_size_bytes
    if key_status is not None:
        payload["key_source"] = key_status.source
        payload["key_degraded"] = key_status.degraded
    _out(ok(payload), json_output)
    if not json_output:
        from ._app import console

        color = "green" if result.ok else "red"
        mode_label = {"hmac": "HMAC-SHA256", "sha256": "SHA-256"}.get(result.mode, result.mode)
        console.print(
            f"Audit chain ({mode_label}): [bold {color}]{'VERIFIED' if result.ok else 'FAILED'}[/bold {color}]"
        )
    if not result.ok:
        raise typer.Exit(1)


@audit_app.command("export")
def audit_export(
    run_id: str = typer.Argument(..., help="Run ID to export audit records for"),
    chain_path: str = typer.Option("", "--chain", "-c", help="Path to audit chain file"),
    format: str = typer.Option("jsonl", "--format", help="Output format: jsonl, json"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Export audit chain records for a run."""
    _setup_logging(debug)
    import json as json_mod

    ws = Path.cwd()
    audit_dir = ws / ".arc" / "audit"
    if chain_path:
        chain = Path(chain_path)
    else:
        new_chain = audit_dir / f"{run_id}.audit.jsonl"
        old_chain = audit_dir / f"{run_id}.jsonl"
        if new_chain.exists():
            chain = new_chain
        elif old_chain.exists():
            chain = old_chain
        else:
            _out(
                err(ArcErrorCode.RUN_NOT_FOUND, f"Audit chain not found for run {run_id}"),
                json_output,
            )
            raise typer.Exit(1)
    lines = chain.read_text(encoding="utf-8").splitlines()
    records = [json_mod.loads(l) for l in lines if l.strip()]
    if format == "json":
        payload = {"run_id": run_id, "record_count": len(records), "records": records}
    else:
        payload = {"run_id": run_id, "record_count": len(records), "chain_path": str(chain)}
    _out(ok(payload), json_output)
    if not json_output:
        from ._app import console

        console.print(f"Audit records for {run_id}: {len(records)} records at {chain}")
        if format == "jsonl":
            for r in records:
                console.print(json_mod.dumps(r, sort_keys=True))


@audit_app.command("query")
def audit_query(
    run_id: str = typer.Argument(..., help="Run ID to query audit events for"),
    kind: str = typer.Option(
        None, "--kind", help="Filter by event type (e.g., POLICY_BYPASS_WARNING)"
    ),
    surface: str = typer.Option(None, "--surface", help="Filter by surface (composes with --kind)"),
    chain_path: str = typer.Option("", "--chain", "-c", help="Path to audit chain file"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Query audit events with filters (Phase 22.1).

    Filter audit events by type (--kind) and optionally by surface.
    Filters compose: --kind POLICY_BYPASS_WARNING --surface provider_call
    returns only bypass warnings from provider calls.
    """
    _setup_logging(debug)
    import json as json_mod

    ws = Path.cwd()
    audit_dir = ws / ".arc" / "audit"
    if chain_path:
        chain = Path(chain_path)
    else:
        new_chain = audit_dir / f"{run_id}.audit.jsonl"
        old_chain = audit_dir / f"{run_id}.jsonl"
        if new_chain.exists():
            chain = new_chain
        elif old_chain.exists():
            chain = old_chain
        else:
            _out(
                err(ArcErrorCode.RUN_NOT_FOUND, f"Audit chain not found for run {run_id}"),
                json_output,
            )
            raise typer.Exit(1)

    # Read and parse audit records
    lines = chain.read_text(encoding="utf-8").splitlines()
    records = [json_mod.loads(l) for l in lines if l.strip()]

    # Filter by kind (event type)
    if kind:
        records = [r for r in records if r.get("event", {}).get("type") == kind]

    # Filter by surface (composes with kind filter)
    if surface:
        records = [
            r for r in records if r.get("event", {}).get("data", {}).get("surface") == surface
        ]

    payload = {
        "run_id": run_id,
        "filters": {"kind": kind, "surface": surface},
        "matched_count": len(records),
        "events": [r.get("event") for r in records],
    }
    _out(ok(payload), json_output)

    if not json_output:
        from ._app import console

        filter_desc = []
        if kind:
            filter_desc.append(f"kind={kind}")
        if surface:
            filter_desc.append(f"surface={surface}")
        filter_str = ", ".join(filter_desc) if filter_desc else "no filters"

        console.print(f"Query results for {run_id} ({filter_str}): {len(records)} events")
        for r in records:
            event = r.get("event", {})
            console.print(json_mod.dumps(event, sort_keys=True, indent=2))


@key_app.command("init")
def audit_key_init(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate and store a new HMAC audit key in keychain."""
    _setup_logging(debug)
    from ..audit.key_manager import AuditKeyManager

    mgr = AuditKeyManager()
    new_key = mgr.generate_key()
    stored = mgr.set_key(new_key)
    payload = {
        "generated": True,
        "stored_to_keychain": stored,
        "key_hint": new_key[:8] + "..." if stored else new_key,
    }
    _out(ok(payload), json_output)
    if not json_output:
        from ._app import console

        if stored:
            console.print("[green]Audit key generated and stored in keychain.[/green]")
        else:
            console.print("[yellow]Key generated but could not store in keychain.[/yellow]")


@key_app.command("show")
def audit_key_show(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show audit key status (key is never printed)."""
    _setup_logging(debug)
    from ..audit.key_manager import AuditKeyManager

    mgr = AuditKeyManager()
    _, status = mgr.get_key()
    _out(ok(status.model_dump()), json_output)
    if not json_output:
        from ._app import console

        if status.available:
            console.print(f"Audit key: [green]available[/green] (source: {status.source})")
        else:
            console.print("Audit key: [red]not available[/red]")


@key_app.command("delete")
def audit_key_delete(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Delete the stored HMAC audit key from keychain."""
    _setup_logging(debug)
    from ..audit.key_manager import AuditKeyManager

    mgr = AuditKeyManager()
    deleted = mgr.delete_key()
    payload = {"deleted_from_keychain": deleted}
    _out(ok(payload), json_output)
    if not json_output:
        from ._app import console

        console.print(
            "[green]Audit key deleted from keychain.[/green]"
            if deleted
            else "[yellow]No key found.[/yellow]"
        )
