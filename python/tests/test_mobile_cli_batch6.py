"""Batch 6 Track C: CLI surfaces for the new mobile modules (gate/flags/egress/queue/...)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli.mobile import mobile_app

runner = CliRunner()


def _json(result):
    return json.loads(result.output)


def test_gate_evaluate_default_denied_fixtures() -> None:
    res = runner.invoke(mobile_app, ["gate", "evaluate", "device.camera.capture.mock", "--json"])
    assert res.exit_code == 0, res.output
    data = _json(res)["data"]
    assert data["eligible"] is False
    assert data["route"] == "fixtures"
    assert "compliance_artifact_missing" in data["missing"]
    assert "signed_plan_invalid" in data["missing"]


def test_flags_enable_list_killswitch(tmp_path) -> None:
    store = str(tmp_path / "flags.json")
    en = runner.invoke(mobile_app, ["flags", "enable", "native.camera", "--store", store, "--json"])
    assert en.exit_code == 0, en.output
    assert _json(en)["data"]["flags"]["native.camera"] is True

    lst = runner.invoke(mobile_app, ["flags", "list", "--store", store, "--json"])
    assert _json(lst)["data"]["effective"]["native.camera"] is True

    ks = runner.invoke(mobile_app, ["flags", "kill-switch", "on", "--store", store, "--json"])
    assert _json(ks)["data"]["kill_switch"] is True
    # kill switch overrides effective to off
    assert _json(ks)["data"]["effective"]["native.camera"] is False


def test_flags_killswitch_bad_state(tmp_path) -> None:
    res = runner.invoke(
        mobile_app, ["flags", "kill-switch", "maybe", "--store", str(tmp_path / "f.json")]
    )
    assert res.exit_code == 1


def test_egress_check_allow_deny_block() -> None:
    ok_res = runner.invoke(mobile_app, ["egress", "check", "100", "--budget", "1000", "--json"])
    assert _json(ok_res)["data"]["allowed"] is True

    over = runner.invoke(mobile_app, ["egress", "check", "2000", "--budget", "1000", "--json"])
    assert _json(over)["data"]["allowed"] is False

    crit = runner.invoke(
        mobile_app,
        ["egress", "check", "10", "--budget", "1000", "--classification", "critical", "--json"],
    )
    assert _json(crit)["data"]["allowed"] is False
    assert "blocked" in _json(crit)["data"]["reason"]


def test_queue_enqueue_status_flush_hash_only(tmp_path) -> None:
    store = str(tmp_path / "q.json")
    secret = "RAW-CLI-PAYLOAD-7q"
    enq = runner.invoke(
        mobile_app,
        [
            "queue",
            "enqueue",
            "app.memory.write.mock",
            "--payload",
            json.dumps({"v": secret}),
            "--store",
            store,
            "--json",
        ],
    )
    assert enq.exit_code == 0, enq.output
    assert secret not in enq.output  # hash-only, no raw payload
    assert len(_json(enq)["data"]["payload_hash"]) == 64

    st = runner.invoke(mobile_app, ["queue", "status", "--store", store, "--json"])
    assert _json(st)["data"]["pending"] == 1

    fl = runner.invoke(mobile_app, ["queue", "flush", "--store", store, "--json"])
    assert _json(fl)["data"]["flushed"] == 1
    assert (
        _json(runner.invoke(mobile_app, ["queue", "status", "--store", store, "--json"]))["data"][
            "pending"
        ]
        == 0
    )


def test_secure_store_never_prints_plaintext(tmp_path) -> None:
    store = str(tmp_path / "ss.json")
    key_file = str(tmp_path / "ss.key")
    secret = "TOP-SECRET-CLI-VALUE-42x"
    common = ["--store", store, "--key-file", key_file, "--json"]

    put = runner.invoke(
        mobile_app,
        ["secure-store", "put", "api_key", secret, "--classification", "critical", *common],
    )
    assert put.exit_code == 0, put.output
    assert secret not in put.output  # value never echoed
    assert _json(put)["data"]["stored"] is True

    # at-rest file holds ciphertext only
    assert secret not in (tmp_path / "ss.json").read_text()

    get = runner.invoke(mobile_app, ["secure-store", "get", "api_key", *common])
    assert get.exit_code == 0
    assert secret not in get.output
    assert _json(get)["data"]["value"] == "[REDACTED]"
    assert _json(get)["data"]["classification"] == "critical"

    exp = runner.invoke(mobile_app, ["secure-store", "export", *common])
    assert secret not in exp.output
    assert all("value" not in e for e in _json(exp)["data"]["entries"])

    dele = runner.invoke(mobile_app, ["secure-store", "delete", "api_key", *common])
    assert _json(dele)["data"]["deleted"] is True


def test_secure_store_get_missing(tmp_path) -> None:
    res = runner.invoke(
        mobile_app,
        [
            "secure-store",
            "get",
            "nope",
            "--store",
            str(tmp_path / "s.json"),
            "--key-file",
            str(tmp_path / "s.key"),
        ],
    )
    assert res.exit_code == 1


def test_audit_retention_prune(tmp_path) -> None:
    log = tmp_path / "decisions.jsonl"
    log.write_text("".join(json.dumps({"i": i}) + "\n" for i in range(10)), encoding="utf-8")
    res = runner.invoke(
        mobile_app, ["audit-retention", "--file", str(log), "--max-entries", "3", "--json"]
    )
    assert res.exit_code == 0, res.output
    data = _json(res)["data"]
    assert data["before"] == 10 and data["after"] == 3 and data["removed"] == 7
    assert len(log.read_text().strip().splitlines()) == 3


def test_simulate_routes_through_gate(tmp_path) -> None:
    from agent_runtime_cockpit.mobile import MobileActionPlan
    from agent_runtime_cockpit.mobile.models import MobileActionStep

    plan = MobileActionPlan(
        plan_id="gate-demo",
        steps=[
            MobileActionStep(step_id="s1", capability_id="app.memory.write.mock"),
            MobileActionStep(step_id="s2", capability_id="device.camera.capture.mock"),
        ],
    )
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(plan.model_dump_json(), encoding="utf-8")

    res = runner.invoke(mobile_app, ["simulate", str(plan_file), "--json"])
    assert res.exit_code in (0, 1), res.output  # exit 1 only if a step blocked
    gate = _json(res)["data"]["gate"]
    assert gate["route"] == "fixtures"
    assert gate["all_fixtures"] is True
    assert {e["capability_id"] for e in gate["evaluated"]} == {
        "app.memory.write.mock",
        "device.camera.capture.mock",
    }
    assert all(e["route"] == "fixtures" for e in gate["evaluated"])
