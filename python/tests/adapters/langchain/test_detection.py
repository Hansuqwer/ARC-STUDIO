"""Tests for LangChain adapter detection (Phase 26 T1).

Phase 26 T1: Detection only.
Minimum 8 tests required per roadmap.
"""

from __future__ import annotations

import importlib.util
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent_runtime_cockpit.adapters.langchain import LangChainAdapter
from agent_runtime_cockpit.adapters.langchain.detect import (
    detect_langchain,
    detect_langchain_community,
    detect_langchain_core,
    detect_langchain_import,
    detect_provider_integrations,
    scan_workspace_for_langchain,
)
from agent_runtime_cockpit.adapters.registry import default_registry


# Test 1: Detect langchain import when installed
def test_detect_langchain_import_installed(monkeypatch):
    """Test detection when langchain is installed."""
    mock_spec = MagicMock()
    mock_langchain = MagicMock()
    mock_langchain.__version__ = "0.3.5"

    def fake_find_spec(name):
        if name == "langchain":
            return mock_spec
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    with patch.dict("sys.modules", {"langchain": mock_langchain}):
        installed, version = detect_langchain_import()
        assert installed is True
        assert version == "0.3.5"


# Test 2: Detect langchain import when not installed
def test_detect_langchain_import_not_installed(monkeypatch):
    """Test detection when langchain is not installed."""

    def fake_find_spec(name):
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    installed, version = detect_langchain_import()
    assert installed is False
    assert version is None


# Test 3: Detect langchain_core
def test_detect_langchain_core(monkeypatch):
    """Test detection of langchain_core package."""
    mock_spec = MagicMock()

    def fake_find_spec(name):
        if name == "langchain_core":
            return mock_spec
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    has_core = detect_langchain_core()
    assert has_core is True


# Test 4: Detect langchain_community
def test_detect_langchain_community(monkeypatch):
    """Test detection of langchain_community package."""
    mock_spec = MagicMock()

    def fake_find_spec(name):
        if name == "langchain_community":
            return mock_spec
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    has_community = detect_langchain_community()
    assert has_community is True


# Test 5: Detect provider integrations
def test_detect_provider_integrations(monkeypatch):
    """Test detection of LangChain provider integrations."""
    mock_spec = MagicMock()

    def fake_find_spec(name):
        if name in ["langchain_openai", "langchain_anthropic"]:
            return mock_spec
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    providers = detect_provider_integrations()
    assert "langchain_openai" in providers
    assert "langchain_anthropic" in providers
    assert len(providers) == 2


# Test 6: Scan workspace for langchain usage
def test_scan_workspace_for_langchain(tmp_path: Path):
    """Test workspace scanning for LangChain imports."""
    # Create Python file with langchain import
    py_file = tmp_path / "agent.py"
    py_file.write_text(
        textwrap.dedent("""
        from langchain.chains import LLMChain
        from langchain_core.prompts import PromptTemplate
        
        def create_chain():
            return LLMChain()
    """)
    )

    # Create requirements.txt with langchain
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("langchain>=0.3.0\nlangchain-openai\n")

    evidence = scan_workspace_for_langchain(tmp_path)

    assert "agent.py" in evidence
    assert "requirements.txt" in evidence
    assert len(evidence) >= 2


# Test 7: Full detection with high confidence
def test_detect_langchain_high_confidence(tmp_path: Path, monkeypatch):
    """Test full detection with high confidence score."""
    # Mock installed packages
    mock_spec = MagicMock()
    mock_langchain = MagicMock()
    mock_langchain.__version__ = "0.3.5"

    def fake_find_spec(name):
        if name in ["langchain", "langchain_core", "langchain_community", "langchain_openai"]:
            return mock_spec
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    # Create workspace with langchain usage
    py_file = tmp_path / "chain.py"
    py_file.write_text("from langchain.chains import LLMChain")

    req_file = tmp_path / "requirements.txt"
    req_file.write_text("langchain>=0.3.0")

    with patch.dict("sys.modules", {"langchain": mock_langchain}):
        result = detect_langchain(tmp_path)

    assert result.detected is True
    assert result.confidence >= 0.8  # High confidence
    assert result.version == "0.3.5"
    assert result.has_core is True
    assert result.has_community is True
    assert "langchain_openai" in result.provider_integrations
    assert len(result.evidence) >= 4


# Test 8: Detection with no langchain installed
def test_detect_langchain_not_installed(tmp_path: Path, monkeypatch):
    """Test detection when langchain is not installed."""

    def fake_find_spec(name):
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    result = detect_langchain(tmp_path)

    assert result.detected is False
    assert result.confidence == 0.0
    assert result.version is None
    assert result.has_core is False
    assert result.has_community is False
    assert len(result.provider_integrations) == 0


# Test 9: LangChainAdapter detect method
def test_langchain_adapter_detect(tmp_path: Path, monkeypatch):
    """Test LangChainAdapter.detect() method."""
    mock_spec = MagicMock()
    mock_langchain = MagicMock()
    mock_langchain.__version__ = "0.3.5"

    def fake_find_spec(name):
        if name == "langchain":
            return mock_spec
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    with patch.dict("sys.modules", {"langchain": mock_langchain}):
        adapter = LangChainAdapter()
        detected, confidence, evidence = adapter.detect(tmp_path)

    assert detected is True
    assert confidence >= 0.3
    assert len(evidence) >= 1
    assert any("langchain installed" in e for e in evidence)


# Test 10: LangChainAdapter properties
def test_langchain_adapter_properties():
    """Test LangChainAdapter basic properties."""
    adapter = LangChainAdapter()

    assert adapter.adapter_id == "langchain"
    assert adapter.adapter_name == "LangChain"

    caps = adapter.capabilities()
    assert caps.can_inspect is True
    assert caps.can_run is True  # T3 implemented
    assert caps.can_export_workflow is True  # T2 implemented
    assert caps.can_stream_events is True  # T3 implemented


# Test 11: LangChainAdapter capability report - not detected
def test_langchain_adapter_capability_report_not_detected(tmp_path: Path, monkeypatch):
    """Test capability report when langchain is not detected."""

    def fake_find_spec(name):
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    adapter = LangChainAdapter()
    report = adapter.capability_report(tmp_path)

    assert report.runtime_id == "langchain"
    assert report.detected is False
    assert report.can_run is False
    assert report.availability == "not_detected"
    assert len(report.doctor_actions) == 1
    assert report.doctor_actions[0].id == "install-langchain"


# Test 12: LangChainAdapter capability report - detected
def test_langchain_adapter_capability_report_detected(tmp_path: Path, monkeypatch):
    """Test capability report when langchain is detected."""
    mock_spec = MagicMock()
    mock_langchain = MagicMock()
    mock_langchain.__version__ = "0.3.5"

    def fake_find_spec(name):
        if name == "langchain":
            return mock_spec
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    with patch.dict("sys.modules", {"langchain": mock_langchain}):
        adapter = LangChainAdapter()
        report = adapter.capability_report(tmp_path)

    assert report.runtime_id == "langchain"
    assert report.detected is True
    assert report.can_run is False  # T1 only
    assert report.availability == "detected_not_runnable"
    assert report.version == "0.3.5"
    assert "T2" in report.reason or "T3" in report.reason


# Test 13: LangChainAdapter registered in default registry
def test_langchain_adapter_registered_in_registry():
    """Test that LangChainAdapter is registered in default registry."""
    registry = default_registry()
    adapter = registry.get("langchain")

    assert adapter is not None
    assert isinstance(adapter, LangChainAdapter)
    assert adapter.adapter_id == "langchain"


# Test 14: Workspace scanning ignores venv directories
def test_scan_workspace_ignores_venv(tmp_path: Path):
    """Test that workspace scanning ignores .venv and venv directories."""
    # Create file in venv (should be ignored)
    venv_dir = tmp_path / ".venv" / "lib"
    venv_dir.mkdir(parents=True)
    venv_file = venv_dir / "langchain.py"
    venv_file.write_text("from langchain import something")

    # Create file in main workspace (should be detected)
    main_file = tmp_path / "app.py"
    main_file.write_text("from langchain import LLMChain")

    evidence = scan_workspace_for_langchain(tmp_path)

    assert "app.py" in evidence
    assert not any(".venv" in e for e in evidence)


# Test 15: Confidence calculation with partial installation
def test_detect_langchain_partial_installation(tmp_path: Path, monkeypatch):
    """Test confidence calculation with only langchain_core installed."""
    mock_spec = MagicMock()

    def fake_find_spec(name):
        if name == "langchain_core":
            return mock_spec
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    result = detect_langchain(tmp_path)

    assert result.detected is True
    assert result.confidence == 0.3  # Base confidence only
    assert result.has_core is True
    assert result.has_community is False
