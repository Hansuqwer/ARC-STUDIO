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
