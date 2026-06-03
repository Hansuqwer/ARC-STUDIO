"""Tests for all 12 static validation rules (R1–R12).

Each test class targets exactly one rule so failures are easy to diagnose.
Fixtures are constructed with correct hashes *unless* we're specifically testing
the hash-integrity rule (R12), to avoid noise from R12 in rule-specific tests.
"""

from __future__ import annotations

from agent_runtime_cockpit.runtime_packs import (
    DefaultDecision,
    OpaqueNodePolicy,
    RuntimeCapability,
    RuntimeEntrypoints,
    RuntimeIdentity,
    RuntimeIrDeclaration,
    RuntimeKind,
    RuntimeMcpDeclaration,
    RuntimePackManifest,
    RuntimePermission,
    manifest_hash,
    validate_manifest,
)


def _pin(m: RuntimePackManifest) -> RuntimePackManifest:
    m.manifest_hash = manifest_hash(m)
    return m


def _base(**kwargs) -> RuntimePackManifest:
    """Return a minimal, hash-pinned manifest; kwargs override fields."""
    m = RuntimePackManifest(
        id=kwargs.pop("id", "test.runtime"),
        name=kwargs.pop("name", "Test Runtime"),
        runtime=kwargs.pop(
            "runtime", RuntimeIdentity(runtime_name="TestRuntime", runtime_kind=RuntimeKind.AGENT)
        ),
        **kwargs,
    )
    return _pin(m)


class TestR1SchemaVersion:
    def test_valid_schema_version_passes(self):
        rep = validate_manifest(_base())
        assert not any(f.rule == "schema_version" for f in rep.findings)

    def test_wrong_schema_version_fails(self):
        m = _base()
        m.schema_version = 999
        rep = validate_manifest(m)
        assert any(f.rule == "schema_version" and f.severity == "error" for f in rep.findings)
        assert rep.ok is False


class TestR2Id:
    def test_valid_id_passes(self):
        rep = validate_manifest(_base())
        assert not any(f.rule == "id" for f in rep.findings)

    def test_id_with_path_separator_fails(self):
        m = _base(id="bad/id")
        rep = validate_manifest(m)
        assert any(f.rule == "id" and f.severity == "error" for f in rep.findings)

    def test_id_with_dotdot_fails(self):
        m = _base(id="my..runtime")
        rep = validate_manifest(m)
        assert any(f.rule == "id" and f.severity == "error" for f in rep.findings)

    def test_id_dotted_valid(self):
        rep = validate_manifest(_base(id="org.my-runtime.v2"))
        assert not any(f.rule == "id" for f in rep.findings)


class TestR3Version:
    def test_valid_semver_passes(self):
        rep = validate_manifest(_base())
        assert not any(f.rule == "version" for f in rep.findings)

    def test_non_semver_fails(self):
        m = _base()
        m.version = "not-a-version"
        rep = validate_manifest(m)
        assert any(f.rule == "version" for f in rep.findings)

    def test_semver_with_prerelease_passes(self):
        m = _base()
        m.version = "1.0.0-beta.1"
        m = _pin(m)
        rep = validate_manifest(m)
        assert not any(f.rule == "version" for f in rep.findings)


class TestR4Entrypoints:
    def test_safe_dotted_entrypoint_passes(self):
        m = _base(entrypoints=RuntimeEntrypoints(inspect="my_pack.adapter:inspect"))
        rep = validate_manifest(m)
        assert not any(f.rule == "entrypoint_shell" for f in rep.findings)
        assert not any(f.rule == "entrypoint_absolute" for f in rep.findings)

    def test_shell_entrypoint_fails(self):
        m = _base(entrypoints=RuntimeEntrypoints(run="bash run.sh"))
        rep = validate_manifest(m)
        assert any(f.rule == "entrypoint_shell" and f.severity == "error" for f in rep.findings)

    def test_sh_suffix_fails(self):
        m = _base(entrypoints=RuntimeEntrypoints(run="./run.sh"))
        rep = validate_manifest(m)
        assert any(f.rule == "entrypoint_shell" for f in rep.findings)

    def test_absolute_path_fails_by_default(self):
        m = _base(entrypoints=RuntimeEntrypoints(inspect="/usr/local/bin/inspect"))
        rep = validate_manifest(m)
        assert any(f.rule == "entrypoint_absolute" and f.severity == "error" for f in rep.findings)

    def test_absolute_path_allowed_with_flag(self):
        m = _base(entrypoints=RuntimeEntrypoints(inspect="/usr/local/bin/inspect"))
        rep = validate_manifest(m, allow_absolute_entrypoints=True)
        assert not any(f.rule == "entrypoint_absolute" for f in rep.findings)


class TestR5UnknownPermission:
    def test_unknown_permission_fails(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            permissions=[RuntimePermission(kind="superpowers")],
        )
        m = _pin(m)
        rep = validate_manifest(m)
        assert any(f.rule == "unknown_permission" and f.severity == "error" for f in rep.findings)
        assert rep.ok is False

    def test_known_permission_no_unknown_error(self):
        m = _base()
        m.permissions = [RuntimePermission(kind="filesystem")]
        m = _pin(m)
        rep = validate_manifest(m)
        assert not any(f.rule == "unknown_permission" for f in rep.findings)


class TestR6DangerousPermissionReason:
    def test_dangerous_perm_without_reason_fails(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            permissions=[RuntimePermission(kind="network", required=True)],
        )
        m = _pin(m)
        rep = validate_manifest(m)
        assert any(
            f.rule == "dangerous_permission_no_reason" and f.severity == "error"
            for f in rep.findings
        )

    def test_dangerous_perm_with_reason_passes_r6(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            permissions=[
                RuntimePermission(kind="network", reason="Needed for remote tracing", required=True)
            ],
        )
        m = _pin(m)
        rep = validate_manifest(m)
        assert not any(f.rule == "dangerous_permission_no_reason" for f in rep.findings)


class TestR7CapabilityMissingPermission:
    def test_network_cap_without_perm_fails(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            capabilities=[RuntimeCapability(name="net_cap", network=True)],
        )
        m = _pin(m)
        rep = validate_manifest(m)
        assert any(f.rule == "capability_missing_permission" for f in rep.findings)

    def test_network_cap_with_perm_passes_r7(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            capabilities=[RuntimeCapability(name="net_cap", network=True)],
            permissions=[RuntimePermission(kind="network", reason="Needed")],
        )
        m = _pin(m)
        rep = validate_manifest(m)
        assert not any(f.rule == "capability_missing_permission" for f in rep.findings)

    def test_mcp_cap_without_perm_is_warning_not_error(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            capabilities=[RuntimeCapability(name="mcp_cap", mcp=True)],
        )
        m = _pin(m)
        rep = validate_manifest(m)
        soft = [f for f in rep.findings if f.rule == "capability_missing_permission_soft"]
        assert soft and all(f.severity == "warning" for f in soft)
        assert rep.ok is True  # warnings don't fail validation


class TestR8DangerousDefaultAllow:
    def test_dangerous_perm_default_allow_is_warning(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            permissions=[
                RuntimePermission(
                    kind="network",
                    reason="Needed",
                    default_decision=DefaultDecision.ALLOW,
                )
            ],
        )
        m = _pin(m)
        rep = validate_manifest(m)
        warn = [f for f in rep.findings if f.rule == "dangerous_permission_default_allow"]
        assert warn and all(f.severity == "warning" for f in warn)
        # Only a warning, not an error → still passes
        assert rep.ok is True


class TestR9McpMissingHash:
    def test_required_mcp_without_hash_fails(self):

        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            mcp=[RuntimeMcpDeclaration(server_id="my-mcp-server", required=True)],
        )
        m = _pin(m)
        rep = validate_manifest(m)
        assert any(f.rule == "mcp_missing_hash" and f.severity == "error" for f in rep.findings)

    def test_required_mcp_with_good_hash_passes(self):

        ok_hash = "a" * 64
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            mcp=[
                RuntimeMcpDeclaration(
                    server_id="my-mcp-server", required=True, manifest_hash=ok_hash
                )
            ],
        )
        m = _pin(m)
        rep = validate_manifest(m)
        assert not any(f.rule == "mcp_missing_hash" for f in rep.findings)

    def test_malformed_mcp_hash_is_warning(self):

        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            mcp=[
                RuntimeMcpDeclaration(
                    server_id="my-mcp-server", required=False, manifest_hash="not-a-hash"
                )
            ],
        )
        m = _pin(m)
        rep = validate_manifest(m)
        warn = [f for f in rep.findings if f.rule == "mcp_hash_format"]
        assert warn and all(f.severity == "warning" for f in warn)


class TestR10IrExport:
    def test_ir_export_without_version_fails(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            ir=RuntimeIrDeclaration(
                can_export_ir=True,
                opaque_node_policy=OpaqueNodePolicy.REJECT,
            ),
        )
        m = _pin(m)
        rep = validate_manifest(m)
        assert any(f.rule == "ir_missing_version" and f.severity == "error" for f in rep.findings)

    def test_ir_export_without_opaque_policy_fails(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            ir=RuntimeIrDeclaration(can_export_ir=True, supported_ir_version=1),
        )
        m = _pin(m)
        rep = validate_manifest(m)
        assert any(
            f.rule == "ir_missing_opaque_policy" and f.severity == "error" for f in rep.findings
        )

    def test_valid_ir_manifest_passes(self, ir_manifest):
        rep = validate_manifest(ir_manifest)
        assert rep.ok is True
        ir_errors = [f for f in rep.errors if f.rule.startswith("ir_")]
        assert not ir_errors


class TestR11SecretInManifest:
    def test_manifest_with_secret_fails(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            metadata={"api_key": "sk-abcdefghijklmnopqrstuvwx"},
        )
        m = _pin(m)
        rep = validate_manifest(m)
        assert any(f.rule == "secret_in_manifest" and f.severity == "error" for f in rep.findings)
        assert rep.ok is False

    def test_clean_manifest_no_secret_error(self, minimal_manifest):
        rep = validate_manifest(minimal_manifest)
        assert not any(f.rule == "secret_in_manifest" for f in rep.findings)


class TestR12ManifestHash:
    def test_pinned_manifest_passes_r12(self, minimal_manifest):
        rep = validate_manifest(minimal_manifest)
        assert not any(
            f.rule in ("manifest_hash_mismatch", "manifest_not_pinned") for f in rep.findings
        )

    def test_drifted_hash_is_error(self, minimal_manifest):
        minimal_manifest.manifest_hash = "b" * 64  # wrong hash
        rep = validate_manifest(minimal_manifest)
        assert any(
            f.rule == "manifest_hash_mismatch" and f.severity == "error" for f in rep.findings
        )
        assert rep.ok is False

    def test_absent_hash_is_warning(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
        )
        # No hash pinned
        rep = validate_manifest(m)
        assert any(
            f.rule == "manifest_not_pinned" and f.severity == "warning" for f in rep.findings
        )
        # Warning only, not an error
        assert rep.ok is True


class TestValidationReport:
    def test_report_errors_property(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            permissions=[RuntimePermission(kind="network")],  # missing reason
        )
        rep = validate_manifest(m)
        assert rep.errors  # at least one error
        assert all(f.severity == "error" for f in rep.errors)

    def test_report_warnings_property(self, minimal_manifest):
        # A pinned, valid manifest has no warnings
        rep = validate_manifest(minimal_manifest)
        assert rep.warnings == []

    def test_parse_error_returns_ok_false(self):
        rep = validate_manifest({"schema_version": "not_an_int_and_missing_required"})
        assert rep.ok is False

    def test_error_count_and_warning_count(self):

        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            permissions=[
                RuntimePermission(kind="network", reason=None),  # R6 error
                RuntimePermission(
                    kind="network",
                    reason="ok",
                    default_decision=DefaultDecision.ALLOW,
                ),  # R8 warning
            ],
            mcp=[RuntimeMcpDeclaration(server_id="s", required=True)],  # R9 error
        )
        rep = validate_manifest(m)
        assert rep.error_count >= 2
        assert rep.warning_count >= 1
