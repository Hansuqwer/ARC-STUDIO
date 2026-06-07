import logging

from agent_runtime_cockpit.mcp.proxy import _sanitise_env


def test_strips_api_key():
    result = _sanitise_env({"OPENAI_API_KEY": "sk-x", "PATH": "/bin"})
    assert "OPENAI_API_KEY" not in result
    assert result["PATH"] == "/bin"


def test_keeps_safe_keys():
    assert _sanitise_env({"PATH": "/bin", "HOME": "/root"}) == {"PATH": "/bin", "HOME": "/root"}


def test_none_sanitises_current_environment(monkeypatch):
    """env=None must sanitise the *current* environment, not return None.

    Returning None would make create_subprocess_exec inherit the full parent
    environment (secrets included). The proxy instead passes a sanitised copy.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-leak")
    monkeypatch.setenv("PATH", "/usr/bin")
    result = _sanitise_env(None)
    assert isinstance(result, dict)
    assert "OPENAI_API_KEY" not in result
    assert result.get("PATH") == "/usr/bin"


def test_does_not_log_value(caplog):
    with caplog.at_level(logging.DEBUG, logger="agent_runtime_cockpit.mcp.proxy"):
        _sanitise_env({"OPENAI_API_KEY": "sk-secret"})
    assert "sk-secret" not in caplog.text
    assert "OPENAI_API_KEY" in caplog.text
