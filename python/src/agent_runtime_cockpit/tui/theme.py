"""Theme manager for ARC Studio TUI.

Ships five themes (R-UX4):
  - ``dark``          TokyoNight (default)
  - ``light``         TokyoNight light
  - ``mocha``         Catppuccin Mocha (alt dark)
  - ``latte``         Catppuccin Latte (alt light)
  - ``high-contrast`` accessibility (pure black/white, bright accents)
  - ``mono``          monochrome (NO_COLOR / reduced-color; glyphs fall back to ASCII)

Selection precedence: ``NO_COLOR`` → mono; else ``ARC_THEME=<name>`` → that
theme; else dark. ``toggle()`` keeps its historical dark↔light behaviour;
``select(name)`` and ``cycle()`` reach the full palette.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Theme:
    name: str
    background: str = "#1a1b26"
    foreground: str = "#c0caf5"
    surface: str = "#24283b"
    input_bg: str = "#1f2335"
    accent: str = "#7aa2f7"
    success: str = "#9ece6a"
    error: str = "#f7768e"
    warning: str = "#e0af68"
    info: str = "#7dcfff"
    muted: str = "#565f89"
    border: str = "#3b4261"
    border_focus: str = "#7aa2f7"
    user_msg: str = "#bb9af7"
    assistant_msg: str = "#7dcfff"
    system_msg: str = "#565f89"
    diff_add: str = "#9ece6a"
    diff_add_bg: str = "#1a3620"
    diff_del: str = "#f7768e"
    diff_del_bg: str = "#361a20"
    highlight: str = "#7aa2f7"
    highlight_bg: str = "#283457"
    no_color: bool = False


DARK_THEME = Theme(name="dark")

LIGHT_THEME = Theme(
    name="light",
    background="#f5f5f5",
    foreground="#2c2c2c",
    surface="#ffffff",
    input_bg="#ffffff",
    accent="#2563eb",
    success="#16a34a",
    error="#dc2626",
    warning="#d97706",
    info="#0891b2",
    muted="#9ca3af",
    border="#d1d5db",
    border_focus="#2563eb",
    user_msg="#7c3aed",
    assistant_msg="#2563eb",
    system_msg="#9ca3af",
    diff_add="#16a34a",
    diff_add_bg="#dcfce7",
    diff_del="#dc2626",
    diff_del_bg="#fecaca",
    highlight="#2563eb",
    highlight_bg="#dbeafe",
)

# Catppuccin Mocha — alternate dark palette.
MOCHA_THEME = Theme(
    name="mocha",
    background="#1e1e2e",
    foreground="#cdd6f4",
    surface="#313244",
    input_bg="#181825",
    accent="#89b4fa",
    success="#a6e3a1",
    error="#f38ba8",
    warning="#f9e2af",
    info="#89dceb",
    muted="#6c7086",
    border="#45475a",
    border_focus="#89b4fa",
    user_msg="#cba6f7",
    assistant_msg="#89dceb",
    system_msg="#6c7086",
    diff_add="#a6e3a1",
    diff_add_bg="#1f3320",
    diff_del="#f38ba8",
    diff_del_bg="#33202a",
    highlight="#89b4fa",
    highlight_bg="#2a2b3c",
)

# Catppuccin Latte — alternate light palette.
LATTE_THEME = Theme(
    name="latte",
    background="#eff1f5",
    foreground="#4c4f69",
    surface="#e6e9ef",
    input_bg="#ffffff",
    accent="#1e66f5",
    success="#40a02b",
    error="#d20f39",
    warning="#df8e1d",
    info="#179299",
    muted="#9ca0b0",
    border="#bcc0cc",
    border_focus="#1e66f5",
    user_msg="#8839ef",
    assistant_msg="#04a5e5",
    system_msg="#9ca0b0",
    diff_add="#40a02b",
    diff_add_bg="#e0f0d8",
    diff_del="#d20f39",
    diff_del_bg="#f5d8de",
    highlight="#1e66f5",
    highlight_bg="#dce6fa",
)

# High-contrast accessibility theme — pure black/white + bright accents.
HIGH_CONTRAST_THEME = Theme(
    name="high-contrast",
    background="#000000",
    foreground="#ffffff",
    surface="#000000",
    input_bg="#000000",
    accent="#ffff00",
    success="#00ff00",
    error="#ff3333",
    warning="#ffaa00",
    info="#00ffff",
    muted="#c0c0c0",
    border="#ffffff",
    border_focus="#ffff00",
    user_msg="#00ffff",
    assistant_msg="#ffffff",
    system_msg="#c0c0c0",
    diff_add="#00ff00",
    diff_add_bg="#003300",
    diff_del="#ff3333",
    diff_del_bg="#330000",
    highlight="#ffff00",
    highlight_bg="#333300",
)

# Monochrome — grayscale; sets no_color so widgets swap glyphs for ASCII.
MONO_THEME = Theme(
    name="mono",
    background="#000000",
    foreground="#e0e0e0",
    surface="#1a1a1a",
    input_bg="#0d0d0d",
    accent="#ffffff",
    success="#d0d0d0",
    error="#f0f0f0",
    warning="#c0c0c0",
    info="#b0b0b0",
    muted="#808080",
    border="#606060",
    border_focus="#ffffff",
    user_msg="#f0f0f0",
    assistant_msg="#d0d0d0",
    system_msg="#808080",
    diff_add="#e0e0e0",
    diff_add_bg="#1a1a1a",
    diff_del="#a0a0a0",
    diff_del_bg="#262626",
    highlight="#ffffff",
    highlight_bg="#333333",
    no_color=True,
)

# Registry keyed by canonical name. Order defines the cycle() rotation.
THEMES: dict[str, Theme] = {
    DARK_THEME.name: DARK_THEME,
    LIGHT_THEME.name: LIGHT_THEME,
    MOCHA_THEME.name: MOCHA_THEME,
    LATTE_THEME.name: LATTE_THEME,
    HIGH_CONTRAST_THEME.name: HIGH_CONTRAST_THEME,
    MONO_THEME.name: MONO_THEME,
}

# Friendly aliases accepted by select() / ARC_THEME.
_ALIASES: dict[str, str] = {
    "catppuccin-mocha": "mocha",
    "catppuccin": "mocha",
    "catppuccin-latte": "latte",
    "hc": "high-contrast",
    "contrast": "high-contrast",
    "a11y": "high-contrast",
    "monochrome": "mono",
    "no-color": "mono",
    "nocolor": "mono",
}


def theme_names() -> list[str]:
    """Return the canonical selectable theme names in cycle order."""
    return list(THEMES.keys())


def resolve_theme_name(name: str) -> str | None:
    """Map a user-supplied name/alias to a canonical theme name, or None."""
    key = name.strip().lower()
    key = _ALIASES.get(key, key)
    return key if key in THEMES else None


class ThemeManager:
    def __init__(self) -> None:
        self._dark = DARK_THEME
        self._light = LIGHT_THEME
        self._current: Theme = self._detect_theme()

    def _detect_theme(self) -> Theme:
        if os.environ.get("NO_COLOR"):
            return MONO_THEME
        override = os.environ.get("ARC_THEME", "")
        canonical = resolve_theme_name(override) if override else None
        if canonical:
            return THEMES[canonical]
        return self._dark

    @property
    def current(self) -> Theme:
        return self._current

    @property
    def is_dark(self) -> bool:
        return self._current is self._dark

    @property
    def is_light(self) -> bool:
        return self._current is self._light

    @property
    def is_no_color(self) -> bool:
        return self._current.no_color

    def toggle(self) -> Theme:
        """Historical dark↔light toggle (kept for back-compat)."""
        self._current = self._light if self._current is self._dark else self._dark
        return self._current

    def select(self, name: str) -> Theme | None:
        """Select a theme by name or alias. Returns the theme, or None if unknown."""
        canonical = resolve_theme_name(name)
        if canonical is None:
            return None
        self._current = THEMES[canonical]
        return self._current

    def cycle(self) -> Theme:
        """Rotate to the next theme in registry order."""
        names = theme_names()
        try:
            idx = names.index(self._current.name)
        except ValueError:
            idx = -1
        self._current = THEMES[names[(idx + 1) % len(names)]]
        return self._current

    def css_variables(self) -> str:
        t = self._current
        return (
            f"$background: {t.background};\n$foreground: {t.foreground};\n"
            f"$surface: {t.surface};\n$input-bg: {t.input_bg};\n"
            f"$accent: {t.accent};\n$success: {t.success};\n$error: {t.error};\n"
            f"$warning: {t.warning};\n$info: {t.info};\n$muted: {t.muted};\n"
            f"$border: {t.border};\n$border-focus: {t.border_focus};\n"
            f"$user-msg: {t.user_msg};\n$assistant-msg: {t.assistant_msg};\n"
            f"$system-msg: {t.system_msg};\n"
            f"$diff-add: {t.diff_add};\n$diff-add-bg: {t.diff_add_bg};\n"
            f"$diff-del: {t.diff_del};\n$diff-del-bg: {t.diff_del_bg};\n"
            f"$highlight: {t.highlight};\n$highlight-bg: {t.highlight_bg};\n"
        )
