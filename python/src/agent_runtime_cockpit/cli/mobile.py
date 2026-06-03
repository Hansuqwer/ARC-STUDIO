"""arc mobile — ARC Mobile Runtime SDK commands.

arc mobile doctor
arc mobile capabilities [--json]
arc mobile validate <path> [--json]
arc mobile simulate <plan-file> [--json]
arc mobile init-runtime-pack <path> [--json]
arc mobile export-runtime-pack <path> [--json]
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import DEBUG_FLAG, JSON_FLAG, _out, _setup_logging
from ._subapps import mobile_app


@mobile_app.command("doctor")
def mobile_doctor_cmd(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Mobile runtime health check — SDK status and capability catalog."""
    _setup_logging(debug)
    from ..mobile import list_capabilities, MOBILE_SCHEMA_VERSION

    caps = list_capabilities()
    mock_count = sum(1 for c in caps if c.id.endswith(".mock"))
    _out(
        ok(
            {
                "schema_version": MOBILE_SCHEMA_VERSION,
                "capability_count": len(caps),
                "mock_only_count": mock_count,
                "simulator_mode": True,
                "background_execution": False,
                "network_by_default": False,
                "status": "ok",
                "note": "MVP: all capabilities are mock/simulator-only. No real native bridges.",
            }
        ),
        json_output,
    )


@mobile_app.command("capabilities")
def mobile_capabilities_cmd(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List all available mobile capabilities."""
    _setup_logging(debug)
    from ..mobile import list_capabilities

    caps = list_capabilities()
    _out(
        ok(
            {
                "count": len(caps),
                "capabilities": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "category": c.category.value,
                        "platforms": [p.value for p in c.platforms],
                        "approval_mode": c.approval_mode.value,
                        "data_sensitivity": c.data_sensitivity.value,
                        "simulator_supported": c.simulator_supported,
                        "capability_hash": c.capability_hash,
                    }
                    for c in caps
                ],
            }
        ),
        json_output,
    )


@mobile_app.command("validate")
def mobile_validate_cmd(
    path: str = typer.Argument(..., help="Path to arc-mobile-capabilities.json or directory."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Validate a mobile runtime manifest."""
    _setup_logging(debug)
    from ..mobile import MobileManifestLoadError, validate_manifest
    from ..mobile.manifest import load_manifest

    try:
        manifest = load_manifest(path)
    except MobileManifestLoadError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot load manifest: {exc}"), json_output)
        raise typer.Exit(1) from exc

    report = validate_manifest(manifest)
    payload = {
        "ok": report.ok,
        "manifest_id": report.manifest_id,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
        "findings": [f.model_dump() for f in report.findings],
    }
    if not report.ok:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT, f"Manifest '{manifest.id}' failed validation.", payload
            ),
            json_output,
        )
        raise typer.Exit(1)
    _out(ok(payload), json_output)


@mobile_app.command("simulate")
def mobile_simulate_cmd(
    plan_file: str = typer.Argument(..., help="Path to action plan JSON file."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Simulate a mobile action plan (no execution)."""
    _setup_logging(debug)
    from ..mobile import MobileActionPlan, simulate_action_plan

    p = Path(plan_file)
    if not p.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Plan file not found: {plan_file}"), json_output)
        raise typer.Exit(1)

    try:
        plan = MobileActionPlan.model_validate(json.loads(p.read_text()))
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid plan file: {exc}"), json_output)
        raise typer.Exit(1) from exc

    report = simulate_action_plan(plan)
    payload = report.model_dump(mode="json")
    _out(ok(payload), json_output)
    if not report.overall_allowed:
        raise typer.Exit(1)


@mobile_app.command("init-runtime-pack")
def mobile_init_runtime_pack_cmd(
    target: str = typer.Argument(..., help="Target directory for the runtime pack."),
    manifest_id: str = typer.Option("arc.mobile.runtime", "--id", help="Mobile manifest ID."),
    name: str = typer.Option("ARC Mobile Runtime", "--name", help="Runtime name."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Initialize a mobile runtime pack at the target directory."""
    _setup_logging(debug)
    from ..mobile import build_default_manifest
    from ..mobile.runtime_pack import build_runtime_pack_manifest

    target_path = Path(target)
    manifest = build_default_manifest(manifest_id, name)
    pack_data = build_runtime_pack_manifest(manifest, target_path)

    # Also write the mobile manifest
    from ..mobile.manifest import MANIFEST_FILENAME

    mobile_manifest_data = manifest.model_dump(mode="json")
    (target_path / MANIFEST_FILENAME).write_text(
        json.dumps(mobile_manifest_data, indent=2) + "\n", encoding="utf-8"
    )

    _out(
        ok(
            {
                "pack_id": pack_data["id"],
                "manifest_id": manifest.id,
                "target": str(target_path),
                "manifest_hash": manifest.manifest_hash,
                "capabilities_count": len(manifest.capabilities),
                "message": f"Mobile runtime pack '{pack_data['id']}' initialized at {target_path}.",
            }
        ),
        json_output,
    )


@mobile_app.command("export-runtime-pack")
def mobile_export_runtime_pack_cmd(
    path: str = typer.Argument(..., help="Path to runtime pack directory."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Inspect and export a mobile runtime pack."""
    _setup_logging(debug)
    from ..runtime_packs.loader import ManifestLoadError, load_manifest, inspect_manifest

    try:
        pack = load_manifest(path)
        summary = inspect_manifest(pack)
    except ManifestLoadError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot load pack: {exc}"), json_output)
        raise typer.Exit(1) from exc

    _out(ok(summary), json_output)


@mobile_app.command("pin")
def mobile_pin_cmd(
    path: str = typer.Argument(..., help="Path to arc-mobile-capabilities.json or directory."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Recompute and write the manifest_hash field in-place."""
    import json as _json
    from ..mobile import MobileManifestLoadError
    from ..mobile.hashing import manifest_hash as compute_hash
    from ..mobile.manifest import MANIFEST_FILENAME, load_manifest

    p = Path(path)
    manifest_file = p if p.is_file() else p / MANIFEST_FILENAME

    try:
        manifest = load_manifest(path)
    except MobileManifestLoadError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot load manifest: {exc}"), json_output)
        raise typer.Exit(1) from exc

    new_hash = compute_hash(manifest)
    manifest.manifest_hash = new_hash

    data = manifest.model_dump(mode="json")
    manifest_file.write_text(
        _json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    _out(
        ok({"id": manifest.id, "manifest_hash": new_hash, "path": str(manifest_file)}), json_output
    )
