from __future__ import annotations

import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.cli_repl.session_bundle import (
    export_session_bundle,
    import_session_bundle,
)


def test_session_bundle_export_redacts_secret():
    session = ChatSession(id="s-test")
    session.metadata["api_key"] = "sk-12345678901234567890123456789012"

    bundle = export_session_bundle(session)

    dumped = bundle.model_dump_json()
    assert "sk-123456" not in dumped
    assert "[REDACTED]" in dumped


def test_session_bundle_import_validates_before_write(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions"))
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema":"wrong"}', encoding="utf-8")

    try:
        import_session_bundle(bad)
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected rejection")

    assert not (tmp_path / "sessions").exists()


def test_session_bundle_import_export_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions"))
    session = ChatSession(id="s-roundtrip")
    session.add_message("user", "hello")
    bundle = export_session_bundle(session)
    path = tmp_path / "bundle.json"
    path.write_text(bundle.model_dump_json(), encoding="utf-8")

    imported = import_session_bundle(path)

    assert imported.id == "s-roundtrip"
    assert imported.history[0]["content"] == "hello"


def test_session_bundle_rejects_future_version(tmp_path):
    session = ChatSession(id="s-version")
    data = export_session_bundle(session).model_dump(mode="json")
    data["session_schema_version"] = 999
    path = tmp_path / "future.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    try:
        import_session_bundle(path)
    except ValueError as exc:
        assert "unsupported future" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected rejection")


def test_session_cli_export_import(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions"))
    session = ChatSession(id="s-cli")
    session.save()
    out = tmp_path / "bundle.json"
    runner = CliRunner()

    exported = runner.invoke(
        app, ["studio", "sessions", "export", "s-cli", "--output", str(out), "--json"]
    )
    assert exported.exit_code == 0
    imported = runner.invoke(app, ["studio", "sessions", "import", str(out), "--new-id", "--json"])
    assert imported.exit_code == 0
    payload = json.loads(imported.output)
    assert payload["ok"] is True
