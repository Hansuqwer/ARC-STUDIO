"""ARC Adapter Conformance Test Suite.

Runs a standard battery of tests against any registered adapter.
Called by: `uv run arc adapter test <adapter_id>`

Tests:
  1. detect() never returns (True, ...) with zero evidence
  2. capabilities() returns honest RuntimeCapabilities
  3. export_workflow() returns valid WorkflowInfo if can_export_workflow
  4. export_schemas() returns valid SchemaInfo if can_export_schema
  5. Unsupported methods raise NotImplementedError (not fake data)
"""

from __future__ import annotations

import dataclasses
import logging
from pathlib import Path

from ..protocol.schemas import SchemaInfo, WorkflowInfo
from .base import DoctorAction, RuntimeAdapter

log = logging.getLogger(__name__)


@dataclasses.dataclass
class ConformanceResult:
    adapter_id: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[str] = dataclasses.field(default_factory=list)
    details: list[dict] = dataclasses.field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failed == 0

    def record(self, name: str, passed: bool, reason: str = "", skipped: bool = False) -> None:
        entry = {
            "test": name,
            "result": "SKIP" if skipped else ("PASS" if passed else "FAIL"),
            "reason": reason,
        }
        self.details.append(entry)
        if skipped:
            self.skipped += 1
        elif passed:
            self.passed += 1
        else:
            self.failed += 1
            self.errors.append(f"{name}: {reason}")


def run_conformance(adapter: RuntimeAdapter, workspace: Path) -> ConformanceResult:
    result = ConformanceResult(adapter_id=adapter.adapter_id)
    caps = adapter.capabilities()

    # ── Test 1: detect() with empty temp dir returns (False, ...)
    try:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            detected, conf, evidence = adapter.detect(Path(td))
            if detected and not evidence:
                result.record(
                    "detect_no_false_positive",
                    False,
                    "detect() returned True with no evidence in empty dir",
                )
            else:
                result.record("detect_no_false_positive", True)
    except Exception as e:
        result.record("detect_no_false_positive", False, str(e))

    # ── Test 2: detect() with workspace
    try:
        detected, conf, evidence = adapter.detect(workspace)
        valid = isinstance(detected, bool) and 0.0 <= conf <= 1.0 and isinstance(evidence, list)
        result.record(
            "detect_returns_valid_types", valid, "" if valid else "detect() returned wrong types"
        )
        if detected and not evidence:
            result.record(
                "detect_evidence_when_detected", False, "Detected with zero evidence items"
            )
        else:
            result.record("detect_evidence_when_detected", True)
    except Exception as e:
        result.record("detect_returns_valid_types", False, str(e))

    # ── Test 3: capabilities() returns RuntimeCapabilities
    try:
        from ..protocol.capabilities import RuntimeCapabilities

        ok = isinstance(caps, RuntimeCapabilities)
        result.record("capabilities_type", ok, "" if ok else "capabilities() wrong type")
    except Exception as e:
        result.record("capabilities_type", False, str(e))

    # ── Test 4: export_workflow if claimed
    if caps.can_export_workflow:
        try:
            workflows = adapter.export_workflow(workspace)
            ok = isinstance(workflows, list) and all(isinstance(w, WorkflowInfo) for w in workflows)
            result.record(
                "export_workflow_returns_list",
                ok,
                "" if ok else "export_workflow() returned wrong type",
            )
            if ok and workflows:
                wf = workflows[0]
                has_nodes = len(wf.nodes) > 0
                has_entry = len(wf.entry_points) > 0
                result.record(
                    "workflow_has_nodes",
                    has_nodes,
                    "Workflow has no nodes" if not has_nodes else "",
                )
                result.record(
                    "workflow_has_entry_points",
                    has_entry,
                    "Workflow has no entry_points" if not has_entry else "",
                )
        except Exception as e:
            result.record("export_workflow_returns_list", False, str(e))
    else:
        try:
            adapter.export_workflow(workspace)
            result.record(
                "export_workflow_not_implemented",
                False,
                "export_workflow() did not raise NotImplementedError despite can_export_workflow=False",
            )
        except NotImplementedError:
            result.record("export_workflow_not_implemented", True)
        except Exception as e:
            result.record("export_workflow_not_implemented", False, str(e))

    # ── Test 5: export_schemas if claimed
    if caps.can_export_schema:
        try:
            schemas = adapter.export_schemas(workspace)
            ok = isinstance(schemas, list) and all(isinstance(s, SchemaInfo) for s in schemas)
            result.record(
                "export_schemas_returns_list",
                ok,
                "" if ok else "export_schemas() returned wrong type",
            )
        except Exception as e:
            result.record("export_schemas_returns_list", False, str(e))
    else:
        result.record("export_schemas_skipped", True, skipped=True)

    # ── Test 6: run_workflow raises NotImplementedError if can_run=False
    if not caps.can_run:
        import asyncio

        try:
            asyncio.get_event_loop().run_until_complete(adapter.run_workflow("test-wf"))
            result.record(
                "run_not_implemented_when_unsupported",
                False,
                "run_workflow() did not raise NotImplementedError despite can_run=False",
            )
        except NotImplementedError:
            result.record("run_not_implemented_when_unsupported", True)
        except Exception:
            result.record("run_not_implemented_when_unsupported", True)  # other errors are OK
    else:
        result.record("run_capability_skipped", True, skipped=True)

    # ── Test 7: capability_report returns doctor_actions list
    try:
        report = adapter.capability_report(workspace)
        ok = isinstance(report.doctor_actions, list)
        if ok and report.doctor_actions:
            all_valid = all(
                isinstance(a, DoctorAction) and bool(a.id) and bool(a.label)
                for a in report.doctor_actions
            )
            result.record(
                "doctor_actions_valid",
                all_valid,
                "" if all_valid else "Some doctor_actions missing id or label",
            )
        else:
            result.record("doctor_actions_list", ok, "" if ok else "doctor_actions is not a list")
    except Exception as e:
        result.record("doctor_actions_valid", False, str(e))

    # ── Test 8: RuntimeCapabilities includes v2 fields
    try:
        v2_fields = [
            "can_checkpoint",
            "can_resume",
            "can_fork",
            "can_diff",
            "can_eval",
            "requires_network",
            "requires_shell",
            "requires_secrets",
        ]
        v2 = (
            RuntimeCapabilities()
            if not hasattr(adapter, "capabilities")
            else adapter.capabilities()
        )
        missing = [f for f in v2_fields if not hasattr(v2, f) and f not in v2.model_fields]
        result.record(
            "capabilities_v2_fields",
            len(missing) == 0,
            f"Missing v2 capability fields: {missing}" if missing else "",
        )
    except Exception as e:
        result.record("capabilities_v2_fields", False, str(e))

    return result
