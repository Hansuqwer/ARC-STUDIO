"""Tests for audit event redaction (ADR-021, D.10)."""
from __future__ import annotations

from agent_runtime_cockpit.audit.schema import (
    LlmRequestEvent,
    LlmResponseEvent,
    ToolCallEvent,
    ToolResultEvent,
    TrustLevel,
)
from agent_runtime_cockpit.audit.session import RedactionConfig, redact_event


class TestRedactionConfig:
    def test_from_env_defaults_false(self, monkeypatch):
        monkeypatch.delenv("ARC_AUDIT_REDACT_MESSAGES", raising=False)
        monkeypatch.delenv("ARC_AUDIT_REDACT_TOOL_ARGS", raising=False)
        monkeypatch.delenv("ARC_AUDIT_REDACT_TOOL_RESULTS", raising=False)
        config = RedactionConfig.from_env()
        assert config.redact_messages is False
        assert config.redact_tool_args is False
        assert config.redact_tool_results is False

    def test_from_env_reads_true_values(self, monkeypatch):
        monkeypatch.setenv("ARC_AUDIT_REDACT_MESSAGES", "true")
        monkeypatch.setenv("ARC_AUDIT_REDACT_TOOL_ARGS", "1")
        monkeypatch.setenv("ARC_AUDIT_REDACT_TOOL_RESULTS", "yes")
        config = RedactionConfig.from_env()
        assert config.redact_messages is True
        assert config.redact_tool_args is True
        assert config.redact_tool_results is True

    def test_from_env_false_values(self, monkeypatch):
        monkeypatch.setenv("ARC_AUDIT_REDACT_MESSAGES", "false")
        monkeypatch.setenv("ARC_AUDIT_REDACT_TOOL_ARGS", "0")
        monkeypatch.setenv("ARC_AUDIT_REDACT_TOOL_RESULTS", "no")
        config = RedactionConfig.from_env()
        assert config.redact_messages is False
        assert config.redact_tool_args is False
        assert config.redact_tool_results is False


class TestRedactEvent:
    def test_redact_llm_request_messages(self):
        event = LlmRequestEvent(
            run_id="run_abc",
            provider="anthropic",
            model="claude-3-5-sonnet",
            messages=[{"role": "user", "content": "secret prompt"}],
        )
        config = RedactionConfig(redact_messages=True)
        redacted = redact_event(event, config)
        assert isinstance(redacted, LlmRequestEvent)
        assert redacted.messages == ["<redacted>"]
        assert redacted.provider == "anthropic"  # non-sensitive preserved

    def test_redact_llm_request_skipped_when_disabled(self):
        event = LlmRequestEvent(
            run_id="run_abc",
            provider="anthropic",
            model="claude-3-5-sonnet",
            messages=[{"role": "user", "content": "keep me"}],
        )
        config = RedactionConfig(redact_messages=False)
        redacted = redact_event(event, config)
        assert redacted.messages == [{"role": "user", "content": "keep me"}]

    def test_redact_llm_response_content(self):
        event = LlmResponseEvent(
            run_id="run_abc",
            provider="anthropic",
            model="claude-3-5-sonnet",
            content=[{"type": "text", "text": "sensitive output"}],
        )
        config = RedactionConfig(redact_messages=True)
        redacted = redact_event(event, config)
        assert isinstance(redacted, LlmResponseEvent)
        assert redacted.content == ["<redacted>"]
        assert redacted.response_id == ""  # default preserved

    def test_redact_llm_response_skipped_when_disabled(self):
        event = LlmResponseEvent(
            run_id="run_abc",
            provider="anthropic",
            model="claude-3-5-sonnet",
            content=[{"type": "text", "text": "keep me"}],
        )
        config = RedactionConfig(redact_messages=False)
        redacted = redact_event(event, config)
        assert redacted.content == [{"type": "text", "text": "keep me"}]

    def test_redact_tool_call_args(self):
        event = ToolCallEvent(
            run_id="run_abc",
            tool_name="read_file",
            arguments={"path": "/secret/file.txt", "format": "json"},
            trust_level=TrustLevel.untrusted,
        )
        config = RedactionConfig(redact_tool_args=True)
        redacted = redact_event(event, config)
        assert isinstance(redacted, ToolCallEvent)
        assert redacted.arguments == {"__redacted__": "<redacted>"}
        assert redacted.tool_name == "read_file"

    def test_redact_tool_call_skipped_when_disabled(self):
        event = ToolCallEvent(
            run_id="run_abc",
            tool_name="read_file",
            arguments={"path": "/keep/me"},
            trust_level=TrustLevel.untrusted,
        )
        config = RedactionConfig(redact_tool_args=False)
        redacted = redact_event(event, config)
        assert redacted.arguments == {"path": "/keep/me"}

    def test_redact_tool_result(self):
        event = ToolResultEvent(
            run_id="run_abc",
            tool_name="read_file",
            result={"content": "sensitive file data"},
            trust_level=TrustLevel.untrusted,
        )
        config = RedactionConfig(redact_tool_results=True)
        redacted = redact_event(event, config)
        assert isinstance(redacted, ToolResultEvent)
        assert redacted.result == {"__redacted__": "<redacted>"}

    def test_redact_tool_result_skipped_when_disabled(self):
        event = ToolResultEvent(
            run_id="run_abc",
            tool_name="read_file",
            result={"content": "keep me"},
            trust_level=TrustLevel.untrusted,
        )
        config = RedactionConfig(redact_tool_results=False)
        redacted = redact_event(event, config)
        assert redacted.result == {"content": "keep me"}

    def test_non_redactable_event_passes_through(self):
        from agent_runtime_cockpit.audit.schema import RunStartedEvent, RuntimeMode
        event = RunStartedEvent(run_id="run_abc", runtime="swarmgraph", mode=RuntimeMode.gated_local)
        config = RedactionConfig(redact_messages=True, redact_tool_args=True, redact_tool_results=True)
        redacted = redact_event(event, config)
        assert redacted is event  # same object, no redaction needed


class TestAuditSessionRedactionIntegration:
    def test_session_redacts_via_config(self, tmp_path):
        from agent_runtime_cockpit.audit.session import AuditSession
        from agent_runtime_cockpit.audit.storage import AuditChainStore

        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        store = AuditChainStore(audit_dir=audit_dir, key_manager=FakeKeyManager())
        config = RedactionConfig(redact_messages=True, redact_tool_args=True)
        session = AuditSession(run_id="run_abc", store=store, redaction=config)
        session.store.ensure_run("run_abc")
        session.log_llm_request(provider="anthropic", model="claude", messages=[{"role": "user", "content": "secret"}])
        session.log_tool_call(tool_name="read_file", arguments={"path": "/secret"})
        session.log_run_completed()

        path = audit_dir / "run_abc.audit.jsonl"
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        assert len(lines) == 3

    def test_session_respects_env_vars(self, tmp_path, monkeypatch):
        from agent_runtime_cockpit.audit.session import AuditSession
        from agent_runtime_cockpit.audit.storage import AuditChainStore

        monkeypatch.setenv("ARC_AUDIT_REDACT_MESSAGES", "true")
        monkeypatch.setenv("ARC_AUDIT_REDACT_TOOL_RESULTS", "1")

        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        store = AuditChainStore(audit_dir=audit_dir, key_manager=FakeKeyManager())
        session = AuditSession(run_id="run_env", store=store)
        assert session._redaction.redact_messages is True
        assert session._redaction.redact_tool_args is False
        assert session._redaction.redact_tool_results is True


class FakeKeyManager:
    def get_key(self):
        return b"test-key-32-bytes-long-0123456789abcdef", type(
            "Status", (), {"available": True, "source": "test", "degraded": True, "warning": "", "key_id": ""}
        )()
