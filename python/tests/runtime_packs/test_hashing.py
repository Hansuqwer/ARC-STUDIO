"""Tests for manifest hashing: stability, volatile-key exclusion, canonicality."""

from __future__ import annotations

import json

from agent_runtime_cockpit.runtime_packs import (
    RuntimeCapability,
    RuntimeIdentity,
    RuntimePackManifest,
    canonical_json,
    manifest_hash,
    verify_manifest_hash,
)
from agent_runtime_cockpit.runtime_packs.hashing import _VOLATILE_KEYS


class TestHashStability:
    def test_same_manifest_same_hash(self, minimal_manifest):
        h1 = manifest_hash(minimal_manifest)
        h2 = manifest_hash(minimal_manifest)
        assert h1 == h2

    def test_hash_is_64_char_hex(self, minimal_manifest):
        h = manifest_hash(minimal_manifest)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_dict_input_matches_model_input(self, minimal_manifest):
        model_hash = manifest_hash(minimal_manifest)
        data = minimal_manifest.model_dump(mode="json")
        dict_hash = manifest_hash(data)
        assert model_hash == dict_hash


class TestVolatileKeysExcluded:
    def test_manifest_hash_field_excluded(self, minimal_manifest):
        """Pinning a different manifest_hash must not change the canonical hash."""
        minimal_manifest.manifest_hash = "x" * 64
        h_pinned = manifest_hash(minimal_manifest)
        minimal_manifest.manifest_hash = None
        h_none = manifest_hash(minimal_manifest)
        assert h_pinned == h_none

    def test_created_at_excluded(self):
        """created_at in provenance is volatile and excluded from the hash."""
        from agent_runtime_cockpit.runtime_packs import RuntimePackProvenance

        m1 = RuntimePackManifest(
            id="x.test",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            provenance=RuntimePackProvenance(created_at="2024-01-01T00:00:00Z"),
        )
        m2 = RuntimePackManifest(
            id="x.test",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            provenance=RuntimePackProvenance(created_at="2099-12-31T23:59:59Z"),
        )
        assert manifest_hash(m1) == manifest_hash(m2)

    def test_volatile_keys_constant(self):
        expected = {"manifest_hash", "created_at", "compiled_at", "imported_at", "installed_at"}
        assert _VOLATILE_KEYS >= expected


class TestHashChangesOnMutation:
    def test_hash_changes_on_new_capability(self, minimal_manifest):
        original = manifest_hash(minimal_manifest)
        minimal_manifest.capabilities.append(RuntimeCapability(name="new_cap"))
        assert manifest_hash(minimal_manifest) != original

    def test_hash_changes_on_id_change(self, minimal_manifest):
        original = manifest_hash(minimal_manifest)
        minimal_manifest.id = "different.id"
        assert manifest_hash(minimal_manifest) != original

    def test_hash_changes_on_version_change(self, minimal_manifest):
        original = manifest_hash(minimal_manifest)
        minimal_manifest.version = "9.9.9"
        assert manifest_hash(minimal_manifest) != original


class TestVerifyManifestHash:
    def test_verify_pinned_hash(self, minimal_manifest):
        assert verify_manifest_hash(minimal_manifest, minimal_manifest.manifest_hash) is True

    def test_verify_fails_on_drift(self, minimal_manifest):
        assert verify_manifest_hash(minimal_manifest, "a" * 64) is False

    def test_verify_none_hash(self, minimal_manifest):
        assert verify_manifest_hash(minimal_manifest, None) is False


class TestCanonicalJson:
    def test_keys_sorted(self, minimal_manifest):
        raw = canonical_json(minimal_manifest.model_dump(mode="json"))
        parsed = json.loads(raw)
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    def test_no_whitespace(self, minimal_manifest):
        raw = canonical_json(minimal_manifest.model_dump(mode="json"))
        # Canonical JSON uses separators=(',',':') — no space after delimiters
        assert ", " not in raw, "Canonical JSON must not have space-after-comma formatting"
        assert ": " not in raw, "Canonical JSON must not have space-after-colon formatting"
