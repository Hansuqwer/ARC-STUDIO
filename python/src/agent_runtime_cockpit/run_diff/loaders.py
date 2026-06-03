"""Loaders for Run Diff - read-only artifact loading."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional, Union

log = logging.getLogger(__name__)


class LoadError:
    def __init__(self, code: str, message: str, path: Optional[str] = None) -> None:
        self.code = code
        self.message = message
        self.path = path


class LoadResult:
    def __init__(
        self,
        data: Any = None,
        errors: Optional[list[LoadError]] = None,
        warnings: Optional[list[str]] = None,
    ) -> None:
        self.data = data
        self.errors = errors or []
        self.warnings = warnings or []

    @property
    def ok(self) -> bool:
        return self.data is not None and len(self.errors) == 0

    def add_error(self, code: str, message: str, path: Optional[str] = None) -> None:
        self.errors.append(LoadError(code, message, path))

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


def load_ir_from_path(path: Union[str, Path]) -> LoadResult:
    p = Path(path).expanduser().resolve()
    result = LoadResult()
    if not p.exists():
        result.add_error("INVALID_INPUT", f"IR file not found: {p}", str(p))
        return result
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as exc:
        result.add_error("INTERNAL_ERROR", f"Failed to read file: {exc}", str(p))
        return result
    try:
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph = from_json(text)
        result.data = graph
    except Exception as exc:
        result.add_warning(f"IR parse failed, loading raw dict: {exc}")
        try:
            raw = json.loads(text)
            result.data = raw
        except json.JSONDecodeError:
            result.add_error("INVALID_INPUT", f"Invalid JSON: {exc}", str(p))
    return result


def load_ir_from_json(json_str: str) -> LoadResult:
    result = LoadResult()
    try:
        from agent_runtime_cockpit.swarmgraph_ir import from_json

        graph = from_json(json_str)
        result.data = graph
    except Exception as exc:
        result.add_error("INVALID_INPUT", f"Invalid IR JSON: {exc}")
        try:
            raw = json.loads(json_str)
            result.data = raw
            result.add_warning(f"Fallback to raw dict: {exc}")
        except json.JSONDecodeError:
            pass
    return result


def load_policy_from_path(path: Union[str, Path]) -> LoadResult:
    p = Path(path).expanduser().resolve()
    result = LoadResult()
    if not p.exists():
        result.add_error("INVALID_INPUT", f"Policy file not found: {p}", str(p))
        return result
    try:
        from agent_runtime_cockpit.security.policy_linter import PolicyReport

        data = json.loads(p.read_text(encoding="utf-8"))
        report = PolicyReport.model_validate(data)
        result.data = report
    except json.JSONDecodeError as exc:
        result.add_error("INVALID_INPUT", f"Invalid JSON: {exc}", str(p))
    except Exception as exc:
        result.add_error("INTERNAL_ERROR", f"Failed to parse policy: {exc}", str(p))
        try:
            result.data = json.loads(p.read_text())
            result.add_warning(f"Fallback to raw dict: {exc}")
        except Exception:
            pass
    return result


def load_run_from_store(run_id: str, trace_dir: Optional[Path] = None) -> LoadResult:
    result = LoadResult()
    ws = trace_dir or Path.cwd()
    try:
        from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

        store = JsonlTraceStore(ws / ".arc" / "traces")
        record = store.load(run_id)
        if record is None:
            result.add_error("RUN_NOT_FOUND", f"Run not found: {run_id}")
            return result
        result.data = record
    except Exception as exc:
        result.add_error("INTERNAL_ERROR", f"Failed to load run: {exc}")
    return result


def load_run_from_json(path: Union[str, Path]) -> LoadResult:
    p = Path(path).expanduser().resolve()
    result = LoadResult()
    if not p.exists():
        result.add_error("INVALID_INPUT", f"Run file not found: {p}", str(p))
        return result
    try:
        from agent_runtime_cockpit.protocol.schemas import RunRecord

        data = json.loads(p.read_text(encoding="utf-8"))
        record = RunRecord.model_validate(data)
        result.data = record
    except json.JSONDecodeError as exc:
        result.add_error("INVALID_INPUT", f"Invalid JSON: {exc}", str(p))
    except Exception as exc:
        result.add_error("INTERNAL_ERROR", f"Failed to parse run: {exc}", str(p))
        try:
            result.data = json.loads(p.read_text())
            result.add_warning(f"Fallback to raw dict: {exc}")
        except Exception:
            pass
    return result


def load_jsonl_events(path: Union[str, Path]) -> LoadResult:
    p = Path(path).expanduser().resolve()
    result = LoadResult(warnings=[])
    if not p.exists():
        result.add_error("INVALID_INPUT", f"JSONL file not found: {p}", str(p))
        return result
    events = []
    corrupt_lines = 0
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                corrupt_lines += 1
                result.add_warning(f"Corrupt JSONL line {i + 1}: skipping")
    except Exception as exc:
        result.add_error("INTERNAL_ERROR", f"Failed to read JSONL: {exc}", str(p))
        return result
    if corrupt_lines and not events:
        result.add_error("INVALID_INPUT", f"All {corrupt_lines} JSONL lines corrupt", str(p))
        return result
    result.data = events
    if corrupt_lines:
        result.add_warning(f"Skipped {corrupt_lines} corrupt JSONL lines")
    return result


def load_simulation_from_path(path: Union[str, Path]) -> LoadResult:
    p = Path(path).expanduser().resolve()
    result = LoadResult()
    if not p.exists():
        result.add_error("INVALID_INPUT", f"Simulation file not found: {p}", str(p))
        return result
    try:
        from agent_runtime_cockpit.simulation.models import SimulationReport

        data = json.loads(p.read_text(encoding="utf-8"))
        report = SimulationReport.model_validate(data)
        result.data = report
    except json.JSONDecodeError as exc:
        result.add_error("INVALID_INPUT", f"Invalid JSON: {exc}", str(p))
    except Exception as exc:
        result.add_error("INTERNAL_ERROR", f"Failed to parse simulation: {exc}", str(p))
        try:
            result.data = json.loads(p.read_text())
            result.add_warning(f"Fallback: {exc}")
        except Exception:
            pass
    return result


def load_capability_card_from_path(path: Union[str, Path]) -> LoadResult:
    p = Path(path).expanduser().resolve()
    result = LoadResult()
    if not p.exists():
        result.add_error("INVALID_INPUT", f"Capability card not found: {p}", str(p))
        return result
    try:
        from agent_runtime_cockpit.capabilities.models import CapabilityCard

        data = json.loads(p.read_text(encoding="utf-8"))
        card = CapabilityCard.model_validate(data)
        result.data = card
    except json.JSONDecodeError as exc:
        result.add_error("INVALID_INPUT", f"Invalid JSON: {exc}", str(p))
    except Exception as exc:
        result.add_error("INTERNAL_ERROR", f"Failed to parse capability card: {exc}", str(p))
        try:
            result.data = json.loads(p.read_text())
            result.add_warning(f"Fallback: {exc}")
        except Exception:
            pass
    return result


def load_any(path: Union[str, Path]) -> LoadResult:
    p = Path(path).expanduser().resolve()
    result = LoadResult()
    if not p.exists():
        result.add_error("INVALID_INPUT", f"File not found: {p}", str(p))
        return result
    try:
        text = p.read_text(encoding="utf-8")
        data = json.loads(text)
    except json.JSONDecodeError:
        result.add_error("INVALID_INPUT", f"Invalid JSON: {p}", str(p))
        return result
    if isinstance(data, dict):
        if data.get("ir_version"):
            return load_ir_from_path(p)
        if data.get("schema_version") == 2 and data.get("events"):
            return load_run_from_json(p)
        if data.get("workflow_id") and data.get("issues") is not None:
            return load_policy_from_path(p)
        if data.get("config"):
            return load_simulation_from_path(p)
        if data.get("capabilities"):
            return load_capability_card_from_path(p)
        if isinstance(data.get("nodes"), list) and isinstance(data.get("edges"), list):
            return load_ir_from_path(p)
    result.data = data
    result.add_warning("Unknown artifact type")
    return result
