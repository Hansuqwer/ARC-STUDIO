"""Tests for LangGraph replay capability detection (Phase 28 / R21)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


from agent_runtime_cockpit.adapters.langgraph.replay_detector import (
    analyze_graph_replay_capability,
    analyze_run_replay_capability,
    detect_checkpointer,
    detect_thread_id_from_run,
)
from agent_runtime_cockpit.schemas.replay_capability import ReplayCapability


# ── ReplayCapability Model Tests ──────────────────────────────────────


def test_replay_capability_creation():
    """Test ReplayCapability model creation with defaults."""
    capability = ReplayCapability(run_id="test_run", runtime="langgraph")

    assert capability.run_id == "test_run"
    assert capability.runtime == "langgraph"
    assert capability.can_replay_trace is True
    assert capability.can_resume_checkpoint is False
    assert capability.requires_thread_id is False
    assert capability.side_effects_wrapped is False
    assert capability.determinism_level == "inspect_only"
    assert capability.has_checkpointer is False
    assert capability.checkpointer_type is None
    assert capability.warnings == []


def test_replay_capability_is_resumable():
    """Test is_resumable() method."""
    # Not resumable (no checkpointer)
    capability = ReplayCapability(run_id="test", runtime="langgraph")
    assert not capability.is_resumable()

    # Not resumable (checkpointer but can_resume_checkpoint is False)
    capability.has_checkpointer = True
    assert not capability.is_resumable()

    # Resumable (both flags set)
    capability.can_resume_checkpoint = True
    assert capability.is_resumable()


def test_replay_capability_is_safe_to_replay():
    """Test is_safe_to_replay() method."""
    capability = ReplayCapability(run_id="test", runtime="langgraph")

    # Not safe (side effects not wrapped, not exact)
    assert not capability.is_safe_to_replay()

    # Safe (side effects wrapped)
    capability.side_effects_wrapped = True
    assert capability.is_safe_to_replay()

    # Safe (exact determinism)
    capability.side_effects_wrapped = False
    capability.determinism_level = "exact"
    assert capability.is_safe_to_replay()


def test_replay_capability_get_capability_summary():
    """Test get_capability_summary() method."""
    capability = ReplayCapability(run_id="test", runtime="langgraph")

    # Inspect-only
    assert capability.get_capability_summary() == "Inspect-only (no checkpoint resume)"

    # Resumable with safe replay
    capability.can_resume_checkpoint = True
    capability.has_checkpointer = True
    capability.side_effects_wrapped = True
    assert capability.get_capability_summary() == "Resumable with safe replay"

    # Resumable but may have side effects
    capability.side_effects_wrapped = False
    assert capability.get_capability_summary() == "Resumable but may have side effects"


def test_replay_capability_add_warning():
    """Test add_warning() method."""
    capability = ReplayCapability(run_id="test", runtime="langgraph")

    assert len(capability.warnings) == 0

    capability.add_warning("Test warning 1")
    assert len(capability.warnings) == 1
    assert "Test warning 1" in capability.warnings

    # Adding same warning again should not duplicate
    capability.add_warning("Test warning 1")
    assert len(capability.warnings) == 1

    capability.add_warning("Test warning 2")
    assert len(capability.warnings) == 2


def test_replay_capability_generate_report():
    """Test generate_report() method."""
    capability = ReplayCapability(
        run_id="test_run_123",
        runtime="langgraph",
        has_checkpointer=True,
        checkpointer_type="MemorySaver",
        thread_id_detected=True,
        thread_id="th-test_run_123",
    )
    capability.add_warning("Test warning")

    report = capability.generate_report()

    assert "test_run_123" in report
    assert "langgraph" in report
    assert "MemorySaver" in report
    assert "th-test_run_123" in report
    assert "Test warning" in report
    assert "✓" in report or "✗" in report


# ── Checkpointer Detection Tests ──────────────────────────────────────


def test_detect_checkpointer_with_checkpointer():
    """Test detecting a graph with a checkpointer."""
    # Mock graph with checkpointer
    mock_graph = MagicMock()
    mock_checkpointer = MagicMock()
    mock_checkpointer.__class__.__name__ = "MemorySaver"
    mock_graph.checkpointer = mock_checkpointer

    has_checkpointer, checkpointer_type = detect_checkpointer(mock_graph)

    assert has_checkpointer is True
    assert checkpointer_type == "MemorySaver"


def test_detect_checkpointer_without_checkpointer():
    """Test detecting a graph without a checkpointer."""
    # Mock graph without checkpointer
    mock_graph = MagicMock()
    mock_graph.checkpointer = None

    has_checkpointer, checkpointer_type = detect_checkpointer(mock_graph)

    assert has_checkpointer is False
    assert checkpointer_type is None


def test_detect_checkpointer_no_attribute():
    """Test detecting a graph that doesn't have checkpointer attribute."""
    # Mock graph without checkpointer attribute
    mock_graph = MagicMock(spec=[])  # No attributes

    has_checkpointer, checkpointer_type = detect_checkpointer(mock_graph)

    assert has_checkpointer is False
    assert checkpointer_type is None


def test_detect_checkpointer_different_types():
    """Test detecting different checkpointer types."""
    checkpointer_types = ["MemorySaver", "SqliteSaver", "PostgresSaver"]

    for cp_type in checkpointer_types:
        mock_graph = MagicMock()
        mock_checkpointer = MagicMock()
        mock_checkpointer.__class__.__name__ = cp_type
        mock_graph.checkpointer = mock_checkpointer

        has_checkpointer, checkpointer_type = detect_checkpointer(mock_graph)

        assert has_checkpointer is True
        assert checkpointer_type == cp_type


# ── Thread ID Detection Tests ─────────────────────────────────────────


def test_detect_thread_id_from_run_with_thread_id():
    """Test detecting thread ID from a run that has one."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        run_id = "test_run_123"

        # Mock run record with thread ID in events
        mock_run_record = MagicMock()
        mock_run_record.id = run_id
        mock_event = MagicMock()
        mock_event.model_dump.return_value = {"thread_id": f"th-{run_id}"}
        mock_run_record.events = [mock_event]

        with patch(
            "agent_runtime_cockpit.adapters.langgraph.replay_detector.JsonlTraceStore"
        ) as mock_store_class:
            mock_store = MagicMock()
            mock_store.load.return_value = mock_run_record
            mock_store_class.return_value = mock_store

            thread_id_detected, thread_id = detect_thread_id_from_run(run_id, workspace)

            assert thread_id_detected is True
            assert thread_id == f"th-{run_id}"


def test_detect_thread_id_from_run_without_thread_id():
    """Test detecting thread ID from a run that doesn't have one."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        run_id = "test_run_123"

        # Mock run record without thread ID in events
        mock_run_record = MagicMock()
        mock_run_record.id = run_id
        mock_event = MagicMock()
        mock_event.model_dump.return_value = {"some_field": "value"}
        mock_run_record.events = [mock_event]

        with patch(
            "agent_runtime_cockpit.adapters.langgraph.replay_detector.JsonlTraceStore"
        ) as mock_store_class:
            mock_store = MagicMock()
            mock_store.load.return_value = mock_run_record
            mock_store_class.return_value = mock_store

            thread_id_detected, thread_id = detect_thread_id_from_run(run_id, workspace)

            # Should still detect thread ID (assumes LangGraph runner creates one)
            assert thread_id_detected is True
            assert thread_id == f"th-{run_id}"


def test_detect_thread_id_from_run_not_found():
    """Test detecting thread ID from a non-existent run."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        run_id = "nonexistent_run"

        with patch(
            "agent_runtime_cockpit.adapters.langgraph.replay_detector.JsonlTraceStore"
        ) as mock_store_class:
            mock_store = MagicMock()
            mock_store.load.return_value = None
            mock_store_class.return_value = mock_store

            thread_id_detected, thread_id = detect_thread_id_from_run(run_id, workspace)

            assert thread_id_detected is False
            assert thread_id is None


# ── Full Analysis Tests ───────────────────────────────────────────────


def test_analyze_run_replay_capability_resumable():
    """Test analyzing a run with checkpointer and thread ID (resumable)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        run_id = "test_run_123"

        # Mock graph with checkpointer
        mock_graph = MagicMock()
        mock_checkpointer = MagicMock()
        mock_checkpointer.__class__.__name__ = "MemorySaver"
        mock_graph.checkpointer = mock_checkpointer

        # Mock run record
        mock_run_record = MagicMock()
        mock_run_record.id = run_id
        mock_event = MagicMock()
        mock_event.model_dump.return_value = {"thread_id": f"th-{run_id}"}
        mock_run_record.events = [mock_event]

        with (
            patch(
                "agent_runtime_cockpit.adapters.langgraph.replay_detector.load_graph"
            ) as mock_load_graph,
            patch(
                "agent_runtime_cockpit.adapters.langgraph.replay_detector.JsonlTraceStore"
            ) as mock_store_class,
        ):
            mock_load_graph.return_value = mock_graph
            mock_store = MagicMock()
            mock_store.load.return_value = mock_run_record
            mock_store_class.return_value = mock_store

            capability = analyze_run_replay_capability(run_id, workspace)

            assert capability.run_id == run_id
            assert capability.runtime == "langgraph"
            assert capability.can_replay_trace is True
            assert capability.can_resume_checkpoint is True
            assert capability.requires_thread_id is True
            assert capability.has_checkpointer is True
            assert capability.checkpointer_type == "MemorySaver"
            assert capability.thread_id_detected is True
            assert capability.determinism_level == "simulated"
            assert len(capability.warnings) > 0


def test_analyze_run_replay_capability_inspect_only():
    """Test analyzing a run without checkpointer (inspect-only)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        run_id = "test_run_123"

        # Mock graph without checkpointer
        mock_graph = MagicMock()
        mock_graph.checkpointer = None

        # Mock run record
        mock_run_record = MagicMock()
        mock_run_record.id = run_id
        mock_run_record.events = []

        with (
            patch(
                "agent_runtime_cockpit.adapters.langgraph.replay_detector.load_graph"
            ) as mock_load_graph,
            patch(
                "agent_runtime_cockpit.adapters.langgraph.replay_detector.JsonlTraceStore"
            ) as mock_store_class,
        ):
            mock_load_graph.return_value = mock_graph
            mock_store = MagicMock()
            mock_store.load.return_value = mock_run_record
            mock_store_class.return_value = mock_store

            capability = analyze_run_replay_capability(run_id, workspace)

            assert capability.can_replay_trace is True
            assert capability.can_resume_checkpoint is False
            assert capability.has_checkpointer is False
            assert capability.determinism_level == "inspect_only"
            assert any("No checkpointer" in w for w in capability.warnings)


def test_analyze_graph_replay_capability_with_checkpointer():
    """Test analyzing a graph with checkpointer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Mock graph with checkpointer
        mock_graph = MagicMock()
        mock_checkpointer = MagicMock()
        mock_checkpointer.__class__.__name__ = "SqliteSaver"
        mock_graph.checkpointer = mock_checkpointer

        with patch(
            "agent_runtime_cockpit.adapters.langgraph.replay_detector.load_graph"
        ) as mock_load_graph:
            mock_load_graph.return_value = mock_graph

            capability = analyze_graph_replay_capability(workspace)

            assert capability.run_id == "N/A"
            assert capability.runtime == "langgraph"
            assert capability.can_replay_trace is False  # No trace to replay
            assert capability.can_resume_checkpoint is True
            assert capability.requires_thread_id is True
            assert capability.has_checkpointer is True
            assert capability.checkpointer_type == "SqliteSaver"
            assert capability.determinism_level == "simulated"


def test_analyze_graph_replay_capability_without_checkpointer():
    """Test analyzing a graph without checkpointer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Mock graph without checkpointer
        mock_graph = MagicMock()
        mock_graph.checkpointer = None

        with patch(
            "agent_runtime_cockpit.adapters.langgraph.replay_detector.load_graph"
        ) as mock_load_graph:
            mock_load_graph.return_value = mock_graph

            capability = analyze_graph_replay_capability(workspace)

            assert capability.can_replay_trace is False
            assert capability.can_resume_checkpoint is False
            assert capability.has_checkpointer is False
            assert capability.determinism_level == "inspect_only"
            assert any("No checkpointer" in w for w in capability.warnings)


def test_analyze_run_replay_capability_load_error():
    """Test analyzing a run when graph loading fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        run_id = "test_run_123"

        from agent_runtime_cockpit.adapters.langgraph.loader import LangGraphLoadError

        with patch(
            "agent_runtime_cockpit.adapters.langgraph.replay_detector.load_graph"
        ) as mock_load_graph:
            mock_load_graph.side_effect = LangGraphLoadError("langgraph.json not found")

            capability = analyze_run_replay_capability(run_id, workspace)

            assert capability.run_id == run_id
            assert capability.determinism_level == "unsafe"
            assert any("Could not load graph" in w for w in capability.warnings)
