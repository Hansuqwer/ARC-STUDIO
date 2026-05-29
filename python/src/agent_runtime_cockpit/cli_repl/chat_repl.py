from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console

from .. import __version__
from ..runtime.mode import RuntimeMode
from ..security.trust import resolve_trust
from .session import ChatSession
from .slash_commands import SlashCommandHandler

HISTORY_FILE = Path.home() / ".arc" / "repl_history.txt"
console = Console(highlight=False)


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
    _configure_provider_default(session)

    handler = SlashCommandHandler(
        progress_sink=lambda name, payload: print(_format_progress_event(name, payload))
    )

    if initial_prompt:
        _handle_input(initial_prompt, session, handler, print)
        if non_interactive:
            session.save()
            return

    history = _load_history()
    for line in _format_startup_banner(session):
        console.print(line)

    try:
        while True:
            try:
                user_input = input(_format_prompt(session)).strip()
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
            from .slash_commands import CommandResult

            if isinstance(result, CommandResult):
                prefix = _render_state_prefix(result.state)
                if result.output:
                    output(f"{prefix} {result.output}")
                elif result.reason:
                    output(f"{prefix} {result.state}: {result.reason}")
                else:
                    output(f"{prefix}")
            else:
                output(result)
        return

    if session.mode == "auto" and session.runtime_mode is RuntimeMode.PROVIDER_BACKED:
        result = handler.handle(f"/agent {text}", session)
        output(_result_text(result))
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


def _render_state_prefix(state: str) -> str:
    """Return a short prefix indicating the structured result state."""
    _MAP = {
        "present": "[ok]",
        "ok": "[ok]",
        "absent": "[empty]",
        "blocked": "[blocked]",
        "denied": "[denied]",
        "degraded": "[degraded]",
        "error": "[error]",
        "failed": "[error]",
    }
    return _MAP.get(state, f"[{state}]")


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


def _configure_provider_default(session: ChatSession) -> None:
    import os

    provider = os.environ.get("ARC_DEFAULT_PROVIDER")
    if not provider:
        if os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.environ.get("OPENAI_API_KEY"):
            provider = "openai"
    if not provider:
        return
    session.runtime_mode = RuntimeMode.PROVIDER_BACKED
    session.allow_paid_calls = True
    session.tools_enabled = True
    session.metadata["provider"] = provider


def _format_startup_banner(session: ChatSession, workspace: Path | None = None) -> list[str]:
    ws = (workspace or Path.cwd()).resolve()
    trust = _trust_label(ws)
    provider = _provider_label(session)
    model = str((session.metadata or {}).get("provider_model") or "unknown")
    tools = "on" if session.tools_enabled else "off"
    return [
        f"ARC Studio v{__version__}",
        "Run agents. See everything.",
        f"workspace: {ws}",
        (
            "state: "
            f"mode={session.mode} runtime={RuntimeMode.from_legacy(session.runtime_mode).value} "
            f"provider={provider} model={model} trust={trust} sandbox=subprocess tools={tools} "
            f"context={_context_label(session)}"
        ),
        "next: /status  /tools list  /context pack <task>  /agent <task>  /help",
    ]


def _format_prompt(session: ChatSession) -> str:
    runtime = RuntimeMode.from_legacy(session.runtime_mode).value
    provider = _provider_label(session)
    tools = "on" if session.tools_enabled else "off"
    return (
        f"arc[{session.mode}|{runtime}|{provider}|tools:{tools}|ctx:{_context_short(session)}] > "
    )


def _provider_label(session: ChatSession) -> str:
    metadata = session.metadata or {}
    return str(metadata.get("provider") or "none")


def _trust_label(workspace: Path) -> str:
    try:
        return resolve_trust(workspace).level.value
    except Exception:  # noqa: BLE001 - startup/status must stay best-effort.
        return "unknown"


def _context_short(session: ChatSession) -> str:
    context = (session.metadata or {}).get("last_context")
    if not isinstance(context, dict) or not context.get("available"):
        return "?"
    pct = context.get("usage_pct")
    return f"{pct}%" if pct is not None else "?"


def _context_label(session: ChatSession) -> str:
    context = (session.metadata or {}).get("last_context")
    if not isinstance(context, dict) or not context.get("available"):
        return "unknown"
    used = context.get("used_tokens")
    maximum = context.get("max_context_tokens")
    pct = context.get("usage_pct")
    if used is None or maximum is None or pct is None:
        return "unknown"
    return f"{pct}%({used}/{maximum})"


def _result_text(result: Any) -> str:
    if result is None:
        return ""
    if hasattr(result, "output"):
        return str(result.output or result.reason or result.state)
    return str(result)


def _format_progress_event(name: str, payload: dict[str, Any]) -> str:
    if name == "run.started":
        return "[progress] run started"
    if name == "turn.started":
        return f"[agent] turn started ({payload.get('prompt_chars', 0)} chars)"
    if name == "turn.completed":
        return f"[agent] turn completed ({payload.get('content_chars', 0)} chars)"
    if name == "turn.cancelled":
        return f"[agent] turn cancelled: {payload.get('detail', 'cancelled')}"
    if name == "tool.requested":
        args = payload.get("args_preview") or "{}"
        return f"[tool] {payload.get('tool', 'unknown')} args={args}"
    if name == "tool.executed":
        lines = [
            f"[tool] {payload.get('tool', 'unknown')} ok trust={payload.get('trust', 'unknown')}"
        ]
        if payload.get("summary"):
            lines.append(f"[tool] summary: {payload['summary']}")
        if payload.get("diff"):
            lines.extend(["[diff]", str(payload["diff"]).rstrip()])
        return "\n".join(lines)
    if name == "tool.result.blocked":
        return (
            f"[blocked] tool {payload.get('tool', 'unknown')}: {payload.get('reason', 'blocked')}"
        )
    if name.startswith("stream.chunk.delta") and payload.get("delta"):
        return str(payload["delta"])
    if name.startswith("run.progress."):
        return f"[progress] {payload.get('stage') or name.removeprefix('run.progress.')}"
    if name == "run.completed":
        return f"[progress] run completed in {payload.get('elapsed_ms', 0)}ms"
    if name == "run.cancelled":
        reason = payload.get("reason", "unknown")
        return f"[progress] run cancelled: {reason}"
    return f"[progress] {name}"
