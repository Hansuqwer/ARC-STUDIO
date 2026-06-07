"""arc mobile — ARC Mobile Runtime SDK commands.

arc mobile doctor
arc mobile capabilities [--json]
arc mobile validate <path> [--json]
arc mobile simulate <plan-file> [--json]
arc mobile trace <trace-file> [--json]
arc mobile policy explain [--capability <id> | --plan <path>] [--json]
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

mobile_policy_app = typer.Typer(name="policy", help="Mobile runtime policy commands")
mobile_app.add_typer(mobile_policy_app)


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
    manifest: str | None = typer.Option(
        None, "--manifest", help="Optional manifest file/directory."
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List all available mobile capabilities."""
    _setup_logging(debug)
    from ..mobile import MobileManifestLoadError, list_capabilities
    from ..mobile.manifest import load_manifest

    try:
        caps = load_manifest(manifest).capabilities if manifest else list_capabilities()
    except MobileManifestLoadError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot load manifest: {exc}"), json_output)
        raise typer.Exit(1) from exc
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
    plan_file: str | None = typer.Argument(None, help="Path to action plan JSON file."),
    plan_option: str | None = typer.Option(None, "--plan", help="Path to action plan JSON file."),
    manifest: str | None = typer.Option(
        None, "--manifest", help="Optional manifest file/directory."
    ),
    trace: str | None = typer.Option(None, "--trace", help="Optional JSONL trace output path."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Simulate a mobile action plan (no execution)."""
    _setup_logging(debug)
    from ..mobile import (
        MobileActionPlan,
        MobileManifestLoadError,
        append_trace,
        build_trace,
        simulate_action_plan,
    )
    from ..mobile.manifest import load_manifest

    selected_plan = plan_option or plan_file
    if not selected_plan:
        _out(err(ArcErrorCode.INVALID_INPUT, "Plan file is required."), json_output)
        raise typer.Exit(1)
    p = Path(selected_plan)
    if not p.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Plan file not found: {selected_plan}"), json_output)
        raise typer.Exit(1)

    try:
        plan = MobileActionPlan.model_validate(json.loads(p.read_text()))
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid plan file: {exc}"), json_output)
        raise typer.Exit(1) from exc

    extra_capabilities = None
    if manifest:
        try:
            extra_capabilities = load_manifest(manifest).capabilities
        except MobileManifestLoadError as exc:
            _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot load manifest: {exc}"), json_output)
            raise typer.Exit(1) from exc
    report = simulate_action_plan(plan, extra_capabilities=extra_capabilities)
    payload = report.model_dump(mode="json")
    if trace:
        mobile_trace = build_trace(report)
        append_trace(trace, mobile_trace)
        payload["trace"] = {"path": trace, "trace_hash": mobile_trace.trace_hash}
    _out(ok(payload), json_output)
    if not report.overall_allowed:
        raise typer.Exit(1)


@mobile_app.command("trace")
def mobile_trace_cmd(
    trace_file: str = typer.Argument(..., help="Path to mobile simulator JSONL trace."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Inspect a mobile simulator trace JSONL file."""
    _setup_logging(debug)
    from ..mobile import read_trace

    p = Path(trace_file)
    if not p.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Trace file not found: {trace_file}"), json_output)
        raise typer.Exit(1)
    try:
        trace = read_trace(p)
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid trace file: {exc}"), json_output)
        raise typer.Exit(1) from exc
    _out(
        ok(
            {
                "plan_id": trace.plan_id,
                "event_count": len(trace.events),
                "trace_hash": trace.trace_hash,
                "events": [event.model_dump(mode="json") for event in trace.events],
            }
        ),
        json_output,
    )


@mobile_policy_app.command("explain")
def mobile_policy_explain_cmd(
    capability: str | None = typer.Option(None, "--capability", help="Capability ID to explain."),
    plan: str | None = typer.Option(None, "--plan", help="Action plan JSON to explain."),
    manifest: str | None = typer.Option(
        None, "--manifest", help="Optional manifest file/directory."
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Explain mobile policy for a capability or action plan."""
    _setup_logging(debug)
    from ..mobile import (
        MobileActionPlan,
        MobileManifestLoadError,
        explain_capability_policy,
        explain_plan_policy,
        get_capability,
        list_capabilities,
    )
    from ..mobile.manifest import load_manifest

    if bool(capability) == bool(plan):
        _out(
            err(ArcErrorCode.INVALID_INPUT, "Pass exactly one of --capability or --plan."),
            json_output,
        )
        raise typer.Exit(1)
    try:
        capabilities = load_manifest(manifest).capabilities if manifest else list_capabilities()
    except MobileManifestLoadError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot load manifest: {exc}"), json_output)
        raise typer.Exit(1) from exc
    if capability:
        cap = next(
            (item for item in capabilities if item.id == capability), None
        ) or get_capability(capability)
        if cap is None:
            _out(
                ok(
                    {
                        "allowed": False,
                        "approval_required": False,
                        "capability_id": capability,
                        "reason": "unknown capability",
                        "denied_rules": ["unknown_capability"],
                        "required_approvals": [],
                        "mcp_exposable": False,
                    }
                ),
                json_output,
            )
            raise typer.Exit(1)
        decision = explain_capability_policy(cap)
    else:
        assert plan is not None
        p = Path(plan)
        if not p.is_file():
            _out(err(ArcErrorCode.INVALID_INPUT, f"Plan file not found: {plan}"), json_output)
            raise typer.Exit(1)
        try:
            action_plan = MobileActionPlan.model_validate(json.loads(p.read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001
            _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid plan file: {exc}"), json_output)
            raise typer.Exit(1) from exc
        decision = explain_plan_policy(action_plan, capabilities)
    _out(ok(decision.model_dump(mode="json")), json_output)
    if not decision.allowed:
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


mobile_trace_app = typer.Typer(name="trace", help="Mobile trace sub-commands")
mobile_app.add_typer(mobile_trace_app)


@mobile_trace_app.command("verify")
def mobile_trace_verify_cmd(
    trace_file: str = typer.Argument(..., help="Path to mobile simulator JSONL trace."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Verify the prev_event_hash chain of a trace. Exits 1 if tampered."""
    _setup_logging(debug)
    from ..mobile import read_trace, verify_trace

    p = Path(trace_file)
    if not p.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Trace file not found: {trace_file}"), json_output)
        raise typer.Exit(1)
    try:
        trace = read_trace(p)
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid trace file: {exc}"), json_output)
        raise typer.Exit(1) from exc

    chain_ok, message = verify_trace(trace)
    payload = {
        "ok": chain_ok,
        "plan_id": trace.plan_id,
        "event_count": len(trace.events),
        "trace_hash": trace.trace_hash,
        "message": message,
    }
    if chain_ok:
        _out(ok(payload), json_output)
    else:
        _out(
            err(ArcErrorCode.INVALID_INPUT, f"Trace verification failed: {message}", payload),
            json_output,
        )
        raise typer.Exit(1)
mobile_schema_app = typer.Typer(name="schema", help="Mobile schema commands")
mobile_app.add_typer(mobile_schema_app)


@mobile_schema_app.command("check")
def mobile_schema_check_cmd(
    file: str = typer.Argument(..., help="Path to JSON file to validate."),
    kind: str = typer.Option(
        ...,
        "--kind",
        help="Schema kind: manifest|action_plan|simulation_report|event|trace|policy_decision",
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Validate a JSON file against a mobile protocol schema."""
    _setup_logging(debug)
    from ..mobile.schema_validator import validate_against_schema
    import json as _json

    p = Path(file)
    if not p.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"File not found: {file}"), json_output)
        raise typer.Exit(1)
    try:
        data = _json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot parse JSON: {exc}"), json_output)
        raise typer.Exit(1) from exc

    try:
        errors = validate_against_schema(data, kind)
    except ValueError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(1) from exc

    if errors:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Schema validation failed ({len(errors)} error(s))",
                {"errors": errors},
            ),
            json_output,
        )
        raise typer.Exit(1)
    _out(ok({"ok": True, "kind": kind, "file": file}), json_output)


@mobile_schema_app.command("export")
def mobile_schema_export_cmd(
    out: str = typer.Option(".", "--out", help="Output directory for schema files."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Copy all mobile protocol schemas to the output directory."""
    _setup_logging(debug)
    from ..mobile.schema_validator import _find_spec_dir, list_schema_kinds
    import shutil

    spec_dir = _find_spec_dir()
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    copied = []
    for kind in list_schema_kinds():
        from ..mobile.schema_validator import _SCHEMA_FILES

        src = spec_dir / _SCHEMA_FILES[kind]
        if src.exists():
            shutil.copy2(src, out_path / src.name)
            copied.append(src.name)
    _out(ok({"copied": copied, "out": str(out_path)}), json_output)
