from __future__ import annotations

from agent_runtime_cockpit.cli_repl.slash_commands import _build_registry


PHASE_2_COMMANDS = {
    "help",
    "version",
    "exit",
    "clear",
    "summary",
    "sessions",
    "history",
    "run",
    "plan",
    "build",
    "auto",
    "status",
    "doctor",
    "runs",
}


def test_phase_2_registry_command_set_is_exact() -> None:
    registry = _build_registry()
    assert set(registry.commands) == PHASE_2_COMMANDS


def test_phase_2_registry_metadata_is_explicit() -> None:
    registry = _build_registry()
    for cmd in registry.list_commands():
        assert cmd.category
        assert isinstance(cmd.gates_required, list)
        assert isinstance(cmd.mode_required, list)
        assert cmd.renders, cmd.name
        assert isinstance(cmd.requires_events, list)
        assert cmd.trust_required in {"system", "user", "workspace"}
        assert isinstance(cmd.privileged, bool)
        assert isinstance(cmd.visible_in_ide, bool)
        assert isinstance(cmd.popup_visible, bool)


def test_phase_2_registry_aliases() -> None:
    registry = _build_registry()
    assert registry.get("quit") is registry.get("exit")
    assert registry.aliases == {"quit": "exit"}
