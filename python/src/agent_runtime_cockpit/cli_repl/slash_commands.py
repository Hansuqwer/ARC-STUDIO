from __future__ import annotations

from typing import Any

from ..swarmgraph import SwarmGraphRunner
from ..swarmgraph.config import SwarmGraphConfig
from .session import ChatSession


class SlashCommandHandler:
    def __init__(self, runner: SwarmGraphRunner | None = None):
        self.runner = runner

    def handle(self, command: str, session: ChatSession) -> str | None:
        cmd = command.lower().strip()
        parts = cmd.split(maxsplit=1)
        name = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        handler = getattr(self, f"cmd_{name[1:]}", None)
        if handler:
            return handler(arg, session)
        if name.startswith("/"):
            return f"Unknown slash command: {name}. Try /help."
        return None

    def cmd_help(self, _arg: str, _session: ChatSession) -> str:
        return (
            "Available slash commands:\n"
            "  /help       - Show this help\n"
            "  /clear      - Clear session history\n"
            "  /run        - Execute prompt with SwarmGraph runner\n"
            "  /summary    - Show session summary\n"
            "  /sessions   - List all sessions\n"
            "  /history    - Show recent messages\n"
            "  /version    - Show version info\n"
            "  /quit       - Exit the REPL"
        )

    def cmd_clear(self, _arg: str, session: ChatSession) -> str:
        session.history.clear()
        return "Session history cleared."

    def cmd_run(self, arg: str, session: ChatSession) -> str:
        if not arg:
            return "Usage: /run <prompt>"
        config = SwarmGraphConfig(
            num_workers=3,
            max_rounds=1,
        )
        runner = SwarmGraphRunner(config=config)
        result = runner.run(prompt=arg)
        session.add_message("user", arg)
        output = result.get("results", [])
        summary = f"Run completed: status={result.get('status')}, "
        summary += f"tasks={result.get('total_tasks', 0)}, "
        summary += f"cost=${result.get('total_cost_usd', 0):.4f}"
        if output:
            summary += f"\nOutput: {output[0].get('output', '')}"
        return summary

    def cmd_summary(self, _arg: str, session: ChatSession) -> str:
        n = len(session.history)
        return f"Session {session.id}: {n} messages, created {session.created_at[:19]}"

    def cmd_sessions(self, _arg: str, _session: ChatSession) -> str:
        sessions = ChatSession.list_sessions()
        if not sessions:
            return "No saved sessions."
        lines = ["Saved sessions:"]
        for s in sessions[:10]:
            n = len(s.history)
            lines.append(f"  {s.id[:16]}... - {n} msgs, {s.updated_at[:19]}")
        return "\n".join(lines)

    def cmd_history(self, arg: str, session: ChatSession) -> str:
        n = int(arg) if arg.isdigit() else 10
        recent = session.history[-n:]
        if not recent:
            return "No messages in history."
        lines: list[str] = []
        for msg in recent:
            role = msg.get("role", "?")
            content = msg.get("content", "")[:200]
            lines.append(f"[{role}] {content}")
        return "\n".join(lines)

    def cmd_version(self, _arg: str, _session: ChatSession) -> str:
        return "ARC Studio - SwarmGraph Native Runtime v0.1.0-alpha"

    def cmd_quit(self, _arg: str, _session: ChatSession) -> str:
        return "__EXIT__"

    def cmd_exit(self, arg: str, session: ChatSession) -> str:
        return self.cmd_quit(arg, session)
