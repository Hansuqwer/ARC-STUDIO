"""Tests for PR9: compliance generators."""

from __future__ import annotations


def _safe_demo_manifest():
    from agent_runtime_cockpit.mobile.manifest import load_manifest
    from pathlib import Path

    fixture = (
        Path(__file__).parent.parent.parent.parent
        / "runtimes"
        / "mobile"
        / "fixtures"
        / "capabilities.safe-demo.json"
    )
    if fixture.exists():
        return load_manifest(fixture)
    from agent_runtime_cockpit.mobile import build_default_manifest

    return build_default_manifest("test.compliance", "Compliance Test")


class TestIosCompliance:
    def test_usage_strings_from_full_manifest(self):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.compliance.ios import generate_usage_strings

        m = build_default_manifest("test.ios", "iOS Test")
        strings = generate_usage_strings(m)
        # Full catalog has camera, mic, location, etc.
        assert "NSCameraUsageDescription" in strings
        assert "NSMicrophoneUsageDescription" in strings
        assert "NSLocationWhenInUseUsageDescription" in strings

    def test_usage_strings_advisory_text(self):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.compliance.ios import generate_usage_strings

        m = build_default_manifest("test.ios2", "iOS Test 2")
        strings = generate_usage_strings(m)
        for v in strings.values():
            assert "REVIEW REQUIRED" in v

    def test_privacy_manifest_xml_is_valid_plist_like(self):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.compliance.ios import generate_privacy_manifest

        m = build_default_manifest("test.plist", "Plist Test")
        xml = generate_privacy_manifest(m)
        assert "<?xml" in xml
        assert "PrivacyInfo" in xml or "NSPrivacy" in xml
        assert "advisory" in xml.lower() or "ADVISORY" in xml

    def test_empty_manifest_produces_no_usage_strings(self):
        from agent_runtime_cockpit.mobile.models import MobileRuntimeManifest
        from agent_runtime_cockpit.mobile.compliance.ios import generate_usage_strings

        m = MobileRuntimeManifest(id="x", name="x")
        assert generate_usage_strings(m) == {}


class TestAndroidCompliance:
    def test_manifest_permissions_from_full_catalog(self):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.compliance.android import generate_manifest_permissions

        m = build_default_manifest("test.android", "Android Test")
        xml = generate_manifest_permissions(m)
        assert "uses-permission" in xml
        assert "ADVISORY" in xml or "advisory" in xml.lower()

    def test_data_safety_has_advisory_flag(self):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.compliance.android import generate_data_safety_notes

        m = build_default_manifest("test.ds", "Data Safety")
        result = generate_data_safety_notes(m)
        assert result["advisory"] is True
        assert result["requires_human_review"] is True

    def test_empty_manifest_no_permissions(self):
        from agent_runtime_cockpit.mobile.models import MobileRuntimeManifest
        from agent_runtime_cockpit.mobile.compliance.android import generate_manifest_permissions

        m = MobileRuntimeManifest(id="x", name="x")
        xml = generate_manifest_permissions(m)
        assert "No dangerous permissions" in xml


class TestReviewNotes:
    def test_review_notes_contains_banner(self):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.compliance.review_notes import generate_review_notes

        m = build_default_manifest("test.notes", "Review Notes")
        notes = generate_review_notes(m)
        assert "ADVISORY" in notes
        assert "REVIEW REQUIRED" in notes

    def test_review_notes_lists_capabilities(self):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.compliance.review_notes import generate_review_notes

        m = build_default_manifest("test.notes2", "Notes 2")
        notes = generate_review_notes(m)
        assert "device.camera.capture.mock" in notes
