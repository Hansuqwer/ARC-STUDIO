"""Theme manager for ARC Studio TUI."""

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


class ThemeManager:
    def __init__(self) -> None:
        self._dark = DARK_THEME
        self._light = LIGHT_THEME
        self._current: Theme = self._detect_theme()

    def _detect_theme(self) -> Theme:
        if os.environ.get("NO_COLOR"):
            return Theme(name="no-color", no_color=True)
        override = os.environ.get("ARC_THEME", "").lower()
        if override == "light":
            return self._light
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
        self._current = self._light if self._current is self._dark else self._dark
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
