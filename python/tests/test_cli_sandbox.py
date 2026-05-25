import json
import os
import platform
import shutil
import subprocess

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.security.sandbox import (
    CommandClassification,
    classify_command,
    microvm_preflight,
)


def _payload(result):
    return json.loads(result.output)


def test_read_only_command_allowed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app, ["sandbox", "run", "--json", "--policy", "local-safe", "--", "pwd"]
    )
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert data["decision"]["allowed"] is True
    assert data["classification"] == "read_only"


def test_network_command_denied_by_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app, ["sandbox", "run", "--json", "--", "curl", "https://example.com"]
    )
    assert result.exit_code == 3
    data = _payload(result)["data"]
    assert data["decision"]["allowed"] is False
    assert data["classification"] == "network"


def test_destructive_command_denied_by_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["sandbox", "run", "--json", "--", "rm", "-rf", "."])
    assert result.exit_code == 3
    assert _payload(result)["data"]["classification"] == "destructive"


def test_command_writing_outside_workspace_denied_by_cwd(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    monkeypatch.chdir(outside)
    result = CliRunner().invoke(
        app, ["sandbox", "run", "--json", "--workspace", str(workspace), "--", "pwd"]
    )
    assert result.exit_code == 2
    assert _payload(result)["ok"] is False


def test_symlink_escape_denied(tmp_path):
    from agent_runtime_cockpit.security.sandbox import ensure_workspace_cwd

    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    link = workspace / "link"
    link.symlink_to(outside, target_is_directory=True)
    import pytest

    with pytest.raises(ValueError):
        ensure_workspace_cwd(link, workspace)


def test_env_secret_stripped(tmp_path, monkeypatch):
    from agent_runtime_cockpit.isolation.subprocess import SubprocessIsolationProvider
    import asyncio

    monkeypatch.setenv("OPENAI_API_KEY", "sk-secretsecretsecretsecretsecretsecret")
    code = "import os; print(os.environ.get('OPENAI_API_KEY', 'missing'))"
    provider = SubprocessIsolationProvider(workspace_root=tmp_path)
    result = asyncio.run(provider.execute(["python", "-c", code], cwd=tmp_path, timeout_seconds=5))
    assert result.stdout.strip() == "missing"


def test_timeout_kills_process(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = "import time; time.sleep(60)"
    from agent_runtime_cockpit.isolation.subprocess import SubprocessIsolationProvider

    provider = SubprocessIsolationProvider(workspace_root=tmp_path)
    import asyncio

    result = asyncio.run(provider.execute(["python", "-c", code], cwd=tmp_path, timeout_seconds=1))
    assert result.killed is True
    assert result.kill_reason == "timeout"


def test_stdout_stderr_capped(tmp_path):
    from agent_runtime_cockpit.isolation.subprocess import SubprocessIsolationProvider
    import asyncio

    provider = SubprocessIsolationProvider(workspace_root=tmp_path, max_output_bytes=10)
    code = "import sys; print('x'*100); print('y'*100, file=sys.stderr)"
    result = asyncio.run(provider.execute(["python", "-c", code], cwd=tmp_path, timeout_seconds=5))
    assert result.stdout_truncated is True
    assert result.stderr_truncated is True
    assert len(result.stdout.encode("utf-8")) == 10
    assert len(result.stderr.encode("utf-8")) == 10


def test_stdout_stderr_caps_do_not_buffer_large_output(tmp_path):
    from agent_runtime_cockpit.isolation.subprocess import SubprocessIsolationProvider
    import asyncio

    provider = SubprocessIsolationProvider(workspace_root=tmp_path, max_output_bytes=128)
    code = (
        "import sys; "
        "sys.stdout.write('x' * 200000); sys.stdout.flush(); "
        "sys.stderr.write('y' * 200000); sys.stderr.flush()"
    )
    result = asyncio.run(provider.execute(["python", "-c", code], cwd=tmp_path, timeout_seconds=5))
    assert result.exit_code == 0
    assert result.stdout_truncated is True
    assert result.stderr_truncated is True
    assert len(result.stdout.encode("utf-8")) == 128
    assert len(result.stderr.encode("utf-8")) == 128


def test_json_output_stable(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["policy", "explain", "--json", "--", "ls", "-la"])
    assert result.exit_code == 0
    data = _payload(result)["data"]
    assert set(data) == {"command", "decision"}


def test_audit_event_emitted_for_allowed_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / "audit"))
    result = CliRunner().invoke(app, ["sandbox", "run", "--json", "--", "pwd"])
    event = _payload(result)["data"]["audit_event"]
    assert event["type"] == "SANDBOX_COMMAND"
    assert event["allowed"] is True
    assert (tmp_path / "audit" / "sandbox.audit.jsonl").exists()
    assert (tmp_path / "audit" / "sandbox.events.jsonl").exists()


def test_denial_event_emitted_for_denied_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / "audit"))
    result = CliRunner().invoke(
        app, ["sandbox", "run", "--json", "--", "curl", "https://example.com"]
    )
    event = _payload(result)["data"]["audit_event"]
    assert event["type"] == "SANDBOX_DENIED"
    assert event["allowed"] is False
    assert (tmp_path / "audit" / "sandbox.audit.jsonl").exists()


def test_ask_decline_preserves_denial_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app, ["sandbox", "run", "--ask", "--", "curl", "https://example.com"], input="n\n"
    )
    assert result.exit_code == 3
    assert '"allowed": false' in result.output
    assert '"approval_required": true' in result.output


def test_ask_approval_executes_unknown_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["sandbox", "run", "--ask", "--", "true"], input="y\n")
    assert result.exit_code == 0, result.output
    assert '"allowed": true' in result.output
    assert '"approved": true' in result.output
    assert '"classification": "unknown"' in result.output


def test_ask_rejected_with_json_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app, ["sandbox", "run", "--json", "--ask", "--", "curl", "https://example.com"]
    )
    assert result.exit_code == 2
    assert _payload(result)["ok"] is False


def test_non_interactive_approval_tokens(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARC_SANDBOX_APPROVAL_STORE", str(tmp_path / ".arc" / "approvals.json"))
    approve = CliRunner().invoke(
        app, ["policy", "approve", "--json", "--token", "tok-1", "--", "true"]
    )
    assert approve.exit_code == 0, approve.output
    run = CliRunner().invoke(
        app, ["sandbox", "run", "--json", "--approval-token", "tok-1", "--", "true"]
    )
    assert run.exit_code == 0, run.output
    decision = _payload(run)["data"]["decision"]
    assert decision["allowed"] is True
    assert decision["approved"] is True
    assert decision["reason"] == "approval token"


def test_approval_removal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARC_SANDBOX_APPROVAL_STORE", str(tmp_path / ".arc" / "approvals.json"))
    CliRunner().invoke(app, ["policy", "approve", "--json", "--token", "tok-1", "--", "true"])
    revoke = CliRunner().invoke(app, ["policy", "revoke", "--json", "--token", "tok-1"])
    assert revoke.exit_code == 0, revoke.output
    assert _payload(revoke)["data"]["revoked"] == 1
    run = CliRunner().invoke(
        app, ["sandbox", "run", "--json", "--approval-token", "tok-1", "--", "true"]
    )
    assert run.exit_code == 3
    assert _payload(run)["data"]["decision"]["allowed"] is False


def test_approval_persistence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = tmp_path / ".arc" / "approvals.json"
    monkeypatch.setenv("ARC_SANDBOX_APPROVAL_STORE", str(store))
    result = CliRunner().invoke(
        app, ["policy", "approve", "--json", "--token", "tok-1", "--", "true"]
    )
    assert result.exit_code == 0, result.output
    assert store.exists()
    data = json.loads(store.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["approvals"][0]["policy"] == "local-safe"
    assert data["approvals"][0]["classification"] == "unknown"
    assert data["approvals"][0]["workspace_root"] == str(tmp_path.resolve())


def test_approval_token_is_hashed_with_ttl_and_private_file_mode(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = tmp_path / ".arc" / "approvals.json"
    monkeypatch.setenv("ARC_SANDBOX_APPROVAL_STORE", str(store))
    result = CliRunner().invoke(
        app, ["policy", "approve", "--json", "--token", "tok-secret", "--", "true"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(store.read_text(encoding="utf-8"))
    approval = data["approvals"][0]
    assert approval["token"] == ""
    assert approval["token_hash"]
    assert approval["expires_at"]
    assert "tok-secret" not in store.read_text(encoding="utf-8")
    assert oct(store.stat().st_mode & 0o777) == "0o600"


def test_expired_approval_token_denied(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = tmp_path / ".arc" / "approvals.json"
    monkeypatch.setenv("ARC_SANDBOX_APPROVAL_STORE", str(store))
    policy_file = tmp_path / "sandbox-policies.json"
    policy_file.write_text(
        json.dumps(
            {
                "version": 1,
                "policies": [{"version": 1, "name": "short", "approval_ttl_seconds": -1}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ARC_SANDBOX_POLICY_CONFIG", str(policy_file))
    approve = CliRunner().invoke(
        app, ["policy", "approve", "--json", "--policy", "short", "--token", "tok-1", "--", "true"]
    )
    assert approve.exit_code == 0, approve.output
    run = CliRunner().invoke(
        app,
        [
            "sandbox",
            "run",
            "--json",
            "--policy",
            "short",
            "--approval-token",
            "tok-1",
            "--",
            "true",
        ],
    )
    assert run.exit_code == 3
    assert _payload(run)["data"]["decision"]["allowed"] is False


def test_prune_expired_approvals_removes_stale_entries(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = tmp_path / ".arc" / "approvals.json"
    monkeypatch.setenv("ARC_SANDBOX_APPROVAL_STORE", str(store))
    policy_file = tmp_path / "sandbox-policies.json"
    policy_file.write_text(
        json.dumps(
            {
                "version": 1,
                "policies": [{"version": 1, "name": "short", "approval_ttl_seconds": -1}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ARC_SANDBOX_POLICY_CONFIG", str(policy_file))
    approve = CliRunner().invoke(
        app, ["policy", "approve", "--json", "--policy", "short", "--token", "tok-1", "--", "true"]
    )
    assert approve.exit_code == 0, approve.output
    data = json.loads(store.read_text(encoding="utf-8"))
    assert len(data["approvals"]) == 1
    prune = CliRunner().invoke(app, ["policy", "prune", "--json"])
    assert prune.exit_code == 0, prune.output
    result = _payload(prune)["data"]
    assert result["pruned"] == 1
    assert result["remaining"] == 0
    data = json.loads(store.read_text(encoding="utf-8"))
    assert len(data["approvals"]) == 0


def test_prune_keeps_non_expired_approvals(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = tmp_path / ".arc" / "approvals.json"
    monkeypatch.setenv("ARC_SANDBOX_APPROVAL_STORE", str(store))
    approve = CliRunner().invoke(
        app, ["policy", "approve", "--json", "--token", "tok-1", "--", "true"]
    )
    assert approve.exit_code == 0, approve.output
    prune = CliRunner().invoke(app, ["policy", "prune", "--json"])
    assert prune.exit_code == 0, prune.output
    result = _payload(prune)["data"]
    assert result["pruned"] == 0
    assert result["remaining"] == 1


def test_microvm_doctor_unavailable_gracefully(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    result = CliRunner().invoke(app, ["sandbox", "doctor", "--json"])
    assert result.exit_code == 0
    providers = _payload(result)["data"]["providers"]
    assert any(p.get("provider") == "microvm" for p in providers)


def test_linux_microvm_preflight_checks_kvm_and_binary(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        shutil, "which", lambda name: f"/usr/bin/{name}" if name == "firecracker" else None
    )
    data = microvm_preflight("Linux")
    assert data["platform"] == "linux"
    assert "kvm" in data
    assert data["binary"] == "/usr/bin/firecracker"


def test_macos_microvm_preflight_checks_lima(monkeypatch):
    monkeypatch.setattr(
        shutil, "which", lambda name: "/opt/homebrew/bin/limactl" if name == "limactl" else None
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout="limactl 1.0", stderr=""
        ),
    )
    data = microvm_preflight("Darwin")
    assert data["platform"] == "macos"
    assert data["binary"].endswith("limactl")
    assert data["limactl_version"]["ok"] is True


def test_windows_explicitly_unsupported():
    data = microvm_preflight("Windows")
    assert data["status"] == "blocked"
    assert "unsupported" in data["reason"].lower()


def test_microvm_provider_run_denied_even_with_integration_gate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
    monkeypatch.setattr(
        shutil, "which", lambda name: "/usr/bin/limactl" if name == "limactl" else None
    )
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    result = CliRunner().invoke(
        app, ["sandbox", "run", "--json", "--provider", "microvm", "--", "pwd"]
    )
    assert result.exit_code == 2
    assert _payload(result)["ok"] is False
    assert "not implemented/proven" in _payload(result)["error"]["message"]


def test_microvm_doctor_never_claims_execution_implemented(monkeypatch):
    from agent_runtime_cockpit.isolation.microvm import MicroVMIsolationProvider

    monkeypatch.setenv("ARC_MICROVM_INTEGRATION", "1")
    monkeypatch.setattr(
        shutil, "which", lambda name: "/usr/bin/limactl" if name == "limactl" else None
    )
    data = MicroVMIsolationProvider().describe()
    assert data["execution"] == "gated_unproven"
    assert data["execution"] != "implemented"


def test_custom_sandbox_policy_loaded_from_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    policy_file = tmp_path / "sandbox-policies.json"
    policy_file.write_text(
        json.dumps(
            {"version": 1, "policies": [{"version": 1, "name": "net-ok", "allow_network": True}]}
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ARC_SANDBOX_POLICY_CONFIG", str(policy_file))
    result = CliRunner().invoke(
        app,
        ["policy", "explain", "--json", "--policy", "net-ok", "--", "curl", "https://example.com"],
    )
    assert result.exit_code == 0
    assert _payload(result)["data"]["decision"]["allowed"] is True


def test_policy_list_and_show(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    policy_file = tmp_path / "sandbox-policies.json"
    policy_file.write_text(
        json.dumps(
            {"version": 1, "policies": [{"version": 1, "name": "net-ok", "allow_network": True}]}
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ARC_SANDBOX_POLICY_CONFIG", str(policy_file))
    listed = CliRunner().invoke(app, ["policy", "list", "--json"])
    assert listed.exit_code == 0
    names = [p["name"] for p in _payload(listed)["data"]["policies"]]
    assert names == ["local-safe", "net-ok"]
    shown = CliRunner().invoke(app, ["policy", "show", "net-ok", "--json"])
    assert shown.exit_code == 0
    assert _payload(shown)["data"]["allow_network"] is True


def test_policy_validate_reports_invalid_config(tmp_path):
    policy_file = tmp_path / "bad.json"
    policy_file.write_text(
        json.dumps({"version": 1, "policies": [{"version": 1, "name": "local-safe"}]}),
        encoding="utf-8",
    )
    result = CliRunner().invoke(app, ["policy", "validate", "--json", "--config", str(policy_file)])
    assert result.exit_code == 1
    data = _payload(result)["data"]
    assert data["ok"] is False
    assert "duplicate" in data["errors"][0]["error"]


def test_policy_validate_rejects_unknown_fields_and_missing_version(tmp_path):
    policy_file = tmp_path / "bad-shape.json"
    policy_file.write_text(
        json.dumps({"policies": [{"version": 1, "name": "x", "extra": True}]}), encoding="utf-8"
    )
    result = CliRunner().invoke(app, ["policy", "validate", "--json", "--config", str(policy_file)])
    assert result.exit_code == 1
    assert "version must be 1" in _payload(result)["data"]["errors"][0]["error"]
    policy_file.write_text(
        json.dumps({"version": 1, "policies": [{"version": 1, "name": "x", "extra": True}]}),
        encoding="utf-8",
    )
    result = CliRunner().invoke(app, ["policy", "validate", "--json", "--config", str(policy_file)])
    assert result.exit_code == 1
    assert "Extra inputs" in _payload(result)["data"]["errors"][0]["error"]


def test_sandbox_audit_verify_cli(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / "audit"))
    run = CliRunner().invoke(app, ["sandbox", "run", "--json", "--", "pwd"])
    assert run.exit_code == 0
    verify = CliRunner().invoke(
        app, ["sandbox", "audit-verify", "--json", "--audit-dir", str(tmp_path / "audit")]
    )
    assert verify.exit_code == 0
    assert _payload(verify)["data"]["ok"] is True


def test_sandbox_audit_chain_continues_across_runs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / "audit"))
    first = CliRunner().invoke(app, ["sandbox", "run", "--json", "--", "pwd"])
    second = CliRunner().invoke(app, ["sandbox", "run", "--json", "--", "ls"])
    assert first.exit_code == 0
    assert second.exit_code == 0
    verify = CliRunner().invoke(
        app, ["sandbox", "audit-verify", "--json", "--audit-dir", str(tmp_path / "audit")]
    )
    assert verify.exit_code == 0
    assert _payload(verify)["data"]["reason"] == "ok"


def test_sandbox_audit_list_filters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / "audit"))
    CliRunner().invoke(app, ["sandbox", "run", "--json", "--", "pwd"])
    CliRunner().invoke(app, ["sandbox", "run", "--json", "--", "curl", "https://example.com"])
    result = CliRunner().invoke(
        app,
        [
            "sandbox",
            "audit-list",
            "--json",
            "--audit-dir",
            str(tmp_path / "audit"),
            "--denied",
            "--classification",
            "network",
        ],
    )
    assert result.exit_code == 0
    data = _payload(result)["data"]
    assert data["count"] == 1
    assert data["events"][0]["allowed"] is False


def test_lima_template_requires_experimental_gate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ARC_MICROVM_EXPERIMENTAL", raising=False)
    result = CliRunner().invoke(app, ["sandbox", "lima-template", "--json"])
    assert result.exit_code == 2


def test_lima_template_renders_with_experimental_gate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARC_MICROVM_EXPERIMENTAL", "1")
    result = CliRunner().invoke(app, ["sandbox", "lima-template", "--json"])
    assert result.exit_code == 0
    template = _payload(result)["data"]["template"]
    assert "vmType: vz" in template
    assert "networks: []" in template


def test_microvm_plan_cli_is_design_only_and_does_not_probe_runtime(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def fail_probe(*_args, **_kwargs):
        raise AssertionError("microvm-plan must not execute subprocess probes")

    monkeypatch.setattr(subprocess, "run", fail_probe)
    monkeypatch.setattr(subprocess, "Popen", fail_probe)
    result = CliRunner().invoke(
        app, ["sandbox", "microvm-plan", "--json", "--provider", "lima", "--", "pwd"]
    )
    assert result.exit_code == 0, result.output
    plan = _payload(result)["data"]
    assert plan["provider"] == "lima"
    assert plan["execution_enabled"] is False
    assert plan["execution_status"] == "design_proof_only"
    assert [step["name"] for step in plan["steps"]] == [
        "template",
        "create_start",
        "network_off",
        "run",
        "teardown",
    ]


def test_microvm_plan_cli_firecracker_shape(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app, ["sandbox", "microvm-plan", "--json", "--provider", "firecracker", "--", "pwd"]
    )
    assert result.exit_code == 0, result.output
    plan = _payload(result)["data"]
    assert plan["provider"] == "firecracker"
    assert plan["network_default"] == "deny"
    assert "kernel/rootfs cache provenance missing" in plan["blockers"]


def test_microvm_plan_cli_rejects_unknown_provider(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app, ["sandbox", "microvm-plan", "--json", "--provider", "docker", "--", "pwd"]
    )
    assert result.exit_code == 2
    assert _payload(result)["ok"] is False


def test_container_provider_disabled_without_gate(monkeypatch):
    from agent_runtime_cockpit.isolation.docker_provider import DockerIsolationProvider
    import asyncio

    monkeypatch.delenv("ARC_ENABLE_CONTAINER_SANDBOX", raising=False)
    provider = DockerIsolationProvider()
    result = asyncio.run(provider.execute(["echo", "nope"]))
    assert result.exit_code == -1
    assert "disabled" in result.stderr.lower()


def test_firecracker_preflight_reports_detail(monkeypatch, tmp_path):
    kernel = tmp_path / "vmlinux"
    rootfs = tmp_path / "rootfs.ext4"
    kernel.write_text("kernel", encoding="utf-8")
    rootfs.write_text("rootfs", encoding="utf-8")
    monkeypatch.setenv("ARC_FIRECRACKER_KERNEL", str(kernel))
    monkeypatch.setenv("ARC_FIRECRACKER_ROOTFS", str(rootfs))
    monkeypatch.setattr(
        shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in {"firecracker", "jailer"} else None,
    )
    data = microvm_preflight("Linux")
    assert data["jailer"] == "/usr/bin/jailer"
    assert data["cache_ready"] is True
    assert "kvm_rw" in data
    assert "arch_supported" in data
    assert "version" in data
    assert "jailer_version" in data
    assert "kernel_size" in data
    assert "jail_perms" in data


def test_linux_microvm_preflight_deep(monkeypatch, tmp_path):
    """Test deep Linux preflight diagnostics."""
    kernel = tmp_path / "vmlinux"
    rootfs = tmp_path / "rootfs.ext4"
    kernel.write_text("kernel", encoding="utf-8")
    rootfs.write_text("rootfs", encoding="utf-8")
    monkeypatch.setenv("ARC_FIRECRACKER_KERNEL", str(kernel))
    monkeypatch.setenv("ARC_FIRECRACKER_ROOTFS", str(rootfs))
    monkeypatch.setattr(
        shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in {"firecracker", "jailer"} else None,
    )
    data = microvm_preflight("Linux")
    assert data["kernel_exists"] is True
    assert data["rootfs_exists"] is True
    assert data["kernel_size"] is not None
    assert "jail_perms" in data
    # jailer_version may be None if version probe fails
    assert "jailer_version" in data


def test_classification_categories():
    assert classify_command(["curl", "https://example.com"]) == CommandClassification.NETWORK
    assert classify_command(["pip", "install", "x"]) == CommandClassification.INSTALL
    assert classify_command(["sudo", "id"]) == CommandClassification.PRIVILEGED
    assert classify_command(["python", "-c", "print('hello')"]) == CommandClassification.READ_ONLY


@pytest.mark.parametrize(
    ("command", "classification"),
    [
        (["python", "-c", "open('x', 'w').write('x')"], CommandClassification.WRITES_WORKSPACE),
        (["python", "-c", "import socket"], CommandClassification.NETWORK),
        (["python", "-c", "import subprocess"], CommandClassification.NETWORK),
        (["python", "-m", "pip", "install", "x"], CommandClassification.INSTALL),
        (["node", "-e", "console.log(1)"], CommandClassification.UNKNOWN),
        (["ruby", "-e", "puts 1"], CommandClassification.UNKNOWN),
        (["perl", "-e", "print 1"], CommandClassification.UNKNOWN),
        (["bash", "-lc", "ls"], CommandClassification.UNKNOWN),
        (["git", "clean", "-fdx"], CommandClassification.DESTRUCTIVE),
        (["git", "reset", "--hard"], CommandClassification.DESTRUCTIVE),
        (["git", "checkout", "--", "file"], CommandClassification.DESTRUCTIVE),
        (["git", "rm", "file"], CommandClassification.DESTRUCTIVE),
        (["find", ".", "-delete"], CommandClassification.DESTRUCTIVE),
        (["find", ".", "-exec", "rm", "{}", ";"], CommandClassification.DESTRUCTIVE),
        (["tar", "--overwrite", "-xf", "a.tar"], CommandClassification.DESTRUCTIVE),
        (["rsync", "a", "b"], CommandClassification.NETWORK),
        (["dd", "if=/dev/zero", "of=x"], CommandClassification.DESTRUCTIVE),
        (["truncate", "-s", "0", "x"], CommandClassification.DESTRUCTIVE),
        (["chmod", "600", "x"], CommandClassification.PRIVILEGED),
        (["chown", "root", "x"], CommandClassification.PRIVILEGED),
        (["touch", "file.txt"], CommandClassification.WRITES_WORKSPACE),
        (["mkdir", "newdir"], CommandClassification.WRITES_WORKSPACE),
        (["ln", "-s", "target", "link"], CommandClassification.WRITES_WORKSPACE),
        (["cp", "src", "dst"], CommandClassification.WRITES_WORKSPACE),
        (["unzip", "archive.zip", "-d", "outdir"], CommandClassification.WRITES_WORKSPACE),
        (["install", "-m", "755", "src", "dst"], CommandClassification.INSTALL),
        (["install", "-d", "/usr/local/bin"], CommandClassification.INSTALL),
        (["node", "-e", "require('http')"], CommandClassification.NETWORK),
        (["ruby", "-e", "require 'socket'"], CommandClassification.NETWORK),
        (["perl", "-e", "use LWP::Simple"], CommandClassification.NETWORK),
        (["bash", "-c", "curl http://example.com"], CommandClassification.NETWORK),
    ],
)
def test_adversarial_classification_matrix(command, classification):
    assert classify_command(command) == classification


def test_python_write_outside_workspace_denied_before_execution(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    monkeypatch.chdir(workspace)
    result = CliRunner().invoke(
        app,
        [
            "sandbox",
            "run",
            "--json",
            "--workspace",
            str(workspace),
            "--",
            "python",
            "-c",
            f"open({str(outside)!r}, 'w').write('x')",
        ],
    )
    assert result.exit_code == 2
    assert outside.exists() is False


def test_symlink_path_argument_escape_denied(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    link = workspace / "escape"
    link.symlink_to(outside, target_is_directory=True)
    monkeypatch.chdir(workspace)
    result = CliRunner().invoke(
        app,
        [
            "sandbox",
            "run",
            "--json",
            "--workspace",
            str(workspace),
            "--",
            "python",
            "-c",
            f"open({str(link / 'x')!r}, 'w').write('x')",
        ],
    )
    assert result.exit_code == 2


def test_absolute_output_path_denied(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    result = CliRunner().invoke(
        app,
        [
            "sandbox",
            "run",
            "--json",
            "--workspace",
            str(workspace),
            "--",
            "python",
            "-c",
            "open('/tmp/arc-out', 'w').write('x')",
        ],
    )
    assert result.exit_code == 2


def test_safe_workspace_relative_output_path_allowed(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    result = CliRunner().invoke(
        app,
        [
            "sandbox",
            "run",
            "--json",
            "--workspace",
            str(workspace),
            "--",
            "python",
            "-c",
            "open('out.txt', 'w').write('x')",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (workspace / "out.txt").read_text(encoding="utf-8") == "x"


def test_read_only_absolute_path_outside_workspace_denied(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    monkeypatch.chdir(workspace)
    result = CliRunner().invoke(
        app, ["sandbox", "run", "--json", "--workspace", str(workspace), "--", "cat", str(outside)]
    )
    assert result.exit_code == 2


def test_approval_rules_default_behavior(tmp_path, monkeypatch):
    """Test that approval_required is True by default for risky classifications."""
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app, ["policy", "explain", "--json", "--", "curl", "https://example.com"]
    )
    assert result.exit_code == 0
    data = _payload(result)["data"]
    assert data["decision"]["approval_required"] is True
    assert data["decision"]["allowed"] is False


def test_approval_rules_allow_policy(tmp_path, monkeypatch):
    """Test that allow_network=True makes approval_required=False."""
    monkeypatch.chdir(tmp_path)
    policy_file = tmp_path / "sandbox-policies.json"
    policy_file.write_text(
        json.dumps(
            {
                "version": 1,
                "policies": [
                    {
                        "version": 1,
                        "name": "network-ok",
                        "allow_network": True,
                        "network_approval_required": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ARC_SANDBOX_POLICY_CONFIG", str(policy_file))
    result = CliRunner().invoke(
        app,
        [
            "policy",
            "explain",
            "--json",
            "--policy",
            "network-ok",
            "--",
            "curl",
            "https://example.com",
        ],
    )
    assert result.exit_code == 0
    data = _payload(result)["data"]
    assert data["decision"]["approval_required"] is False
    assert data["decision"]["allowed"] is True


def test_destructive_commands_cannot_be_approved(tmp_path, monkeypatch):
    """Test that destructive commands remain denied and cannot be approved."""
    monkeypatch.chdir(tmp_path)
    # Create a permissive policy but it shouldn't matter for destructive commands
    policy_file = tmp_path / "sandbox-policies.json"
    policy_file.write_text(
        json.dumps(
            {
                "version": 1,
                "policies": [
                    {
                        "version": 1,
                        "name": "permissive",
                        "allow_network": True,
                        "allow_install": True,
                        "allow_unknown": True,
                        "allow_privileged": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ARC_SANDBOX_POLICY_CONFIG", str(policy_file))
    result = CliRunner().invoke(
        app, ["policy", "explain", "--json", "--policy", "permissive", "--", "rm", "-rf", "."]
    )
    assert result.exit_code == 0
    data = _payload(result)["data"]
    assert data["decision"]["allowed"] is False
    assert "destructive commands denied" in data["decision"]["reason"]
    # destructive commands should not have approval_required set (they can't be approved)


def test_privileged_commands_cannot_be_approved(tmp_path, monkeypatch):
    """Test that privileged commands remain denied and cannot be approved."""
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["policy", "explain", "--json", "--", "sudo", "ls"])
    assert result.exit_code == 0
    data = _payload(result)["data"]
    assert data["decision"]["allowed"] is False
    assert "privileged commands denied" in data["decision"]["reason"]
    # privileged commands should not have approval_required set (they can't be approved)


def test_unknown_commands_approval_required_by_default(tmp_path, monkeypatch):
    """Test that unknown commands have approval_required=True by default."""
    monkeypatch.chdir(tmp_path)
    # Create a workspace and run an unknown command (not in our known lists)
    # Using a custom command that's not in READ_ONLY_COMMANDS
    result = CliRunner().invoke(app, ["policy", "explain", "--json", "--", "custom-tool"])
    assert result.exit_code == 0
    data = _payload(result)["data"]
    assert data["decision"]["classification"] == "unknown"
    assert data["decision"]["approval_required"] is True
    assert data["decision"]["allowed"] is False


@pytest.mark.skipif(
    os.environ.get("ARC_MICROVM_INTEGRATION") != "1",
    reason="requires ARC_MICROVM_INTEGRATION=1 and local microVM runtime",
)
def test_microvm_integration_skeleton_doctor_only():
    result = CliRunner().invoke(app, ["sandbox", "doctor", "--json"])
    assert result.exit_code == 0
    providers = _payload(result)["data"]["providers"]
    microvm = next(provider for provider in providers if provider.get("provider") == "microvm")
    assert microvm["status"] in {"unavailable", "installed_not_configured", "ready", "blocked"}
