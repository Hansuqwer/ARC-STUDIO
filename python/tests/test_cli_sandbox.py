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


def test_classification_categories():
    assert classify_command(["curl", "https://example.com"]) == CommandClassification.NETWORK
    assert classify_command(["pip", "install", "x"]) == CommandClassification.INSTALL
    assert classify_command(["sudo", "id"]) == CommandClassification.PRIVILEGED
    assert classify_command(["python", "-c", "print('hello')"]) == CommandClassification.READ_ONLY


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
