"""Tests for A2A loopback client."""

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.a2a.client import (
    NonLoopbackError,
    UnapprovedCardError,
    UnsignedCardError,
    _validate_url,
    approve_card,
    invoke_sync,
    is_card_approved,
    revoke_card,
)
from agent_runtime_cockpit.a2a.models import AgentCard, AgentCardSignature


def test_loopback_valid():
    _validate_url("http://127.0.0.1:8080/")
    _validate_url("http://127.0.0.1:9000/a2a")
    _validate_url("http://127.0.0.1:80")


def test_loopback_rejects_non_local():
    with pytest.raises(NonLoopbackError):
        _validate_url("http://192.168.1.1:8080/")
    with pytest.raises(NonLoopbackError):
        _validate_url("http://example.com:8080/")
    with pytest.raises(NonLoopbackError):
        _validate_url("https://127.0.0.1:8080/")
    with pytest.raises(NonLoopbackError):
        _validate_url("http://0.0.0.0:8080/")


def test_unsigned_card_refused(tmp_path: Path):
    card = AgentCard(name="no-sig", url="http://127.0.0.1:9000/")
    with pytest.raises(UnsignedCardError):
        invoke_sync(card, payload={}, arc_dir=tmp_path)


def test_unapproved_card_refused(tmp_path: Path):
    card = AgentCard(
        name="not-approved",
        url="http://127.0.0.1:9000/",
        signature=AgentCardSignature(algorithm="hmac_sha256", signature="x"),
    )
    with pytest.raises(UnapprovedCardError):
        invoke_sync(card, payload={}, arc_dir=tmp_path)


def test_approve_and_check(tmp_path: Path):
    card = AgentCard(name="my-agent", version="1.0.0")
    assert not is_card_approved(card, arc_dir=tmp_path)
    approve_card(card, arc_dir=tmp_path)
    assert is_card_approved(card, arc_dir=tmp_path)


def test_revoke(tmp_path: Path):
    card = AgentCard(name="rev", version="1.0.0")
    approve_card(card, arc_dir=tmp_path)
    assert revoke_card("rev", arc_dir=tmp_path) is True
    assert not is_card_approved(card, arc_dir=tmp_path)
    assert revoke_card("rev", arc_dir=tmp_path) is False


def test_approved_json_persists(tmp_path: Path):
    card = AgentCard(name="persist")
    approve_card(card, arc_dir=tmp_path)
    path = tmp_path / "a2a" / "approved.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert "persist" in data


def test_non_loopback_url_invoke(tmp_path: Path):
    card = AgentCard(
        name="remote",
        url="http://192.168.1.1:8080/",
        signature=AgentCardSignature(algorithm="hmac_sha256", signature="x"),
    )
    approve_card(card, arc_dir=tmp_path)
    with pytest.raises(NonLoopbackError):
        invoke_sync(card, payload={}, arc_dir=tmp_path)
