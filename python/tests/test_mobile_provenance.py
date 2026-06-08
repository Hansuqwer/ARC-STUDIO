"""R79.4 / Batch 7 T26: mobile supply-chain provenance attestation."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from agent_runtime_cockpit.mobile import build_provenance, sign_provenance, verify_provenance

_KEY = b"provenance-key-32-bytes-aaaaaaaa"


def test_build_provenance_has_sbom_and_digest() -> None:
    prov = build_provenance("1.2.3")
    assert prov["schema"] == "arc-mobile-provenance/v1"
    assert prov["subject"]["version"] == "1.2.3"
    assert len(prov["sbom_sha256"]) == 64
    assert "sbom" in prov and prov["component_count"] >= 0


def test_sign_and_verify_roundtrip() -> None:
    env = sign_provenance(build_provenance("1.0.0"), _KEY)
    assert verify_provenance(env, _KEY) is True


def test_tamper_or_wrong_key_fails_closed() -> None:
    env = sign_provenance(build_provenance("1.0.0"), _KEY)
    assert verify_provenance(env, b"wrong-key-32-bytes-bbbbbbbbbbbbbb") is False
    env["provenance"]["subject"]["version"] = "9.9.9"  # tamper
    assert verify_provenance(env, _KEY) is False
    assert verify_provenance({"provenance": {}, "signature": ""}, _KEY) is False  # malformed


def test_cli_provenance_sign(tmp_path) -> None:
    from agent_runtime_cockpit.cli._subapps import mobile_app

    key_file = tmp_path / "k.key"
    key_file.write_bytes(_KEY)
    res = CliRunner().invoke(
        mobile_app,
        ["provenance", "--version", "2.0.0", "--sign", "--key-file", str(key_file), "--json"],
    )
    assert res.exit_code == 0, res.output
    env = json.loads(res.output)["data"]
    assert verify_provenance(env, _KEY) is True
