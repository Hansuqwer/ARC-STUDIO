"""Tests for T9 (Phase 12): SIEM export (CEF/JSON) from mobile traces."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.cli.mobile import mobile_app
from agent_runtime_cockpit.mobile import export_trace, export_trace_cef, export_trace_json
from agent_runtime_cockpit.mobile.recorder import MobileRuntimeEvent, MobileTrace, append_trace

runner = CliRunner()

SECRET_VALUE = "SENSITIVE-PII-VALUE-9f2"


def _trace() -> MobileTrace:
    events = [
        MobileRuntimeEvent(
            event_id="e1",
            event_type="capability_allowed",
            plan_id="plan-1",
            capability_id="app.memory.write.mock",
            timestamp="2026-01-01T00:00:00Z",
            sequence=0,
            allowed=True,
            payload_hash="a" * 64,
            event_hash="h1",
            metadata={"secret_key": SECRET_VALUE, "region": "eu"},
        ),
        MobileRuntimeEvent(
            event_id="e2",
            event_type="capability_denied",
            plan_id="plan-1",
            capability_id="device.camera.capture.mock",
            timestamp="2026-01-01T00:00:01Z",
            sequence=1,
            allowed=False,
            payload_hash="b" * 64,
            event_hash="h2",
            metadata={},
        ),
    ]
    return MobileTrace(plan_id="plan-1", events=events, trace_hash="t" * 64)


def test_cef_format_and_severity() -> None:
    cef = export_trace_cef(_trace())
    lines = cef.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("CEF:0|ARC|MobileRuntime|")
    # allowed -> severity 3, denied -> severity 7
    assert "|3|" in lines[0] and "act=allowed" in lines[0]
    assert "|7|" in lines[1] and "act=denied" in lines[1]
    assert "payloadHash" in lines[0] and "a" * 64 in lines[0]


def test_redaction_metadata_keys_only() -> None:
    cef = export_trace_cef(_trace())
    j = export_trace_json(_trace())
    # the metadata KEY is present, the VALUE never is (CEF + JSON)
    assert "secret_key" in cef and SECRET_VALUE not in cef
    blob = json.dumps(j)
    assert "secret_key" in blob and SECRET_VALUE not in blob
    assert j["events"][0]["metadata_keys"] == ["region", "secret_key"]
    assert "metadata" not in j["events"][0]  # no raw metadata values


def test_json_structure_payload_hash_only() -> None:
    j = export_trace_json(_trace())
    assert j["format"] == "arc-mobile-siem/1" and j["event_count"] == 2
    ev = j["events"][0]
    assert ev["payload_hash"] == "a" * 64
    assert "payload" not in ev and "outputs" not in ev  # never raw payloads


def test_deterministic() -> None:
    assert export_trace(_trace(), "cef") == export_trace(_trace(), "cef")
    assert export_trace(_trace(), "json") == export_trace(_trace(), "json")


def test_unknown_format_raises() -> None:
    with pytest.raises(ValueError):
        export_trace(_trace(), "syslog")


def test_cli_siem_export(tmp_path) -> None:
    path = tmp_path / "t.jsonl"
    append_trace(path, _trace())
    res = runner.invoke(mobile_app, ["siem-export", str(path), "--format", "cef"])
    assert res.exit_code == 0, res.output
    assert "CEF:0|ARC|MobileRuntime|" in res.output
    assert SECRET_VALUE not in res.output

    res_json = runner.invoke(mobile_app, ["siem-export", str(path), "--format", "json", "--json"])
    assert res_json.exit_code == 0, res_json.output
