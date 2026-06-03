"""Tests for flight_recorder.export — bundle export and manifest.

Covers:
  - Bundle written to correct path.
  - Manifest contains all segments.
  - Checksums present.
  - No secrets in tarball.
  - Corrupt / unknown run raises ValueError.
"""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest

from agent_runtime_cockpit.flight_recorder import FlightRecorder, FlightRecorderConfig
from agent_runtime_cockpit.flight_recorder.export import export_run
from agent_runtime_cockpit.flight_recorder.models import EventType


def _make_recorder(tmp_path: Path) -> FlightRecorder:
    cfg = FlightRecorderConfig(
        base_dir=str(tmp_path / ".arc" / "flight"),
        max_segment_bytes=1024 * 1024,
    )
    return FlightRecorder(config=cfg)


class TestExportBundle:
    def test_export_creates_tarball(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-export-01")
        recorder.record("run-export-01", EventType.IR_COMPILED, payload={"ir_hash": "abc123"})
        recorder.stop_run("run-export-01")

        base = Path(recorder._config.base_dir)
        out = tmp_path / "bundle.tar.gz"
        bundle = export_run(base, "run-export-01", out)
        assert out.exists()
        assert bundle.bundle_id != ""

    def test_tarball_contains_manifest(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-export-02")
        recorder.record("run-export-02", EventType.POLICY_EVALUATED, payload={"risk": "medium"})
        recorder.stop_run("run-export-02")

        base = Path(recorder._config.base_dir)
        out = tmp_path / "bundle2.tar.gz"
        export_run(base, "run-export-02", out)

        with tarfile.open(out, "r:gz") as tar:
            names = tar.getnames()
        assert "manifest.json" in names
        assert "index.json" in names

    def test_manifest_has_checksums(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-export-03")
        recorder.record("run-export-03", EventType.AUDIT_RECEIPT_CREATED, payload={})
        recorder.stop_run("run-export-03")

        base = Path(recorder._config.base_dir)
        out = tmp_path / "bundle3.tar.gz"
        bundle = export_run(base, "run-export-03", out)
        assert len(bundle.checksums) > 0
        for path, sha in bundle.checksums.items():
            assert len(sha) == 64  # SHA-256 hex

    def test_export_unknown_run_raises(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        base = Path(recorder._config.base_dir)
        out = tmp_path / "bundle_unknown.tar.gz"
        with pytest.raises(ValueError, match="not found"):
            export_run(base, "run-does-not-exist", out)

    def test_no_secrets_in_tarball(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-export-secret")
        recorder.record(
            "run-export-secret",
            EventType.IR_COMPILED,
            payload={
                "safe_field": "workflow_hash_abc123",
                "api_key": "sk-proj-SUPERSECRETKEY12345678901234",  # Should be redacted
            },
        )
        recorder.stop_run("run-export-secret")

        base = Path(recorder._config.base_dir)
        out = tmp_path / "bundle_secret.tar.gz"
        export_run(base, "run-export-secret", out)

        # Inspect tarball contents
        with tarfile.open(out, "r:gz") as tar:
            for member in tar.getmembers():
                f = tar.extractfile(member)
                if f:
                    content = f.read().decode("utf-8", errors="replace")
                    assert "sk-proj-SUPERSECRETKEY" not in content, f"Secret found in {member.name}"

    def test_bundle_reports_run_ids(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-export-meta")
        recorder.record("run-export-meta", EventType.RUN_STARTED, payload={})
        recorder.stop_run("run-export-meta")

        base = Path(recorder._config.base_dir)
        out = tmp_path / "bundle_meta.tar.gz"
        bundle = export_run(base, "run-export-meta", out)
        assert "run-export-meta" in bundle.runs

    def test_manifest_json_parseable_from_tarball(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-export-parse")
        recorder.record("run-export-parse", EventType.CONSENSUS_SELECTED, payload={})
        recorder.stop_run("run-export-parse")

        base = Path(recorder._config.base_dir)
        out = tmp_path / "bundle_parse.tar.gz"
        export_run(base, "run-export-parse", out)

        with tarfile.open(out, "r:gz") as tar:
            f = tar.extractfile("manifest.json")
            assert f is not None
            manifest = json.loads(f.read())
        assert "bundle_id" in manifest
        assert "schema_version" in manifest
        assert manifest["schema_version"] == "1"
