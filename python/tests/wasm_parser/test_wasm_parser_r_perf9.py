"""Tests for ARC WASM Trace Parser — research module (R-PERF9, Phase 329)."""

from __future__ import annotations

import json
from pathlib import Path

from agent_runtime_cockpit.wasm_parser import (
    WASM_PARSER_SCHEMA_VERSION,
    TraceParser,
    TraceParseResult,
    WasmTraceParser,
    benchmark_parser,
    generate_test_trace,
)


class TestTraceParser:
    def test_parse_file(self, tmp_path: Path) -> None:
        trace_file = tmp_path / "test.jsonl"
        trace_file.write_text(
            '{"type": "event1", "data": "test1"}\n{"type": "event2", "data": "test2"}\n',
            encoding="utf-8",
        )

        parser = TraceParser()
        result = parser.parse_file(trace_file)

        assert result.event_count == 2
        assert result.parse_time_ms > 0
        assert len(result.events) == 2
        assert result.events[0]["type"] == "event1"

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        trace_file = tmp_path / "empty.jsonl"
        trace_file.write_text("", encoding="utf-8")

        parser = TraceParser()
        result = parser.parse_file(trace_file)

        assert result.event_count == 0
        assert len(result.events) == 0

    def test_parse_invalid_json(self, tmp_path: Path) -> None:
        trace_file = tmp_path / "invalid.jsonl"
        trace_file.write_text(
            '{"type": "valid"}\ninvalid json\n{"type": "also_valid"}\n',
            encoding="utf-8",
        )

        parser = TraceParser()
        result = parser.parse_file(trace_file)

        assert result.event_count == 2
        assert len(result.events) == 2

    def test_parse_stream(self) -> None:
        stream = iter(
            [
                '{"type": "event1"}\n',
                '{"type": "event2"}\n',
                '{"type": "event3"}\n',
            ]
        )

        parser = TraceParser()
        result = parser.parse_stream(stream)

        assert result.event_count == 3
        assert result.metadata.get("stream") is True

    def test_iter_events(self, tmp_path: Path) -> None:
        trace_file = tmp_path / "test.jsonl"
        trace_file.write_text(
            '{"type": "e1"}\n{"type": "e2"}\n{"type": "e3"}\n',
            encoding="utf-8",
        )

        parser = TraceParser()
        events = list(parser.iter_events(trace_file))

        assert len(events) == 3
        assert events[0]["type"] == "e1"
        assert events[2]["type"] == "e3"

    def test_parse_result_to_dict(self) -> None:
        result = TraceParseResult(
            event_count=10,
            parse_time_ms=5.5,
            events=[],
            metadata={"test": "data"},
        )
        d = result.to_dict()
        assert d["event_count"] == 10
        assert d["parse_time_ms"] == 5.5
        assert d["metadata"]["test"] == "data"


class TestWasmTraceParser:
    def test_wasm_not_available(self) -> None:
        parser = WasmTraceParser()
        assert parser.wasm_available is False

    def test_fallback_to_python(self, tmp_path: Path) -> None:
        trace_file = tmp_path / "test.jsonl"
        trace_file.write_text('{"type": "test"}\n', encoding="utf-8")

        parser = WasmTraceParser()
        result = parser.parse_file(trace_file)

        assert result.event_count == 1
        assert result.events[0]["type"] == "test"

    def test_schema_version(self) -> None:
        parser = WasmTraceParser()
        assert parser.schema_version == WASM_PARSER_SCHEMA_VERSION


class TestBenchmark:
    def test_benchmark_parser(self, tmp_path: Path) -> None:
        trace_file = tmp_path / "bench.jsonl"
        generate_test_trace(trace_file, event_count=100)

        result = benchmark_parser(trace_file, iterations=3)

        assert result["iterations"] == 3
        assert result["event_count"] == 100
        assert result["avg_time_ms"] > 0
        assert result["min_time_ms"] <= result["avg_time_ms"]
        assert result["max_time_ms"] >= result["avg_time_ms"]
        assert result["throughput_events_per_sec"] > 0

    def test_benchmark_large_trace(self, tmp_path: Path) -> None:
        trace_file = tmp_path / "large.jsonl"
        generate_test_trace(trace_file, event_count=1000)

        result = benchmark_parser(trace_file, iterations=5)

        assert result["event_count"] == 1000
        assert result["throughput_events_per_sec"] > 0


class TestGenerateTestTrace:
    def test_generate_test_trace(self, tmp_path: Path) -> None:
        trace_file = tmp_path / "generated.jsonl"
        generate_test_trace(trace_file, event_count=50)

        assert trace_file.exists()
        lines = trace_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 50

        first_event = json.loads(lines[0])
        assert first_event["type"] == "test_event"
        assert first_event["sequence"] == 0

    def test_generate_creates_parent_dirs(self, tmp_path: Path) -> None:
        trace_file = tmp_path / "subdir" / "nested" / "trace.jsonl"
        generate_test_trace(trace_file, event_count=10)

        assert trace_file.exists()


class TestWasmParserCLI:
    def test_wasm_parser_help(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
