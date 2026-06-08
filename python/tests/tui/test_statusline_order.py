"""B2P-01: status-line slot reordering is config-driven, default preserved."""

from agent_runtime_cockpit.tui.data import STATUSLINE_SLOTS, DataStore


def _store() -> DataStore:
    return DataStore(seed=1, workspace=__import__("pathlib").Path("/tmp/ws"), total_cost_usd=0.0)


def test_default_order_preserved() -> None:
    d = _store()
    assert d.statusline_order == list(STATUSLINE_SLOTS)
    line = d.status_line(200)
    # mode appears before cost in the default order
    assert line.index(d.mode) < line.index("$0")


def test_reorder_changes_render_order() -> None:
    d = _store()
    ok, _ = d.set_statusline_order(["cost", "mode"])
    assert ok
    line = d.status_line(200)
    assert line.index("$0") < line.index(f" {d.mode} ")  # cost now first
    # only the two requested slots render
    assert "Esc:cancel" not in line


def test_unknown_slot_rejected_and_order_unchanged() -> None:
    d = _store()
    ok, msg = d.set_statusline_order(["mode", "bogus"])
    assert not ok and "bogus" in msg
    assert d.statusline_order == list(STATUSLINE_SLOTS)  # unchanged


def test_empty_order_rejected() -> None:
    d = _store()
    ok, _ = d.set_statusline_order([])
    assert not ok


def test_duplicates_deduped() -> None:
    d = _store()
    ok, _ = d.set_statusline_order(["mode", "mode", "cost"])
    assert ok and d.statusline_order == ["mode", "cost"]


def test_reset_restores_default() -> None:
    d = _store()
    d.set_statusline_order(["cost"])
    d.reset_statusline_order()
    assert d.statusline_order == list(STATUSLINE_SLOTS)


def test_status_line_is_no_color_safe() -> None:
    # a11y / WCAG 1.4.1 (gate 2): the status line conveys all information as TEXT, not color.
    # The rendered string carries no ANSI color escapes, so it is byte-identical under NO_COLOR.
    d = _store()
    line = d.status_line(200)
    assert "\x1b[" not in line  # no ANSI escape sequences -> NO_COLOR cannot change it
    assert d.mode in line and "$0" in line  # meaning lives in the text, not a color


def test_status_line_degraded_and_bounded() -> None:
    # UX states (gate 1): no session / zero cost render explicit placeholders, never blanks.
    d = _store()
    d.session_id = ""  # degraded: no active session
    line = d.status_line(200)
    assert "--------" in line  # no session id -> placeholder
    assert "$0" in line  # zero cost -> explicit, not empty
    # Performance/render safety (gate 5): output is bounded to the requested width.
    assert len(d.status_line(20)) <= 20
