from __future__ import annotations

import json

from agent_runtime_cockpit.providers.e2e_evidence import (
    build_provider_e2e_evidence,
    resolve_provider_e2e_artifact_path,
    sha256_text,
    write_provider_e2e_evidence,
)


def test_provider_e2e_evidence_redacts_prompt_and_output(monkeypatch):
    monkeypatch.setenv("ARC_RUN_LIVE_PROVIDER_E2E", "1")
    monkeypatch.setenv("ARC_ALLOW_LIVE_PROVIDER_TESTS", "true")

    evidence = build_provider_e2e_evidence(
        provider="crofai",
        model="deepseek-v4-pro-precision",
        prompt="secret prompt",
        output="secret output",
        status="completed",
        completed_tasks=1,
        events=[{"kind": "worker"}, {"kind": "topology"}, {"kind": "worker"}],
        calls=[{"content_length": 13, "degraded": False}],
        started_at="2026-06-01T00:00:00Z",
        ended_at="2026-06-01T00:00:01Z",
    )

    payload = json.loads(evidence.model_dump_json())
    serialized = json.dumps(payload)

    assert payload["prompt_length"] == len("secret prompt")
    assert payload["prompt_sha256"] == sha256_text("secret prompt")
    assert payload["output_length"] == len("secret output")
    assert payload["output_sha256"] == sha256_text("secret output")
    assert payload["event_kinds"] == ["topology", "worker"]
    assert payload["raw_prompt_stored"] is False
    assert payload["raw_output_stored"] is False
    assert payload["redaction_applied"] is True
    assert "secret prompt" not in serialized
    assert "secret output" not in serialized


def test_write_provider_e2e_evidence_writes_stable_json(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_RUN_LIVE_PROVIDER_E2E", "1")
    monkeypatch.setenv("ARC_ALLOW_LIVE_PROVIDER_TESTS", "true")
    evidence = build_provider_e2e_evidence(
        provider="crofai",
        model="deepseek-v4-pro-precision",
        prompt="prompt",
        output="output",
        status="completed",
        completed_tasks=1,
        events=[{"kind": "consensus"}],
        calls=[{"content_length": 6, "degraded": False}],
        started_at="2026-06-01T00:00:00Z",
        ended_at="2026-06-01T00:00:01Z",
    )

    path = tmp_path / "nested" / "evidence.json"
    written = write_provider_e2e_evidence(evidence, path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert written == path
    assert payload["schema_version"] == 1
    assert payload["evidence_type"] == "provider_backed_swarmgraph_e2e"
    assert payload["provider_call_count"] == 1
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_resolve_provider_e2e_artifact_path_prefers_explicit_path(tmp_path, monkeypatch):
    explicit = tmp_path / "custom.json"
    monkeypatch.setenv("ARC_PROVIDER_E2E_ARTIFACT", str(explicit))
    monkeypatch.setenv("ARC_PROVIDER_E2E_ARTIFACT_DIR", str(tmp_path / "ignored"))

    assert resolve_provider_e2e_artifact_path(provider="crofai", model="model") == explicit


def test_resolve_provider_e2e_artifact_path_sanitizes_dir_name(tmp_path, monkeypatch):
    monkeypatch.delenv("ARC_PROVIDER_E2E_ARTIFACT", raising=False)
    monkeypatch.setenv("ARC_PROVIDER_E2E_ARTIFACT_DIR", str(tmp_path))

    path = resolve_provider_e2e_artifact_path(provider="9/router", model="vendor/model:v1")

    assert path.parent == tmp_path
    assert path.name == "provider-e2e-9-router-vendor-model-v1.json"
