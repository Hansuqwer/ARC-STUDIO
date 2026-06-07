"""Tests for PR6: JSON Schema validation for mobile protocol objects."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "mobile" / "fixtures"


class TestSchemaValidator:
    def test_manifest_schema_validates_fixture(self):
        from agent_runtime_cockpit.mobile.schema_validator import validate_against_schema

        data = json.loads((FIXTURES / "valid_mobile_runtime.json").read_text())
        errors = validate_against_schema(data, "manifest")
        assert errors == [], errors

    def test_action_plan_schema_validates_fixture(self):
        from agent_runtime_cockpit.mobile.schema_validator import validate_against_schema

        data = json.loads((FIXTURES / "mock_action_plan.json").read_text())
        errors = validate_against_schema(data, "action_plan")
        assert errors == [], errors

    def test_manifest_schema_rejects_background_true(self):
        from agent_runtime_cockpit.mobile.schema_validator import validate_against_schema

        data = {
            "schema_version": 1,
            "id": "x",
            "name": "x",
            "version": "0.1.0",
            "capabilities": [],
            "background_execution": True,  # INVALID
            "network_by_default": False,
            "simulator_mode": True,
        }
        errors = validate_against_schema(data, "manifest")
        assert errors  # must fail

    def test_action_plan_schema_rejects_requires_network_true(self):
        from agent_runtime_cockpit.mobile.schema_validator import validate_against_schema

        data = {
            "schema_version": 1,
            "plan_id": "p1",
            "steps": [],
            "requires_network": True,
            "requires_background": False,
        }
        errors = validate_against_schema(data, "action_plan")
        assert errors

    def test_unknown_kind_raises(self):
        from agent_runtime_cockpit.mobile.schema_validator import validate_against_schema

        with pytest.raises(ValueError, match="Unknown schema kind"):
            validate_against_schema({}, "not_a_kind")

    def test_list_schema_kinds_has_all_six(self):
        from agent_runtime_cockpit.mobile.schema_validator import list_schema_kinds

        kinds = list_schema_kinds()
        for k in (
            "manifest",
            "action_plan",
            "simulation_report",
            "event",
            "trace",
            "policy_decision",
        ):
            assert k in kinds

    def test_strict_load_runs_schema_validation(self, tmp_path):
        from agent_runtime_cockpit.mobile.manifest import (
            load_manifest,
            MANIFEST_FILENAME,
            MobileManifestLoadError,
        )

        data = {
            "schema_version": 1,
            "id": "t",
            "name": "t",
            "version": "0.1.0",
            "capabilities": [],
            "background_execution": True,  # blocked in schema
            "network_by_default": False,
            "simulator_mode": True,
        }
        (tmp_path / MANIFEST_FILENAME).write_text(json.dumps(data))
        with pytest.raises(MobileManifestLoadError):
            load_manifest(tmp_path, strict=True)
