"""Tests for R-UX3 view/menu polish: SlashMenu MRU+chips, RunsView sort/filter,
HitlView field-name fix + age, SessionsView snippet + fork."""

from __future__ import annotations

import time

import pytest


# ── R-010 SlashMenu: category chips + MRU ─────────────────────────────────────


def test_category_chip_color_and_ascii(monkeypatch):
    from agent_runtime_cockpit.tui.widgets import slash_menu as sm

    monkeypatch.delenv("NO_COLOR", raising=False)
    chip = sm._category_chip("session")
    assert "session" in chip and "cyan" in chip

    monkeypatch.setenv("NO_COLOR", "1")
    chip2 = sm._category_chip("session")
    assert chip2 == "(session) "
    assert "[" not in chip2  # no Rich markup in NO_COLOR mode


def test_category_chip_empty():
    from agent_runtime_cockpit.tui.widgets import slash_menu as sm

    assert sm._category_chip("") == ""


def test_slash_menu_commands_still_two_tuples():
    """Contract: _commands and filter() stay (name, help_text) 2-tuples."""
    from agent_runtime_cockpit.tui.widgets.slash_menu import SlashMenu

    menu = SlashMenu()
    assert len(menu._commands) > 0
    assert all(isinstance(n, str) and isinstance(h, str) for n, h in menu._commands)
    results = menu.filter("/ru")
    assert all(n.startswith("ru") for n, _ in results)


def test_slash_menu_mru_first_on_empty_query():
    from agent_runtime_cockpit.tui.widgets.slash_menu import SlashMenu

    menu = SlashMenu()
    names = [n for n, _ in menu._commands]
    assert len(names) >= 2
    target = names[-1]  # a command that is not normally first
    menu.record_use("/" + target)
    ordered = menu._ordered(menu.filter("/"), "/")
    assert ordered[0][0] == target


def test_slash_menu_mru_ignored_for_nonempty_prefix():
    from agent_runtime_cockpit.tui.widgets.slash_menu import SlashMenu

    menu = SlashMenu()
    menu.record_use("status")
    res = menu._ordered(menu.filter("/ru"), "/ru")
    assert all(n.startswith("ru") for n, _ in res)


def test_slash_menu_record_use_bounded():
    from agent_runtime_cockpit.tui.widgets.slash_menu import SlashMenu

    menu = SlashMenu()
    for i in range(40):
        menu.record_use(f"cmd{i}")
    assert len(menu._mru) <= 16


# ── R-017 RunsView: sort + filter ─────────────────────────────────────────────


def _runs_view(tmp_path):
    from agent_runtime_cockpit.tui.views.runs_view import RunsView

    view = RunsView(workspace=tmp_path)
    view._rows = [
        ("run-a", "completed", "swarmgraph", "5", "2026-06-01T10:00:00"),
        ("run-b", "failed", "langgraph", "3", "2026-06-03T10:00:00"),
        ("run-c", "completed", "crewai", "1", "2026-06-02T10:00:00"),
    ]
    return view


def test_runs_view_sort_by_date_desc(tmp_path):
    view = _runs_view(tmp_path)
    view._sort_idx = 0  # date
    assert view._sorted(view._rows)[0][0] == "run-b"  # newest


def test_runs_view_sort_by_status(tmp_path):
    view = _runs_view(tmp_path)
    view._sort_idx = 1  # status
    assert view._sorted(view._rows)[0][1] == "completed"


def test_runs_view_filter_substring(tmp_path):
    view = _runs_view(tmp_path)
    f = view._filtered("langgraph")
    assert len(f) == 1 and f[0][0] == "run-b"
    # empty query returns all
    assert len(view._filtered("")) == 3


# ── R-018 HitlView: age helper + real-field rendering ─────────────────────────


def test_hitl_age_buckets():
    from agent_runtime_cockpit.tui.views.hitl_view import _age

    now = time.time()
    assert _age(now - 5).endswith("s ago")
    assert _age(now - 120).endswith("m ago")
    assert _age(now - 7200).endswith("h ago")
    # ISO string (the real created_at format) → no age, no crash
    assert _age("2026-06-01T10:00:00") == ""


@pytest.mark.asyncio
async def test_hitl_view_renders_real_fields(tmp_path):
    """Proves the field-name fix: prompt_text + hitl_id actually render."""
    from textual.app import App
    from textual.widgets import Label

    from agent_runtime_cockpit.audit.hitl import HitlPrompt
    from agent_runtime_cockpit.audit.hitl_sqlite_store import HitlSqliteStore
    from agent_runtime_cockpit.tui.views.hitl_view import HitlView

    arc = tmp_path / ".arc"
    arc.mkdir()
    store = HitlSqliteStore(arc / "hitl.db")
    store.init_db()
    store.save_prompt(
        HitlPrompt(
            hitl_id="habc123456789",
            run_id="runxyz789012",
            step_id="step-1",
            prompt_text="Approve deployment to staging?",
        )
    )

    class _App(App):
        async def on_mount(self) -> None:
            await self.push_screen(HitlView(workspace=tmp_path))

    app = _App()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        view = app.screen
        text = " ".join(str(lbl.render()) for lbl in view.query(Label))
        assert "Approve deployment to staging?" in text
        assert "habc123456789" in text


# ── R-019 SessionsView: snippet + fork ────────────────────────────────────────


def test_last_user_snippet():
    from agent_runtime_cockpit.tui.views.sessions_view import _last_user_snippet

    class S:
        history = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply"},
            {"role": "user", "content": "second question here"},
        ]

    assert _last_user_snippet(S()) == "second question here"

    class E:
        history: list = []

    assert _last_user_snippet(E()) == ""


@pytest.mark.asyncio
async def test_sessions_view_fork(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path / "sessions"))
    from textual.app import App
    from textual.widgets import ListView

    from agent_runtime_cockpit.cli_repl.session import ChatSession
    from agent_runtime_cockpit.tui.data import DataStore
    from agent_runtime_cockpit.tui.views.sessions_view import SessionsView

    src = ChatSession(id="s-original0001")
    src.add_message("user", "hello world")
    src.add_message("assistant", "hi there")
    src.save()

    data = DataStore(seed=99)

    class _App(App):
        async def on_mount(self) -> None:
            await self.push_screen(SessionsView(data=data))

    app = _App()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        view = app.screen
        lv = view.query_one("#sessions-list", ListView)
        lv.index = 0
        view.action_fork()
        await pilot.pause()

    assert data.session_id != "s-original0001"
    assert data.session_id.startswith("s-")
    # The forked transcript carries the copied user message
    assert any(e.content == "hello world" for e in data.entries)
