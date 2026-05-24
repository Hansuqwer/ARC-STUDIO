"""Tests for audit event schema Pydantic models."""

import json

from agent_runtime_cockpit.schemas.audit_events import (
    AuditChainLink,
    AuditChainManifest,
    AuditEvent,
    AuditEventSeverity,
    AuditEventType,
)

AUDIT_EVENT_CHAIN_STARTED = AuditEventType.AUDIT_CHAIN_STARTED


class TestAuditEventType:
    def test_has_all_expected_values(self):
        expected = [
            "AUDIT_CHAIN_STARTED",
            "AUDIT_CHAIN_LINK_ADDED",
            "AUDIT_CHAIN_SEALED",
            "AUDIT_CHAIN_VERIFIED",
            "AUDIT_CHAIN_FAILED",
            "AUDIT_KEY_ROTATED",
            "AUDIT_EXPORTED",
        ]
        for name in expected:
            assert AuditEventType(name).value == name
        assert len(AuditEventType) == 7


class TestAuditEventSeverity:
    def test_has_expected_values(self):
        assert AuditEventSeverity.INFO.value == "info"
        assert AuditEventSeverity.WARNING.value == "warning"
        assert AuditEventSeverity.CRITICAL.value == "critical"


class TestAuditEvent:
    def test_minimal_construction(self):
        event = AuditEvent(
            runId="run-sg-abc123",
            eventType=AUDIT_EVENT_CHAIN_STARTED,
            timestamp="2026-05-22T10:00:00.000Z",
            sequence=0,
            severity=AuditEventSeverity.INFO,
            producer="arc-backend",
        )
        assert event.run_id == "run-sg-abc123"
        assert event.event_type == AuditEventType.AUDIT_CHAIN_STARTED
        assert event.sequence == 0
        assert event.data == {}

    def test_serialization(self):
        event = AuditEvent(
            runId="run-sg-abc123",
            eventType=AUDIT_EVENT_CHAIN_STARTED,
            timestamp="2026-05-22T10:00:00.000Z",
            sequence=0,
            severity=AuditEventSeverity.INFO,
            producer="arc-backend",
            data={"workflow": "wf-swarmgraph-fixture"},
        )
        dumped = event.model_dump(by_alias=True)
        assert dumped["runId"] == "run-sg-abc123"
        assert dumped["eventType"] == "AUDIT_CHAIN_STARTED"
        assert dumped["data"]["workflow"] == "wf-swarmgraph-fixture"
        assert dumped["severity"] == "info"

    def test_by_alias_false(self):
        event = AuditEvent(
            runId="run-sg-abc123",
            eventType=AUDIT_EVENT_CHAIN_STARTED,
            timestamp="2026-05-22T10:00:00.000Z",
            sequence=0,
            severity=AuditEventSeverity.WARNING,
            producer="arc-backend",
        )
        plain = event.model_dump(by_alias=False)
        assert plain["run_id"] == "run-sg-abc123"
        assert plain["event_type"] == "AUDIT_CHAIN_STARTED"
        assert plain["severity"] == "warning"


class TestAuditChainLink:
    def test_construction(self):
        event = AuditEvent(
            runId="run-sg-abc123",
            eventType=AuditEventType.AUDIT_CHAIN_LINK_ADDED,
            timestamp="2026-05-22T10:00:01.000Z",
            sequence=1,
            severity=AuditEventSeverity.INFO,
            producer="arc-backend",
        )
        link = AuditChainLink(
            chainId="chain-abc",
            previousHash="0" * 64,
            hash="a" * 64,
            event=event,
        )
        assert link.chain_id == "chain-abc"
        assert link.previous_hash == "0" * 64
        assert link.event.event_type == AuditEventType.AUDIT_CHAIN_LINK_ADDED
        assert link.sealed_at is None

    def test_sealed_at(self):
        event = AuditEvent(
            runId="run-sg-abc123",
            eventType=AuditEventType.AUDIT_CHAIN_LINK_ADDED,
            timestamp="2026-05-22T10:00:01.000Z",
            sequence=1,
            severity=AuditEventSeverity.INFO,
            producer="arc-backend",
        )
        link = AuditChainLink(
            chainId="chain-abc",
            previousHash="0" * 64,
            hash="a" * 64,
            event=event,
            sealedAt="2026-05-22T10:00:02.000Z",
        )
        assert link.sealed_at == "2026-05-22T10:00:02.000Z"

    def test_json_roundtrip(self):
        event = AuditEvent(
            runId="run-sg-abc123",
            eventType=AuditEventType.AUDIT_CHAIN_LINK_ADDED,
            timestamp="2026-05-22T10:00:01.000Z",
            sequence=1,
            severity=AuditEventSeverity.INFO,
            producer="arc-backend",
        )
        link = AuditChainLink(
            chainId="chain-abc",
            previousHash="0" * 64,
            hash="a" * 64,
            event=event,
        )
        serialized = json.loads(link.model_dump_json(by_alias=True))
        assert serialized["chainId"] == "chain-abc"
        assert serialized["event"]["runId"] == "run-sg-abc123"


class TestAuditChainManifest:
    def test_schema_version_defaults_to_1(self):
        manifest = AuditChainManifest(
            chainId="chain-abc",
            runId="run-sg-abc123",
            links=[],
            createdAt="2026-05-22T10:00:00.000Z",
            status="active",
        )
        assert manifest.schema_version == 1
        assert manifest.status == "active"
        assert manifest.sealed_at is None

    def test_sealed_manifest(self):
        manifest = AuditChainManifest(
            chainId="chain-def",
            runId="run-sg-def456",
            links=[],
            createdAt="2026-05-22T10:00:00.000Z",
            sealedAt="2026-05-22T11:00:00.000Z",
            verifiedAt="2026-05-22T11:05:00.000Z",
            status="verified",
        )
        assert manifest.sealed_at == "2026-05-22T11:00:00.000Z"
        assert manifest.verified_at == "2026-05-22T11:05:00.000Z"
        assert manifest.status == "verified"

    def test_by_alias(self):
        manifest = AuditChainManifest(
            chainId="chain-def",
            runId="run-sg-def456",
            links=[],
            createdAt="2026-05-22T10:00:00.000Z",
            status="active",
        )
        plain = manifest.model_dump(by_alias=False)
        assert plain["chain_id"] == "chain-def"
        assert plain["run_id"] == "run-sg-def456"
        assert plain["schema_version"] == 1

    def test_json_serialization(self):
        manifest = AuditChainManifest(
            chainId="chain-def",
            runId="run-sg-def456",
            links=[],
            createdAt="2026-05-22T10:00:00.000Z",
            status="active",
        )
        serialized = json.loads(manifest.model_dump_json(by_alias=True))
        assert serialized["chainId"] == "chain-def"
        assert serialized["schemaVersion"] == 1
        assert serialized["status"] == "active"
