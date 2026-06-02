"""CLI: arc ir compile / inspect / validate / policy (Commit 4)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


FIX = Path(__file__).parent / "fixtures"


def _copy_fixture(name: str, dest_dir: Path) -> Path:
    src = FIX / name
    dst = dest_dir / name
    shutil.copy(src, dst)
    return dst


def test_ir_help_lists_commands(run_cli) -> None:
    res = run_cli("ir --help")
    assert res.exit_code == 0
    for cmd in ("compile", "inspect", "validate", "policy"):
        assert cmd in res.stdout


def test_ir_compile_writes_deterministic_output(run_cli, tmp_path) -> None:
    wf = _copy_fixture("native_minimal.workflow.json", tmp_path)
    out1 = tmp_path / "a.ir.json"
    out2 = tmp_path / "b.ir.json"

    r1 = run_cli(f"ir compile {wf} --runtime native --no-sdk-risk --out {out1} --json")
    r2 = run_cli(f"ir compile {wf} --runtime native --no-sdk-risk --out {out2} --json")
    assert r1.exit_code == 0 and r2.exit_code == 0
    assert out1.read_text() == out2.read_text()  # byte-identical → deterministic


def test_ir_inspect_emits_summary(run_cli, tmp_path) -> None:
    ir_file = _copy_fixture("mcp_graph.ir.json", tmp_path)
    res = run_cli(f"ir inspect {ir_file} --json")
    assert res.exit_code == 0
    payload = json.loads(res.stdout)["data"]
    assert payload["graph_id"] == "wf-mcp"
    assert payload["node_kinds"].get("mcp_tool") == 1


def test_ir_validate_passes_for_good_fixture(run_cli, tmp_path) -> None:
    ir_file = _copy_fixture("native_minimal.ir.json", tmp_path)
    res = run_cli(f"ir validate {ir_file} --json")
    assert res.exit_code == 0
    assert json.loads(res.stdout)["data"]["ok"] is True


def test_ir_compile_fails_closed_for_invalid(run_cli, tmp_path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps(
            {
                "id": "bad",
                "name": "bad",
                "runtime": "native",
                "nodes": [{"id": "a", "type": "agent", "label": "a"}],
                "edges": [{"id": "e", "from_node": "a", "to_node": "ghost"}],
                "entry_points": ["a"],
            }
        )
    )
    res = run_cli(f"ir compile {bad} --no-sdk-risk --json")
    assert res.exit_code == 2  # fail-closed exit code


def test_ir_compile_missing_file_is_input_error(run_cli, tmp_path) -> None:
    res = run_cli(f"ir compile {tmp_path / 'nope.json'} --json")
    assert res.exit_code == 1
