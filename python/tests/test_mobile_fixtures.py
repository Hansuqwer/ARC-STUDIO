"""Tests for PR8: fixture-backed simulator skeleton."""

from __future__ import annotations


class TestMockStore:
    def setup_method(self):
        from agent_runtime_cockpit.mobile.mock_store import reset_default_store

        reset_default_store()

    def test_write_and_retrieve(self):
        from agent_runtime_cockpit.mobile.mock_store import MockStore

        store = MockStore()
        result = store.write("k1", "hello")
        assert result["stored"] is True
        got = store.retrieve("k1")
        assert got["found"] is True
        assert got["value"] == "hello"

    def test_retrieve_last(self):
        from agent_runtime_cockpit.mobile.mock_store import MockStore

        store = MockStore()
        store.write("a", "first")
        store.write("b", "second")
        got = store.retrieve("last")
        assert got["found"] is True
        assert got["value"] == "second"

    def test_retrieve_missing_key(self):
        from agent_runtime_cockpit.mobile.mock_store import MockStore

        store = MockStore()
        got = store.retrieve("nonexistent")
        assert got["found"] is False


class TestFixtureRegistry:
    def test_all_13_capabilities_have_fixtures(self):
        from agent_runtime_cockpit.mobile import list_capabilities, list_fixtures

        cap_ids = {c.id for c in list_capabilities()}
        fixture_ids = set(list_fixtures())
        missing = cap_ids - fixture_ids
        assert not missing, f"Capabilities missing fixtures: {missing}"

    def test_memory_write_then_retrieve(self):
        from agent_runtime_cockpit.mobile.fixtures_registry import get_fixture
        from agent_runtime_cockpit.mobile.mock_store import MockStore

        store = MockStore()
        write_fn = get_fixture("app.memory.write.mock")
        retrieve_fn = get_fixture("app.memory.retrieve.mock")
        assert write_fn and retrieve_fn
        write_fn({"key": "msg", "value": "hello"}, store)
        result = retrieve_fn({"key": "msg"}, store)
        assert result["found"] is True
        assert result["value"] == "hello"

    def test_memory_retrieve_last(self):
        from agent_runtime_cockpit.mobile.fixtures_registry import get_fixture
        from agent_runtime_cockpit.mobile.mock_store import MockStore

        store = MockStore()
        write_fn = get_fixture("app.memory.write.mock")
        retrieve_fn = get_fixture("app.memory.retrieve.mock")
        write_fn({"text": "mobile hello"}, store)
        result = retrieve_fn({"key": "last"}, store)
        assert result["found"] is True

    def test_location_fixture_returns_coordinates(self):
        from agent_runtime_cockpit.mobile.fixtures_registry import get_fixture
        from agent_runtime_cockpit.mobile.mock_store import MockStore

        fn = get_fixture("device.location.current.mock")
        assert fn is not None
        result = fn({}, MockStore())
        assert "latitude" in result
        assert result["mock"] is True

    def test_camera_fixture_returns_uri(self):
        from agent_runtime_cockpit.mobile.fixtures_registry import get_fixture
        from agent_runtime_cockpit.mobile.mock_store import MockStore

        fn = get_fixture("device.camera.capture.mock")
        result = fn({}, MockStore())
        assert "uri" in result
        assert result["mock"] is True

    def test_unknown_fixture_returns_none(self):
        from agent_runtime_cockpit.mobile.fixtures_registry import get_fixture

        assert get_fixture("nonexistent.cap") is None

    def test_no_real_native_access_in_fixtures(self):
        """Fixture executors must not import subprocess, socket, requests, etc."""
        from pathlib import Path

        src = (
            Path(__file__).parent.parent
            / "src"
            / "agent_runtime_cockpit"
            / "mobile"
            / "fixtures_registry.py"
        )
        text = src.read_text()
        forbidden = [
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "urllib.request",
            "AVCapture",
            "CLLocation",
        ]
        for f in forbidden:
            assert f not in text, f"Forbidden symbol {f!r} found in fixtures_registry.py"
