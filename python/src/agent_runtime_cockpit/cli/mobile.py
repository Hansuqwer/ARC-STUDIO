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
    # Explicit UX states (DoD gate 1): "ok" | "empty" (no capabilities registered)
    ux_state = "ok" if caps else "empty"
    _out(
        ok(
            {
                "schema_version": MOBILE_SCHEMA_VERSION,
                "capability_count": len(caps),
                "mock_only_count": mock_count,
                "simulator_mode": True,
                "background_execution": False,
                "network_by_default": False,
                "status": ux_state,
                "state": ux_state,
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
    # Explicit UX state (DoD gate 1): "ok" | "degraded" | "error"
    ux_state = (
        "ok"
        if report.ok
        else ("degraded" if report.warning_count > 0 and report.error_count == 0 else "error")
    )
    payload = {
        "ok": report.ok,
        "state": ux_state,
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
    max_steps: int = typer.Option(
        500, "--max-steps", help="Maximum steps to simulate (DoD gate 7 reliability cap)."
    ),
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

    # Gate 7 (reliability): enforce step count limit before simulation to prevent
    # unbounded CPU/memory use on malformed or adversarially large plans.
    if len(plan.steps) > max_steps:
        _out(
            err(
                ArcErrorCode.PERMISSION_DENIED,
                f"Plan has {len(plan.steps)} steps; limit is {max_steps} (use --max-steps to override).",
                {"step_count": len(plan.steps), "max_steps": max_steps},
            ),
            json_output,
        )
        raise typer.Exit(1)

    extra_capabilities = None
    if manifest:
        try:
            extra_capabilities = load_manifest(manifest).capabilities
        except MobileManifestLoadError as exc:
            _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot load manifest: {exc}"), json_output)
            raise typer.Exit(1) from exc
    report = simulate_action_plan(plan, extra_capabilities=extra_capabilities)
    payload = report.model_dump(mode="json")

    # D1: route the simulate path through the capability entry-gate. The gate decision is
    # recorded per step; with default-off flags every capability routes to fixtures, which
    # matches the simulator's behaviour (no real device access).
    import secrets as _secrets

    from ..mobile import CapabilityEntryGate, FeatureFlags

    _gate = CapabilityEntryGate(FeatureFlags(), _secrets.token_bytes(32))
    gate_routes = [
        {"capability_id": s.capability_id, "eligible": _d.eligible, "route": _d.route}
        for s in report.steps
        for _d in (_gate.evaluate(s.capability_id),)
    ]
    payload["gate"] = {
        "route": "fixtures",  # this build never routes a native capability to a real device
        "all_fixtures": all(r["route"] == "fixtures" for r in gate_routes),
        "evaluated": gate_routes,
    }

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
    org_bundle: str | None = typer.Option(
        None, "--org-bundle", help="Signed OrgPolicyBundle JSON (RBAC/ABAC overlay)."
    ),
    tenant: str | None = typer.Option(None, "--tenant", help="Tenant id for the org bundle."),
    role: str | None = typer.Option(None, "--role", help="Caller role for RBAC."),
    bundle_key_file: str | None = typer.Option(
        None, "--bundle-key-file", help="Key file to verify the org bundle signature."
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Explain mobile policy for a capability or action plan.

    Pass --org-bundle (+ --tenant/--role/--bundle-key-file) to apply a signed tenant RBAC/ABAC
    overlay; an unsigned/forged bundle, tenant mismatch, or disallowed role fails closed.
    """
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

    # D2: optional signed org/tenant RBAC/ABAC overlay.
    enterprise_hook = None
    if org_bundle:
        from ..mobile import OrgPolicyBundle, OrgPolicyContext, TenantPolicyHook

        try:
            bundle = OrgPolicyBundle.model_validate_json(Path(org_bundle).read_text())
        except Exception as exc:  # noqa: BLE001
            _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid org bundle: {exc}"), json_output)
            raise typer.Exit(1) from exc
        key = Path(bundle_key_file).read_bytes() if bundle_key_file else b""
        enterprise_hook = TenantPolicyHook(
            bundle, key, OrgPolicyContext(tenant or bundle.tenant_id, role or "", {})
        )

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
        decision = explain_capability_policy(cap, enterprise_hook=enterprise_hook)
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


@mobile_app.command("trace-verify")
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
    # Explicit UX state (DoD gate 1 parity with other mobile commands): "ok" | "tampered"
    payload = {
        "ok": chain_ok,
        "state": "ok" if chain_ok else "tampered",
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


mobile_approval_app = typer.Typer(name="approval", help="Mobile approval grant commands")
mobile_app.add_typer(mobile_approval_app)


@mobile_approval_app.command("issue")
def mobile_approval_issue_cmd(
    capability: str = typer.Option(..., "--cap", help="Capability ID to approve."),
    scope: str = typer.Option("execute:once", "--scope", help="Approval scope string."),
    ttl: int = typer.Option(300, "--ttl", help="TTL in seconds."),
    subject: str | None = typer.Option(None, "--subject"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Issue a scoped approval grant for a capability."""
    _setup_logging(debug)
    from ..mobile.approval import issue_grant

    grant = issue_grant(capability, scope, ttl, subject=subject)
    _out(ok(grant.model_dump(mode="json")), json_output)


@mobile_approval_app.command("revoke")
def mobile_approval_revoke_cmd(
    grant_id: str = typer.Argument(..., help="Grant ID to revoke."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Revoke an approval grant. Exits 1 if grant not found."""
    _setup_logging(debug)
    from ..mobile.approval import revoke_grant

    revoked = revoke_grant(grant_id)
    if revoked:
        _out(ok({"revoked": True, "grant_id": grant_id}), json_output)
    else:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT, f"Grant '{grant_id}' not found", {"grant_id": grant_id}
            ),
            json_output,
        )
        raise typer.Exit(1)


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


@mobile_app.command("sbom")
def mobile_sbom_cmd(
    out: str | None = typer.Option(None, "--out", help="Write the SBOM JSON to this path."),
    component_version: str = typer.Option(
        "0.1.0", "--component-version", help="SBOM component version."
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate a CycloneDX-style SBOM for the mobile SDK (modules + framework bindings)."""
    _setup_logging(debug)
    import json as _json

    from ..mobile import generate_sbom

    sbom = generate_sbom(component_version)
    if out:
        Path(out).write_text(_json.dumps(sbom, indent=2, sort_keys=True), encoding="utf-8")
    _out(ok(sbom), json_output)


@mobile_app.command("siem-export")
def mobile_siem_export_cmd(
    trace_file: str = typer.Argument(..., help="Path to a mobile simulator JSONL trace."),
    fmt: str = typer.Option("json", "--format", help="SIEM format: json|cef."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Export a trace to a SIEM format (CEF or JSON). Payloads stay hash-only and event
    metadata is exported as key names only — no raw payloads or secret values leave."""
    _setup_logging(debug)
    from ..mobile import export_trace, read_trace

    p = Path(trace_file)
    if not p.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Trace file not found: {trace_file}"), json_output)
        raise typer.Exit(1)
    try:
        trace = read_trace(p)
        rendered = export_trace(trace, fmt)
    except ValueError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid trace file: {exc}"), json_output)
        raise typer.Exit(1) from exc

    if json_output:
        _out(
            ok({"format": fmt.lower(), "event_count": len(trace.events), "rendered": rendered}),
            json_output,
        )
    else:
        typer.echo(rendered)


@mobile_app.command("replay")
def mobile_replay_cmd(
    trace_file: str = typer.Argument(..., help="Recorded trace JSONL to compare."),
    golden: str = typer.Option(..., "--golden", help="Golden trace JSONL to compare against."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Replay a trace against a golden trace; exits 1 on divergence."""
    _setup_logging(debug)
    from ..mobile import read_trace, replay_trace

    for fpath in (trace_file, golden):
        if not Path(fpath).is_file():
            _out(err(ArcErrorCode.INVALID_INPUT, f"File not found: {fpath}"), json_output)
            raise typer.Exit(1)
    try:
        recorded = read_trace(trace_file)
        gold = read_trace(golden)
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot read trace: {exc}"), json_output)
        raise typer.Exit(1) from exc

    diff = replay_trace(recorded, gold)
    payload = {
        "match": diff.match,
        "summary": diff.summary,
        "recorded_count": diff.recorded_count,
        "golden_count": diff.golden_count,
        "first_diff_index": diff.first_diff_index,
        "diffs": diff.diffs,
    }
    if diff.match:
        _out(ok(payload), json_output)
    else:
        _out(
            err(ArcErrorCode.INVALID_INPUT, f"Replay divergence: {diff.summary}", payload),
            json_output,
        )
        raise typer.Exit(1)


mobile_generate_app = typer.Typer(name="generate", help="Generate advisory compliance artifacts")
mobile_app.add_typer(mobile_generate_app)


def _load_manifest_for_generate(manifest_path: str | None, json_output: bool):
    from ..mobile.manifest import load_manifest as _load
    from ..mobile import build_default_manifest, MobileManifestLoadError

    if manifest_path:
        try:
            return _load(manifest_path)
        except MobileManifestLoadError as exc:
            _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot load manifest: {exc}"), json_output)
            raise typer.Exit(1) from exc
    return build_default_manifest("arc.mobile.runtime", "ARC Mobile Runtime")


@mobile_generate_app.command("ios-privacy")
def mobile_gen_ios_privacy_cmd(
    manifest: str | None = typer.Option(None, "--manifest"),
    out: str | None = typer.Option(None, "--out", help="Output file path (default: stdout/json)"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate advisory Apple PrivacyInfo.xcprivacy from a manifest."""
    _setup_logging(debug)
    from ..mobile.compliance.ios import generate_privacy_manifest, generate_usage_strings

    m = _load_manifest_for_generate(manifest, json_output)
    xml = generate_privacy_manifest(m)
    if out:
        Path(out).write_text(xml, encoding="utf-8")
    _out(
        ok(
            {
                "advisory": True,
                "requires_human_review": True,
                "manifest_id": m.id,
                "output": xml,
                "usage_strings": generate_usage_strings(m),
            }
        ),
        json_output,
    )


@mobile_generate_app.command("android-manifest")
def mobile_gen_android_manifest_cmd(
    manifest: str | None = typer.Option(None, "--manifest"),
    out: str | None = typer.Option(None, "--out"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate advisory Android manifest permission fragment."""
    _setup_logging(debug)
    from ..mobile.compliance.android import generate_manifest_permissions

    m = _load_manifest_for_generate(manifest, json_output)
    xml = generate_manifest_permissions(m)
    if out:
        Path(out).write_text(xml, encoding="utf-8")
    _out(
        ok({"advisory": True, "requires_human_review": True, "manifest_id": m.id, "output": xml}),
        json_output,
    )


@mobile_generate_app.command("data-safety")
def mobile_gen_data_safety_cmd(
    manifest: str | None = typer.Option(None, "--manifest"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate advisory Android Data Safety notes."""
    _setup_logging(debug)
    from ..mobile.compliance.android import generate_data_safety_notes

    m = _load_manifest_for_generate(manifest, json_output)
    _out(ok(generate_data_safety_notes(m)), json_output)


@mobile_generate_app.command("review-notes")
def mobile_gen_review_notes_cmd(
    manifest: str | None = typer.Option(None, "--manifest"),
    out: str | None = typer.Option(None, "--out"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate advisory app-store review notes."""
    _setup_logging(debug)
    from ..mobile.compliance.review_notes import generate_review_notes

    m = _load_manifest_for_generate(manifest, json_output)
    notes = generate_review_notes(m)
    if out:
        Path(out).write_text(notes, encoding="utf-8")
    _out(
        ok({"advisory": True, "requires_human_review": True, "manifest_id": m.id, "notes": notes}),
        json_output,
    )


@mobile_generate_app.command("compliance-report")
def mobile_gen_compliance_report_cmd(
    manifest: str | None = typer.Option(None, "--manifest"),
    out: str | None = typer.Option(None, "--out"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate an aggregated advisory compliance report (iOS + Android + review notes)."""
    _setup_logging(debug)
    import json as _json

    from ..mobile.compliance import generate_compliance_report

    m = _load_manifest_for_generate(manifest, json_output)
    report = generate_compliance_report(m)
    if out:
        Path(out).write_text(_json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    _out(ok(report), json_output)


@mobile_app.command("privacy-budget")
def mobile_privacy_budget_cmd(
    manifest: str | None = typer.Option(None, "--manifest", help="Path to manifest file/dir."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Summarise the privacy budget declared by a manifest."""
    _setup_logging(debug)
    from ..mobile.manifest import load_manifest as _load, MobileManifestLoadError
    from ..mobile import build_default_manifest
    from ..mobile.privacy_budget import compute_privacy_budget

    if manifest:
        try:
            m = _load(manifest)
        except MobileManifestLoadError as exc:
            _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot load manifest: {exc}"), json_output)
            raise typer.Exit(1) from exc
    else:
        m = build_default_manifest("arc.mobile.runtime", "ARC Mobile Runtime")

    budget = compute_privacy_budget(m)
    _out(ok(budget.as_dict()), json_output)


mobile_plan_app = typer.Typer(name="plan", help="Mobile action plan commands")
mobile_app.add_typer(mobile_plan_app)


@mobile_plan_app.command("sign")
def mobile_plan_sign_cmd(
    plan_file: str = typer.Argument(..., help="Path to action plan JSON."),
    key_hex: str = typer.Option(
        None, "--key", help="32-byte signing key as hex (generated if omitted)."
    ),
    out: str | None = typer.Option(None, "--out", help="Output envelope JSON path."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Sign an action plan and produce a SignedPlanEnvelope."""
    _setup_logging(debug)
    import secrets as _secrets
    from ..mobile import MobileActionPlan, sign_plan

    p = Path(plan_file)
    if not p.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Plan file not found: {plan_file}"), json_output)
        raise typer.Exit(1)
    try:
        import json as _json

        plan = MobileActionPlan.model_validate(_json.loads(p.read_text()))
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid plan: {exc}"), json_output)
        raise typer.Exit(1) from exc

    if key_hex:
        try:
            key = bytes.fromhex(key_hex)
        except ValueError as exc:
            _out(err(ArcErrorCode.INVALID_INPUT, "key must be valid hex"), json_output)
            raise typer.Exit(1) from exc
    else:
        key = _secrets.token_bytes(32)

    envelope = sign_plan(plan, key)
    data = envelope.model_dump(mode="json")
    if out:
        Path(out).write_text(_json.dumps(data, indent=2), encoding="utf-8")
    _out(
        ok({**data, "key_hex": key.hex(), "note": "Store key_hex securely; needed for verify."}),
        json_output,
    )


@mobile_plan_app.command("verify")
def mobile_plan_verify_cmd(
    envelope_file: str = typer.Argument(..., help="Path to signed envelope JSON."),
    key_hex: str = typer.Option(..., "--key", help="32-byte signing key as hex."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Verify a SignedPlanEnvelope. Exits 1 if invalid."""
    _setup_logging(debug)
    from ..mobile import SignedPlanEnvelope, verify_plan

    p = Path(envelope_file)
    if not p.is_file():
        _out(
            err(ArcErrorCode.INVALID_INPUT, f"Envelope file not found: {envelope_file}"),
            json_output,
        )
        raise typer.Exit(1)
    try:
        import json as _json

        envelope = SignedPlanEnvelope.model_validate(_json.loads(p.read_text()))
        key = bytes.fromhex(key_hex)
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INVALID_INPUT, f"Cannot parse envelope or key: {exc}"), json_output)
        raise typer.Exit(1) from exc

    valid = verify_plan(envelope, key)
    payload = {"ok": valid, "plan_id": envelope.plan_id, "algorithm": envelope.algorithm}
    if valid:
        _out(ok(payload), json_output)
    else:
        _out(
            err(ArcErrorCode.INVALID_INPUT, "Plan signature verification failed", payload),
            json_output,
        )
        raise typer.Exit(1)


mobile_gate_app = typer.Typer(
    name="gate", help="Native capability entry-gate (default-denied, fixtures-only)"
)
mobile_app.add_typer(mobile_gate_app)


@mobile_gate_app.command("evaluate")
def mobile_gate_evaluate_cmd(
    capability_id: str = typer.Argument(..., help="Capability id to evaluate."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Evaluate the native capability entry-gate for a capability.

    With the default (off) feature flags and no signed plan/approval/compliance, the gate is
    DENIED. Even an eligible capability is routed to fixtures in this build — no real device
    access is performed (that flip is human-gated and out of scope).
    """
    _setup_logging(debug)
    import secrets

    from ..mobile import CapabilityEntryGate, FeatureFlags

    gate = CapabilityEntryGate(FeatureFlags(), secrets.token_bytes(32))
    decision = gate.evaluate(capability_id)
    _out(ok(decision.as_dict()), json_output)


# Flat alias: 'arc mobile gate check' → README-documented name (parity with docs).
mobile_gate_app.command("check")(mobile_gate_evaluate_cmd)


mobile_flags_app = typer.Typer(
    name="flags", help="Mobile feature flags + kill switch (default-off)"
)
mobile_app.add_typer(mobile_flags_app)

_DEFAULT_FLAGS_STORE = ".arc/mobile/feature_flags.json"


def _flags(store: str):
    from ..mobile import FeatureFlags

    return FeatureFlags(path=Path(store))


@mobile_flags_app.command("list")
def mobile_flags_list_cmd(
    store: str = typer.Option(_DEFAULT_FLAGS_STORE, "--store"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show the feature-flag snapshot (effective state honours the kill switch)."""
    _setup_logging(debug)
    _out(ok(_flags(store).snapshot()), json_output)


@mobile_flags_app.command("enable")
def mobile_flags_enable_cmd(
    name: str = typer.Argument(...),
    store: str = typer.Option(_DEFAULT_FLAGS_STORE, "--store"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Enable a feature flag (still gated by the kill switch)."""
    _setup_logging(debug)
    ff = _flags(store)
    ff.enable(name)
    _out(ok(ff.snapshot()), json_output)


@mobile_flags_app.command("disable")
def mobile_flags_disable_cmd(
    name: str = typer.Argument(...),
    store: str = typer.Option(_DEFAULT_FLAGS_STORE, "--store"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Disable a feature flag."""
    _setup_logging(debug)
    ff = _flags(store)
    ff.disable(name)
    _out(ok(ff.snapshot()), json_output)


@mobile_flags_app.command("kill-switch")
def mobile_flags_kill_switch_cmd(
    state: str = typer.Argument(..., help="on|off"),
    store: str = typer.Option(_DEFAULT_FLAGS_STORE, "--store"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Engage/disengage the global kill switch (overrides all flags to off when on)."""
    _setup_logging(debug)
    if state not in ("on", "off"):
        _out(err(ArcErrorCode.INVALID_INPUT, "state must be 'on' or 'off'"), json_output)
        raise typer.Exit(1)
    ff = _flags(store)
    ff.set_kill_switch(state == "on")
    _out(ok(ff.snapshot()), json_output)


mobile_egress_app = typer.Typer(
    name="egress", help="Mobile data-egress guard (budget-bound, deterministic)"
)
mobile_app.add_typer(mobile_egress_app)


@mobile_egress_app.command("check")
def mobile_egress_check_cmd(
    cost: int = typer.Argument(..., help="Byte cost of the egress."),
    budget: int = typer.Option(..., "--budget", help="Total egress byte budget."),
    classification: str = typer.Option("low", "--classification", help="Data sensitivity class."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Check whether a simulated egress is permitted (deterministic; critical class blocked)."""
    _setup_logging(debug)
    from ..mobile import EgressGuard

    guard = EgressGuard(budget_bytes=budget)
    decision = guard.check(cost, classification)
    _out(ok(decision.as_dict()), json_output)


mobile_queue_app = typer.Typer(name="queue", help="Mobile offline queue (durable, hash-only, TTL)")
mobile_app.add_typer(mobile_queue_app)

_DEFAULT_QUEUE_STORE = ".arc/mobile/offline_queue.json"


def _queue(store: str, max_entries: int = 1000):
    from ..mobile import OfflineQueue

    return OfflineQueue(path=Path(store), max_entries=max_entries)


@mobile_queue_app.command("enqueue")
def mobile_queue_enqueue_cmd(
    capability_id: str = typer.Argument(...),
    payload: str = typer.Option("{}", "--payload", help="JSON payload (stored hash-only)."),
    ttl: int = typer.Option(None, "--ttl", help="TTL seconds (optional)."),
    store: str = typer.Option(_DEFAULT_QUEUE_STORE, "--store"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Enqueue an action (only a SHA-256 hash + metadata is stored — no raw payload)."""
    _setup_logging(debug)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid --payload JSON: {exc}"), json_output)
        raise typer.Exit(1) from exc
    entry = _queue(store).enqueue(capability_id, data, ttl_seconds=ttl)
    _out(ok(entry.as_dict()), json_output)


@mobile_queue_app.command("status")
def mobile_queue_status_cmd(
    store: str = typer.Option(_DEFAULT_QUEUE_STORE, "--store"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show pending queue entries (hash-only)."""
    _setup_logging(debug)
    q = _queue(store)
    _out(ok({"pending": len(q), "entries": [e.as_dict() for e in q.pending()]}), json_output)


@mobile_queue_app.command("flush")
def mobile_queue_flush_cmd(
    store: str = typer.Option(_DEFAULT_QUEUE_STORE, "--store"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Flush all ready (non-expired) entries and clear the queue."""
    _setup_logging(debug)
    flushed = _queue(store).flush()
    _out(ok({"flushed": len(flushed), "entries": [e.as_dict() for e in flushed]}), json_output)


@mobile_queue_app.command("gc")
def mobile_queue_gc_cmd(
    store: str = typer.Option(_DEFAULT_QUEUE_STORE, "--store"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Drop expired entries. Returns the number removed."""
    _setup_logging(debug)
    _out(ok({"removed": _queue(store).gc()}), json_output)


mobile_secure_store_app = typer.Typer(
    name="secure-store", help="Mobile encrypted local store (redacted output, no plaintext)"
)
mobile_app.add_typer(mobile_secure_store_app)

_DEFAULT_SS_STORE = ".arc/mobile/secure_store.json"
_DEFAULT_SS_KEY = ".arc/mobile/secure_store.key"


def _secure_store(store: str, key_path: str):
    from cryptography.fernet import Fernet

    from ..mobile import InMemoryKeyProvider, SecureLocalStore

    kp = Path(key_path)
    if kp.exists():
        key = kp.read_bytes()
    else:
        key = Fernet.generate_key()
        kp.parent.mkdir(parents=True, exist_ok=True)
        kp.write_bytes(key)
    return SecureLocalStore(key_provider=InMemoryKeyProvider(key), path=Path(store))


@mobile_secure_store_app.command("put")
def mobile_ss_put_cmd(
    key: str = typer.Argument(...),
    value: str = typer.Argument(..., help="Value to encrypt at rest (never echoed)."),
    classification: str = typer.Option("low", "--classification"),
    store: str = typer.Option(_DEFAULT_SS_STORE, "--store"),
    key_file: str = typer.Option(_DEFAULT_SS_KEY, "--key-file"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Encrypt-and-store a value. The value is never echoed back."""
    _setup_logging(debug)
    ss = _secure_store(store, key_file)
    ss.put(key, value, classification)
    _out(ok({"stored": True, "key": key, "classification": classification}), json_output)


@mobile_secure_store_app.command("get")
def mobile_ss_get_cmd(
    key: str = typer.Argument(...),
    store: str = typer.Option(_DEFAULT_SS_STORE, "--store"),
    key_file: str = typer.Option(_DEFAULT_SS_KEY, "--key-file"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Confirm a key exists + its classification. The plaintext value is NEVER printed."""
    _setup_logging(debug)
    ss = _secure_store(store, key_file)
    if key not in ss.keys():
        _out(err(ArcErrorCode.INVALID_INPUT, f"key not found: {key}"), json_output)
        raise typer.Exit(1)
    _out(
        ok(
            {
                "key": key,
                "exists": True,
                "classification": ss.classification_of(key).value,
                "value": "[REDACTED]",
            }
        ),
        json_output,
    )


@mobile_secure_store_app.command("export")
def mobile_ss_export_cmd(
    store: str = typer.Option(_DEFAULT_SS_STORE, "--store"),
    key_file: str = typer.Option(_DEFAULT_SS_KEY, "--key-file"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Export entry metadata only (no values)."""
    _setup_logging(debug)
    _out(ok(_secure_store(store, key_file).export(include_values=False)), json_output)


@mobile_secure_store_app.command("delete")
def mobile_ss_delete_cmd(
    key: str = typer.Argument(...),
    store: str = typer.Option(_DEFAULT_SS_STORE, "--store"),
    key_file: str = typer.Option(_DEFAULT_SS_KEY, "--key-file"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Delete a stored key."""
    _setup_logging(debug)
    _out(ok({"deleted": _secure_store(store, key_file).delete(key), "key": key}), json_output)


@mobile_app.command("audit-retention")
def mobile_audit_retention_cmd(
    file: str = typer.Option(
        str(Path.home() / ".arc" / "audit" / "mobile_decisions.jsonl"),
        "--file",
        help="JSONL decisions audit log to prune.",
    ),
    max_age_seconds: int = typer.Option(
        None, "--max-age", help="Drop entries older than N seconds."
    ),
    max_entries: int = typer.Option(None, "--max-entries", help="Keep only the newest N entries."),
    rotate_bytes: int = typer.Option(None, "--rotate-bytes", help="Rotate to .1 past this size."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Apply TTL/count retention (and optional size rotation) to the decisions audit log."""
    _setup_logging(debug)
    from ..mobile import apply_retention, rotate_if_oversized

    rotated = rotate_if_oversized(file, rotate_bytes) if rotate_bytes is not None else False
    summary = apply_retention(file, max_age_seconds=max_age_seconds, max_entries=max_entries)
    summary["rotated"] = rotated
    _out(ok(summary), json_output)


@mobile_app.command("provenance")
def mobile_provenance_cmd(
    version: str = typer.Option("0.1.0", "--version", help="Package version for the attestation."),
    sign: bool = typer.Option(
        False, "--sign", help="Locally sign the attestation (needs --key-file)."
    ),
    key_file: str = typer.Option(None, "--key-file", help="Key file for local signing."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Build a mobile supply-chain provenance attestation (SBOM + build metadata).

    With --sign + --key-file the attestation is signed locally (deterministic HMAC; no external
    signing infrastructure). Verifiable offline. Simulator-preview posture; advisory.
    """
    _setup_logging(debug)
    from ..mobile import build_provenance, sign_provenance

    provenance = build_provenance(version)
    if sign:
        if not key_file:
            _out(err(ArcErrorCode.INVALID_INPUT, "--sign requires --key-file"), json_output)
            raise typer.Exit(1)
        key = Path(key_file).read_bytes()
        _out(ok(sign_provenance(provenance, key)), json_output)
    else:
        _out(ok(provenance), json_output)


mobile_posture_app = typer.Typer(
    name="posture", help="Device posture / MDM evaluation (simulator-preview, fixtures)"
)
mobile_app.add_typer(mobile_posture_app)


@mobile_posture_app.command("check")
def mobile_posture_check_cmd(
    require_mdm: bool = typer.Option(False, "--require-mdm", help="Require MDM enrollment."),
    require_passcode: bool = typer.Option(
        False, "--require-passcode", help="Require a device passcode."
    ),
    jailbroken: bool = typer.Option(
        False, "--jailbroken", help="Simulate a jailbroken device (fixture)."
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Evaluate (fixture) device posture against a policy. Deterministic; no real device access."""
    _setup_logging(debug)
    from ..mobile import (
        DevicePosture,
        FixtureDevicePostureHook,
        PosturePolicy,
        evaluate_posture,
    )

    hook = FixtureDevicePostureHook(DevicePosture(jailbroken=jailbroken))
    policy = PosturePolicy(require_mdm=require_mdm, require_passcode=require_passcode)
    decision = evaluate_posture(hook.read(), policy)
    _out(ok(decision.model_dump()), json_output)
