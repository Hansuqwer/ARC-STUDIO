"""CLI commands for Runtime Pack SDK.

Commands:
  arc runtime-pack init      Scaffold a new runtime pack skeleton.
  arc runtime-pack validate  Statically validate a pack manifest.
  arc runtime-pack inspect   Produce a full inspection summary.
  arc runtime-pack list      List installed runtime packs.
  arc runtime-pack install   Install a pack's metadata (no code executed).
  arc runtime-pack uninstall Remove an installed pack.
  arc runtime-pack doctor    Validate + drift-check + integration report.

All commands accept ``--json`` to emit machine-readable envelope output.
No command imports, executes, or starts pack code; no network is opened.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import JSON_FLAG, WORKSPACE_FLAG, _out, _workspace

runtime_pack_app = typer.Typer(
    name="runtime-pack",
    help="Discover, validate, inspect, and install ARC runtime packs (metadata only, no code exec).",
    no_args_is_help=True,
)


@runtime_pack_app.command("init")
def runtime_pack_init(
    target: str = typer.Argument(default=".", help="Directory to scaffold the pack into."),
    pack_id: str = typer.Option(..., "--id", help="Stable pack id (e.g. 'org.my-runtime')."),
    name: str = typer.Option(..., "--name", help="Human-readable runtime name."),
    runtime_name: Optional[str] = typer.Option(None, "--runtime-name"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing manifest."),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Scaffold a minimal, valid, fail-closed runtime pack skeleton."""
    from ..runtime_packs.scaffold import ScaffoldError, init_pack

    try:
        created = init_pack(
            Path(target),
            pack_id=pack_id,
            name=name,
            runtime_name=runtime_name,
            force=force,
        )
        _out(
            ok(
                {
                    "pack_id": pack_id,
                    "target": str(Path(target).resolve()),
                    "created": [str(p) for p in created],
                    "message": (
                        f"Runtime pack '{pack_id}' scaffolded at {target}. "
                        "Run 'arc runtime-pack validate .' to verify."
                    ),
                }
            ),
            as_json,
        )
    except ScaffoldError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), as_json)
        raise typer.Exit(1)


@runtime_pack_app.command("validate")
def runtime_pack_validate(
    path: str = typer.Argument(default=".", help="Pack directory or manifest file."),
    allow_absolute: bool = typer.Option(
        False, "--allow-absolute", help="Relax R4 absolute-path check."
    ),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Statically validate a runtime pack manifest (all 12 rules)."""
    from ..runtime_packs.loader import ManifestLoadError, load_manifest
    from ..runtime_packs.validation import validate_manifest

    try:
        manifest = load_manifest(Path(path))
    except ManifestLoadError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot load manifest: {exc}"), as_json)
        raise typer.Exit(1)

    report = validate_manifest(manifest, allow_absolute_entrypoints=allow_absolute)
    payload = {
        "ok": report.ok,
        "manifest_id": report.manifest_id,
        "manifest_hash": report.manifest_hash,
        "computed_hash": report.computed_hash,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
        "findings": [
            {
                "rule": f.rule,
                "field": f.field,
                "severity": f.severity,
                "message": f.message,
                "remediation": f.remediation,
            }
            for f in report.findings
        ],
    }
    if report.ok:
        _out(ok(payload), as_json)
    else:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Pack '{report.manifest_id}' failed validation.",
                payload,
            ),
            as_json,
        )
        raise typer.Exit(1)


@runtime_pack_app.command("inspect")
def runtime_pack_inspect(
    path: str = typer.Argument(default=".", help="Pack directory or manifest file."),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Produce a structured inspection summary of a runtime pack."""
    from ..runtime_packs.loader import ManifestLoadError, inspect_manifest, load_manifest

    try:
        manifest = load_manifest(Path(path))
    except ManifestLoadError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot load manifest: {exc}"), as_json)
        raise typer.Exit(1)

    _out(ok(inspect_manifest(manifest)), as_json)


@runtime_pack_app.command("list")
def runtime_pack_list(
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """List all installed runtime packs in the workspace registry."""
    from ..runtime_packs.registry import create_registry

    ws = _workspace(workspace)
    reg = create_registry(workspace=ws)
    packs = reg.list_packs()
    _out(
        ok(
            {
                "count": len(packs),
                "packs": [
                    {
                        "id": e.id,
                        "name": e.name,
                        "version": e.version,
                        "manifest_hash": e.manifest_hash,
                        "installed_at": e.installed_at,
                    }
                    for e in packs
                ],
            }
        ),
        as_json,
    )


@runtime_pack_app.command("install")
def runtime_pack_install(
    path: str = typer.Argument(..., help="Pack directory or manifest file to install."),
    force: bool = typer.Option(False, "--force", help="Overwrite if already installed."),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Install a pack's metadata into the workspace registry (no code executed)."""
    from ..runtime_packs.registry import RuntimePackInstallError, create_registry

    ws = _workspace(workspace)
    reg = create_registry(workspace=ws)
    try:
        entry = reg.install(Path(path), force=force)
        _out(
            ok(
                {
                    "id": entry.id,
                    "name": entry.name,
                    "version": entry.version,
                    "manifest_hash": entry.manifest_hash,
                    "installed_at": entry.installed_at,
                    "message": f"Pack '{entry.id}' installed successfully.",
                }
            ),
            as_json,
        )
    except RuntimePackInstallError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), as_json)
        raise typer.Exit(1)


@runtime_pack_app.command("uninstall")
def runtime_pack_uninstall(
    pack_id: str = typer.Argument(..., help="Pack id to remove."),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Remove an installed runtime pack from the workspace registry."""
    from ..runtime_packs.registry import RuntimePackInstallError, create_registry

    ws = _workspace(workspace)
    reg = create_registry(workspace=ws)
    try:
        reg.uninstall(pack_id)
        _out(ok({"id": pack_id, "message": f"Pack '{pack_id}' uninstalled."}), as_json)
    except RuntimePackInstallError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), as_json)
        raise typer.Exit(1)


@runtime_pack_app.command("doctor")
def runtime_pack_doctor(
    path: str = typer.Argument(default=".", help="Pack directory or manifest file to diagnose."),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Validate, drift-check, and report integration availability for a pack.

    Combines 'validate', registry drift detection, and availability checks for
    the optional SwarmGraph IR, Capability Card, and MCP registry integrations.
    Does not execute any pack code.
    """
    from ..runtime_packs.exporters import ir_compatibility
    from ..runtime_packs.loader import ManifestLoadError, load_manifest
    from ..runtime_packs.registry import create_registry
    from ..runtime_packs.validation import validate_manifest

    try:
        manifest = load_manifest(Path(path))
    except ManifestLoadError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot load manifest: {exc}"), as_json)
        raise typer.Exit(1)

    report = validate_manifest(manifest)

    ws = _workspace(workspace)
    reg = create_registry(workspace=ws)
    drift_info = reg.check_drift(manifest.id)

    ir_compat = ir_compatibility(manifest)

    cap_card_available = False
    try:
        from ..capabilities.models import CapabilityCard  # type: ignore  # noqa: F401

        cap_card_available = True
    except Exception:
        pass

    mcp_reg_available = False
    try:
        from ..mcp.registry import McpRegistryStore  # type: ignore  # noqa: F401

        mcp_reg_available = True
    except Exception:
        pass

    overall_ok = report.ok and not drift_info.get("drifted", False)
    payload = {
        "overall_ok": overall_ok,
        "validation": {
            "ok": report.ok,
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "findings": [
                {"rule": f.rule, "severity": f.severity, "message": f.message}
                for f in report.findings
            ],
        },
        "registry": drift_info,
        "integrations": {
            "ir_export": ir_compat,
            "capability_card_available": cap_card_available,
            "mcp_registry_available": mcp_reg_available,
        },
    }
    if overall_ok:
        _out(ok(payload), as_json)
    else:
        reasons = []
        if not report.ok:
            reasons.append(f"{report.error_count} validation error(s)")
        if drift_info.get("drifted"):
            reasons.append("manifest drift detected")
        _out(
            err(ArcErrorCode.INVALID_INPUT, "Doctor found issues: " + "; ".join(reasons), payload),
            as_json,
        )
        raise typer.Exit(1)


__all__ = ["runtime_pack_app"]


@runtime_pack_app.command("pin")
def runtime_pack_pin(
    path: str = typer.Argument(default=".", help="Pack directory or arc-runtime-pack.json file."),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Recompute and write the manifest_hash field in-place."""
    from pathlib import Path as _Path
    from ..runtime_packs.loader import ManifestLoadError, load_manifest
    from ..runtime_packs.hashing import manifest_hash as compute_hash
    from ..runtime_packs.models import MANIFEST_FILENAME
    import json as _json

    p = _Path(path)
    manifest_file = p if p.is_file() else p / MANIFEST_FILENAME

    try:
        manifest = load_manifest(path)
    except ManifestLoadError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot load manifest: {exc}"), as_json)
        raise typer.Exit(1) from exc

    new_hash = compute_hash(manifest)
    manifest.manifest_hash = new_hash

    data = manifest.model_dump(mode="json")
    manifest_file.write_text(
        _json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    _out(ok({"id": manifest.id, "manifest_hash": new_hash, "path": str(manifest_file)}), as_json)
