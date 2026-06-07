"""TUI core unit tests — DataStore, ThemeManager, dispatch, headless Textual.

Phase 4.1 (Tasks 1-3):
- DataStore operations
- ThemeManager detection and toggle
- _app.py dispatch logic
- Headless Textual interaction tests (Task 3)
"""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.tui.data import DataStore, TranscriptEntry
from agent_runtime_cockpit.tui.theme import ThemeManager


# ── DataStore ──────────────────────────────────────────────────────────────


class TestDataStore:
    def test_add_entry_returns_entry(self):
        ds = DataStore()
        e = ds.add_entry("user", "hello")
        assert isinstance(e, TranscriptEntry)
        assert e.role == "user"
        assert e.content == "hello"
        assert len(ds.entries) == 1

    def test_add_entry_increments(self):
        ds = DataStore()
        ds.add_entry("user", "a")
        ds.add_entry("assistant", "b")
        assert len(ds.entries) == 2

    def test_append_to_last_extends_assistant(self):
        ds = DataStore()
        ds.add_entry("assistant", "Hello")
        ds.append_to_last(" world")
        assert ds.entries[-1].content == "Hello world"

    def test_append_to_last_creates_entry_if_no_assistant(self):
        ds = DataStore()
        ds.add_entry("user", "hi")
        ds.append_to_last("response")
        assert len(ds.entries) == 2
        assert ds.entries[-1].role == "assistant"
        assert ds.entries[-1].content == "response"

    def test_clear_transcript(self):
        ds = DataStore()
        ds.add_entry("user", "x")
        ds.add_entry("assistant", "y")
        ds.clear_transcript()
        assert ds.entries == []

    def test_update_last_metadata(self):
        ds = DataStore()
        ds.add_entry("tool", "output")
        ds.update_last_metadata("status", "success")
        assert ds.entries[-1].metadata["status"] == "success"

    def test_session_id_auto_generated(self):
        ds = DataStore()
        assert ds.session_id.startswith("s-")
        assert len(ds.session_id) == 14  # s- + 12 hex

    def test_add_to_history_deduplicates(self):
        ds = DataStore()
        ds.add_to_history("cmd1")
        ds.add_to_history("cmd1")
        assert len(ds.input_history) == 1

    def test_add_to_history_different_entries(self):
        ds = DataStore()
        ds.add_to_history("a")
        ds.add_to_history("b")
        assert len(ds.input_history) == 2

    def test_history_up_returns_last(self):
        ds = DataStore()
        ds.add_to_history("cmd1")
        ds.add_to_history("cmd2")
        result = ds.history_up("")
        assert result == "cmd2"

    def test_history_up_continues(self):
        ds = DataStore()
        ds.add_to_history("cmd1")
        ds.add_to_history("cmd2")
        ds.history_up("")
        result = ds.history_up("")
        assert result == "cmd1"

    def test_history_down_after_up(self):
        ds = DataStore()
        ds.add_to_history("cmd1")
        ds.add_to_history("cmd2")
        ds.history_up("")
        ds.history_up("")
        result = ds.history_down()
        assert result == "cmd2"

    def test_history_up_empty(self):
        ds = DataStore()
        assert ds.history_up("") is None

    def test_transcript_entry_display_time(self):
        e = TranscriptEntry(id="x", role="user", content="hi")
        assert len(e.display_time) == 8  # HH:MM:SS

    def test_status_line_fits_width(self):
        ds = DataStore()
        line = ds.status_line(80)
        assert len(line) <= 80


# ── ThemeManager ───────────────────────────────────────────────────────────


class TestThemeManager:
    def test_default_is_dark(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("ARC_THEME", raising=False)
        tm = ThemeManager()
        assert tm.current.name == "dark"

    def test_toggle_to_light(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("ARC_THEME", raising=False)
        tm = ThemeManager()
        result = tm.toggle()
        assert result.name == "light"
        assert tm.is_light

    def test_toggle_back_to_dark(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("ARC_THEME", raising=False)
        tm = ThemeManager()
        tm.toggle()
        result = tm.toggle()
        assert result.name == "dark"

    def test_no_color_via_env(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        tm = ThemeManager()
        assert tm.is_no_color

    def test_light_theme_via_env(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("ARC_THEME", "light")
        tm = ThemeManager()
        assert tm.is_light

    def test_dark_theme_via_env(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("ARC_THEME", "dark")
        tm = ThemeManager()
        assert tm.is_dark

    def test_css_variables_contains_background(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        tm = ThemeManager()
        css = tm.css_variables()
        assert "$background:" in css


# ── Banner version ─────────────────────────────────────────────────────────


class TestBanner:
    def test_banner_init_does_not_raise(self):
        from agent_runtime_cockpit.tui.widgets.banner import Banner

        ds = DataStore()
        tm = ThemeManager()
        b = Banner(ds, tm)
        assert b is not None

    def test_banner_version_matches_package(self):
        from agent_runtime_cockpit import __version__
        from agent_runtime_cockpit.tui.widgets.banner import Banner

        ds = DataStore()
        tm = ThemeManager()
        b = Banner(ds, tm)
        # _render_full() uses __version__ directly — verify it's in the output
        rendered = b._render_full()
        assert __version__ in rendered


# ── Dispatch ───────────────────────────────────────────────────────────────


class TestDispatch:
    def test_tui_launched_in_tty(self, monkeypatch):
        """With ARC_NO_TUI unset and TTY, run_tui is called."""
        monkeypatch.delenv("ARC_NO_TUI", raising=False)
        monkeypatch.delenv("ARC_CLASSIC", raising=False)
        calls: list[str] = []
        monkeypatch.setattr(
            "agent_runtime_cockpit.tui.app.ArcApp.run",
            lambda self: calls.append("tui"),
        )
        import agent_runtime_cockpit.tui.app as m

        m.run_tui()
        assert "tui" in calls

    def test_classic_repl_when_arc_classic_set(self, monkeypatch):
        monkeypatch.setenv("ARC_CLASSIC", "1")
        monkeypatch.delenv("ARC_NO_TUI", raising=False)
        calls: list[str] = []
        monkeypatch.setattr(
            "agent_runtime_cockpit.cli_repl.chat_repl.run_chat_repl",
            lambda: calls.append("classic"),
        )
        import agent_runtime_cockpit.tui.app as m

        m.run_tui()
        assert "classic" in calls

    def test_no_tui_env_skips_launch(self, monkeypatch):
        monkeypatch.setenv("ARC_NO_TUI", "1")
        calls: list[str] = []
        monkeypatch.setattr(
            "agent_runtime_cockpit.tui.app.ArcApp.run",
            lambda self: calls.append("tui"),
        )
        import agent_runtime_cockpit.tui.app as m

        m.run_tui()
        assert calls == []


# ── Error card ─────────────────────────────────────────────────────────────


class TestErrorCard:
    def test_error_entry_format(self):
        ds = DataStore()
        # Simulate _add_error_entry
        code = "INVALID_INPUT"
        message = "bad value"
        border = "─" * 50
        content = f"┌ Error {border}┐\n│ [{code}] {message}\n"
        content += f"└{border}─┘"
        ds.add_entry("system", content, {"type": "error", "code": code})
        e = ds.entries[-1]
        assert "Error" in e.content
        assert code in e.content
        assert e.metadata["type"] == "error"


# ── arc tui subcommand ─────────────────────────────────────────────────────


class TestTuiSubcommand:
    def test_arc_tui_help_exits_ok(self):
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli import app

        result = CliRunner().invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        assert "tui" in result.output.lower() or "TUI" in result.output


# ── Domain views empty state ───────────────────────────────────────────────


class TestRunsViewEmptyState:
    def test_runs_view_instantiates(self, tmp_path):
        from agent_runtime_cockpit.tui.views.runs_view import RunsView

        view = RunsView(workspace=tmp_path)
        assert view is not None

    def test_hitl_view_instantiates(self, tmp_path):
        from agent_runtime_cockpit.tui.views.hitl_view import HitlView

        view = HitlView(workspace=tmp_path)
        assert view is not None

    def test_sessions_view_instantiates(self):
        from agent_runtime_cockpit.tui.views.sessions_view import SessionsView

        ds = DataStore()
        view = SessionsView(data=ds)
        assert view is not None


# ── Headless Textual tests (Task 3) ───────────────────────────────────────


@pytest.mark.asyncio
async def test_headless_app_mounts():
    """ArcApp composes and mounts without error."""
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)):
        # App started — at least the welcome message should be in entries
        assert len(app.data.entries) >= 1


@pytest.mark.asyncio
async def test_headless_widgets_render():
    """ArcScreen widgets are actually mounted (guards the blank-window bug)."""
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert app.query_one("#banner") is not None
        assert app.query_one("#transcript") is not None
        assert app.query_one("#status-bar") is not None
        assert app.query_one("#input-area") is not None


@pytest.mark.asyncio
async def test_headless_slash_version():
    """Typing /version adds an entry with the version string."""
    from agent_runtime_cockpit import __version__
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        screen = app.screen
        screen._handle_slash("/version")
        await pilot.pause()
        assert any(__version__ in e.content for e in app.data.entries)


@pytest.mark.asyncio
async def test_headless_clear_empties_transcript():
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.data.add_entry("user", "test")
        app.data.clear_transcript()
        assert len(app.data.entries) == 0


@pytest.mark.asyncio
async def test_headless_streaming_flag():
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)):
        app.data.is_streaming = True
        screen = app.screen
        screen.action_handle_escape()
        assert app.data.is_streaming is False


@pytest.mark.asyncio
async def test_headless_help_slash():
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        screen = app.screen
        screen._show_help_inline()
        await pilot.pause()
        assert any("KEYBOARD SHORTCUTS" in e.content for e in app.data.entries)


# ── Slash menu (Issue 1) ───────────────────────────────────────────────────


class TestSlashMenu:
    def test_menu_loads_descriptions(self):
        from agent_runtime_cockpit.tui.widgets.slash_menu import SlashMenu

        menu = SlashMenu()
        assert len(menu._commands) > 0
        # every entry is (name, help_text)
        assert all(isinstance(n, str) and isinstance(h, str) for n, h in menu._commands)

    def test_menu_filters_by_prefix(self):
        from agent_runtime_cockpit.tui.widgets.slash_menu import SlashMenu

        menu = SlashMenu()
        results = menu.filter("/ru")
        assert all(n.startswith("ru") for n, _ in results)

    def test_menu_best_match(self):
        from agent_runtime_cockpit.tui.widgets.slash_menu import SlashMenu

        menu = SlashMenu()
        assert menu.best_match("/zzzznope") is None


@pytest.mark.asyncio
async def test_headless_slash_menu_visible_on_slash():
    from types import SimpleNamespace

    from agent_runtime_cockpit.tui.app import ArcApp
    from agent_runtime_cockpit.tui.widgets.slash_menu import SlashMenu

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        screen = app.screen
        menu = screen.query_one(SlashMenu)
        screen.on_text_area_changed(SimpleNamespace(text_area=SimpleNamespace(text="/")))
        await pilot.pause()
        assert menu.has_class("visible")
        screen.on_text_area_changed(SimpleNamespace(text_area=SimpleNamespace(text="/zzzz@")))
        await pilot.pause()
        assert not menu.has_class("visible")


@pytest.mark.asyncio
async def test_headless_slash_menu_rerender_no_duplicate_ids():
    """Re-rendering a multi-match prefix must not raise DuplicateIds."""
    from types import SimpleNamespace

    from agent_runtime_cockpit.tui.app import ArcApp
    from agent_runtime_cockpit.tui.widgets.slash_menu import SlashMenu

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        screen = app.screen
        for text in ("/m", "/mo", "/m", "/pr", "/m"):
            screen.on_text_area_changed(SimpleNamespace(text_area=SimpleNamespace(text=text)))
            await pilot.pause()
        # No exception == pass; the menu is still operable.
        assert screen.query_one(SlashMenu) is not None


# ── Slash execution (Issue 2) ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_headless_unknown_slash_reports():
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        before = len(app.data.entries)
        app.screen._handle_slash("/definitely-not-a-real-command")
        await pilot.pause()
        assert len(app.data.entries) > before
        assert any("Unknown slash command" in e.content for e in app.data.entries)


@pytest.mark.asyncio
async def test_headless_known_slash_non_silent():
    """A delegated slash command always produces a visible (non-empty) entry."""
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        before = len(app.data.entries)
        app.screen._handle_slash("/doctor")
        await pilot.pause()
        assert len(app.data.entries) > before
        assert app.data.entries[-1].content.strip() != ""


# ── Paid fail-closed by default (CR-002) ────────────────────────────────────


class TestPaidDefault:
    def test_paid_off_by_default(self, monkeypatch):
        monkeypatch.delenv("ARC_TUI_NO_PAID", raising=False)
        monkeypatch.delenv("ARC_TUI_ALLOW_PAID", raising=False)
        assert DataStore().allow_paid is False

    def test_paid_opt_in_env(self, monkeypatch):
        monkeypatch.delenv("ARC_TUI_NO_PAID", raising=False)
        monkeypatch.setenv("ARC_TUI_ALLOW_PAID", "1")
        assert DataStore().allow_paid is True

    def test_paid_opt_out_env(self, monkeypatch):
        monkeypatch.setenv("ARC_TUI_NO_PAID", "1")
        assert DataStore().allow_paid is False

    def test_paid_deny_wins_when_both_env_set(self, monkeypatch):
        monkeypatch.setenv("ARC_TUI_ALLOW_PAID", "1")
        monkeypatch.setenv("ARC_TUI_NO_PAID", "1")
        assert DataStore().allow_paid is False

    def test_status_bar_shows_paid(self, monkeypatch):
        monkeypatch.delenv("ARC_TUI_NO_PAID", raising=False)
        from agent_runtime_cockpit.tui.widgets.status_bar import StatusBar

        ds = DataStore()
        ds.allow_paid = True  # fail-closed default is off; enable to show the indicator
        bar = StatusBar(ds, ThemeManager())
        assert "$paid" in bar.render()

    def test_status_bar_hides_paid_when_fail_closed(self, monkeypatch):
        monkeypatch.delenv("ARC_TUI_NO_PAID", raising=False)
        monkeypatch.delenv("ARC_TUI_ALLOW_PAID", raising=False)
        from agent_runtime_cockpit.tui.widgets.status_bar import StatusBar

        bar = StatusBar(DataStore(), ThemeManager())
        assert "$paid" not in bar.render()


# ── Enter-key routing regression tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_enter_submits_slash_command():
    """Pressing Enter after a slash command runs it (not inserts a newline)."""
    from agent_runtime_cockpit.tui.app import ArcApp
    from agent_runtime_cockpit.tui.widgets.input_area import InputArea

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        # Type /version and press Enter.
        await pilot.press("/", "v", "e", "r", "s", "i", "o", "n")
        before = len(app.data.entries)
        await pilot.press("enter")
        await pilot.pause()
        # The input should be cleared (submitted, not newline-inserted).
        input_area = app.screen.query_one("#input-area", InputArea)
        assert input_area._input.text.strip() == ""
        # A new transcript entry should have appeared.
        assert len(app.data.entries) > before


@pytest.mark.asyncio
async def test_shift_enter_inserts_newline_not_submit():
    """Shift+Enter does NOT submit — no new transcript entry produced."""
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        before_entries = len(app.data.entries)
        await pilot.press("h", "i")
        await pilot.press("shift+enter")
        await pilot.pause()
        # Must not have submitted.
        assert len(app.data.entries) == before_entries


@pytest.mark.asyncio
async def test_enter_unknown_slash_shows_error():
    """Enter on an unknown slash command produces transcript output."""
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("/", "x", "y", "z", "n", "o", "t", "r", "e", "a", "l")
        before = len(app.data.entries)
        await pilot.press("enter")
        await pilot.pause()
        assert len(app.data.entries) > before
        assert any("Unknown slash command" in e.content for e in app.data.entries)


# ── ProvidersView tests ────────────────────────────────────────────────────


class TestProvidersView:
    def test_instantiates(self):
        from agent_runtime_cockpit.tui.views.providers_view import ProvidersView

        view = ProvidersView(data=DataStore())
        assert view is not None

    def test_load_all_providers_returns_list(self):
        from agent_runtime_cockpit.tui.views.providers_view import _load_all_providers

        providers = _load_all_providers()
        assert len(providers) >= 7  # at least the original snapshot size

    def test_all_providers_have_models(self):
        from agent_runtime_cockpit.tui.views.providers_view import _load_all_providers

        for p in _load_all_providers():
            assert len(p.models) >= 1, f"{p.id} has no models"

    def test_free_providers_marked(self):
        from agent_runtime_cockpit.tui.views.providers_view import (
            _has_free_model,
            _load_all_providers,
        )

        has_any_free = any(_has_free_model(p) for p in _load_all_providers())
        assert has_any_free, "Expected at least one provider with free models"

    def test_configured_provider_shows_check(self, monkeypatch):
        from agent_runtime_cockpit.tui.views.providers_view import (
            _load_all_providers,
            _provider_row,
        )

        providers = _load_all_providers()
        p = providers[0]
        # Simulate key set in env
        monkeypatch.setenv(p.env[0], "fake-test-key")
        row = _provider_row(p)
        assert "✓" in row

    def test_unconfigured_provider_shows_empty(self, monkeypatch):
        from agent_runtime_cockpit.tui.views.providers_view import (
            _load_all_providers,
            _is_configured,
            _provider_row,
        )

        providers = _load_all_providers()
        p = providers[0]
        for env_var in p.env:
            monkeypatch.delenv(env_var, raising=False)
        # Patch get_decrypted_api_key to return None
        monkeypatch.setattr(
            "agent_runtime_cockpit.auth.manager.get_decrypted_api_key",
            lambda *a, **kw: None,
        )
        assert not _is_configured(p)
        row = _provider_row(p)
        assert "[ ]" in row


@pytest.mark.asyncio
async def test_headless_providers_view_opens():
    """Typing /providers pushes ProvidersView onto the screen stack."""
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.screen._handle_slash("/providers")
        await pilot.pause()
        # A modal screen should now be active (not ArcScreen)
        from agent_runtime_cockpit.tui.views.providers_view import ProvidersView

        assert any(isinstance(s, ProvidersView) for s in app.screen_stack)
