"""CLI tests for receipt/contract/autopsy show, export, verify commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.protocol.failure_autopsy import FailureAutopsy
from agent_runtime_cockpit.protocol.run_contract import RunContract
from agent_runtime_cockpit.protocol.run_receipt import RunReceipt

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "cockpit"

RCPT_ID = "rcpt_01JKLMNOPQRSTUVWXYZ1"
RUN_ID = "run_test_001"
CTR_ID = "ctr_01JABCDEFGHIJKLMNOPQ"

TEST_KEY = "arc-dev-key-change-in-production"


def _has(cli_app, name: str) -> bool:
    if hasattr(cli_app, "commands"):
        return name in cli_app.commands
    if cli_app.__class__.__name__ == "Typer":
        names = {c.name for c in cli_app.registered_commands if c.name}
        return name in names
    return False


def _sub_has(cli_app, parent: str, name: str) -> bool:
    if cli_app.__class__.__name__ == "Typer":
        groups = {g.typer_instance: g.name for g in cli_app.registered_groups}
        for typer_inst, gname in groups.items():
            if gname == parent:
                return any(c.name == name for c in typer_inst.registered_commands if c.name)
    return False


def _seed_receipt(ws: Path, run_id: str = RUN_ID, status: str = "completed") -> RunReceipt:
    receipt = RunReceipt(
        receipt_id=RCPT_ID,
        run_id=run_id,
        status=status,
        summary="Test receipt",
        cost_usd=0.01,
        duration_ms=1000,
    )
    receipt.sign(TEST_KEY)
    receipts_dir = ws / ".arc" / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    (receipts_dir / f"{run_id}.receipt.json").write_text(
        receipt.model_dump_json(indent=2, by_alias=True)
    )
    return receipt


def _seed_contract(ws: Path) -> RunContract:
    contract = RunContract(
        contract_id=CTR_ID,
        run_id=RUN_ID,
        session_id="ses_test_001",
        objective="Test objective",
        runtime="swarmgraph",
        mode="build",
        allowed_tools=["read_file", "search_codebase"],
        write_scope=["src/**/*.py"],
    )
    traces_dir = ws / ".arc" / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    (traces_dir / f"{RUN_ID}.contract.json").write_text(contract.model_dump_json(indent=2))
    return contract


def _seed_autopsy(ws: Path) -> FailureAutopsy:
    autopsy = FailureAutopsy(
        run_id="run_test_failed_001",
        probable_cause="Tool execution timeout",
        confidence="high",
        failed_node="reviewer",
        knows=["Node was active for 45.2s"],
        guesses=["Search tool may be rate-limited"],
        retry_options=[{"label": "Retry", "risk": "low"}],
    )
    traces_dir = ws / ".arc" / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    (traces_dir / "run_test_failed_001.autopsy.json").write_text(
        autopsy.model_dump_json(indent=2, by_alias=True)
    )
    return autopsy


# ─── receipt show ─────────────────────────────────────────────────────────────


@pytest.mark.needs("receipt")
def test_receipt_show_missing(run_cli, workspace):
    r = run_cli(["receipt", "show", "nosuch"])
    assert r.exit_code != 0
    assert "not found" in (r.stdout + r.stderr).lower()


@pytest.mark.needs("receipt")
def test_receipt_show_prints_receipt_info(run_cli, workspace):
    _seed_receipt(workspace)
    r = run_cli(["receipt", "show", RUN_ID])
    assert r.exit_code == 0
    assert RCPT_ID in r.stdout
    assert "completed" in r.stdout.lower()


@pytest.mark.needs("receipt")
def test_receipt_show_with_json_flag(run_cli, workspace):
    _seed_receipt(workspace)
    r = run_cli(["receipt", "show", RUN_ID, "--json"])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["data"]["receipt_id"] == RCPT_ID
    assert data["data"]["status"] == "completed"


# ─── receipt export ───────────────────────────────────────────────────────────


@pytest.mark.needs("receipt")
def test_receipt_export_missing_gives_error(run_cli, workspace):
    r = run_cli(["receipt", "export", "nosuch"])
    assert r.exit_code != 0
    assert "not found" in (r.stdout + r.stderr).lower()


@pytest.mark.needs("receipt")
def test_receipt_export_writes_json(run_cli, workspace):
    _seed_receipt(workspace)
    r = run_cli(["receipt", "export", RUN_ID])
    assert r.exit_code == 0
    export_path = workspace / ".arc" / "receipts" / f"{RUN_ID}.receipt.json"
    assert export_path.exists()
    data = json.loads(export_path.read_text())
    assert data["receipt_id"] == RCPT_ID


@pytest.mark.needs("receipt")
def test_receipt_export_markdown(run_cli, workspace):
    _seed_receipt(workspace)
    r = run_cli(["receipt", "export", RUN_ID, "--format", "markdown"])
    assert r.exit_code == 0
    md_path = workspace / ".arc" / "receipts" / f"{RUN_ID}.receipt.md"
    assert md_path.exists()
    content = md_path.read_text()
    assert RCPT_ID in content
    assert "completed" in content.lower()


@pytest.mark.needs("receipt")
def test_receipt_export_custom_output_path(run_cli, workspace):
    _seed_receipt(workspace)
    out_path = workspace / "my-receipt.json"
    r = run_cli(["receipt", "export", RUN_ID, "--output", str(out_path)])
    assert r.exit_code == 0
    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert data["receipt_id"] == RCPT_ID


# ─── receipt verify ───────────────────────────────────────────────────────────


@pytest.mark.needs("receipt")
def test_receipt_verify_missing_file(run_cli, workspace):
    r = run_cli(["receipt", "verify", str(workspace / "nonexistent.json")])
    assert r.exit_code != 0
    assert "not found" in (r.stdout + r.stderr).lower()


@pytest.mark.needs("receipt")
def test_receipt_verify_untampered(run_cli, workspace):
    _seed_receipt(workspace)
    path = workspace / ".arc" / "receipts" / f"{RUN_ID}.receipt.json"
    r = run_cli(["receipt", "verify", str(path)])
    assert r.exit_code == 0
    assert "VALID" in r.stdout
    assert RCPT_ID in r.stdout


@pytest.mark.needs("receipt")
def test_receipt_verify_tampered(run_cli, workspace):
    _seed_receipt(workspace)
    path = workspace / ".arc" / "receipts" / f"{RUN_ID}.receipt.json"
    data = json.loads(path.read_text())
    data["summary"] = "tampered"
    path.write_text(json.dumps(data, indent=2))
    r = run_cli(["receipt", "verify", str(path)])
    assert r.exit_code != 0
    assert "INVALID" in r.stdout


@pytest.mark.needs("receipt")
def test_receipt_verify_with_json_output(run_cli, workspace):
    _seed_receipt(workspace)
    path = workspace / ".arc" / "receipts" / f"{RUN_ID}.receipt.json"
    r = run_cli(["receipt", "verify", str(path), "--json"])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["data"]["receipt_id"] == RCPT_ID
    assert data["data"]["valid"] is True


@pytest.mark.needs("receipt")
def test_receipt_verify_without_key_uses_audit_key_manager(run_cli, workspace, monkeypatch):
    """Verify works without --key when receipt was signed with AuditKeyManager key."""
    test_key = "arc-test-audit-key-32bytes-for-hmac!!"
    monkeypatch.setenv("ARC_AUDIT_HMAC_KEY", test_key)

    receipt = _seed_receipt(workspace)
    receipt.sign(test_key)
    path = workspace / ".arc" / "receipts" / f"{RUN_ID}.receipt.json"
    path.write_text(receipt.model_dump_json(indent=2, by_alias=True))

    r = run_cli(["receipt", "verify", str(path)])
    assert r.exit_code == 0, f"Failed: stdout={r.stdout} stderr={r.stderr}"
    assert "VALID" in r.stdout


@pytest.mark.needs("receipt")
def test_receipt_verify_explicit_key_still_works(run_cli, workspace):
    """Explicit --key still verifies even when AuditKeyManager key differs."""
    explicit_key = "explicit-test-key-not-from-audit-manager"
    receipt = _seed_receipt(workspace)
    receipt.sign(explicit_key)
    path = workspace / ".arc" / "receipts" / f"{RUN_ID}.receipt.json"
    path.write_text(receipt.model_dump_json(indent=2, by_alias=True))

    r = run_cli(["receipt", "verify", str(path), "--key", explicit_key])
    assert r.exit_code == 0, f"Failed: stdout={r.stdout} stderr={r.stderr}"
    assert "VALID" in r.stdout


# ─── contract show ────────────────────────────────────────────────────────────


@pytest.mark.needs("runs")
def test_contract_show_missing(run_cli, workspace):
    r = run_cli(["runs", "contract", "nosuch"])
    assert r.exit_code != 0
    assert "not found" in (r.stdout + r.stderr).lower()


@pytest.mark.needs("runs")
def test_contract_show_prints_contract_info(run_cli, workspace):
    _seed_contract(workspace)
    r = run_cli(["runs", "contract", RUN_ID])
    assert r.exit_code == 0
    assert CTR_ID in r.stdout
    assert "swarmgraph" in r.stdout.lower()


@pytest.mark.needs("runs")
def test_contract_show_with_json(run_cli, workspace):
    _seed_contract(workspace)
    r = run_cli(["runs", "contract", RUN_ID, "--json"])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["data"]["contract_id"] == CTR_ID
    assert data["data"]["objective"] == "Test objective"


# ─── autopsy show ─────────────────────────────────────────────────────────────


@pytest.mark.needs("runs")
def test_autopsy_show_missing(run_cli, workspace):
    r = run_cli(["runs", "autopsy", "nosuch"])
    assert r.exit_code != 0
    assert "not found" in (r.stdout + r.stderr).lower()


@pytest.mark.needs("runs")
def test_autopsy_show_prints_knowns_before_guesses(run_cli, workspace):
    _seed_autopsy(workspace)
    r = run_cli(["runs", "autopsy", "run_test_failed_001"])
    assert r.exit_code == 0
    # Knowns appear in output
    assert "Node was active" in r.stdout
    # Guesses appear in output
    assert "Search tool may be rate-limited" in r.stdout


@pytest.mark.needs("runs")
def test_autopsy_show_with_json(run_cli, workspace):
    _seed_autopsy(workspace)
    r = run_cli(["runs", "autopsy", "run_test_failed_001", "--json"])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
    assert data["data"]["probable_cause"] == "Tool execution timeout"
    assert "Node was active for 45.2s" in data["data"]["knows"]
    assert "Search tool may be rate-limited" in data["data"]["guesses"]


# ─── e2e: receipt roundtrip ──────────────────────────────────────────────────


@pytest.mark.needs("receipt")
def test_receipt_show_export_verify_roundtrip(run_cli, workspace):
    _seed_receipt(workspace)
    path = workspace / ".arc" / "receipts" / f"{RUN_ID}.receipt.json"

    r_show = run_cli(["receipt", "show", RUN_ID])
    assert r_show.exit_code == 0
    assert RCPT_ID in r_show.stdout

    r_verify = run_cli(["receipt", "verify", str(path)])
    assert r_verify.exit_code == 0
    assert "VALID" in r_verify.stdout

    r_export = run_cli(["receipt", "export", RUN_ID, "--format", "markdown"])
    assert r_export.exit_code == 0
    md_path = workspace / ".arc" / "receipts" / f"{RUN_ID}.receipt.md"
    assert md_path.exists()
