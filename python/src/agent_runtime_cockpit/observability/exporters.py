"""Main export pipeline: trace → ArcTraceExport → local JSON file.

Pipeline:
  1. load_trace_file()
  2. map_events_to_spans()   (OTel mapping)
  3. attach IR/policy/MCP metadata if paths provided
  4. apply format-specific postprocessing
  5. redact resource attributes
  6. compute export_hash
  7. validate
  8. write to output path

No network, no model calls, no tool execution, no source mutation.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .hashing import export_hash as _hash
from .loaders import LoadedTrace, load_ir_json, load_policy_json, load_trace_file
from .models import (
    ArcTraceExport,
    ExportSource,
    ExportWarning,
    ObservabilityExportConfig,
    RedactionSummary,
)
from .otel_mapping import map_events_to_spans
from .redaction import redact_attributes

log = logging.getLogger(__name__)


def _build_resource(cfg: ObservabilityExportConfig, trace: LoadedTrace) -> dict:
    resource = {
        "service.name": "arc-studio",
        "arc.runtime.name": trace.runtime or "",
        "arc.workflow_id": trace.workflow_id or "",
        "arc.schema_version": str(cfg.schema_version),
    }
    resource.update(cfg.resource_attributes)
    if cfg.redact_secrets:
        resource, _ = redact_attributes(resource)
    return resource


def _attach_ir_metadata(
    export: ArcTraceExport,
    ir_path: Optional[str],
    cfg: ObservabilityExportConfig,
    warnings: list[ExportWarning],
) -> int:
    """Attach IR graph metadata as a span event on the root span. Returns tokens redacted."""
    if not cfg.include_ir or not ir_path:
        return 0
    ir = load_ir_json(ir_path)
    if ir is None:
        warnings.append(
            ExportWarning(code="ir_load_failed", message=f"Could not load IR: {ir_path}")
        )
        return 0
    from .models import ArcSpanEvent

    tokens = 0
    attrs = {
        "arc.ir.graph_id": ir.get("id", ""),
        "arc.ir.graph_hash": ir.get("graph_hash", ""),
        "arc.ir.runtime": ir.get("runtime", ""),
        "arc.ir.node_count": len(ir.get("nodes", [])),
        "arc.ir.risk_level": (ir.get("risk") or {}).get("level", ""),
    }
    if cfg.redact_secrets:
        attrs, tokens = redact_attributes(attrs)
    if export.spans:
        export.spans[0].events.append(
            ArcSpanEvent(
                name="arc.ir.graph",
                attributes=attrs,
            )
        )
    export.source.ir_hash = ir.get("graph_hash")
    return tokens


def _attach_policy_metadata(
    export: ArcTraceExport,
    policy_path: Optional[str],
    cfg: ObservabilityExportConfig,
    warnings: list[ExportWarning],
) -> int:
    if not cfg.include_policy or not policy_path:
        return 0
    policy = load_policy_json(policy_path)
    if policy is None:
        warnings.append(
            ExportWarning(
                code="policy_load_failed", message=f"Could not load policy: {policy_path}"
            )
        )
        return 0
    from .models import ArcSpanEvent

    tokens = 0
    attrs = {
        "arc.policy.can_run": policy.get("can_run", True),
        "arc.policy.risk_level": policy.get("risk_level", "low"),
        "arc.policy.issue_count": len(policy.get("issues", [])),
        "arc.policy.suggested_consensus": policy.get("suggested_consensus", ""),
    }
    if cfg.redact_secrets:
        attrs, tokens = redact_attributes(attrs)
    if export.spans:
        export.spans[0].events.append(
            ArcSpanEvent(
                name="arc.policy.evaluate",
                attributes=attrs,
            )
        )
    return tokens


def export_trace(
    trace_file: str,
    *,
    cfg: Optional[ObservabilityExportConfig] = None,
    ir_file: Optional[str] = None,
    policy_file: Optional[str] = None,
    out: Optional[str] = None,
) -> ArcTraceExport:
    """Full export pipeline. Returns ArcTraceExport; optionally writes to out path.

    Never mutates source files. Never transmits data. Fail-closed on redaction errors.
    """
    if cfg is None:
        cfg = ObservabilityExportConfig()

    # Step 1: Load
    trace = load_trace_file(trace_file)

    # Step 2: Map events → spans
    spans, map_warnings, tokens_redacted = map_events_to_spans(trace, cfg)

    # Step 3: Build resource
    resource = _build_resource(cfg, trace)

    # Step 4: Assemble export
    warnings: list[ExportWarning] = list(map_warnings)
    if trace.skipped_lines:
        warnings.append(
            ExportWarning(
                code="corrupt_lines_skipped",
                message=f"Skipped {trace.skipped_lines} corrupt JSONL lines",
            )
        )

    source = ExportSource(
        run_id=trace.run_id,
        trace_file=trace_file,
    )

    export = ArcTraceExport(
        export_id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        format=cfg.format,
        source=source,
        resource=resource,
        spans=spans,
        warnings=warnings,
        redaction_summary=RedactionSummary(tokens_redacted=tokens_redacted),
    )

    # Step 5: Attach IR and policy metadata
    tokens_redacted += _attach_ir_metadata(export, ir_file, cfg, warnings)
    tokens_redacted += _attach_policy_metadata(export, policy_file, cfg, warnings)
    export.redaction_summary.tokens_redacted = tokens_redacted

    # Step 6: OpenInference post-processing
    if cfg.format == "openinference-json":
        from .openinference_mapping import apply_openinference_format

        export = apply_openinference_format(export)

    # Step 7: Compute hash (after all mutations, before writing)
    d = json.loads(export.model_dump_json())
    export.export_hash = _hash(d)

    # Step 8: Write to file if requested
    if out:
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(export.model_dump_json(indent=2), encoding="utf-8")
        log.info("Wrote export to %s", out_path)

    return export
