"""Test bench CLI commands — detect and run tests through sandbox (Phase 79 / R49)."""

from __future__ import annotations

import json
from configparser import ConfigParser
from pathlib import Path
from typing import Optional

import typer

from ..isolation.subprocess import SubprocessIsolationProvider
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..runtime.streaming import stream_subprocess_events
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


_IGNORE_DIRS = frozenset({"node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".git"})


def _scan_package_json(root: Path, cwd: str) -> list[dict]:
    results: list[dict] = []
    pkg_json = root / "package.json"
    if not pkg_json.is_file():
        return results
    try:
        pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
    except Exception:
        return results
    scripts = pkg.get("scripts", {})
    if "test" not in scripts:
        return results
    lock_files = list(root.glob("pnpm-lock.*")) + list(root.glob("pnpm-lock.yaml"))
    yarn_lock = list(root.glob("yarn.lock"))
    pm = "pnpm" if lock_files else ("yarn" if yarn_lock else "npm")
    pm_from_field = (pkg.get("packageManager") or "").split("@")[0]
    if pm_from_field in ("pnpm", "yarn", "npm"):
        pm = pm_from_field
    results.append(
        {
            "command": f"{pm} test",
            "source": "package.json",
            "runner": pm,
            "cwd": cwd,
            "confidence": "high",
            "script": scripts["test"],
        }
    )
    return results


def _scan_pyproject_toml(root: Path, cwd: str) -> list[dict]:
    results: list[dict] = []
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return results
    try:
        text = pyproject.read_text(encoding="utf-8")
    except Exception:
        return results
    try:
        import tomllib

        data = tomllib.loads(text)
        tool = data.get("tool", {})
        pytest_opts = tool.get("pytest", {})
        if "ini_options" in pytest_opts:
            results.append(
                {
                    "command": "pytest",
                    "source": "pyproject.toml",
                    "runner": "pytest",
                    "cwd": cwd,
                    "confidence": "high",
                }
            )
        elif "tox" in tool:
            results.append(
                {
                    "command": "tox",
                    "source": "pyproject.toml",
                    "runner": "tox",
                    "cwd": cwd,
                    "confidence": "high",
                }
            )
        elif "project" in data:
            tests_dir = root / "tests"
            if tests_dir.is_dir():
                results.append(
                    {
                        "command": "pytest",
                        "source": "pyproject.toml",
                        "runner": "pytest",
                        "cwd": cwd,
                        "confidence": "medium",
                    }
                )
    except Exception:
        if "[tool.pytest.ini_options]" in text:
            results.append(
                {
                    "command": "pytest",
                    "source": "pyproject.toml",
                    "runner": "pytest",
                    "cwd": cwd,
                    "confidence": "high",
                }
            )
        elif "[tool.tox]" in text:
            results.append(
                {
                    "command": "tox",
                    "source": "pyproject.toml",
                    "runner": "tox",
                    "cwd": cwd,
                    "confidence": "high",
                }
            )
    return results


def _scan_tox_ini(root: Path, cwd: str) -> list[dict]:
    tox_ini = root / "tox.ini"
    if not tox_ini.is_file():
        return []
    return [
        {
            "command": "tox",
            "source": "tox.ini",
            "runner": "tox",
            "cwd": cwd,
            "confidence": "high",
        }
    ]


def _scan_noxfile(root: Path, cwd: str) -> list[dict]:
    noxfile = root / "noxfile.py"
    if not noxfile.is_file():
        return []
    return [
        {
            "command": "nox",
            "source": "noxfile.py",
            "runner": "nox",
            "cwd": cwd,
            "confidence": "high",
        }
    ]


def _scan_makefile(root: Path, cwd: str) -> list[dict]:
    for name in ("Makefile", "makefile", "GNUmakefile"):
        mf = root / name
        if mf.is_file():
            try:
                text = mf.read_text(encoding="utf-8")
                for line in text.splitlines():
                    if line.strip().startswith("test:"):
                        return [
                            {
                                "command": "make test",
                                "source": name,
                                "runner": "make",
                                "cwd": cwd,
                                "confidence": "high",
                            }
                        ]
            except Exception:
                pass
    return []


def _scan_pytest_ini(root: Path, cwd: str) -> list[dict]:
    pytest_ini = root / "pytest.ini"
    if not pytest_ini.is_file():
        return []
    return [
        {
            "command": "pytest",
            "source": "pytest.ini",
            "runner": "pytest",
            "cwd": cwd,
            "confidence": "high",
        }
    ]


def _scan_setup_cfg(root: Path, cwd: str) -> list[dict]:
    setup_cfg = root / "setup.cfg"
    if not setup_cfg.is_file():
        return []
    try:
        cfg = ConfigParser()
        cfg.read_string(setup_cfg.read_text(encoding="utf-8"))
        if cfg.has_section("tool:pytest"):
            return [
                {
                    "command": "pytest",
                    "source": "setup.cfg",
                    "runner": "pytest",
                    "cwd": cwd,
                    "confidence": "high",
                }
            ]
    except Exception:
        pass
    return []


def _scan_jest_config(root: Path, cwd: str) -> list[dict]:
    """Detect jest via jest.config.* files."""
    for pattern in ("jest.config.ts", "jest.config.js", "jest.config.mjs", "jest.config.cjs"):
        if (root / pattern).is_file():
            return [
                {
                    "command": "npx jest",
                    "source": pattern,
                    "runner": "jest",
                    "cwd": cwd,
                    "confidence": "high",
                }
            ]
    return []


def _scan_vitest_config(root: Path, cwd: str) -> list[dict]:
    """Detect vitest via vitest.config.* files."""
    for pattern in ("vitest.config.ts", "vitest.config.js", "vitest.config.mjs"):
        if (root / pattern).is_file():
            return [
                {
                    "command": "npx vitest run",
                    "source": pattern,
                    "runner": "vitest",
                    "cwd": cwd,
                    "confidence": "high",
                }
            ]
    return []


def _scan_playwright_config(root: Path, cwd: str) -> list[dict]:
    """Detect playwright via playwright.config.* files."""
    for pattern in ("playwright.config.ts", "playwright.config.js", "playwright.config.mjs"):
        if (root / pattern).is_file():
            return [
                {
                    "command": "npx playwright test",
                    "source": pattern,
                    "runner": "playwright",
                    "cwd": cwd,
                    "confidence": "high",
                }
            ]
    return []


def _scan_cypress_config(root: Path, cwd: str) -> list[dict]:
    """Detect cypress via cypress.config.* files."""
    for pattern in ("cypress.config.ts", "cypress.config.js", "cypress.config.mjs"):
        if (root / pattern).is_file():
            return [
                {
                    "command": "npx cypress run",
                    "source": pattern,
                    "runner": "cypress",
                    "cwd": cwd,
                    "confidence": "high",
                }
            ]
    return []


def _scan_mocha_config(root: Path, cwd: str) -> list[dict]:
    """Detect mocha via .mocharc.* files."""
    for pattern in (".mocharc.yml", ".mocharc.js", ".mocharc.json", ".mocharc.cjs"):
        if (root / pattern).is_file():
            return [
                {
                    "command": "npx mocha",
                    "source": pattern,
                    "runner": "mocha",
                    "cwd": cwd,
                    "confidence": "high",
                }
            ]
    return []


def _scan_ava_config(root: Path, cwd: str) -> list[dict]:
    """Detect ava via ava.config.* files."""
    for pattern in ("ava.config.js", "ava.config.ts", "ava.config.cjs"):
        if (root / pattern).is_file():
            return [
                {
                    "command": "npx ava",
                    "source": pattern,
                    "runner": "ava",
                    "cwd": cwd,
                    "confidence": "high",
                }
            ]
    return []


def _scan_ruff(root: Path, cwd: str) -> list[dict]:
    """Detect ruff linter via ruff.toml or pyproject.toml [tool.ruff]."""
    if (root / "ruff.toml").is_file() or (root / ".ruff.toml").is_file():
        return [
            {
                "command": "ruff check .",
                "source": "ruff.toml",
                "runner": "ruff",
                "cwd": cwd,
                "confidence": "high",
            }
        ]
    pyproject_toml = root / "pyproject.toml"
    if pyproject_toml.is_file():
        try:
            import tomllib

            data = tomllib.loads(pyproject_toml.read_text(encoding="utf-8"))
            if data.get("tool", {}).get("ruff"):
                return [
                    {
                        "command": "ruff check .",
                        "source": "pyproject.toml",
                        "runner": "ruff",
                        "cwd": cwd,
                        "confidence": "high",
                    }
                ]
        except Exception:
            pass
    return []


def _scan_mypy(root: Path, cwd: str) -> list[dict]:
    """Detect mypy via mypy.ini or pyproject.toml [tool.mypy]."""
    if (root / "mypy.ini").is_file() or (root / ".mypy.ini").is_file():
        return [
            {
                "command": "mypy .",
                "source": "mypy.ini",
                "runner": "mypy",
                "cwd": cwd,
                "confidence": "high",
            }
        ]
    pyproject_toml = root / "pyproject.toml"
    if pyproject_toml.is_file():
        try:
            import tomllib

            data = tomllib.loads(pyproject_toml.read_text(encoding="utf-8"))
            if data.get("tool", {}).get("mypy"):
                return [
                    {
                        "command": "mypy .",
                        "source": "pyproject.toml",
                        "runner": "mypy",
                        "cwd": cwd,
                        "confidence": "high",
                    }
                ]
        except Exception:
            pass
    return []


def _scan_pylint(root: Path, cwd: str) -> list[dict]:
    """Detect pylint via .pylintrc or pyproject.toml [tool.pylint]."""
    if (root / ".pylintrc").is_file():
        return [
            {
                "command": "pylint .",
                "source": ".pylintrc",
                "runner": "pylint",
                "cwd": cwd,
                "confidence": "high",
            }
        ]
    return []


def _scan_flake8(root: Path, cwd: str) -> list[dict]:
    """Detect flake8 via .flake8 or setup.cfg [flake8]."""
    if (root / ".flake8").is_file():
        return [
            {
                "command": "flake8 .",
                "source": ".flake8",
                "runner": "flake8",
                "cwd": cwd,
                "confidence": "high",
            }
        ]
    return []


_SCANNERS = [
    _scan_package_json,
    _scan_pyproject_toml,
    _scan_tox_ini,
    _scan_noxfile,
    _scan_makefile,
    _scan_pytest_ini,
    _scan_setup_cfg,
    _scan_jest_config,
    _scan_vitest_config,
    _scan_playwright_config,
    _scan_cypress_config,
    _scan_mocha_config,
    _scan_ava_config,
    _scan_ruff,
    _scan_mypy,
    _scan_pylint,
    _scan_flake8,
]


def _find_candidate_roots(workspace: Path) -> list[tuple[Path, str]]:
    roots: list[tuple[Path, str]] = [(workspace, ".")]
    seen: set[Path] = {workspace}

    # pnpm workspace
    pnpm_yaml = workspace / "pnpm-workspace.yaml"
    if pnpm_yaml.is_file():
        try:
            import yaml as _yaml

            data = _yaml.safe_load(pnpm_yaml.read_text(encoding="utf-8")) or {}
            pkgs = data.get("packages", [])
        except Exception:
            pkgs = []
        for pattern in pkgs:
            if isinstance(pattern, str):
                for p in workspace.glob(pattern):
                    p = p.resolve()
                    if (
                        p.is_dir()
                        and p not in seen
                        and not any(
                            ign in p.parts
                            for ign in ("node_modules", ".venv", "venv", "dist", "build")
                        )
                    ):
                        try:
                            rel = str(p.relative_to(workspace))
                        except ValueError:
                            rel = str(p)
                        seen.add(p)
                        roots.append((p, rel))

    # package.json workspaces
    pkg_json = workspace / "package.json"
    if pkg_json.is_file():
        try:
            pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
            ws_config = pkg.get("workspaces")
            if isinstance(ws_config, dict):
                ws_config = ws_config.get("packages", [])
            if isinstance(ws_config, list):
                for pattern in ws_config:
                    if isinstance(pattern, str):
                        for p in workspace.glob(pattern):
                            p = p.resolve()
                            if (
                                p.is_dir()
                                and p not in seen
                                and not any(
                                    ign in p.parts
                                    for ign in ("node_modules", ".venv", "venv", "dist", "build")
                                )
                            ):
                                try:
                                    rel = str(p.relative_to(workspace))
                                except ValueError:
                                    rel = str(p)
                                seen.add(p)
                                roots.append((p, rel))
        except Exception:
            pass

    # pyproject.toml uv workspace
    pyproject = workspace / "pyproject.toml"
    if pyproject.is_file():
        try:
            import tomllib

            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            members = data.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", [])
            for pattern in members:
                if isinstance(pattern, str):
                    for p in workspace.glob(pattern):
                        p = p.resolve()
                        if (
                            p.is_dir()
                            and p not in seen
                            and not any(
                                ign in p.parts
                                for ign in ("node_modules", ".venv", "venv", "dist", "build")
                            )
                        ):
                            try:
                                rel = str(p.relative_to(workspace))
                            except ValueError:
                                rel = str(p)
                            seen.add(p)
                            roots.append((p, rel))
        except Exception:
            pass

    roots.sort(key=lambda x: (x[1] != ".", x[1]))
    return roots


def _detect_commands(workspace: Path) -> list[dict]:
    detected: list[dict] = []
    roots = _find_candidate_roots(workspace)

    for root, cwd in roots:
        for scanner in _SCANNERS:
            detected.extend(scanner(root, cwd))

    detected.sort(key=lambda d: (d.get("cwd", "."), d.get("source", "")))
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
    stream_json: bool = typer.Option(False, "--stream-json", help="Emit JSONL stream events"),
    cancel_after_events: Optional[int] = typer.Option(
        None, "--cancel-after-events", help="Deterministically cancel after N output events"
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

    if stream_json:
        events, stream_result = stream_subprocess_events(
            command,
            cwd=cwd,
            source="testbench",
            timeout_seconds=policy_model.timeout_seconds,
            max_output_bytes=policy_model.max_output_bytes,
            cancel_after_events=cancel_after_events,
            safe_env_keys=frozenset(policy_model.env_allowlist),
        )
        for event in events:
            typer.echo(
                json.dumps(
                    ok(event.model_dump(mode="json"), workspace=str(ws)).model_dump(mode="json"),
                    sort_keys=True,
                )
            )
        if stream_result.terminal_event.value in {"cancelled", "timeout"}:
            raise typer.Exit(130 if stream_result.terminal_event.value == "cancelled" else 124)
        if stream_result.exit_code not in (0, None):
            raise typer.Exit(stream_result.exit_code)
        return

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
