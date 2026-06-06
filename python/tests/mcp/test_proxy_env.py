import logging

from agent_runtime_cockpit.mcp.proxy import _sanitise_env


def test_strips_api_key():
    result = _sanitise_env({"OPENAI_API_KEY": "sk-x", "PATH": "/bin"})
    assert "OPENAI_API_KEY" not in result
    assert result["PATH"] == "/bin"


def test_keeps_safe_keys():
    assert _sanitise_env({"PATH": "/bin", "HOME": "/root"}) == {"PATH": "/bin", "HOME": "/root"}


def test_none_passthrough():
    assert _sanitise_env(None) is None


def test_does_not_log_value(caplog):
    with caplog.at_level(logging.DEBUG, logger="agent_runtime_cockpit.mcp.proxy"):
        _sanitise_env({"OPENAI_API_KEY": "sk-secret"})
    assert "sk-secret" not in caplog.text
    assert "OPENAI_API_KEY" in caplog.text
