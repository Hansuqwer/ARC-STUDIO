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
}
