"""ArcScreen — the main chat screen composing all widgets."""

from __future__ import annotations

import time

from textual.app import ComposeResult
from textual.screen import Screen

from .data import DataStore
from .theme import ThemeManager
from .widgets.activity_tray import ActivityTray  # UX R-008
from .widgets.banner import Banner  # noqa: F401  # kept for backward compat / external imports
from .widgets.header import Header  # UX R-001: modern header
from .widgets.input_area import InputArea
from .widgets.mode_badge import ModeBadge  # UX R-003
from .widgets.slash_menu import SlashMenu
from .widgets.status_bar import StatusBar
from .widgets.transcript import Transcript


def _free_hint() -> str:
    """One-line free-provider hint derived from the bundled snapshot."""
    try:
        from agent_runtime_cockpit.providers.models_dev import free_providers_hint

        return free_providers_hint()
    except Exception:
        return ""


class ArcScreen(Screen):
    """Primary screen: Banner + Transcript + StatusBar + InputArea."""

    BINDINGS = [
        ("ctrl+c", "handle_ctrl_c", "Interrupt / Exit"),
        ("ctrl+p", "toggle_palette", "Command Palette"),
        ("ctrl+k", "toggle_palette", "Command Palette"),
        ("ctrl+l", "scroll_bottom", "Scroll to Bottom"),
        ("ctrl+d", "handle_ctrl_d", "Exit (empty input)"),
        ("escape", "handle_escape", "Cancel / Interrupt"),
        ("ctrl+t", "export_transcript", "Export Transcript"),
        ("ctrl+x", "toggle_activity", "Activity Tray"),
        ("ctrl+o", "toggle_expand", "Expand/Collapse"),
        ("f1", "toggle_help", "Help"),
        ("?", "toggle_help", "Help"),
        # UX R-003: Shift+Tab cycles Plan → Build → Auto → Review
        ("shift+tab", "cycle_mode", "Cycle Mode"),
    ]

    def __init__(self, data: DataStore, theme: ThemeManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data
        self.theme = theme
        self._ctrl_c_count = 0
        self._ctrl_c_timer: float = 0.0
        self._daemon_was_online: bool = False
        self._session = None  # lazily-built persistent ChatSession

    def compose(self) -> ComposeResult:
        # UX R-001: modern Header replaces the ASCII banner. We keep the
        # id="banner" so existing tests/CSS selectors continue to work, and
        # add a "header" class for the new selector.
        header = Header(self.data, self.theme, id="banner")
        header.add_class("header")
        yield header
        yield Transcript(self.data, self.theme, id="transcript")
        yield SlashMenu()
        yield StatusBar(self.data, self.theme, id="status-bar")
        yield InputArea(self.data, self.theme, id="input-area")
        # UX R-008: ActivityTray (Ctrl+X); hidden until toggled
        no_color = bool(getattr(self.theme.current, "no_color", False))
        yield ActivityTray(no_color=no_color)

    def on_mount(self) -> None:
        from agent_runtime_cockpit import __version__

        self.data.add_entry(
            "system",
            f"ARC Studio v{__version__} — Agent Runtime Cockpit\n"
            "Type a message to begin, /help for commands, Ctrl+C to exit.\n"
            f"Session: {self.data.session_id[:12]}…  ·  Workspace: {self.data.workspace}\n"
            + _free_hint(),
        )
        self.set_interval(5.0, self._check_daemon)
        self._check_daemon()
        self.set_interval(1.0, self._refresh_status)
        self.query_one("#input-area", InputArea).focus_input()

    # ── Daemon health ────────────────────────────────────────────────────

    def _check_daemon(self) -> None:
        try:
            import urllib.request

            req = urllib.request.Request(
                f"http://{self.data.daemon_host}:{self.data.daemon_port}/health"
            )
            with urllib.request.urlopen(req, timeout=1) as resp:
                self.data.daemon_online = resp.status == 200
        except Exception:
            self.data.daemon_online = False

        # Detect reconnection
        if self.data.daemon_online and not self._daemon_was_online:
            if self._daemon_was_online is not None:  # skip first check
                self.data.add_entry("system", "Daemon reconnected.")
        self._daemon_was_online = self.data.daemon_online

    def _refresh_status(self) -> None:
        self.query_one("#status-bar", StatusBar).refresh()

    # ── Input handling ───────────────────────────────────────────────────

    def on_input_area_submitted(self, event: InputArea.Submitted) -> None:
        self._ctrl_c_count = 0
        text = event.text
        if text.startswith("/"):
            self._handle_slash(text)
        elif text.startswith("!"):
            self._handle_shell_escape(text)
        else:
            self._handle_chat_message(text)

    def on_text_area_changed(self, event) -> None:
        """Drive the slash dropdown as the user types."""
        try:
            text = event.text_area.text
        except Exception:
            return
        menu = self.query_one(SlashMenu)
        first_line = text.split("\n", 1)[0]
        if first_line.startswith("/") and " " not in first_line:
            menu.show_for(first_line)
        else:
            menu.hide()

    def on_list_view_selected(self, event) -> None:
        """Mouse/Enter selection of a slash-menu row completes the input."""
        name = getattr(event.item, "command_name", None)
        if name:
            self.query_one(SlashMenu).hide()
            self.query_one("#input-area", InputArea).set_text(f"/{name} ")

    def on_input_area_completion_requested(self, event: InputArea.CompletionRequested) -> None:
        """Tab completion: complete to the best matching slash command."""
        menu = self.query_one(SlashMenu)
        match = menu.best_match(event.text)
        if match:
            menu.hide()
            self.query_one("#input-area", InputArea).set_text(f"/{match} ")

    def _handle_slash(self, text: str) -> None:
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()

        if cmd in ("/exit", "/quit"):
            self._do_exit()
            return
        if cmd == "/clear":
            self.data.clear_transcript()
            old = self.query_one("#transcript", Transcript)
            old.remove()
            self.mount(Transcript(self.data, self.theme))
            self.data.add_entry("system", "Transcript cleared.")
            return
        if cmd == "/help":
            self.action_toggle_help()
            return
        if cmd == "/theme":
            new_theme = self.theme.toggle()
            self.data.add_entry("system", f"Theme: {new_theme.name}")
            return
        if cmd == "/version":
            from agent_runtime_cockpit import __version__

            self.data.add_entry("system", f"ARC Studio v{__version__}")
            return
        # UX R-003 + R-012: mode jumps
        if cmd in ("/plan", "/build", "/auto", "/review"):
            mode = cmd[1:]
            try:
                badge = self.query_one(ModeBadge)
                badge.set_mode(mode)  # type: ignore[arg-type]
            except Exception:
                self.data.mode = mode
            self.data.add_entry("system", f"Mode: {mode}")
            return
        if cmd == "/status":
            self._show_status()
            return
        if cmd == "/runs":
            try:
                from .views.runs_view import RunsView

                self.app.push_screen(RunsView(self.data.workspace))
            except Exception as e:
                self._add_error_entry("VIEW_ERROR", str(e))
            return
        if cmd == "/sessions":
            try:
                from .views.sessions_view import SessionsView

                self.app.push_screen(SessionsView(self.data))
            except Exception as e:
                self._add_error_entry("VIEW_ERROR", str(e))
            return
        if cmd == "/hitl":
            try:
                from .views.hitl_view import HitlView

                self.app.push_screen(HitlView(self.data.workspace))
            except Exception as e:
                self._add_error_entry("VIEW_ERROR", str(e))
            return
        if cmd == "/runtimes":
            try:
                from .views.runtimes_view import RuntimesView

                self.app.push_screen(RuntimesView(self.data.workspace))
            except Exception as e:
                self._add_error_entry("VIEW_ERROR", str(e))
            return

        if cmd in ("/providers", "/connect"):
            try:
                from .views.providers_view import ProvidersView

                self.app.push_screen(ProvidersView(data=self.data))
            except Exception as e:
                self._add_error_entry("VIEW_ERROR", str(e))
            return

        if cmd == "/models":
            try:
                from .views.providers_view import ModelListScreen, ProvidersView
                from agent_runtime_cockpit.providers.models_dev import (
                    bundled_openai_compatible_providers,
                )

                # Find current or first configured provider
                providers = list(bundled_openai_compatible_providers().values())
                provider = next(
                    (
                        p
                        for p in providers
                        if self.data.current_provider and p.id == self.data.current_provider
                    ),
                    None,
                ) or next((p for p in providers), None)
                if provider:
                    self.app.push_screen(ModelListScreen(provider, self.data))
                else:
                    self.app.push_screen(ProvidersView(data=self.data))
            except Exception as e:
                self._add_error_entry("VIEW_ERROR", str(e))
            return

        # Delegate remaining slash commands to backend
        self.query_one(SlashMenu).hide()
        try:
            from agent_runtime_cockpit.cli_repl.slash_commands import (
                SlashCommandHandler,
                _result_text,
            )

            handler = SlashCommandHandler()
            result = handler.handle(text, self._get_session())
            if result == "__EXIT__":
                self._do_exit()
                return
            out = _result_text(result)
            if not out:
                state = getattr(result, "state", None)
                out = f"({state})" if state else "(no output)"
            self.data.add_entry("assistant", out)
        except Exception as e:
            self._add_error_entry("SLASH_ERROR", str(e))

    def _get_session(self):
        """Return a persistent ChatSession bound to this TUI session.

        Paid calls are enabled by default (data.allow_paid); provider-key and
        trust gates still apply downstream.
        """
        if self._session is None:
            from agent_runtime_cockpit.cli_repl.session import ChatSession

            self._session = ChatSession(id=self.data.session_id)
        self._session.allow_paid_calls = bool(getattr(self.data, "allow_paid", True))
        return self._session

    def _handle_shell_escape(self, text: str) -> None:
        import subprocess
        from ..security.trust import resolve_trust, TrustLevel

        cmd = text[1:].strip()
        self.data.add_entry("user", f"!{cmd}")

        # D-03: route the bang-escape through trust + a conservative classifier.
        # We do NOT call security.sandbox.decide() directly because the sandbox
        # API is policy-oriented and would require a full SandboxRequest; this
        # lighter wrapper still surfaces trust and a small denylist so unsafe
        # commands are visibly refused rather than silently executed.
        try:
            trust_state = resolve_trust(self.data.workspace)
            denylist = ("rm -rf", "sudo ", "mkfs", "dd if=", ":(){", "> /dev/")
            lower = cmd.lower()
            blocked_by_denylist = any(d in lower for d in denylist)
            if trust_state.level == TrustLevel.UNTRUSTED or blocked_by_denylist:
                reason = (
                    "workspace untrusted (run /workspace trust)"
                    if trust_state.level == TrustLevel.UNTRUSTED
                    else "command matches sandbox denylist"
                )
                self.data.add_entry(
                    "tool",
                    f"Shell command blocked: {reason}\n  cmd: {cmd}",
                    {"tool_name": f"Bash: {cmd}", "status": "error"},
                )
                return
        except Exception:
            pass  # fall through if trust resolution itself fails
        try:
            result = subprocess.run(  # noqa: S602
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            output = result.stdout
            if result.stderr:
                output += "\n[stderr]\n" + result.stderr
            self.data.add_entry(
                "tool",
                output[:2000],
                {
                    "tool_name": f"Bash: {cmd}",
                    "status": "success" if result.returncode == 0 else "error",
                },
            )
        except subprocess.TimeoutExpired:
            self.data.add_entry("tool", "Command timed out after 30s", {"status": "error"})
        except Exception as e:
            self.data.add_entry("tool", str(e), {"status": "error"})

    def _handle_chat_message(self, text: str) -> None:
        """Send a chat message. Streams via SwarmGraph if available."""
        from .theme_extras import thinking_indicator

        no_color = bool(getattr(self.theme.current, "no_color", False))
        self.data.add_entry("user", text)
        self.data.add_entry("assistant", thinking_indicator(no_color=no_color))

        def run_agent() -> None:
            self.data.is_streaming = True
            try:
                from agent_runtime_cockpit.adapters.swarmgraph import SwarmGraphAdapter
                from agent_runtime_cockpit.protocol.schemas import WorkspaceInfo

                adapter = SwarmGraphAdapter()
                ws_info = WorkspaceInfo(path=str(self.data.workspace))
                result = adapter.run_workflow(text, workspace=ws_info)
                status = getattr(result, "status", "unknown")
                self.app.call_from_thread(
                    self.data.append_to_last,
                    f"\n[SwarmGraph] {status}",
                )
            except Exception as e:
                self.app.call_from_thread(
                    self.data.append_to_last,
                    f"\n(SwarmGraph unavailable: {e})",
                )
            finally:
                self.data.is_streaming = False

        self.run_worker(run_agent, exclusive=False, thread=True)

    # ── Actions ──────────────────────────────────────────────────────────

    def action_handle_ctrl_c(self) -> None:
        if self.data.is_streaming:
            self.data.is_streaming = False
            self.data.add_entry("system", "⏸ Interrupted.")
            return
        now = time.monotonic()
        if self._ctrl_c_count == 0:
            self._ctrl_c_count = 1
            self._ctrl_c_timer = now
            self.data.add_entry("system", "Press Ctrl+C again to exit.")
            self.set_timer(1.0, self._reset_ctrl_c)
            return
        if now - self._ctrl_c_timer < 1.0:
            self._do_exit()

    def _reset_ctrl_c(self) -> None:
        self._ctrl_c_count = 0

    def action_handle_ctrl_d(self) -> None:
        input_area = self.query_one("#input-area", InputArea)
        if not input_area._input.text.strip():
            self._do_exit()

    def action_handle_escape(self) -> None:
        if self.data.is_streaming:
            self.data.is_streaming = False
            self.data.add_entry("system", "⏸ Interrupted.")
        else:
            self.query_one("#input-area", InputArea)._input.load_text("")

    def action_cycle_mode(self) -> None:
        """UX R-003: cycle Plan → Build → Auto → Review with Shift+Tab."""
        try:
            badge = self.query_one(ModeBadge)
            new_mode = badge.cycle()
            self.data.add_entry("system", f"Mode: {new_mode}")
        except Exception:
            pass

    def action_toggle_palette(self) -> None:
        try:
            from .widgets.command_palette import CommandPalette

            self.app.push_screen(CommandPalette())
        except Exception:
            self.data.add_entry("system", "Command palette: use /help for commands.")

    def action_toggle_help(self) -> None:
        try:
            from .widgets.help_screen import HelpScreen

            self.app.push_screen(HelpScreen())
        except Exception:
            self._show_help_inline()

    def action_toggle_activity(self) -> None:
        tray = self.query_one("#activity-tray", ActivityTray)
        tray.toggle()

    def action_toggle_expand(self) -> None:
        pass

    def action_scroll_bottom(self) -> None:
        self.query_one("#transcript", Transcript).scroll_to_bottom()

    def action_export_transcript(self) -> None:
        import os
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for e in self.data.entries:
                f.write(f"[{e.role}] {e.display_time}\n{e.content}\n\n")
            path = f.name
        pager = os.environ.get("PAGER", "less")
        subprocess.run([pager, path])  # noqa: S603

    def _show_help_inline(self) -> None:
        self.data.add_entry(
            "system",
            "ARC Studio — Help\n"
            "═══════════════════════════════════════════════════════════\n"
            "KEYBOARD SHORTCUTS\n"
            "──────────────────\n"
            "  Enter          Submit   Ctrl+C×2  Exit\n"
            "  Ctrl+L         Scroll to bottom\n"
            "  Ctrl+P         Command palette\n"
            "  Ctrl+T         Export transcript\n"
            "  Up/Down        Input history   Tab  Autocomplete\n"
            "  F1 / ?         This help\n"
            "\n"
            "SLASH COMMANDS\n"
            "  /help /clear /exit /theme /version /status\n"
            "  /runs /sessions /hitl /runtimes /doctor\n"
            "\n"
            "SHELL ESCAPE: !<command>",
        )

    def _show_status(self) -> None:
        lines = [
            f"Workspace: {self.data.workspace}",
            f"Mode: {self.data.mode}",
            f"Runtime: {self.data.runtime_mode}",
            f"Session: {self.data.session_id[:12]}…",
            f"Daemon: {'● online' if self.data.daemon_online else '○ offline'}",
            f"Cost: ${self.data.total_cost_usd:.4f}",
            f"Messages: {len(self.data.entries)}",
        ]
        self.data.add_entry("system", "\n".join(lines))

    def _add_error_entry(self, code: str, message: str, suggestion: str = "") -> None:
        border = "─" * 50
        content = f"┌ Error {border}┐\n│ [{code}] {message}\n"
        if suggestion:
            content += f"│ {suggestion}\n"
        content += f"└{border}─┘"
        self.data.add_entry("system", content, {"type": "error", "code": code})

    def _do_exit(self) -> None:
        self.data.add_entry("system", "Goodbye!")
        try:
            from agent_runtime_cockpit.cli_repl.session import ChatSession

            session = ChatSession(id=self.data.session_id)
            for entry in self.data.entries:
                session.add_message(entry.role, entry.content)
            session.save()
        except Exception:
            pass
        self.app.exit()
