from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence

from ..adapters.base import CapabilityReport, RuntimeAdapter
from ..adapters.registry import default_registry

RuntimeId = Literal["swarmgraph", "langgraph", "crewai"]
KNOWN_RUNTIMES: tuple[RuntimeId, ...] = ("swarmgraph", "langgraph", "crewai")
AUTO_PRIORITY: tuple[RuntimeId, ...] = ("swarmgraph", "langgraph", "crewai")


class RuntimeRouterError(Exception):
    code = "RUNTIME_ROUTER_ERROR"


class UnknownRuntime(RuntimeRouterError):
    code = "UNKNOWN_RUNTIME"


class RuntimeNotRunnable(RuntimeRouterError):
    code = "RUNTIME_NOT_RUNNABLE"


class ComboNotImplemented(RuntimeRouterError):
    code = "COMBO_NOT_IMPLEMENTED"


@dataclass(frozen=True)
class RoutedRuntime:
    adapter: RuntimeAdapter
    report: CapabilityReport
    chosen_by: Literal["explicit", "auto"]


def list_runtimes(workspace: Path) -> list[CapabilityReport]:
    return [adapter.capability_report(workspace) for adapter in default_registry().all()]


def resolve(workspace: Path, runtime: str | Sequence[str] | None = "auto", allow_paid_calls: bool = False) -> RoutedRuntime:
    if runtime is None or runtime == "auto":
        return _resolve_auto(workspace, allow_paid_calls=allow_paid_calls)
    if isinstance(runtime, str):
        if runtime not in KNOWN_RUNTIMES:
            raise UnknownRuntime(f"Unknown runtime '{runtime}'. Known: {', '.join(KNOWN_RUNTIMES)}")
        adapter = default_registry().get(runtime)
        if adapter is None:
            raise UnknownRuntime(f"No adapter registered for '{runtime}'")
        report = adapter.capability_report(workspace)
        if not report.can_run:
            raise RuntimeNotRunnable(
                f"Runtime '{runtime}' is not runnable: {report.availability} ({report.reason or 'no detail'})"
            )
        return RoutedRuntime(adapter=adapter, report=report, chosen_by="explicit")
    raise ComboNotImplemented("Combo runtime selection is not implemented yet. Pass one runtime id or 'auto'.")


def _resolve_auto(workspace: Path, allow_paid_calls: bool) -> RoutedRuntime:
    registry = default_registry()
    skipped_paid: list[str] = []
    for runtime_id in AUTO_PRIORITY:
        adapter = registry.get(runtime_id)
        if adapter is None:
            continue
        report = adapter.capability_report(workspace)
        if report.can_run:
            if report.requires_paid_calls and not allow_paid_calls:
                skipped_paid.append(runtime_id)
                continue
            return RoutedRuntime(adapter=adapter, report=report, chosen_by="auto")
    if skipped_paid:
        raise RuntimeNotRunnable(
            "No runnable runtime detected under auto-selection. Skipped paid-call runtimes "
            f"(pass --allow-paid-calls to include): {', '.join(skipped_paid)}."
        )
    raise RuntimeNotRunnable("No runnable runtime detected. Set --runtime and verify dependencies/export targets.")
