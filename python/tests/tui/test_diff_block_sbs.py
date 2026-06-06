"""Phase 130 — DiffBlock side-by-side toggle tests."""

from unittest.mock import MagicMock

from agent_runtime_cockpit.tui.widgets.diff_block import DiffBlock

SIMPLE_DIFF = """\
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,3 @@
 context line
-old line
+new line
 another context
"""


def test_s_key_toggles_side_by_side() -> None:
    widget = DiffBlock(SIMPLE_DIFF, filename="foo.py", no_color=True)
    event = MagicMock()
    event.key = "s"
    widget.refresh = MagicMock()
    widget.on_key(event)
    assert widget._side_by_side is True
    rendered = widget.render()
    assert "│" in rendered


def test_unified_default_no_pipe() -> None:
    widget = DiffBlock(SIMPLE_DIFF, filename="foo.py", no_color=True)
    rendered = widget.render()
    assert "│" not in rendered
