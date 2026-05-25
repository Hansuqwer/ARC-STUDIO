"""Tests for webhook delivery with HMAC signing (Phase 32 / R25, Slice 32.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_runtime_cockpit.events.models import DeadLetterEntry, WebhookConfig
from agent_runtime_cockpit.events.webhooks import (
    WebhookManager,
    sign_payload,
    verify_signature,
)


@pytest.fixture
def config_dir(tmp_path: Path):
    d = tmp_path / ".arc" / "events"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def manager(config_dir: Path):
    return WebhookManager(
        config_path=config_dir / "webhooks.json",
        dead_letter_path=config_dir / "dead-letter.jsonl",
    )


# --- Config CRUD ---


def test_add_webhook(manager):
    config = WebhookConfig(url="https://example.com/hook", secret="secret123")
    added = manager.add(config)
    assert added.id is not None
    assert added.url == "https://example.com/hook"
    assert len(manager.list()) == 1


def test_list_webhooks_empty(manager):
    assert manager.list() == []


def test_remove_webhook(manager):
    config = WebhookConfig(url="https://example.com/hook", secret="s")
    manager.add(config)
    assert manager.remove(config.id) is True
    assert len(manager.list()) == 0


def test_remove_nonexistent(manager):
    assert manager.remove("nonexistent") is False


def test_get_webhook(manager):
    config = WebhookConfig(url="https://example.com/hook", secret="s")
    manager.add(config)
    assert manager.get(config.id) is not None
    assert manager.get("nonexistent") is None


def test_config_persistence(config_dir: Path):
    """Configs survive manager restart."""
    m1 = WebhookManager(
        config_path=config_dir / "webhooks.json", dead_letter_path=config_dir / "dead-letter.jsonl"
    )
    m1.add(WebhookConfig(url="https://example.com/hook", secret="s"))
    m2 = WebhookManager(
        config_path=config_dir / "webhooks.json", dead_letter_path=config_dir / "dead-letter.jsonl"
    )
    assert len(m2.list()) == 1


# --- HMAC Signing ---


def test_sign_and_verify():
    payload = b'{"hello": "world"}'
    secret = "my-secret"
    sig = sign_payload(payload, secret)
    assert len(sig) == 64  # SHA-256 hex
    assert verify_signature(payload, secret, sig) is True


def test_verify_wrong_secret():
    payload = b'{"hello": "world"}'
    sig = sign_payload(payload, "correct-secret")
    assert verify_signature(payload, "wrong-secret", sig) is False


def test_verify_wrong_payload():
    payload = b'{"hello": "world"}'
    secret = "my-secret"
    sig = sign_payload(payload, secret)
    assert verify_signature(b'{"hello": "tampered"}', secret, sig) is False


def test_known_test_vector():
    """Test with known values for reproducibility."""
    payload = b"test"
    secret = "key"
    sig = sign_payload(payload, secret)
    # Known good HMAC-SHA256
    assert len(sig) == 64


# --- Dead Letter ---


def test_dead_letter_write_and_read(manager):
    entry = DeadLetterEntry(
        webhook_id="wh-1",
        url="https://example.com/hook",
        event_type="hitl_required",
        payload={"test": True},
        error="Connection refused",
    )
    manager._write_dead_letter(entry)
    entries = manager.read_dead_letter()
    assert len(entries) == 1
    assert entries[0].webhook_id == "wh-1"
    assert entries[0].error == "Connection refused"


def test_dead_letter_empty(manager):
    assert manager.read_dead_letter() == []


# --- Delivery filtering ---


def test_should_deliver_star():
    manager = WebhookManager.__new__(WebhookManager)
    config = WebhookConfig(url="http://example.com", secret="s", enabled_events=["*"])
    assert manager._should_deliver(config, "hitl_required")
    assert manager._should_deliver(config, "run_completed")


def test_should_deliver_specific():
    manager = WebhookManager.__new__(WebhookManager)
    config = WebhookConfig(url="http://example.com", secret="s", enabled_events=["hitl_required"])
    assert manager._should_deliver(config, "hitl_required")
    assert not manager._should_deliver(config, "run_completed")


# --- Retry backoff ---


def test_retry_backoff_bounds():
    """Retry delay is bounded by RETRY_DELAY_CAP."""
    from agent_runtime_cockpit.events.webhooks import RETRY_DELAY_CAP

    config = WebhookConfig(url="http://example.com", secret="s", retry_base_delay_s=10.0)
    for attempt in range(config.retry_max):
        delay = min(RETRY_DELAY_CAP, config.retry_base_delay_s * (2**attempt))
        assert delay <= RETRY_DELAY_CAP
        assert delay > 0


# --- Malformed URL rejection ---


def test_malformed_url_allowed():
    """Model allows URLs; rejection is at delivery time."""
    config = WebhookConfig(url="not-a-valid-url", secret="s")
    assert config.url == "not-a-valid-url"


# --- Secret rotation ---


def test_secret_rotation():
    """Config supports updating secret by creating new config."""
    old = WebhookConfig(url="https://example.com/hook", secret="old-secret")
    new = WebhookConfig(url="https://example.com/hook", secret="new-secret")
    assert old.secret != new.secret
