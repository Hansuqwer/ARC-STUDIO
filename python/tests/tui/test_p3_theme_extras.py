"""Tests for P3 theme extras: NO_COLOR glyph fallbacks and ARC_REDUCED_MOTION."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.tui.theme_extras import (
    _FALLBACK,
    glyph,
    is_reduced_motion,
    thinking_indicator,
)


# ── glyph() ───────────────────────────────────────────────────────────────────


def test_glyph_color_returns_unicode() -> None:
    assert glyph("●", no_color=False) == "●"


def test_glyph_no_color_returns_fallback() -> None:
    assert glyph("●", no_color=True) == "[*]"


def test_glyph_no_color_custom_alt() -> None:
    assert glyph("●", alt="(bullet)", no_color=True) == "(bullet)"


def test_glyph_no_color_unknown_char_returns_itself() -> None:
    assert glyph("★", no_color=True) == "★"


@pytest.mark.parametrize("char", list(_FALLBACK.keys()))
def test_all_fallbacks_are_ascii(char: str) -> None:
    fallback = _FALLBACK[char]
    assert fallback.isascii(), f"Fallback for {char!r} is not ASCII: {fallback!r}"


# ── is_reduced_motion() ───────────────────────────────────────────────────────


def test_reduced_motion_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARC_REDUCED_MOTION", raising=False)
    assert is_reduced_motion() is False


@pytest.mark.parametrize("val", ["1", "true", "yes", "on", "True", "YES"])
def test_reduced_motion_enabled(val: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARC_REDUCED_MOTION", val)
    assert is_reduced_motion() is True


@pytest.mark.parametrize("val", ["0", "false", "no", "off", ""])
def test_reduced_motion_disabled(val: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARC_REDUCED_MOTION", val)
    assert is_reduced_motion() is False


# ── thinking_indicator() ─────────────────────────────────────────────────────


def test_thinking_color_uses_unicode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARC_REDUCED_MOTION", raising=False)
    out = thinking_indicator(no_color=False)
    assert "●" in out


def test_thinking_no_color_uses_ascii(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARC_REDUCED_MOTION", raising=False)
    out = thinking_indicator(no_color=True)
    assert "[*]" in out
    assert "●" not in out


def test_thinking_reduced_motion_no_spinner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARC_REDUCED_MOTION", "1")
    out = thinking_indicator(no_color=False)
    # Reduced motion: no animated glyph, plain text
    assert "Thinking" in out
    assert "●" not in out
