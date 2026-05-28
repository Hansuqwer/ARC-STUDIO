"""Review CLI commands for trace-aware review mode (Phase 74).

Provides ``arc review summarize`` to collect available provenance from
existing producers. Missing/absent producers render explicit unknown
states - never fabricated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..protocol.event_envelope import ok
from ..security.review import (
    HunkProvenance,
    ProvenanceSource,
    build_review_summary,
)
from ._helpers import DEBUG_FLAG, JSON_FLAG, _out, _setup_logging
from ._subapps import review_app


@review_app.command(
    "summarize",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def review_summarize(
    ctx: typer.Context,
    run_id: Optional[str] = typer.Option(None, "--run-id", help="Run ID to summarize"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Summarize available review evidence for a run or workspace.

    Reports provenance from existing producers. Missing producers render
    explicit absent states - no fabricated data.
    """
    _setup_logging(debug)
    command = list(ctx.args)

    # Build provenance from available producers
    provenance_items: list[HunkProvenance] = []

    # If a command was provided, classify it for plan/review context
    classification = None
    if command:
        from ..security.sandbox import SandboxPolicy, decide

        ws = Path.cwd()
        policy = SandboxPolicy(workspace_root=ws)
        try:
            decision = decide(command, policy)
            classification = decision.classification.value if decision else "unknown"
            provenance_items.append(
                HunkProvenance(
                    file_path="(command)",
                    source=ProvenanceSource.PLAN_STEP,
                    classification=classification,
                    policy_name=policy.name,
                    decision_allowed=decision.allowed if decision else None,
                    reason=decision.reason if decision else None,
                    detail=" ".join(command),
                )
            )
        except Exception:
            provenance_items.append(
                HunkProvenance(
                    file_path="(command)",
                    source=ProvenanceSource.UNKNOWN,
                    detail="classification unavailable",
                )
            )

    # Determine which producers are available vs missing
    available_producers: list[str] = []
    missing_producers: list[str] = []

    # Check sandbox audit
    try:
        from ..security.sandbox import list_sandbox_audit_events

        audit_events = list_sandbox_audit_events()
        if audit_events.get("events"):
            available_producers.append("sandbox_audit")
            for evt in audit_events["events"][:10]:
                audit_id = evt.get("audit_id", evt.get("id", ""))
                cmd = evt.get("command", [])
                provenance_items.append(
                    HunkProvenance(
                        file_path=str(evt.get("cwd", "")) if evt.get("cwd") else "(audit)",
                        source=ProvenanceSource.AUDIT_RECORD,
                        source_audit_id=str(audit_id) if audit_id else None,
                        classification=evt.get("classification"),
                        decision_allowed=evt.get("allowed"),
                        detail=" ".join(cmd) if isinstance(cmd, list) else str(cmd),
                    )
                )
        else:
            missing_producers.append("sandbox_audit")
    except Exception:
        missing_producers.append("sandbox_audit")

    # Check HITL store
    try:
        from ..audit.hitl_sqlite_store import HitlSqliteStore

        store = HitlSqliteStore()
        hitl_count = 0
        prompts = store.list_prompts(include_expired=True) if store.db_path.exists() else []
        for prompt in prompts:
            if hitl_count >= 5:
                break
            provenance_items.append(
                HunkProvenance(
                    file_path="(hitl)",
                    source=ProvenanceSource.HITL_DECISION,
                    source_run_id=prompt.run_id if hasattr(prompt, "run_id") else None,
                    source_approval_id=prompt.id if hasattr(prompt, "id") else None,
                    detail=prompt.prompt_text[:200] if hasattr(prompt, "prompt_text") else "",
                )
            )
            hitl_count += 1
        if hitl_count > 0:
            available_producers.append("hitl")
        else:
            missing_producers.append("hitl")
    except Exception:
        missing_producers.append("hitl")

    # Check eval artifacts
    try:
        from ..evals.artifact import EvalArtifactStore

        eval_store = EvalArtifactStore(Path.cwd())
        run_ids = eval_store.list_run_ids() if hasattr(eval_store, "list_run_ids") else []
        if run_ids:
            available_producers.append("eval")
        else:
            missing_producers.append("eval")
    except Exception:
        missing_producers.append("eval")

    # Build summary
    header = build_review_summary(
        run_id=run_id or "(workspace)",
        provenance_items=provenance_items,
        available_producers=available_producers,
        missing_producers=missing_producers,
        approval_count=sum(
            1 for p in provenance_items if p.source == ProvenanceSource.HITL_DECISION
        ),
        sandbox_decision_count=sum(
            1 for p in provenance_items if p.source == ProvenanceSource.AUDIT_RECORD
        ),
    )

    _out(ok(header.model_dump(mode="json")), json_output)
