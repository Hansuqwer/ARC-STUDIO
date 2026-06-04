"""Tests for A2A generator."""

import json
from pathlib import Path

from agent_runtime_cockpit.a2a.generator import (
    generate_agent_card,
    load_agent_card,
    verify_agent_card,
    write_agent_card,
)


def test_generate_unsigned():
    card = generate_agent_card(name="test")
    assert card.name == "test"
    assert card.signature is None


def test_generate_signed():
    card = generate_agent_card(name="signed", secret_key="s3cret")
    assert card.signature is not None
    assert card.signature.algorithm == "hmac_sha256"


def test_verify_valid():
    card = generate_agent_card(name="v", secret_key="key1")
    assert verify_agent_card(card, "key1") is True


def test_verify_invalid_key():
    card = generate_agent_card(name="v", secret_key="key1")
    assert verify_agent_card(card, "wrong") is False


def test_verify_unsigned():
    card = generate_agent_card(name="u")
    assert verify_agent_card(card, "any") is False


def test_deterministic_output():
    a = generate_agent_card(name="det", version="1.0.0", secret_key="k")
    b = generate_agent_card(name="det", version="1.0.0", secret_key="k")
    assert a.model_dump(mode="json") == b.model_dump(mode="json")


def test_write_and_load(tmp_path: Path):
    card = generate_agent_card(name="disk", secret_key="sk")
    out = write_agent_card(card, arc_dir=tmp_path)
    assert out.exists()
    loaded = load_agent_card(arc_dir=tmp_path)
    assert loaded is not None
    assert loaded.name == "disk"
    assert loaded.signature is not None


def test_write_creates_dirs(tmp_path: Path):
    arc = tmp_path / "custom"
    card = generate_agent_card(name="new")
    out = write_agent_card(card, arc_dir=arc)
    assert out.exists()
    assert "a2a" in str(out)


def test_load_missing(tmp_path: Path):
    assert load_agent_card(arc_dir=tmp_path) is None


def test_written_json_sorted(tmp_path: Path):
    card = generate_agent_card(name="sorted", description="z first?")
    path = write_agent_card(card, arc_dir=tmp_path)
    data = json.loads(path.read_text())
    keys = list(data.keys())
    assert keys == sorted(keys)
