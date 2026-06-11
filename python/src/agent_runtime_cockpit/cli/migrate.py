"""CLI commands for ARC Migrate — cross-adapter migration assistant (R102).

Commands:
  arc migrate detect      Detect the agent framework in a workspace.
  arc migrate analyze     Analyze migration feasibility.
  arc migrate run         Run a full migration.
  arc migrate validate    Validate migrated code.

All commands accept --json for machine-readable envelope output.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import JSON_FLAG, WORKSPACE_FLAG, _out, _workspace
from ._subapps import migrate_app


@migrate_app.command("detect")
def migrate_detect(
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Detect the agent framework used in a workspace."""
    from ..migrate import detect_framework

    ws = _workspace(workspace)
    framework = detect_framework(ws)

    _out(
        ok(
            {
                "workspace": str(ws),
                "framework": framework.value,
                "detected": framework.value != "unknown",
            }
        ),
        as_json,
    )

    if not as_json:
        from ._app import console

        console.print("\n[bold]Framework Detection[/bold]")
        console.print(f"  Workspace: {ws}")
        console.print(f"  Framework: {framework.value}")
        if framework.value == "unknown":
            console.print("  [yellow]No known framework detected.[/yellow]")


@migrate_app.command("analyze")
def migrate_analyze(
    target: str = typer.Argument(
        ...,
        help="Target framework: langgraph, crewai, swarmgraph, openai_agents, autogen, llamaindex",
    ),
    source: Optional[str] = typer.Option(
        None, "--source", "-s", help="Source workspace path (default: current workspace)"
    ),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Analyze migration feasibility from source to target framework."""
    from ..migrate import FrameworkType, analyze_migration, detect_framework

    ws = _workspace(workspace)
    source_path = Path(source) if source else ws

    try:
        target_framework = FrameworkType(target)
    except ValueError:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Invalid target framework: {target}. Use: langgraph, crewai, swarmgraph, openai_agents, autogen, llamaindex",
            ),
            as_json,
        )
        raise typer.Exit(1)

    source_framework = detect_framework(source_path)
    analysis = analyze_migration(source_path, source_framework, target_framework)

    _out(ok(analysis.to_dict()), as_json)

    if not as_json:
        from ._app import console

        console.print("\n[bold]Migration Analysis[/bold]")
        console.print(f"  Source: {source_framework.value}")
        console.print(f"  Target: {target_framework.value}")
        console.print(f"  Source files: {len(analysis.source_files)}")
        console.print(f"  Detected patterns: {len(analysis.detected_patterns)}")
        console.print(f"  Compatibility score: {analysis.compatibility_score:.2f}")
        console.print(f"  Estimated effort: {analysis.estimated_effort}")
        if analysis.issues:
            console.print(f"\n  [yellow]Issues ({len(analysis.issues)})[/yellow]")
            for issue in analysis.issues[:5]:
                console.print(f"    [{issue.severity}] {issue.message}")


@migrate_app.command("run")
def migrate_run(
    target: str = typer.Argument(..., help="Target framework"),
    output: str = typer.Option(..., "--output", "-o", help="Output directory for migrated code"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Source workspace path"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Analyze and preview without writing files"
    ),
    yes: bool = typer.Option(False, "--yes", help="Confirm writing migration output"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Run a full migration from source to target framework."""
    from ..migrate import FrameworkType, migrate_workspace

    ws = _workspace(workspace)
    source_path = Path(source) if source else ws
    output_path = Path(output)

    try:
        target_framework = FrameworkType(target)
    except ValueError:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Invalid target framework: {target}. Use: langgraph, crewai, swarmgraph, openai_agents, autogen, llamaindex",
            ),
            as_json,
        )
        raise typer.Exit(1)

    if not dry_run and not yes:
        _out(
            err(
                ArcErrorCode.PERMISSION_DENIED,
                "Migration writes files; pass --yes to confirm or --dry-run to preview.",
                {"output": str(output_path)},
            ),
            as_json,
        )
        raise typer.Exit(1)

    session_id = str(uuid.uuid4())
    result = migrate_workspace(
        source_path, output_path, target_framework, session_id, dry_run=dry_run
    )

    _out(ok(result.to_dict()), as_json)

    if not as_json:
        from ._app import console

        console.print("\n[bold]Migration Result[/bold]")
        console.print(f"  Session ID: {result.session_id}")
        console.print(f"  Status: {result.status.value}")
        console.print(f"  Source: {result.source_framework.value}")
        console.print(f"  Target: {result.target_framework.value}")
        console.print(f"  Generated files: {len(result.generated_files)}")
        console.print(f"  Validation passed: {result.validation_passed}")
        if result.errors:
            console.print(f"\n  [red]Errors ({len(result.errors)})[/red]")
            for error in result.errors[:5]:
                console.print(f"    {error}")


@migrate_app.command("validate")
def migrate_validate(
    output: str = typer.Argument(..., help="Output directory with migrated code"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Source workspace path"),
    strict: bool = typer.Option(False, "--strict", help="Treat missing generated files as errors"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Validate migrated code for equivalence."""
    from ..migrate import analyze_migration, detect_framework, validate_migration

    ws = _workspace(workspace)
    source_path = Path(source) if source else ws
    output_path = Path(output)

    if not output_path.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Output directory not found: {output}"), as_json)
        raise typer.Exit(1)

    source_framework = detect_framework(source_path)
    target_framework = detect_framework(output_path)
    analysis = analyze_migration(source_path, source_framework, target_framework)
    report = validate_migration(source_path, output_path, analysis, strict=strict)

    _out(ok(report), as_json)

    if not as_json:
        from ._app import console

        console.print("\n[bold]Migration Validation[/bold]")
        console.print(f"  Source files: {report['source_files']}")
        console.print(f"  Generated files: {report['generated_files']}")
        console.print(f"  Parse errors: {report['parse_errors']}")
        console.print(f"  Validation passed: {report['validation_passed']}")
        if report["issues"]:
            console.print(f"\n  [yellow]Issues ({len(report['issues'])})[/yellow]")
            for issue in report["issues"][:5]:
                console.print(f"    {issue['type']}: {issue['message']}")


__all__ = ["migrate_app"]
