"""Tests for SDK→RuntimePackManifest converter and validation (Slice 110.4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.adapters.arc_runtime_sdk_pack import (
    sdk_manifest_to_runtime_pack,
    sdk_json_to_runtime_pack,
    validate_sdk_manifest,
)
from agent_runtime_cockpit.runtime_packs.models import (
    RUNTIME_PACK_SCHEMA_VERSION,
    RuntimeKind,
    RuntimePackManifest,
)


def _sdk(tmp_path: Path, **extra) -> Path:
    data = {
        "schema_version": "1.0.0",
        "app_id": "com.test.app",
        "sdk_version": "0.2.0",
        "name": "Test App",
        "description": "A test app",
        "capabilities": [],
    }
    data.update(extra)
    p = tmp_path / "arc-sdk.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# ── Converter output ──────────────────────────────────────────────────────────


def test_returns_runtime_pack_manifest(tmp_path):
    result = sdk_manifest_to_runtime_pack(json.loads(_sdk(tmp_path).read_text()))
    assert isinstance(result, RuntimePackManifest)


def test_schema_version_is_arc_version(tmp_path):
    result = sdk_manifest_to_runtime_pack(json.loads(_sdk(tmp_path).read_text()))
    assert result.schema_version == RUNTIME_PACK_SCHEMA_VERSION


def test_id_and_name_from_sdk(tmp_path):
    result = sdk_manifest_to_runtime_pack(json.loads(_sdk(tmp_path).read_text()))
    assert result.id == "com.test.app"
    assert result.name == "Test App"
    assert result.version == "0.2.0"
    assert result.description == "A test app"


def test_runtime_kind_is_mobile(tmp_path):
    result = sdk_manifest_to_runtime_pack(json.loads(_sdk(tmp_path).read_text()))
    assert result.runtime.runtime_kind == RuntimeKind.MOBILE
    assert result.runtime.framework == "arc-runtime-sdk"


def test_adapter_field_set(tmp_path):
    result = sdk_manifest_to_runtime_pack(json.loads(_sdk(tmp_path).read_text()))
    assert result.adapter == "arc-runtime-sdk"


def test_sdk_metadata_preserved(tmp_path):
    p = _sdk(tmp_path, target_platforms=["expo", "react-native"])
    result = sdk_json_to_runtime_pack(p)
    assert result.metadata.get("sdk_app_id") == "com.test.app"
    assert result.metadata.get("sdk_version") == "0.2.0"
    assert result.metadata.get("sdk_target_platforms") == ["expo", "react-native"]


def test_network_capability_synthesizes_permission(tmp_path):
    p = _sdk(
        tmp_path,
        capabilities=[
            {
                "id": "net_cap",
                "category": "network",
                "allow_paid_calls": False,
            }
        ],
    )
    result = sdk_json_to_runtime_pack(p)
    kinds = {perm.kind for perm in result.permissions}
    assert "network" in kinds
    net_perm = next(p for p in result.permissions if p.kind == "network")
    assert net_perm.reason  # reason must be present for dangerous permissions


def test_paid_capability_synthesizes_permission(tmp_path):
    p = _sdk(
        tmp_path,
        capabilities=[
            {
                "id": "paid_cap",
                "category": "app",
                "allow_paid_calls": True,
            }
        ],
    )
    result = sdk_json_to_runtime_pack(p)
    kinds = {perm.kind for perm in result.permissions}
    assert "paid_models" in kinds


def test_no_capabilities_no_permissions(tmp_path):
    result = sdk_manifest_to_runtime_pack(json.loads(_sdk(tmp_path).read_text()))
    assert result.permissions == []


# ── Validation (R1–R12) ───────────────────────────────────────────────────────


def test_validate_minimal_sdk_ok(tmp_path):
    report = validate_sdk_manifest(_sdk(tmp_path))
    assert report.ok is True
    assert report.error_count == 0


def test_validate_network_capability_passes_r7(tmp_path):
    p = _sdk(tmp_path, capabilities=[{"id": "net", "category": "network"}])
    report = validate_sdk_manifest(p)
    assert report.ok is True
    assert report.error_count == 0


def test_validate_manifest_not_pinned_warning(tmp_path):
    report = validate_sdk_manifest(_sdk(tmp_path))
    assert any(f.rule == "manifest_not_pinned" for f in report.warnings)


def test_validate_example_sdk_passes(tmp_path):
    """The real SDK example project validates without errors."""
    example = Path(__file__).parents[3] / (
        "runtimes/Arc-Studio-Mobile-SDK/arc-runtime-sdk/example/arc-sdk.json"
    )
    if not example.exists():
        pytest.skip("SDK example project not available in this environment")
    report = validate_sdk_manifest(example)
    assert report.ok is True
    assert report.error_count == 0
    assert report.manifest_id == "com.arc.example.todo"
