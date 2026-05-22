"""Shared utility functions for ARC CLI commands (extracted from cli.py Phase 25)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.json import JSON
from rich import print as rprint

from ..gating import GatingError
from ..orchestration import runtime_router
from ..protocol.event_envelope import ArcEnvelope
from ..security.validation import validate_workspace_path

err_console = Console(stderr=True)

JSON_FLAG = typer.Option(False, "--json", help="Output raw JSON envelope")
WORKSPACE_FLAG = typer.Option(None, "--workspace", "-w", help="Workspace path (default: cwd)")
DEBUG_FLAG = typer.Option(False, "--debug", envvar="ARC_DEBUG", help="Enable debug logging")


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(level=level, format="%(name)s %(levelname)s %(message)s")


def _workspace(workspace: Optional[str]) -> Path:
    if workspace:
        try:
            return validate_workspace_path(workspace)
        except ValueError as e:
            err_console.print(f"[red]Invalid workspace: {e}[/red]")
            raise typer.Exit(1)
    return Path.cwd()


def _out(envelope: ArcEnvelope, as_json: bool) -> None:
    if as_json:
        print(envelope.model_dump_json(indent=2))
    else:
        if not envelope.ok:
            err_console.print(f"[red]Error [{envelope.error.code}]: {envelope.error.message}[/red]")
        else:
            rprint(JSON(envelope.model_dump_json()))


def _profile_payload(profile) -> dict[str, object]:
    return {
        "id": profile.id,
        "name": profile.name,
        "allow_paid_calls": profile.allow_paid_calls,
        "allow_network": profile.allow_network,
        "allow_shell": profile.allow_shell,
        "allow_secrets": profile.allow_secrets,
        "env_allowlist": list(profile.env_allowlist),
        "backend": profile.backend.value,
    }


RUNTIME_MODES = {"fake/offline", "local-real"}
CANONICAL_RUNTIME_MODES = {"fake", "gated_local", "provider_backed"}
LOCAL_REAL_GATE_ENVS = ("ARC_REAL_RUNTIME_SMOKE", "ARC_LANGGRAPH_SWARMGRAPH_REAL")


def _validate_runtime_mode(runtime_mode: str) -> str:
    if runtime_mode not in RUNTIME_MODES:
        canonical_map = {
            "fake": "fake/offline",
            "gated_local": "local-real",
            "provider_backed": "local-real",
        }
        corrected = canonical_map.get(runtime_mode, runtime_mode)
        if corrected not in RUNTIME_MODES:
            err_console.print(
                f"[red]Invalid runtime mode '{runtime_mode}'. Use one of: {', '.join(sorted(RUNTIME_MODES))} or canonical: fake, gated_local, provider_backed[/red]"
            )
            raise typer.Exit(2)
        return corrected
    return runtime_mode


def _local_real_gate_open() -> bool:
    return all(os.environ.get(env) for env in LOCAL_REAL_GATE_ENVS)


def _local_real_gate_state(runtime_mode: str) -> dict[str, bool | str]:
    if runtime_mode == "local-real":
        return {
            "open": _local_real_gate_open(),
            "required": True,
            "required_envs": list(LOCAL_REAL_GATE_ENVS),
            "present_envs": [env for env in LOCAL_REAL_GATE_ENVS if os.environ.get(env)],
        }
    return {"open": False, "required": False, "reason": "not_applicable"}


def _run_preflight(
    workspace: Path,
    workflow: str,
    runtime: str,
    profile_id: str,
    allow_paid_calls: bool,
    runtime_mode: str,
) -> dict[str, object]:
    from ..adoption.registry import AdoptionRegistry
    from ..security.profiles import ProfileNotFound, enforce_profile, resolve_profile_strict

    blockers: list[dict[str, str]] = []
    warnings: list[str] = []
    doctor_actions: list[dict[str, str]] = []
    profile_payload: dict[str, object] | None = None
    runtime_mode = _validate_runtime_mode(runtime_mode)
    paid_required = runtime == "crewai"

    try:
        profile = resolve_profile_strict(profile_id)
        profile_payload = _profile_payload(profile)
    except ProfileNotFound:
        blockers.append(
            {"code": "UNKNOWN_PROFILE", "message": f"Profile '{profile_id}' does not exist"}
        )
        profile = None

    if profile is not None:
        try:
            enforce_profile(profile, runtime)
        except GatingError as exc:
            blockers.append({"code": "PROFILE_BLOCKED", "message": str(exc)})
        if paid_required and not profile.allow_paid_calls:
            blockers.append(
                {
                    "code": "PAID_PROFILE_REQUIRED",
                    "message": f"Runtime '{runtime}' requires a profile with paid calls enabled",
                }
            )
        if paid_required and not allow_paid_calls:
            blockers.append(
                {
                    "code": "PAID_FLAG_REQUIRED",
                    "message": "Pass --allow-paid-calls after selecting a paid profile",
                }
            )

    key_ref_status = {
        "provider": "openai",
        "env": "OPENAI_API_KEY",
        "present": bool(os.environ.get("OPENAI_API_KEY")),
    }
    dependency_status: dict[str, object] = {}
    export_target_status: dict[str, object] = {}
    contract_status: dict[str, object] = {
        "runtime_mode": runtime_mode,
        "state": runtime_mode,
        "supported_runtime": runtime == "langgraph+swarmgraph" or runtime_mode == "fake/offline",
        "provider_backed_claim": False,
        "real_provider_call": False,
    }

    if runtime in {"crewai+swarmgraph", "langgraph+swarmgraph"}:
        base_runtime, adoption_mode = AdoptionRegistry.parse_runtime_id(runtime)
        capability = next(
            (
                cap
                for cap in AdoptionRegistry.list_capabilities(workspace)
                if cap.mode == adoption_mode
            ),
            None,
        )
        dependency_status = {
            base_runtime: capability.status.value if capability else "unknown",
            "adoption_runner": bool(capability),
        }
        if runtime == "crewai+swarmgraph" and capability:
            warnings.append(
                "CrewAI + SwarmGraph is fake/offline only; no real provider calls or HMAC audit claims."
            )
            doctor_actions.extend(capability.doctor_actions)
            export_target = os.environ.get("ARC_CREWAI_EXPORT")
            export_target_status = {
                "env": "ARC_CREWAI_EXPORT",
                "present": bool(export_target),
                "format": "module:attr",
            }
            if not export_target:
                blockers.append(
                    {
                        "code": "MISSING_CREWAI_EXPORT",
                        "message": "Set ARC_CREWAI_EXPORT=module:attr for CrewAI export discovery",
                    }
                )
            elif ":" not in export_target:
                blockers.append(
                    {
                        "code": "INVALID_CREWAI_EXPORT",
                        "message": "ARC_CREWAI_EXPORT must use module:attr format",
                    }
                )
        elif capability:
            report = runtime_router.LangGraphSwarmGraphFakeAdapter().capability_report(workspace)
            if runtime_mode == "local-real":
                warnings.append(
                    "LangGraph + SwarmGraph local-real is explicit opt-in smoke scope only; no network/provider/paid calls."
                )
                export_target_status = {
                    "required": False,
                    "reason": "local-real smoke path uses local runtime only",
                }
                if not _local_real_gate_open():
                    blockers.append(
                        {
                            "code": "LOCAL_REAL_GATE_REQUIRED",
                            "message": (
                                "Set ARC_REAL_RUNTIME_SMOKE=1 and ARC_LANGGRAPH_SWARMGRAPH_REAL=1 "
                                "to request langgraph+swarmgraph local-real"
                            ),
                        }
                    )
                elif not report.can_run:
                    blockers.append(
                        {
                            "code": "MISSING_LANGGRAPH_DEPENDENCY",
                            "message": report.reason
                            or "LangGraph + SwarmGraph local-real dependency missing",
                        }
                    )
                contract_status["state"] = (
                    "local_real_available"
                    if report.can_run and _local_real_gate_open()
                    else "local_real_gated"
                )
            else:
                warnings.append(
                    "LangGraph + SwarmGraph is fake/offline deterministic; no real provider calls or HMAC audit claims; real path gated."
                )
                export_target_status = {
                    "required": False,
                    "reason": "fake/offline deterministic path uses an in-process fixture graph",
                }
                contract_status["state"] = "fake_offline"
            dependency_status.update(
                {
                    "availability": report.availability,
                    "detected": report.detected,
                    "can_run": report.can_run,
                    "reason": report.reason,
                    "test_level": report.test_level,
                    "fake_offline_supported": report.fake_offline_supported,
                    "local_real_gated": report.local_real_gated,
                    "local_real_available": report.local_real_available,
                    "provider_backed": report.provider_backed,
                    "required_env": report.required_env,
                }
            )
        elif runtime_mode == "local-real":
            blockers.append(
                {
                    "code": "LOCAL_REAL_UNSUPPORTED",
                    "message": f"Runtime '{runtime}' does not support local-real mode",
                }
            )
            contract_status["state"] = "unsupported"
        dependency_status["runtime_mode"] = runtime_mode
        dependency_status["real_provider_call"] = False
        dependency_status["real_runtime_gated"] = (
            runtime_mode == "fake/offline" or not _local_real_gate_open()
        )
    else:
        try:
            requested_runtime = (
                [part.strip().lower() for part in runtime.split(",") if part.strip()]
                if "," in runtime
                else runtime.lower()
            )
            routed = runtime_router.resolve(
                workspace, requested_runtime, allow_paid_calls=allow_paid_calls
            )
            report = routed.report
            dependency_status = {
                "availability": report.availability,
                "detected": report.detected,
                "can_run": report.can_run,
            }
            if report.requires_paid_calls and not allow_paid_calls:
                blockers.append(
                    {
                        "code": "PAID_FLAG_REQUIRED",
                        "message": f"Runtime '{runtime}' requires --allow-paid-calls",
                    }
                )
        except runtime_router.RuntimeRouterError as exc:
            blockers.append({"code": exc.code, "message": str(exc)})

    return {
        "workflow": workflow,
        "runtime": runtime,
        "runtime_mode": runtime_mode,
        "profile": profile_payload,
        "runnable": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "doctor_actions": doctor_actions,
        "paid_call_required": paid_required,
        "key_ref_status": key_ref_status,
        "export_target_status": export_target_status,
        "dependency_status": dependency_status,
        "contract_status": contract_status,
        "gate_status": _local_real_gate_state(runtime_mode),
        "provider_backed_claim": False,
        "dry_run": True,
        "provider_call": False,
    }


def check_swarmgraph_runtime(timeout: float = 5.0) -> dict[str, object]:
    """Check local SwarmGraph CLI availability without network calls."""
    # enforcement: not-applicable - Diagnostic command checking CLI availability, not executing workflows
    candidates = [
        ("swarmgraph", ["--version"]),
        ("arc-swarmgraph", ["--version"]),
        ("arc", ["run", "--help"]),
    ]
    checks: list[dict[str, object]] = []
    for command, args in candidates:
        resolved = shutil.which(command)
        if not resolved:
            checks.append({"command": command, "available": False, "reason": "not_found"})
            continue
        try:
            # enforcement: not-applicable - Diagnostic command checking CLI availability
            result = subprocess.run(
                [resolved, *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        # enforcement: not-applicable - Exception handler, not a syscall
        except subprocess.TimeoutExpired:
            checks.append(
                {"command": command, "path": resolved, "available": False, "reason": "timeout"}
            )
            continue
        output = (result.stdout or result.stderr).strip().splitlines()
        checks.append(
            {
                "command": command,
                "path": resolved,
                "available": True,
                "version": output[-1] if output else None,
            }
        )
    return {"checks": checks, "any_available": any(c["available"] for c in checks)}
