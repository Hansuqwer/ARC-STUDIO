"""Tests for Phase 12b: feature flags + remote kill switch (default-off)."""

from __future__ import annotations

from agent_runtime_cockpit.mobile import FeatureFlags


def test_unknown_flag_is_off_by_default() -> None:
    ff = FeatureFlags()
    assert ff.is_enabled("native.camera") is False


def test_enable_disable() -> None:
    ff = FeatureFlags()
    ff.enable("native.camera")
    assert ff.is_enabled("native.camera") is True
    ff.disable("native.camera")
    assert ff.is_enabled("native.camera") is False


def test_kill_switch_overrides_all_flags() -> None:
    ff = FeatureFlags(flags={"a": True, "b": True})
    assert ff.is_enabled("a") and ff.is_enabled("b")
    ff.set_kill_switch(True)
    assert ff.is_enabled("a") is False and ff.is_enabled("b") is False
    snap = ff.snapshot()
    assert snap["kill_switch"] is True
    assert snap["effective"] == {"a": False, "b": False}
    ff.set_kill_switch(False)
    assert ff.is_enabled("a") is True


def test_persistence(tmp_path) -> None:
    path = tmp_path / "flags.json"
    ff = FeatureFlags(path=path)
    ff.enable("native.location")
    ff.set_kill_switch(True)
    reloaded = FeatureFlags(path=path)
    assert reloaded.kill_switch is True
    # flag recorded True but kill switch overrides effective state to False
    assert reloaded.snapshot()["flags"]["native.location"] is True
    assert reloaded.is_enabled("native.location") is False
