"""Test bench CLI commands — detect and run tests through sandbox (Phase 79 / R49)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from ..isolation.subprocess import SubprocessIsolationProvider
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..security.sandbox import (
    SandboxPolicy,
    SandboxResult,
    approve_decision_with_token,
    build_audit_event,
    decide,
    ensure_workspace_cwd,
    persist_sandbox_audit_event,
    resolve_sandbox_policy,
    utc_now,
    validate_command_paths,
)
from ._helpers import DEBUG_FLAG, JSON_FLAG, WORKSPACE_FLAG, _out, _setup_logging, _workspace
from ._subapps import testbench_app


def _policy(name: str, workspace: Path) -> SandboxPolicy:
    try:
        return resolve_sandbox_policy(name, workspace)
    except (KeyError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc


def _detect_commands(workspace: Path) -> list[dict]:
    detected: list[dict] = []

    # Check package.json
    pkg_json = workspace / "package.json"
    if pkg_json.is_file():
        try:
            pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
            scripts = pkg.get("scripts", {})
            if "test" in scripts:
                detected.append(
                    {
                        "command": scripts["test"],
                        "source": "package.json",
                        "confidence": "high",
                        "runner": "npm_test",
                    }
                )
        except Exception:
            detected.append(
                {
                    "source": "package.json",
                    "confidence": "none",
                    "reason": "parse_failed",
                }
            )

    # Check pyproject.toml for pytest config
    pyproject = workspace / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8")
            if "[tool.pytest.ini_options]" in text:
                detected.append(
                    {
                        "command": "pytest",
                        "source": "pyproject.toml",
                        "confidence": "high",
                        "runner": "pytest",
                    }
                )
        except Exception:
            pass

    # Check for pytest.ini or setup.cfg with pytest config
    pytest_ini = workspace / "pytest.ini"
    if pytest_ini.is_file():
        detected.append(
            {
                "command": "pytest",
                "source": "pytest.ini",
                "confidence": "high",
                "runner": "pytest",
            }
        )

    # Check setup.cfg for pytest config
    setup_cfg = workspace / "setup.cfg"
    if setup_cfg.is_file():
        try:
            text = setup_cfg.read_text(encoding="utf-8")
            if "[tool:pytest]" in text:
                detected.append(
                    {
                        "command": "pytest",
                        "source": "setup.cfg",
                        "confidence": "high",
                        "runner": "pytest",
                    }
                )
        except Exception:
            pass

    # Check Makefile for test target
    makefile = workspace / "Makefile"
    if makefile.is_file():
        try:
            text = makefile.read_text(encoding="utf-8")
            for line in text.splitlines():
                if line.strip().startswith("test:"):
                    detected.append(
                        {
                            "command": "make test",
                            "source": "Makefile",
                            "confidence": "high",
                            "runner": "make",
                        }
                    )
                    break
        except Exception:
            pass

    return detected


@testbench_app.command("detect")
def testbench_detect(
    command_override: Optional[str] = typer.Option(
        None, "--command", "-c", help="Explicit test command override"
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Detect test commands from workspace configuration."""
    _setup_logging(debug)
    ws = _workspace(workspace)

    if command_override:
        detected = [
            {
                "command": command_override,
                "source": "explicit_override",
                "confidence": "explicit",
                "runner": "custom",
            }
        ]
    else:
        detected = _detect_commands(ws)

    payload = {
        "workspace": str(ws),
        "detected": detected,
        "count": len(detected),
    }
    _out(ok(payload, workspace=str(ws)), json_output)


@testbench_app.command(
    "run", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def testbench_run(
    ctx: typer.Context,
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
    approval_token: Optional[str] = typer.Option(
        None, "--approval-token", help="Use a scoped non-interactive approval token"
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Run argv through sandbox with test bench policy (no inferred pass/fail)."""
    _setup_logging(debug)
    command = list(ctx.args)
    ws = _workspace(workspace)

    if not command:
        _out(err(ArcErrorCode.INVALID_INPUT, "missing command"), json_output)
        raise typer.Exit(2)

    try:
        policy_model = _policy(policy, ws)
        cwd = ensure_workspace_cwd(Path.cwd(), ws)
        decision = decide(command, policy_model)
        decision = approve_decision_with_token(
            token=approval_token, command=command, policy=policy_model, decision=decision
        )
    except (ValueError, typer.BadParameter) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)

    started_at = utc_now()
    ended_at = started_at

    try:
        validate_command_paths(command, policy_model)
    except ValueError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)

    if not decision.allowed:
        audit = build_audit_event(
            command=command,
            cwd=cwd,
            decision=decision,
            provider="subprocess",
            started_at=started_at,
            ended_at=ended_at,
            exit_code=None,
            stdout_truncated=False,
            stderr_truncated=False,
            redaction_applied=False,
        )
        audit_path = persist_sandbox_audit_event(audit)
        audit["audit_path"] = str(audit_path)
        result = SandboxResult(
            command=command,
            cwd=str(cwd),
            classification=decision.classification,
            decision=decision,
            provider="subprocess",
            audit_event=audit,
        )
        _out(ok(result.model_dump(mode="json"), workspace=str(ws)), json_output)
        raise typer.Exit(3)

    import asyncio

    iso = asyncio.run(
        SubprocessIsolationProvider(
            safe_env_keys=frozenset(policy_model.env_allowlist),
            workspace_root=ws,
            max_output_bytes=policy_model.max_output_bytes,
        ).execute(
            command,
            cwd=cwd,
            timeout_seconds=policy_model.timeout_seconds,
        )
    )
    ended_at = utc_now()

    audit = build_audit_event(
        command=command,
        cwd=cwd,
        decision=decision,
        provider=iso.provider if iso.provider != "unknown" else "subprocess",
        started_at=started_at,
        ended_at=ended_at,
        exit_code=iso.exit_code,
        stdout_truncated=iso.stdout_truncated,
        stderr_truncated=iso.stderr_truncated,
        redaction_applied=iso.redaction_applied,
    )
    audit_path = persist_sandbox_audit_event(audit)
    audit["audit_path"] = str(audit_path)

    result = SandboxResult(
        command=command,
        cwd=str(cwd),
        classification=decision.classification,
        decision=decision,
        provider=iso.provider if iso.provider != "unknown" else "subprocess",
        exit_code=iso.exit_code,
        stdout=iso.stdout,
        stderr=iso.stderr,
        duration_ms=iso.duration_ms,
        timed_out=iso.killed and iso.kill_reason == "timeout",
        stdout_truncated=iso.stdout_truncated,
        stderr_truncated=iso.stderr_truncated,
        redaction_applied=iso.redaction_applied,
        audit_event=audit,
    )
    _out(ok(result.model_dump(mode="json"), workspace=str(ws)), json_output)
    if iso.exit_code != 0:
        raise typer.Exit(iso.exit_code)
