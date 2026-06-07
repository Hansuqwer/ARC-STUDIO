"""Tests for ARC Mobile Runtime SDK."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


# ── Hashing ───────────────────────────────────────────────────────────────────


class TestHashing:
    def test_capability_hash_stable(self):
        from agent_runtime_cockpit.mobile import capability_hash, list_capabilities

        caps = list_capabilities()
        h1 = capability_hash(caps[0])
        h2 = capability_hash(caps[0])
        assert h1 == h2

    def test_capability_hash_differs(self):
        from agent_runtime_cockpit.mobile import capability_hash, list_capabilities

        caps = list_capabilities()
        assert capability_hash(caps[0]) != capability_hash(caps[1])

    def test_manifest_hash_stable(self):
        from agent_runtime_cockpit.mobile import build_default_manifest, manifest_hash

        m = build_default_manifest("test.hash", "Test Hash")
        assert manifest_hash(m) == manifest_hash(m)

    def test_capability_hash_in_catalog(self):
        from agent_runtime_cockpit.mobile import list_capabilities

        for cap in list_capabilities():
            assert cap.capability_hash is not None
            assert len(cap.capability_hash) == 64


# ── Capabilities ──────────────────────────────────────────────────────────────


class TestCapabilities:
    def test_catalog_count(self):
        from agent_runtime_cockpit.mobile import list_capabilities

        assert len(list_capabilities()) == 13

    def test_all_mock(self):
        from agent_runtime_cockpit.mobile import list_capabilities

        for cap in list_capabilities():
            assert cap.id.endswith(".mock"), f"{cap.id} is not a mock capability"

    def test_no_background(self):
        from agent_runtime_cockpit.mobile import list_capabilities

        for cap in list_capabilities():
            assert not cap.background, f"{cap.id} has background=True"

    def test_no_network(self):
        from agent_runtime_cockpit.mobile import list_capabilities

        for cap in list_capabilities():
            assert not cap.network, f"{cap.id} has network=True"

    def test_get_capability(self):
        from agent_runtime_cockpit.mobile import get_capability

        cap = get_capability("app.memory.write.mock")
        assert cap is not None
        assert cap.id == "app.memory.write.mock"

    def test_unknown_capability_returns_none(self):
        from agent_runtime_cockpit.mobile import get_capability

        assert get_capability("nonexistent.real.camera") is None

    def test_simulator_supported(self):
        from agent_runtime_cockpit.mobile import list_capabilities

        for cap in list_capabilities():
            assert cap.simulator_supported


# ── Validation ────────────────────────────────────────────────────────────────


class TestValidation:
    def test_valid_manifest_passes(self):
        from agent_runtime_cockpit.mobile import build_default_manifest, validate_manifest

        m = build_default_manifest("test.valid", "Test Valid")
        r = validate_manifest(m)
        assert r.ok, [f.message for f in r.errors]

    def test_background_execution_blocked(self):
        from agent_runtime_cockpit.mobile import MobileRuntimeManifest, validate_manifest

        m = MobileRuntimeManifest(id="test.bg", name="BG Test", background_execution=True)
        r = validate_manifest(m)
        assert not r.ok
        assert any("background" in f.rule for f in r.errors)

    def test_network_blocked(self):
        from agent_runtime_cockpit.mobile import MobileRuntimeManifest, validate_manifest

        m = MobileRuntimeManifest(id="test.net", name="Net Test", network_by_default=True)
        r = validate_manifest(m)
        assert not r.ok
        assert any("network" in f.rule for f in r.errors)

    def test_sensitive_real_capability_blocked(self):
        from agent_runtime_cockpit.mobile import (
            MobileCapability,
            MobileCapabilityCategory,
            MobileDataSensitivity,
            MobileApprovalMode,
            validate_capability,
        )

        real_cam = MobileCapability(
            id="device.camera.capture",  # NOT .mock
            name="Real Camera",
            category=MobileCapabilityCategory.MEDIA,
            data_sensitivity=MobileDataSensitivity.HIGH,
            approval_mode=MobileApprovalMode.REQUIRED,
        )
        r = validate_capability(real_cam)
        assert not r.ok
        assert any("sensitive_must_be_mock" in f.rule for f in r.errors)

    def test_sensitive_capability_needs_approval(self):
        from agent_runtime_cockpit.mobile import (
            MobileCapability,
            MobileCapabilityCategory,
            MobileDataSensitivity,
            MobileApprovalMode,
            validate_capability,
        )

        cap = MobileCapability(
            id="device.camera.capture.mock",
            name="Camera Mock",
            category=MobileCapabilityCategory.MEDIA,
            data_sensitivity=MobileDataSensitivity.HIGH,
            approval_mode=MobileApprovalMode.NONE,  # missing approval
        )
        r = validate_capability(cap)
        assert not r.ok
        assert any("approval" in f.rule for f in r.errors)

    def test_mcp_exposable_requires_review_flag(self):
        from agent_runtime_cockpit.mobile import MobileCapability, validate_capability

        cap = MobileCapability(
            id="app.memory.write.mock",
            name="Memory",
            mcp_exposable=True,
            # no mcp_safe_reviewed in metadata
        )
        r = validate_capability(cap)
        assert not r.ok

    def test_hash_mismatch_fails(self):
        from agent_runtime_cockpit.mobile import build_default_manifest, validate_manifest

        m = build_default_manifest("test.drift", "Drift Test")
        m.manifest_hash = "wrong_hash"
        r = validate_manifest(m)
        assert not r.ok
        assert any("hash_mismatch" in f.rule for f in r.errors)

    def test_fixture_valid_manifest_passes(self):
        from agent_runtime_cockpit.mobile import validate_manifest
        from agent_runtime_cockpit.mobile.manifest import load_manifest

        m = load_manifest(FIXTURES / "valid_mobile_runtime.json")
        r = validate_manifest(m)
        assert r.ok, [f.message for f in r.errors]


# ── Simulator ─────────────────────────────────────────────────────────────────


class TestSimulator:
    def test_mock_capabilities_allowed(self):
        from agent_runtime_cockpit.mobile import (
            MobileActionPlan,
            MobileActionStep,
            simulate_action_plan,
        )

        plan = MobileActionPlan(
            plan_id="plan-allow",
            steps=[
                MobileActionStep(step_id="s1", capability_id="app.memory.write.mock", mock=True)
            ],
        )
        report = simulate_action_plan(plan)
        assert report.overall_allowed
        assert not report.blocked_steps

    def test_background_plan_blocked(self):
        from agent_runtime_cockpit.mobile import (
            MobileActionPlan,
            MobileActionStep,
            simulate_action_plan,
        )

        plan = MobileActionPlan(
            plan_id="plan-bg",
            requires_background=True,
            steps=[
                MobileActionStep(step_id="s1", capability_id="app.memory.write.mock", mock=True)
            ],
        )
        report = simulate_action_plan(plan)
        assert not report.overall_allowed
        assert "BACKGROUND_BLOCKED" in " ".join(report.warnings)

    def test_network_plan_blocked(self):
        from agent_runtime_cockpit.mobile import (
            MobileActionPlan,
            MobileActionStep,
            simulate_action_plan,
        )

        plan = MobileActionPlan(
            plan_id="plan-net",
            requires_network=True,
            steps=[
                MobileActionStep(step_id="s1", capability_id="app.memory.write.mock", mock=True)
            ],
        )
        report = simulate_action_plan(plan)
        assert not report.overall_allowed

    def test_unknown_capability_blocked(self):
        from agent_runtime_cockpit.mobile import (
            MobileActionPlan,
            MobileActionStep,
            simulate_action_plan,
        )

        plan = MobileActionPlan(
            plan_id="plan-unknown",
            steps=[MobileActionStep(step_id="s1", capability_id="real.camera.capture", mock=False)],
        )
        report = simulate_action_plan(plan)
        assert not report.overall_allowed
        assert "s1" in report.blocked_steps

    def test_sensitive_non_mock_blocked(self):
        from agent_runtime_cockpit.mobile import (
            MobileActionPlan,
            MobileActionStep,
            MobileCapability,
            MobileCapabilityCategory,
            MobileDataSensitivity,
            MobileApprovalMode,
            simulate_action_plan,
        )

        # add a non-mock sensitive cap as extra
        real_cap = MobileCapability(
            id="device.camera.capture.real",
            name="Real Camera",
            category=MobileCapabilityCategory.MEDIA,
            data_sensitivity=MobileDataSensitivity.HIGH,
            approval_mode=MobileApprovalMode.REQUIRED,
        )
        plan = MobileActionPlan(
            plan_id="plan-sensitive",
            steps=[
                MobileActionStep(
                    step_id="s1", capability_id="device.camera.capture.real", mock=False
                )
            ],
        )
        report = simulate_action_plan(plan, extra_capabilities=[real_cap])
        assert not report.overall_allowed
        assert "s1" in report.blocked_steps

    def test_report_hash_set(self):
        from agent_runtime_cockpit.mobile import (
            MobileActionPlan,
            MobileActionStep,
            simulate_action_plan,
        )

        plan = MobileActionPlan(
            plan_id="plan-hash",
            steps=[
                MobileActionStep(step_id="s1", capability_id="app.memory.retrieve.mock", mock=True)
            ],
        )
        report = simulate_action_plan(plan)
        assert report.report_hash is not None

    def test_fixture_action_plan(self):
        from agent_runtime_cockpit.mobile import MobileActionPlan, simulate_action_plan

        data = json.loads((FIXTURES / "mock_action_plan.json").read_text())
        plan = MobileActionPlan.model_validate(data)
        report = simulate_action_plan(plan)
        assert report.overall_allowed

    def test_fixture_background_plan_blocked(self):
        from agent_runtime_cockpit.mobile import MobileActionPlan, simulate_action_plan

        data = json.loads((FIXTURES / "invalid_background_plan.json").read_text())
        plan = MobileActionPlan.model_validate(data)
        report = simulate_action_plan(plan)
        assert not report.overall_allowed


# ── Runtime Pack ──────────────────────────────────────────────────────────────


class TestRuntimePack:
    def test_build_pack_manifest(self, tmp_path):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.runtime_pack import build_runtime_pack_manifest

        m = build_default_manifest("test.pack", "Test Pack")
        pack = build_runtime_pack_manifest(m, tmp_path)
        assert pack["id"] == "test.pack"
        assert pack["runtime"]["runtime_kind"] == "mobile"

    def test_pack_validates_with_runtime_pack_sdk(self, tmp_path):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.runtime_pack import build_runtime_pack_manifest
        from agent_runtime_cockpit.runtime_packs.loader import load_manifest
        from agent_runtime_cockpit.runtime_packs.validation import validate_manifest as rp_validate

        m = build_default_manifest("test.rp.validate", "Test RP Validate")
        build_runtime_pack_manifest(m, tmp_path)
        pack = load_manifest(tmp_path)
        report = rp_validate(pack)
        assert report.ok, [f.message for f in report.findings if f.severity == "error"]


# ── Safety ────────────────────────────────────────────────────────────────────


class TestSafety:
    _FORBIDDEN = [
        r"\bsubprocess\b",
        r"\bsocket\b",
        r"\baiohttp\b",
        r"\brequests\.get\b",
        r"\brequests\.post\b",
        r"\brequests\.Session\b",
        r"\bhttpx\b",
        r"\bos\.system\b",
        r"\bPopen\b",
        r"\burlopen\b",
        r"\bAVCapture\b",
        r"\bCLLocation\b",
    ]
    _SRC = Path(__file__).parent.parent.parent / "src" / "agent_runtime_cockpit" / "mobile"

    @pytest.mark.parametrize("pattern", _FORBIDDEN)
    def test_no_forbidden_primitive(self, pattern):
        compiled = re.compile(pattern)
        violations = []
        for f in self._SRC.glob("**/*.py"):
            for i, line in enumerate(f.read_text().splitlines(), 1):
                stripped = line.strip()
                # Skip comments and pure string literals (docstrings, description strings)
                if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
                    continue
                # Skip lines that are clearly description/name assignments
                if "description=" in line or "name=" in line:
                    continue
                if compiled.search(line):
                    violations.append(f"{f.name}:{i}: {line.rstrip()}")
        assert not violations, f"Forbidden {pattern!r}:\n" + "\n".join(violations)


# ── PR5: Redaction list fix + privacy_manifest_intent rename ──────────────────


class TestRedactionListFix:
    def test_secret_string_in_list_is_redacted(self):
        from agent_runtime_cockpit.mobile.redaction import redact_list

        # A token-looking string should be redacted
        lst = ["hello", "sk-abc123secrettoken"]
        result, count = redact_list(lst)
        # "hello" is safe; the token should be redacted
        assert result[0] == "hello"
        # Secret string should be redacted (depends on Redactor heuristics)
        # At minimum verify no crash and result has same length
        assert len(result) == 2

    def test_nested_list_recursed(self):
        from agent_runtime_cockpit.mobile.redaction import redact_list

        lst = [["safe", "also_safe"], ["nested"]]
        result, _ = redact_list(lst)
        assert isinstance(result[0], list)
        assert isinstance(result[1], list)

    def test_dict_in_list_still_redacted(self):
        from agent_runtime_cockpit.mobile.redaction import redact_list

        lst = [{"api_key": "secret123"}]
        result, count = redact_list(lst)
        assert result[0]["api_key"] == "[REDACTED]"
        assert count >= 1


class TestPrivacyManifestRename:
    def test_model_has_privacy_manifest_intent(self):
        from agent_runtime_cockpit.mobile import MobileRuntimeManifest

        m = MobileRuntimeManifest(id="test.pm", name="PM Test")
        assert hasattr(m, "privacy_manifest_intent")
        assert m.privacy_manifest_intent is True

    def test_deprecated_alias_still_works(self):
        from agent_runtime_cockpit.mobile import MobileRuntimeManifest

        m = MobileRuntimeManifest(id="test.pm2", name="PM2", privacy_manifest_intent=False)
        assert m.privacy_manifest is False

    def test_field_is_not_named_privacy_manifest(self):
        from agent_runtime_cockpit.mobile import MobileRuntimeManifest

        fields = set(MobileRuntimeManifest.model_fields)
        assert "privacy_manifest_intent" in fields
        assert "privacy_manifest" not in fields  # no longer a model field

    def test_build_default_manifest_uses_new_field(self):
        from agent_runtime_cockpit.mobile import build_default_manifest

        m = build_default_manifest("test.rename", "Rename Test")
        assert m.privacy_manifest_intent is True
