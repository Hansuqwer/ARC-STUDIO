"""CLI tests for battle commands (Phase 34/R26A)."""

from __future__ import annotations

import json


def test_battle_command_registered(run_cli):
    result = run_cli("battle --help")

    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "show" in result.stdout
    assert "config" in result.stdout


def test_battle_run_json_envelope(run_cli):
    result = run_cli('battle run "Write a deterministic stub" --workers 2 --json')

    assert result.exit_code == 0
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is True
    assert envelope["data"]["status"] == "completed"
    assert envelope["data"]["battle_id"].startswith("battle-")
    assert len(envelope["data"]["candidates"]) == 2
    assert envelope["version"] == "1.0"


def test_battle_run_json_error_envelope(run_cli):
    result = run_cli('battle run "bad" --workers 3 --json')

    assert result.exit_code == 1
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is False
    assert envelope["error"]["code"] == "INVALID_INPUT"
    assert "Only 2 or 4 workers" in envelope["error"]["message"]


def test_battle_config_validate_json(run_cli, tmp_path):
    config_path = tmp_path / "battle.json"
    config_path.write_text('{"workers": 2, "topology": "flat"}')

    result = run_cli(f"battle config validate {config_path} --json")

    assert result.exit_code == 0
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is True
    assert envelope["data"]["valid"] is True
    assert envelope["data"]["format"] == "json"
    assert envelope["data"]["keys"] == ["topology", "workers"]


def test_battle_export_json_envelope(run_cli):
    run_result = run_cli('battle run "export me" --workers 2 --json')
    battle_id = json.loads(run_result.stdout)["data"]["battle_id"]

    export_result = run_cli(f"battle export {battle_id} --json")

    assert export_result.exit_code == 0
    envelope = json.loads(export_result.stdout)
    assert envelope["ok"] is True
    assert envelope["data"]["battle"]["id"] == battle_id
