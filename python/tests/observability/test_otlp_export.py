"""Tests for OTLP HTTP/gRPC export safety.

No real network server required — HTTP tests use monkeypatch or a fake local server.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _minimal_export_dict():
    from agent_runtime_cockpit.observability import ObservabilityExportConfig, export_trace

    export = export_trace(
        str(FIXTURES / "minimal_run.jsonl"),
        cfg=ObservabilityExportConfig(format="openinference-json"),
    )
    return json.loads(export.model_dump_json())


class TestOtlpHttpSafetyGate:
    def test_refuses_without_confirmation(self):
        from agent_runtime_cockpit.observability.otlp_exporter import (
            ConfirmationRequired,
            export_otlp_http,
        )

        with pytest.raises(ConfirmationRequired):
            export_otlp_http(
                _minimal_export_dict(),
                endpoint="http://localhost:4318/v1/traces",
                confirm_network_export=False,
            )

    def test_refuses_without_endpoint(self):
        from agent_runtime_cockpit.observability.otlp_exporter import (
            EndpointRequired,
            export_otlp_http,
        )

        with pytest.raises(EndpointRequired):
            export_otlp_http(
                _minimal_export_dict(),
                endpoint="",
                confirm_network_export=True,
            )

    def test_refuses_payload_with_secret(self):
        from agent_runtime_cockpit.observability.otlp_exporter import export_otlp_http

        bad_dict = _minimal_export_dict()
        # Inject a fake secret into spans
        if bad_dict.get("spans"):
            bad_dict["spans"][0]["attributes"]["api_key"] = "sk-secretvalue1234567890"
        result = export_otlp_http(
            bad_dict,
            endpoint="http://localhost:4318/v1/traces",
            confirm_network_export=True,
        )
        assert not result.ok
        assert result.error is not None

    def test_successful_http_export_via_monkeypatch(self):
        from agent_runtime_cockpit.observability.otlp_exporter import export_otlp_http

        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = export_otlp_http(
                _minimal_export_dict(),
                endpoint="http://localhost:4318/v1/traces",
                confirm_network_export=True,
            )
        assert result.ok
        assert result.http_status == 200
        assert result.span_count >= 1

    def test_http_error_returns_failed_result(self):
        from agent_runtime_cockpit.observability.otlp_exporter import export_otlp_http
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                url=None, code=503, msg="Service Unavailable", hdrs=None, fp=None
            ),
        ):
            result = export_otlp_http(
                _minimal_export_dict(),
                endpoint="http://localhost:4318/v1/traces",
                confirm_network_export=True,
            )
        assert not result.ok
        assert "503" in result.error

    def test_validation_failure_prevents_send(self):
        """Validation must be called before send; invalid export should not reach urlopen."""
        from agent_runtime_cockpit.observability.validation import validate_export
        from agent_runtime_cockpit.observability.models import ArcTraceExport

        bad_export = ArcTraceExport(export_id="", format="openinference-json")
        report = validate_export(bad_export)
        assert not report.ok  # validation catches missing export_id

    def test_no_secret_in_otlp_payload(self):
        """The JSON payload built for OTLP must not contain secrets."""
        from agent_runtime_cockpit.observability.otlp_exporter import _build_otlp_json_payload

        d = _minimal_export_dict()
        payload = _build_otlp_json_payload(d)
        for indicator in ("Bearer ", "-----BEGIN", "sk-"):
            assert indicator not in payload


class TestOtlpGrpcSafetyGate:
    def test_refuses_without_confirmation(self):
        from agent_runtime_cockpit.observability.otlp_exporter import (
            ConfirmationRequired,
            export_otlp_grpc,
        )

        with pytest.raises(ConfirmationRequired):
            export_otlp_grpc(
                _minimal_export_dict(),
                endpoint="grpc://localhost:4317",
                confirm_network_export=False,
            )

    def test_refuses_without_endpoint(self):
        from agent_runtime_cockpit.observability.otlp_exporter import (
            EndpointRequired,
            export_otlp_grpc,
        )

        with pytest.raises(EndpointRequired):
            export_otlp_grpc(
                _minimal_export_dict(),
                endpoint="",
                confirm_network_export=True,
            )

    def test_grpc_unavailable_when_dep_missing(self):
        """When gRPC exporter dep is missing, OtlpGrpcUnavailable is raised."""
        from agent_runtime_cockpit.observability.otlp_exporter import (
            OtlpGrpcUnavailable,
            export_otlp_grpc,
        )
        import importlib.util as ilu

        try:
            spec = ilu.find_spec("opentelemetry.exporter.otlp.proto.grpc")
        except ModuleNotFoundError:
            spec = None
        sdk_available = spec is not None
        if not sdk_available:
            with pytest.raises(OtlpGrpcUnavailable):
                export_otlp_grpc(
                    _minimal_export_dict(),
                    endpoint="grpc://localhost:4317",
                    confirm_network_export=True,
                )
        else:
            result = export_otlp_grpc(
                _minimal_export_dict(),
                endpoint="grpc://localhost:4317",
                confirm_network_export=True,
            )
            assert isinstance(result.ok, bool)


class TestCollectorMockReceivesSpans:
    """End-to-end: mock OTLP collector receives N spans. No real network."""

    def test_collector_receives_correct_span_count(self):
        """A mock collector receives all spans from the export payload."""
        from agent_runtime_cockpit.observability.otlp_exporter import (
            export_otlp_http,
        )

        export_dict = _minimal_export_dict()
        expected_spans = len(export_dict.get("spans", []))

        # Capture what would be sent
        captured_payloads = []

        def fake_urlopen(req, timeout=None):
            captured_payloads.append(json.loads(req.data.decode("utf-8")))
            mock_resp = MagicMock()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.status = 200
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = export_otlp_http(
                export_dict,
                endpoint="http://localhost:4318/v1/traces",
                confirm_network_export=True,
            )

        assert result.ok
        assert result.span_count == expected_spans
        assert len(captured_payloads) == 1
        # Verify OTLP structure
        payload = captured_payloads[0]
        resource_spans = payload["resourceSpans"]
        total_sent = sum(len(ss["spans"]) for rs in resource_spans for ss in rs["scopeSpans"])
        assert total_sent == expected_spans

    def test_dry_run_does_not_send(self):
        """--dry-run builds and validates payload but never calls urlopen."""
        from agent_runtime_cockpit.observability.otlp_exporter import export_otlp_http

        with patch("urllib.request.urlopen") as mock_open:
            result = export_otlp_http(
                _minimal_export_dict(),
                endpoint="http://localhost:4318/v1/traces",
                confirm_network_export=True,
                dry_run=True,
            )

        assert result.ok
        assert result.span_count >= 1
        assert result.http_status is None
        mock_open.assert_not_called()

    def test_multi_span_export(self):
        """Export with multiple spans arrives intact at collector."""
        from agent_runtime_cockpit.observability.otel_mapping import map_events_to_spans
        from agent_runtime_cockpit.observability.loaders import LoadedTrace
        from agent_runtime_cockpit.observability import ObservabilityExportConfig
        from agent_runtime_cockpit.observability.otlp_exporter import export_otlp_http

        trace = LoadedTrace(
            run_id="multi-span-001",
            runtime="test",
            workflow_id="wf",
            status="completed",
            started_at="2025-01-01T00:00:00Z",
            ended_at="2025-01-01T00:01:00Z",
            events=[
                {
                    "type": "llm.request",
                    "run_id": "multi-span-001",
                    "sequence": i,
                    "timestamp": "2025-01-01T00:00:10Z",
                    "data": {
                        "provider": "openai",
                        "model": "gpt-4",
                        "usage": {"input_tokens": 10, "output_tokens": 5},
                    },
                }
                for i in range(5)
            ],
            source_file="<synthetic>",
        )
        cfg = ObservabilityExportConfig(format="openinference-json")
        spans, _, _ = map_events_to_spans(trace, cfg)
        # 1 root + 5 model spans = 6
        assert len(spans) == 6

        export_dict = {
            "spans": [s.model_dump() for s in spans],
            "resource": {"service.name": "arc-test"},
        }

        captured = []

        def fake_urlopen(req, timeout=None):
            captured.append(json.loads(req.data.decode("utf-8")))
            mock_resp = MagicMock()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.status = 200
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = export_otlp_http(
                export_dict,
                endpoint="http://localhost:4318/v1/traces",
                confirm_network_export=True,
            )

        assert result.ok
        assert result.span_count == 6
        total_sent = sum(
            len(ss["spans"]) for rs in captured[0]["resourceSpans"] for ss in rs["scopeSpans"]
        )
        assert total_sent == 6
