from __future__ import annotations

from pathlib import Path
from typing import Any

from .session import ChatSession
from .slash_commands import SlashCommandHandler

HISTORY_FILE = Path.home() / ".arc" / "repl_history.txt"


def _load_history() -> list[str]:
    if not HISTORY_FILE.exists():
        return []
    return [line.rstrip("\n") for line in HISTORY_FILE.read_text().splitlines() if line.strip()]


def _save_history(history: list[str]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text("\n".join(history[-500:]) + "\n")


def run_chat_repl(
    initial_prompt: str | None = None,
    session_id: str | None = None,
    non_interactive: bool = False,
    config: Any = None,
) -> None:
    session: ChatSession | None = None
    if session_id:
        session = ChatSession.load(session_id)
    if not session:
        session = ChatSession()

    handler = SlashCommandHandler(
        progress_sink=lambda name, payload: print(_format_progress_event(name, payload))
    )

    if initial_prompt:
        _handle_input(initial_prompt, session, handler, print)
        if non_interactive:
            session.save()
            return

    history = _load_history()
    welcome = f"ARC Studio - SwarmGraph Chat (session: {session.id[:12]}...)"
    print(welcome)
    print("Type /help for commands, /quit to exit.")

    try:
        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue

            history.append(user_input)
            _handle_input(user_input, session, handler, print)

            if user_input.strip().lower() in ("/quit", "/exit"):
                break

    finally:
        session.save()
        _save_history(history)
        print(f"Session saved: {session.id[:12]}...")


def _handle_input(
    text: str,
    session: ChatSession,
    handler: SlashCommandHandler,
    output: Any,
) -> None:
    """Route one line of REPL input with a per-command exception boundary.

    No unhandled exception from a slash command or the SwarmGraph runner is
    allowed to propagate to the REPL loop.  Each command failure renders an
    error state and returns.
    """
    text = text.strip()
    if not text:
        return

    if text.startswith("/"):
        try:
            result = handler.handle(text, session)
        except SystemExit:
            raise  # /exit must propagate
        except Exception as exc:  # noqa: BLE001
            output(f"[error] command failed: {exc}")
            return
        if result is None:
            output(f"Unknown command: {text}")
        elif result == "__EXIT__":
            session.add_message("user", text)
            raise SystemExit(0)
        else:
            output(result)
        return

    session.add_message("user", text)
    try:
        from ..swarmgraph import SwarmGraphRunner
        from ..swarmgraph.config import SwarmGraphConfig

        cfg = SwarmGraphConfig(num_workers=3, max_rounds=1)
        runner = SwarmGraphRunner(config=cfg)
        result = runner.run(prompt=text)
        reply = _format_result(result)
        session.add_message("assistant", reply)
        output(reply)
    except Exception as exc:  # noqa: BLE001
        output(f"[error] runner failed: {exc}")


def _format_result(result: dict[str, Any]) -> str:
    status = result.get("status", "unknown")
    tasks = result.get("total_tasks", 0)
    completed = result.get("completed_tasks", 0)
    cost = result.get("total_cost_usd", 0.0)

    lines: list[str] = []
    lines.append(f"[SwarmGraph] Run {status} - {completed}/{tasks} tasks, ${cost:.4f}")
    for r in result.get("results", []):
        output_text = r.get("output", "")
        if output_text:
            lines.append(f"  {output_text[:500]}")
    return "\n".join(lines)


def _format_progress_event(name: str, payload: dict[str, Any]) -> str:
    if name == "run.started":
        return "[progress] run started"
    if name.startswith("run.progress."):
        return f"[progress] {payload.get('stage') or name.removeprefix('run.progress.')}"
    if name == "run.completed":
        return f"[progress] run completed in {payload.get('elapsed_ms', 0)}ms"
    if name == "run.cancelled":
        reason = payload.get("reason", "unknown")
        return f"[progress] run cancelled: {reason}"
    return f"[progress] {name}"
