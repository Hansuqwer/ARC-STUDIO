"""LangGraph replay capability detection (Phase 28 / R21)."""

from __future__ import annotations

import logging
import pathlib
from typing import Any, Optional

from agent_runtime_cockpit.schemas.replay_capability import ReplayCapability
from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

from .loader import LangGraphLoadError, load_graph

log = logging.getLogger(__name__)


def detect_checkpointer(graph: Any) -> tuple[bool, Optional[str]]:
    """Detect if a LangGraph graph has a checkpointer configured.

    Args:
        graph: Loaded LangGraph graph object

    Returns:
        Tuple of (has_checkpointer, checkpointer_type)

    """
    try:
        # Check if graph has a checkpointer attribute
        if hasattr(graph, "checkpointer"):
            checkpointer = graph.checkpointer
            if checkpointer is not None:
                # Get checkpointer type name
                checkpointer_type = type(checkpointer).__name__
                log.info(f"Detected checkpointer: {checkpointer_type}")
                return True, checkpointer_type

        # No checkpointer found
        return False, None
    except Exception as e:
        log.warning(f"Error detecting checkpointer: {e}")
        return False, None


def detect_thread_id_from_run(run_id: str, workspace: pathlib.Path) -> tuple[bool, Optional[str]]:
    """Detect thread ID from a stored run.

    Args:
        run_id: Run ID to analyze
        workspace: Workspace path

    Returns:
        Tuple of (thread_id_detected, thread_id)

    """
    try:
        # Load run from trace store
        store = JsonlTraceStore(workspace / ".arc" / "traces")
        run_record = store.load(run_id)

        if run_record is None:
            log.warning(f"Run not found: {run_id}")
            return False, None

        # Check if run has thread_id in metadata or events
        # LangGraph runner creates thread IDs like "th-{run_id}"
        expected_thread_id = f"th-{run_id}"

        # Check events for thread_id references
        for event in run_record.events:
            event_data = event.model_dump() if hasattr(event, "model_dump") else event
            if isinstance(event_data, dict):
                # Check if thread_id appears in event data
                if "thread_id" in str(event_data):
                    return True, expected_thread_id

        # Assume thread ID was used (LangGraph runner always creates one)
        return True, expected_thread_id

    except Exception as e:
        log.warning(f"Error detecting thread ID from run: {e}")
        return False, None


def analyze_run_replay_capability(
    run_id: str,
    workspace: pathlib.Path,
    graph_id: Optional[str] = None,
) -> ReplayCapability:
    """Analyze replay capability for a LangGraph run.

    Args:
        run_id: Run ID to analyze
        workspace: Workspace path
        graph_id: Optional graph ID (will use default if not provided)

    Returns:
        ReplayCapability analysis

    """
    capability = ReplayCapability(
        run_id=run_id,
        runtime="langgraph",
        can_replay_trace=True,  # Traces can always be inspected
    )

    try:
        # Load the graph to check for checkpointer
        graph = load_graph(workspace, graph_id)

        # Detect checkpointer
        has_checkpointer, checkpointer_type = detect_checkpointer(graph)
        capability.has_checkpointer = has_checkpointer
        capability.checkpointer_type = checkpointer_type

        # Detect thread ID from run
        thread_id_detected, thread_id = detect_thread_id_from_run(run_id, workspace)
        capability.thread_id_detected = thread_id_detected
        capability.thread_id = thread_id

        # Determine if checkpoint resume is possible
        if has_checkpointer and thread_id_detected:
            capability.can_resume_checkpoint = True
            capability.requires_thread_id = True
            capability.determinism_level = "simulated"
            capability.add_warning(
                "Checkpoint resume is possible but determinism depends on checkpointer implementation"
            )
        elif has_checkpointer and not thread_id_detected:
            capability.can_resume_checkpoint = False
            capability.requires_thread_id = True
            capability.determinism_level = "inspect_only"
            capability.add_warning("Checkpointer detected but no thread ID found - cannot resume")
        else:
            capability.can_resume_checkpoint = False
            capability.determinism_level = "inspect_only"
            capability.add_warning("No checkpointer detected - only trace inspection available")

        # Side effects detection (conservative - assume not wrapped unless proven)
        # This would require deeper analysis of the graph nodes
        capability.side_effects_wrapped = False
        capability.add_warning(
            "Side effects may not be wrapped - replay may cause duplicate actions"
        )

        # Generate report
        capability.report = capability.generate_report()

    except LangGraphLoadError as e:
        log.error(f"Failed to load graph for replay analysis: {e}")
        capability.add_warning(f"Could not load graph: {e}")
        capability.determinism_level = "unsafe"
        capability.report = capability.generate_report()

    except Exception as e:
        log.error(f"Error analyzing replay capability: {e}")
        capability.add_warning(f"Analysis error: {e}")
        capability.determinism_level = "unsafe"
        capability.report = capability.generate_report()

    return capability


def analyze_graph_replay_capability(
    workspace: pathlib.Path,
    graph_id: Optional[str] = None,
) -> ReplayCapability:
    """Analyze replay capability for a LangGraph graph (without a specific run).

    Args:
        workspace: Workspace path
        graph_id: Optional graph ID (will use default if not provided)

    Returns:
        ReplayCapability analysis for the graph

    """
    capability = ReplayCapability(
        run_id="N/A",
        runtime="langgraph",
        can_replay_trace=False,  # No trace to replay
    )

    try:
        # Load the graph to check for checkpointer
        graph = load_graph(workspace, graph_id)

        # Detect checkpointer
        has_checkpointer, checkpointer_type = detect_checkpointer(graph)
        capability.has_checkpointer = has_checkpointer
        capability.checkpointer_type = checkpointer_type

        # Determine potential for checkpoint resume
        if has_checkpointer:
            capability.can_resume_checkpoint = True
            capability.requires_thread_id = True
            capability.determinism_level = "simulated"
            capability.add_warning("Graph has checkpointer - runs will be resumable with thread ID")
        else:
            capability.can_resume_checkpoint = False
            capability.determinism_level = "inspect_only"
            capability.add_warning("No checkpointer configured - runs will be inspect-only")

        # Side effects detection (conservative)
        capability.side_effects_wrapped = False
        capability.add_warning(
            "Side effects wrapping cannot be determined without runtime analysis"
        )

        # Generate report
        capability.report = capability.generate_report()

    except LangGraphLoadError as e:
        log.error(f"Failed to load graph for replay analysis: {e}")
        capability.add_warning(f"Could not load graph: {e}")
        capability.determinism_level = "unsafe"
        capability.report = capability.generate_report()

    except Exception as e:
        log.error(f"Error analyzing replay capability: {e}")
        capability.add_warning(f"Analysis error: {e}")
        capability.determinism_level = "unsafe"
        capability.report = capability.generate_report()

    return capability
