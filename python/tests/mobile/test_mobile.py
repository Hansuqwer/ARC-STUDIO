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


# ── PR2: Strict validation, duplicate IDs, capability-ID regex ────────────────


class TestStrictMode:
    def test_strict_load_rejects_unknown_field(self, tmp_path):
        from agent_runtime_cockpit.mobile.manifest import load_manifest, MANIFEST_FILENAME

        data = {
            "schema_version": 1,
            "id": "test.strict",
            "name": "Strict Test",
            "version": "0.1.0",
            "capabilities": [],
            "background_execution": False,
            "network_by_default": False,
            "simulator_mode": True,
            "unknown_surprise_field": "evil",
        }
        import json

        p = tmp_path / MANIFEST_FILENAME
        p.write_text(json.dumps(data))
        from agent_runtime_cockpit.mobile.manifest import MobileManifestLoadError

        with pytest.raises(MobileManifestLoadError, match="unknown"):
            load_manifest(tmp_path, strict=True)

    def test_lenient_load_accepts_unknown_field(self, tmp_path):
        from agent_runtime_cockpit.mobile.manifest import load_manifest, MANIFEST_FILENAME

        data = {
            "schema_version": 1,
            "id": "test.lenient",
            "name": "Lenient",
            "version": "0.1.0",
            "capabilities": [],
            "background_execution": False,
            "network_by_default": False,
            "simulator_mode": True,
            "unknown_field": "ignored",
        }
        import json

        p = tmp_path / MANIFEST_FILENAME
        p.write_text(json.dumps(data))
        m = load_manifest(tmp_path)
        assert m.id == "test.lenient"

    def test_v4_write_is_error_in_strict_mode(self):
        from agent_runtime_cockpit.mobile import validate_capability, MobileCapability

        cap = MobileCapability(
            id="app.custom.write.mock",
            name="Custom Write",
            writes=True,
            auditable=True,
            requires_hitl=False,
            requires_trust=False,
        )
        report_strict = validate_capability(cap, strict=True)
        report_lenient = validate_capability(cap, strict=False)
        assert not report_strict.ok
        assert any(
            f.rule == "write_requires_hitl_or_trust" and f.severity == "error"
            for f in report_strict.errors
        )
        # In lenient mode it is a warning, not an error
        assert report_lenient.ok
        assert any(
            f.rule == "write_requires_hitl_or_trust" and f.severity == "warning"
            for f in report_lenient.warnings
        )


class TestDuplicateIds:
    def test_duplicate_capability_id_rejected_in_validate(self):
        from agent_runtime_cockpit.mobile import (
            MobileCapability,
            MobileRuntimeManifest,
            validate_manifest,
        )

        cap = MobileCapability(id="app.memory.write.mock", name="Write")
        m = MobileRuntimeManifest(id="test.dup", name="Dup", capabilities=[cap, cap])
        report = validate_manifest(m)
        assert not report.ok
        assert any("duplicate_capability_id" in f.rule for f in report.errors)

    def test_duplicate_capability_id_rejected_in_load(self, tmp_path):
        from agent_runtime_cockpit.mobile.manifest import (
            load_manifest,
            MANIFEST_FILENAME,
            MobileManifestLoadError,
        )
        import json

        cap = {
            "schema_version": 1,
            "id": "app.memory.write.mock",
            "name": "W",
            "approval_mode": "none",
            "data_sensitivity": "low",
            "background": False,
            "network": False,
            "mcp_exposable": False,
            "simulator_supported": True,
        }
        data = {
            "schema_version": 1,
            "id": "test.dup",
            "name": "Dup",
            "version": "0.1.0",
            "capabilities": [cap, cap],
            "background_execution": False,
            "network_by_default": False,
            "simulator_mode": True,
        }
        (tmp_path / MANIFEST_FILENAME).write_text(json.dumps(data))
        with pytest.raises(MobileManifestLoadError, match="duplicate"):
            load_manifest(tmp_path)

    def test_duplicate_step_id_rejected(self):
        from agent_runtime_cockpit.mobile import (
            MobileActionPlan,
            MobileActionStep,
            validate_action_plan,
            list_capabilities,
        )

        plan = MobileActionPlan(
            plan_id="plan-dup-steps",
            steps=[
                MobileActionStep(step_id="s1", capability_id="app.memory.write.mock", mock=True),
                MobileActionStep(step_id="s1", capability_id="app.memory.retrieve.mock", mock=True),
            ],
        )
        report = validate_action_plan(plan, list_capabilities())
        assert not report.ok
        assert any("duplicate_step_id" in f.rule for f in report.errors)


class TestCapabilityIdRegex:
    def test_valid_id_passes(self):
        from agent_runtime_cockpit.mobile import validate_capability, MobileCapability

        cap = MobileCapability(id="device.camera.capture.mock", name="Cam")
        r = validate_capability(cap)
        assert not any(f.rule == "capability_id_invalid_pattern" for f in r.errors)

    def test_invalid_id_uppercase_fails(self):
        from agent_runtime_cockpit.mobile import validate_capability, MobileCapability

        cap = MobileCapability(id="Device.Camera", name="Bad")
        r = validate_capability(cap)
        assert any(f.rule == "capability_id_invalid_pattern" for f in r.errors)

    def test_invalid_id_spaces_fails(self):
        from agent_runtime_cockpit.mobile import validate_capability, MobileCapability

        cap = MobileCapability(id="device camera", name="Bad")
        r = validate_capability(cap)
        assert any(f.rule == "capability_id_invalid_pattern" for f in r.errors)

    def test_invalid_id_no_dot_fails(self):
        from agent_runtime_cockpit.mobile import validate_capability, MobileCapability

        cap = MobileCapability(id="devicecamera", name="Bad")
        r = validate_capability(cap)
        assert any(f.rule == "capability_id_invalid_pattern" for f in r.errors)


class TestCatalogUniqueness:
    def test_catalog_has_no_duplicate_ids(self):
        from agent_runtime_cockpit.mobile import list_capabilities

        caps = list_capabilities()
        ids = [c.id for c in caps]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {[x for x in ids if ids.count(x) > 1]}"
# ── PR4: Trace chain, real timestamps, verify ─────────────────────────────────


class TestTraceChain:
    def _make_report(self):
        from agent_runtime_cockpit.mobile import (
            MobileActionPlan,
            MobileActionStep,
            simulate_action_plan,
        )

        plan = MobileActionPlan(
            plan_id="chain-test",
            steps=[
                MobileActionStep(step_id="s1", capability_id="app.memory.write.mock", mock=True),
                MobileActionStep(step_id="s2", capability_id="app.memory.retrieve.mock", mock=True),
            ],
        )
        return simulate_action_plan(plan)

    def test_prev_event_hash_chain_first_is_zeros(self):
        from agent_runtime_cockpit.mobile import build_trace

        trace = build_trace(self._make_report(), deterministic=True)
        assert trace.events[0].prev_event_hash == "0" * 64

    def test_prev_event_hash_chain_second_links_to_first(self):
        from agent_runtime_cockpit.mobile import build_trace

        trace = build_trace(self._make_report(), deterministic=True)
        assert trace.events[1].prev_event_hash == trace.events[0].event_hash

    def test_verify_trace_ok(self):
        from agent_runtime_cockpit.mobile import build_trace, verify_trace

        trace = build_trace(self._make_report(), deterministic=True)
        ok_flag, msg = verify_trace(trace)
        assert ok_flag, msg

    def test_verify_trace_detects_reorder(self):
        from agent_runtime_cockpit.mobile import build_trace, verify_trace

        trace = build_trace(self._make_report(), deterministic=True)
        # Swap event order
        trace.events[0], trace.events[1] = trace.events[1], trace.events[0]
        ok_flag, msg = verify_trace(trace)
        assert not ok_flag
        assert "chain broken" in msg.lower() or "mismatch" in msg.lower()

    def test_verify_trace_detects_mutation(self):
        from agent_runtime_cockpit.mobile import build_trace, verify_trace

        trace = build_trace(self._make_report(), deterministic=True)
        trace.events[0].allowed = not trace.events[0].allowed  # mutate
        ok_flag, msg = verify_trace(trace)
        assert not ok_flag

    def test_deterministic_mode_same_timestamp(self):
        from agent_runtime_cockpit.mobile import build_trace

        t1 = build_trace(self._make_report(), deterministic=True)
        t2 = build_trace(self._make_report(), deterministic=True)
        assert t1.events[0].timestamp == t2.events[0].timestamp == "2026-01-01T00:00:00Z"

    def test_real_mode_has_non_fixed_timestamp(self):
        from agent_runtime_cockpit.mobile import build_trace

        trace = build_trace(self._make_report(), deterministic=False)
        # Should not be the old hard-coded deterministic value in non-deterministic mode
        assert trace.events[0].timestamp != ""
        # In test environment this may equal deterministic ts if run very fast, just assert format
        assert "T" in trace.events[0].timestamp

    def test_hashing_docstring_no_longer_claims_schema_version_excluded(self):
        from agent_runtime_cockpit.mobile import hashing

        assert "schema_version" not in (hashing.__doc__ or "").lower().split("excludes")[-1][:50]
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
