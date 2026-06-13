//! Theme — honors `NO_COLOR` (https://no-color.org) and high-contrast mode.
//! DoD gate: high-contrast / NO_COLOR demonstrable (Sprint-2 exit).

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Theme {
    pub high_contrast: bool,
    /// True when the `NO_COLOR` env var is set non-empty (spec: presence wins).
    pub no_color: bool,
}

impl Theme {
    /// Build from the process environment. `ARC_HIGH_CONTRAST=1` opts into
    /// high-contrast; `NO_COLOR` (any non-empty value) disables color.
    pub fn from_env() -> Self {
        Self::from_vars(
            std::env::var("NO_COLOR").ok().as_deref(),
            std::env::var("ARC_HIGH_CONTRAST").ok().as_deref(),
        )
    }

    /// Pure constructor for tests.
    pub fn from_vars(no_color: Option<&str>, high_contrast: Option<&str>) -> Self {
        Self {
            no_color: no_color.is_some_and(|v| !v.is_empty()),
            high_contrast: high_contrast == Some("1"),
        }
    }

    /// Status conveyed by text, not color alone (wireframe a11y blocks): when
    /// `no_color` is set, glyph+text markers replace color coding everywhere.
    pub fn status_marker(&self, level: StatusLevel) -> &'static str {
        match (self.no_color, level) {
            (true, StatusLevel::Ok) => "[OK]",
            (true, StatusLevel::Warn) => "[WARN]",
            (true, StatusLevel::Error) => "[ERR]",
            (false, StatusLevel::Ok) => "●",
            (false, StatusLevel::Warn) => "◐",
            (false, StatusLevel::Error) => "○",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StatusLevel {
    Ok,
    Warn,
    Error,
}

/// A framework-free RGB color triple (0–255 per channel).
/// Used by the WCAG contrast checker — the actual gpui `Rgba` values in
/// `render_gpui` are derived from these same hex constants.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ThemeColor {
    pub r: u8,
    pub g: u8,
    pub b: u8,
}

impl ThemeColor {
    pub const fn hex(hex: u32) -> Self {
        Self {
            r: ((hex >> 16) & 0xff) as u8,
            g: ((hex >> 8) & 0xff) as u8,
            b: (hex & 0xff) as u8,
        }
    }

    /// WCAG relative luminance: L = 0.2126R + 0.7152G + 0.0722B (linearised).
    pub fn luminance(self) -> f64 {
        fn linearise(c: u8) -> f64 {
            let s = c as f64 / 255.0;
            if s <= 0.04045 {
                s / 12.92
            } else {
                ((s + 0.055) / 1.055f64).powf(2.4)
            }
        }
        0.2126 * linearise(self.r) + 0.7152 * linearise(self.g) + 0.0722 * linearise(self.b)
    }

    /// WCAG contrast ratio between two colors: (L_lighter + 0.05) / (L_darker + 0.05).
    pub fn contrast_ratio(self, other: Self) -> f64 {
        let l1 = self.luminance();
        let l2 = other.luminance();
        let (lighter, darker) = if l1 >= l2 { (l1, l2) } else { (l2, l1) };
        (lighter + 0.05) / (darker + 0.05)
    }
}

/// Color palette for a given theme mode.
/// Hex values mirror the constants in `render_gpui.rs` / `render_workspace_gpui.rs`.
pub struct ThemePalette {
    pub fg: ThemeColor,
    pub bg: ThemeColor,
    pub selected_fg: ThemeColor,
    pub selected_bg: ThemeColor,
}

impl ThemePalette {
    pub fn for_theme(theme: &Theme) -> Self {
        if theme.no_color {
            // NO_COLOR: black text on white, grey selection
            Self {
                fg: ThemeColor::hex(0x000000),
                bg: ThemeColor::hex(0xffffff),
                selected_fg: ThemeColor::hex(0x000000),
                selected_bg: ThemeColor::hex(0xd0d0d0),
            }
        } else if theme.high_contrast {
            // High-contrast: white text on black; yellow selection with BLACK text
            // (yellow+white fails WCAG AA; yellow+black = 19.6:1 — well above 4.5:1)
            Self {
                fg: ThemeColor::hex(0xffffff),
                bg: ThemeColor::hex(0x000000),
                selected_fg: ThemeColor::hex(0x000000),
                selected_bg: ThemeColor::hex(0xffff00),
            }
        } else {
            // Default dark theme
            Self {
                fg: ThemeColor::hex(0xd4d4d4),
                bg: ThemeColor::hex(0x1e1e1e),
                selected_fg: ThemeColor::hex(0xffffff),
                selected_bg: ThemeColor::hex(0x094f9c),
            }
        }
    }

    /// Minimum contrast ratio across the fg/bg and selected_fg/selected_bg pairs.
    pub fn min_contrast_ratio(&self) -> f64 {
        self.fg
            .contrast_ratio(self.bg)
            .min(self.selected_fg.contrast_ratio(self.selected_bg))
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn no_color_presence_wins() {
        assert!(Theme::from_vars(Some("1"), None).no_color);
        assert!(Theme::from_vars(Some("anything"), None).no_color);
        assert!(!Theme::from_vars(Some(""), None).no_color); // empty = unset per spec
        assert!(!Theme::from_vars(None, None).no_color);
    }

    #[test]
    fn no_color_swaps_markers_for_text() {
        let plain = Theme::from_vars(Some("1"), None);
        assert_eq!(plain.status_marker(StatusLevel::Ok), "[OK]");
        let color = Theme::from_vars(None, None);
        assert_eq!(color.status_marker(StatusLevel::Ok), "●");
    }

    #[test]
    fn contrast_ratio_black_white_is_21() {
        let black = ThemeColor::hex(0x000000);
        let white = ThemeColor::hex(0xffffff);
        let ratio = black.contrast_ratio(white);
        assert!((ratio - 21.0).abs() < 0.01, "black/white ratio={ratio:.2}");
    }

    #[test]
    fn high_contrast_palette_meets_wcag_aa() {
        let theme = Theme::from_vars(None, Some("1"));
        let palette = ThemePalette::for_theme(&theme);
        let min = palette.min_contrast_ratio();
        assert!(
            min >= 4.5,
            "high-contrast min contrast {min:.2}:1 fails WCAG AA (need 4.5:1); \
             check fg/bg and selected_fg/selected_bg pairs"
        );
    }

    #[test]
    fn no_color_palette_meets_wcag_aa() {
        let theme = Theme::from_vars(Some("1"), None);
        let palette = ThemePalette::for_theme(&theme);
        let min = palette.min_contrast_ratio();
        assert!(
            min >= 4.5,
            "NO_COLOR min contrast {min:.2}:1 fails WCAG AA (need 4.5:1)"
        );
    }

    #[test]
    fn default_dark_palette_meets_wcag_aa() {
        let theme = Theme::from_vars(None, None);
        let palette = ThemePalette::for_theme(&theme);
        // Normal text pair (fg/bg): must meet AA. Selected pair checked separately.
        let fg_bg = palette.fg.contrast_ratio(palette.bg);
        assert!(
            fg_bg >= 4.5,
            "default dark fg/bg contrast {fg_bg:.2}:1 fails WCAG AA"
        );
    }
}
