"""CI guardrails CLI: offline checks, PR summaries, audit verification (Phase 80 / R51)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer

from ..protocol.event_envelope import ok
from ._helpers import DEBUG_FLAG, JSON_FLAG, _out, _setup_logging
from ._subapps import ci_app


@ci_app.command("check")
def ci_check(
    json_output: bool = JSON_FLAG,
    private: bool = typer.Option(True, "--private", help="Run checks offline, no uploads"),
    debug: bool = DEBUG_FLAG,
) -> None:
    """Run offline CI guardrail checks (sandbox audit, policy, eval, receipts).

    Default mode is private/offline — no network calls.
    """
    _setup_logging(debug)
    ws = Path.cwd()

    checks: dict[str, object] = {
        "private": private,
        "workspace": str(ws),
        "checks": {},
    }

    # 1. Sandbox audit — look for denied commands
    from ..security.sandbox import list_sandbox_audit_events

    audit_result = list_sandbox_audit_events(limit=100)
    denied_events = [e for e in audit_result.get("events", []) if e.get("allowed") is False]
    checks["checks"]["sandbox_audit"] = {
        "status": "fail" if denied_events else "pass",
        "total_events": audit_result.get("count", 0),
        "denied_count": len(denied_events),
        "denied_commands": [
            {
                "command": e.get("command", []),
                "classification": e.get("classification"),
                "reason": e.get("reason"),
                "started_at": e.get("started_at"),
            }
            for e in denied_events[:20]
        ],
        "degraded": audit_result.get("degraded", False),
        "source": audit_result.get("source", "unknown"),
    }

    # 2. Policy check
    from ..security.sandbox import list_sandbox_policies, validate_sandbox_policy_config

    policies = list_sandbox_policies(ws)
    policy_validation = validate_sandbox_policy_config()
    checks["checks"]["policy"] = {
        "status": "pass" if policy_validation.get("ok", True) else "fail",
        "policy_count": len(policies),
        "policy_names": [p.name for p in policies],
        "validation_errors": policy_validation.get("errors", []),
    }

    # 3. Eval gate — check for goldens or eval artifacts
    goldens_dir = ws / ".arc" / "goldens"
    eval_dir = ws / ".arc" / "eval"
    goldens_content: list[str] = []
    eval_content: list[str] = []
    if goldens_dir.exists():
        goldens_content = sorted(
            str(p.relative_to(ws)) for p in goldens_dir.iterdir() if p.is_file()
        )
    if eval_dir.exists():
        eval_content = sorted(str(p.relative_to(ws)) for p in eval_dir.iterdir() if p.is_file())
    checks["checks"]["eval"] = {
        "status": "pass" if (goldens_content or eval_content) else "skip",
        "goldens_found": len(goldens_content),
        "eval_files_found": len(eval_content),
        "goldens_files": goldens_content[:20],
        "eval_files": eval_content[:20],
    }

    # 4. Receipt check
    receipts_dir = ws / ".arc" / "receipts"
    receipt_files: list[str] = []
    if receipts_dir.exists():
        receipt_files = sorted(
            str(p.relative_to(ws))
            for p in receipts_dir.iterdir()
            if p.suffix in {".json", ".jsonl", ".md"}
        )
    checks["checks"]["receipt"] = {
        "status": "pass" if receipt_files else "skip",
        "receipt_count": len(receipt_files),
        "receipt_files": receipt_files[:20],
    }

    # Overall status
    all_statuses = [c.get("status", "skip") for c in checks["checks"].values()]
    overall = "fail" if "fail" in all_statuses else "pass"
    checks["overall"] = overall
    checks["checked_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    _out(ok(checks), json_output)


@ci_app.command("summary")
def ci_summary(
    format: str = typer.Option("markdown", "--format", help="Output format: markdown or json"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate an advisory PR summary from local CI data.

    Collects audit events, policy decisions, and eval results into
    deterministic redacted output. Advisory only — no AI judgment claims.
    """
    _setup_logging(debug)
    ws = Path.cwd()

    from ..security.sandbox import list_sandbox_audit_events, list_sandbox_policies

    audit_events = list_sandbox_audit_events(limit=100)
    policies = list_sandbox_policies(ws)

    # Collect denied events
    denied = [e for e in audit_events.get("events", []) if e.get("allowed") is False]
    allowed = [e for e in audit_events.get("events", []) if e.get("allowed") is True]

    # Eval status
    goldens_dir = ws / ".arc" / "goldens"
    eval_dir = ws / ".arc" / "eval"
    goldens_count = (
        len([p for p in goldens_dir.iterdir() if p.is_file()]) if goldens_dir.exists() else 0
    )
    eval_files = (
        [str(p.relative_to(ws)) for p in eval_dir.iterdir() if p.is_file()]
        if eval_dir.exists()
        else []
    )

    # Receipt status
    receipts_dir = ws / ".arc" / "receipts"
    receipt_count = (
        len([p for p in receipts_dir.iterdir() if p.suffix in {".json", ".jsonl", ".md"}])
        if receipts_dir.exists()
        else 0
    )

    summary_data = {
        "advisory": True,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "workspace": str(ws),
        "no_ai_judgment": True,
        "audit_events": {
            "total": audit_events.get("count", 0),
            "allowed": len(allowed),
            "denied": len(denied),
            "denied_commands": [
                {
                    "command": e.get("command", []),
                    "classification": e.get("classification"),
                    "reason": e.get("reason"),
                }
                for e in denied[:20]
            ],
        },
        "policies": {
            "count": len(policies),
            "names": [p.name for p in policies],
        },
        "eval": {
            "goldens_count": goldens_count,
            "eval_files": eval_files[:20],
        },
        "receipts": {
            "count": receipt_count,
        },
    }

    if format == "json" or json_output:
        _out(ok(summary_data), True)
        return

    # Markdown output
    lines: list[str] = [
        "<!-- ARC CI Summary — Advisory Only; No AI Judgment Claims -->",
        "",
        "# ARC CI Summary",
        "",
        f"> **Advisory only.** Generated at {summary_data['generated_at']}",
        f"> Workspace: `{summary_data['workspace']}`",
        "",
        "## Audit Events",
        "",
        f"- **Total events:** {summary_data['audit_events']['total']}",
        f"- **Allowed:** {summary_data['audit_events']['allowed']}",
        f"- **Denied:** {summary_data['audit_events']['denied']}",
    ]

    if summary_data["audit_events"]["denied_commands"]:
        lines.extend(
            [
                "",
                "### Denied Commands",
                "",
                "| Command | Classification | Reason |",
                "|---------|---------------|--------|",
            ]
        )
        for dc in summary_data["audit_events"]["denied_commands"]:
            cmd = (
                " ".join(str(p) for p in dc["command"])
                if isinstance(dc["command"], list)
                else str(dc["command"])
            )
            lines.append(
                f"| `{cmd[:80]}` | {dc.get('classification', '?')} | {dc.get('reason', '?')} |"
            )

    lines.extend(
        [
            "",
            "## Policies",
            "",
            f"- **Policy count:** {summary_data['policies']['count']}",
            f"- **Active policies:** {', '.join(summary_data['policies']['names'])}",
            "",
            "## Evaluation",
            "",
            f"- **Goldens found:** {summary_data['eval']['goldens_count']}",
            f"- **Eval files:** {len(summary_data['eval']['eval_files'])}",
            "",
            "## Receipts",
            "",
            f"- **Receipt count:** {summary_data['receipts']['count']}",
            "",
            "---",
            "",
            "_ARC CI guardrails (Phase 80 / R51) — deterministic, offline, advisory._",
        ]
    )

    from ._app import console

    console.print("\n".join(lines))


@ci_app.command("verify-audit")
def ci_verify_audit(
    audit_dir: str = typer.Option("", "--audit-dir", help="Path to sandbox audit directory"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Verify sandbox audit chain integrity using existing verifier."""
    _setup_logging(debug)

    from ..security.sandbox import verify_sandbox_audit

    target_dir = Path(audit_dir).expanduser().resolve() if audit_dir else None
    result = verify_sandbox_audit(audit_dir=target_dir)
    _out(ok(result), json_output)
    if not json_output:
        from ._app import console

        color = "green" if result.get("ok") else "red"
        status = "VERIFIED" if result.get("ok") else "FAILED"
        console.print(f"Sandbox audit chain: [bold {color}]{status}[/bold {color}]")
        console.print(f"  Chain: {result.get('chain', '?')}")
        console.print(f"  Reason: {result.get('reason', '?')}")
    if not result.get("ok"):
        raise typer.Exit(0)
