"""Receipt commands: show, export, verify (Phase 25.4)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok

from ._helpers import (
    DEBUG_FLAG,
    JSON_FLAG,
    WORKSPACE_FLAG,
    _out,
    _setup_logging,
    _workspace,
)
from ._subapps import receipt_app

DEFAULT_RECEIPT_KEY = "arc-dev-key-change-in-production"


def _receipt_key() -> str:
    """Get receipt HMAC key with fallback chain: ARC_RECEIPT_HMAC_KEY → ARC_AUDIT_HMAC_KEY → default."""
    return (
        os.environ.get("ARC_RECEIPT_HMAC_KEY")
        or os.environ.get("ARC_AUDIT_HMAC_KEY")
        or DEFAULT_RECEIPT_KEY
    )


@receipt_app.command("show")
def receipt_show(
    run_id: str = typer.Argument(..., help="Run ID to show receipt for"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show a human-readable run receipt for a completed/failed run."""
    _setup_logging(debug)
    from ..storage.jsonl import JsonlTraceStore

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    receipt = store.load_receipt(run_id)
    if receipt is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Receipt not found for run: {run_id}"), json_output)
        raise typer.Exit(1)
    _out(ok(receipt.model_dump(by_alias=True), workspace=str(ws)), json_output)
    if not json_output:
        from ._app import console

        console.print(f"[bold]Run Receipt:[/bold] {receipt.receipt_id}")
        console.print(f"  Run ID: {receipt.run_id}  Status: {receipt.status}")
        console.print(f"  Summary: {receipt.summary}  Cost: {receipt.cost_usd}")
        sig = receipt.signature or "unsigned"
        console.print(f"  Signature: {sig[:20]}...")


@receipt_app.command("export")
def receipt_export(
    run_id: str = typer.Argument(..., help="Run ID to export receipt for"),
    format: str = typer.Option("json", "--format", help="Output format: json, markdown"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Export a run receipt to a file (JSON or Markdown)."""
    _setup_logging(debug)
    from ..storage.jsonl import JsonlTraceStore

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    receipt = store.load_receipt(run_id)
    if receipt is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Receipt not found for run: {run_id}"), json_output)
        raise typer.Exit(1)
    ext = ".md" if format == "markdown" else ".json"
    out_path = Path(output) if output else ws / ".arc" / "receipts" / f"{run_id}.receipt{ext}"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if format == "markdown":
        md_lines = [
            f"# Run Receipt: {receipt.receipt_id}",
            "",
            f"- **Run ID:** {receipt.run_id}",
            f"- **Status:** {receipt.status}",
        ]
        out_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    else:
        out_path.write_text(receipt.model_dump_json(indent=2, by_alias=True), encoding="utf-8")
    payload = {"exported": True, "path": str(out_path), "run_id": run_id, "format": format}
    _out(ok(payload, workspace=str(ws)), json_output)
    if not json_output:
        from ._app import console

        console.print(f"[green]Exported[/green] receipt to {out_path}")


@receipt_app.command("verify")
def receipt_verify(
    file: str = typer.Argument(..., help="Path to receipt JSON file"),
    key: Optional[str] = typer.Option(None, "--key", help="HMAC key"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Verify a receipt file's HMAC signature and integrity."""
    _setup_logging(debug)
    import json as json_mod

    from ..protocol.run_receipt import RunReceipt

    path = Path(file).expanduser().resolve()
    if not path.exists():
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Receipt file not found: {path}"), json_output)
        raise typer.Exit(1)

    def _try_legacy(r: RunReceipt, k: str) -> bool:
        try:
            return r.verify(k)
        except Exception:
            return False

    try:
        data = json_mod.loads(path.read_text(encoding="utf-8"))
        receipt = RunReceipt.model_validate(data)
    except Exception as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid receipt file: {exc}"), json_output)
        raise typer.Exit(1)
    hmac_key = key or _receipt_key()
    valid = receipt.verify(hmac_key)
    if not valid and key is None and hmac_key != DEFAULT_RECEIPT_KEY:
        valid = _try_legacy(receipt, DEFAULT_RECEIPT_KEY)
    payload = {
        "file": str(path),
        "receipt_id": receipt.receipt_id,
        "run_id": receipt.run_id,
        "valid": valid,
        "has_signature": receipt.signature is not None,
    }
    _out(ok(payload), json_output)
    if not json_output:
        from ._app import console

        color = "green" if valid else "red"
        console.print(
            f"Receipt signature: [bold {color}]{'VALID' if valid else 'INVALID'}[/bold {color}]"
        )
    if not valid:
        raise typer.Exit(1)
