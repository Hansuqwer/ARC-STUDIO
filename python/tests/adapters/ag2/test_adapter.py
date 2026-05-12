import asyncio
import pathlib
import textwrap

from agent_runtime_cockpit.adapters.ag2.detect import is_ag2_workspace
from agent_runtime_cockpit.adapters.ag2.mapping import _map
from agent_runtime_cockpit.ag_ui import MappingContext


def test_detect(tmp_path: pathlib.Path):
    (tmp_path / "team.py").write_text("from autogen import GroupChatManager\n")
    assert is_ag2_workspace(tmp_path)


def test_mapping_basic():
    ctx = MappingContext(thread_id="th", run_id="r1", runtime="ag2")
    assert _map({"event": "run.start"}, ctx)[0]["type"] == "RUN_STARTED"
    chunk = _map({"event": "message", "sender": "A", "content": "Hi"}, ctx)
    assert [e["type"] for e in chunk] == ["TEXT_MESSAGE_START", "TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END"]


def test_runner_with_fake_team(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_AG2_RUN_BACKEND", "local")
    monkeypatch.setenv("ARC_AG2_ALLOW_COSTS", "true")
    (tmp_path / "team.py").write_text(textwrap.dedent("""
        class _Resp:
            def __init__(self): self.events = self
            def __aiter__(self): self._i = iter([{"sender":"A","content":"Hi"}]); return self
            async def __anext__(self):
                try: e = next(self._i)
                except StopIteration: raise StopAsyncIteration
                class _E: pass
                ev = _E(); ev.sender = e["sender"]; ev.content = e["content"]; return ev
        class Team:
            async def a_run_group_chat(self, messages):
                return _Resp()
        team = Team()
    """))
    from agent_runtime_cockpit.adapters.ag2.runner import AG2Runner
    run_id = asyncio.run(AG2Runner(tmp_path).run("team:team", "ping"))
    text = (tmp_path / ".arc" / "traces" / f"{run_id}.jsonl").read_text()
    assert "RUN_STARTED" in text and "RUN_FINISHED" in text
    assert "Hi" in text
