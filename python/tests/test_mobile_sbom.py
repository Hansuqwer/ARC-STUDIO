"""Tests for Phase 12e: mobile SDK SBOM generator."""

from __future__ import annotations


from typer.testing import CliRunner

from agent_runtime_cockpit.cli.mobile import mobile_app
from agent_runtime_cockpit.mobile import generate_sbom

runner = CliRunner()


def test_sbom_is_valid_cyclonedx_shape() -> None:
    sbom = generate_sbom("1.2.3")
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    assert sbom["metadata"]["component"]["name"] == "arc-mobile-runtime"
    assert {"name": "arc:simulator_preview", "value": "true"} in sbom["metadata"]["properties"]
    assert isinstance(sbom["components"], list) and sbom["components"]


def test_sbom_includes_key_modules_and_bindings() -> None:
    names = {c["name"] for c in generate_sbom()["components"]}
    # introspected python modules
    for mod in ["arc-mobile.secure_store", "arc-mobile.capability_gate", "arc-mobile.siem_export"]:
        assert mod in names, f"{mod} absent from SBOM"
    # framework bindings
    assert "arc-mobile-runtime-expo" in names
    assert "arc-mobile-runtime-react-native" in names
    assert "arc_mobile_runtime-flutter" in names


def test_sbom_version_propagates_and_deterministic() -> None:
    a = generate_sbom("9.9.9")
    b = generate_sbom("9.9.9")
    assert a == b
    assert all(c["version"] == "9.9.9" for c in a["components"])
    # components sorted by name
    names = [c["name"] for c in a["components"]]
    assert names == sorted(names)


def test_cli_sbom() -> None:
    res = runner.invoke(mobile_app, ["sbom", "--json"])
    assert res.exit_code == 0, res.output
    assert "CycloneDX" in res.output
