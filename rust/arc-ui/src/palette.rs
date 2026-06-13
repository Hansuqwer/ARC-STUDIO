//! PaletteModel — framework-free command palette state machine.
//!
//! Keyboard-only operation IS the acceptance test (brief §3.4): open / type /
//! arrow / execute / escape, all modeled here and unit-tested without any UI
//! framework. The Sprint-3 framework only *renders* this model.
//!
//! Matching: `nucleo-matcher` (Helix's matcher) over the CommandRegistry.

use crate::command::{CommandId, CommandRegistry, Enablement};
use nucleo_matcher::pattern::{CaseMatching, Normalization, Pattern};
use nucleo_matcher::{Config, Matcher};

#[derive(Debug, Clone, PartialEq)]
pub struct PaletteItem {
    pub id: CommandId,
    pub title: String,
    pub category: String,
    pub shortcut: Option<String>,
    pub enablement: Enablement,
    pub score: u32,
}

/// Screen-reader announcement for the current selection (wireframe §6.2 a11y
/// block: name, category, enabled/disabled state, shortcut — announced without
/// stealing focus).
pub fn announce(item: &PaletteItem) -> String {
    let state = match &item.enablement {
        Enablement::Enabled => String::from("enabled"),
        Enablement::Disabled { reason } => format!("disabled: {reason}"),
    };
    let shortcut = item
        .shortcut
        .as_deref()
        .map(|s| format!(", shortcut {s}"))
        .unwrap_or_default();
    format!("{}, {}, {}{}", item.title, item.category, state, shortcut)
}

pub struct PaletteModel {
    pub open: bool,
    pub query: String,
    pub items: Vec<PaletteItem>,
    pub selected: usize,
    /// When true, the entire query is selected (Cmd/Ctrl+A). The next printable
    /// character or backspace replaces/clears the whole query, matching standard
    /// text-field select-all semantics. Any cursor move or commit clears it.
    pub select_all: bool,
    matcher: Matcher,
}

impl Default for PaletteModel {
    fn default() -> Self {
        Self {
            open: false,
            query: String::new(),
            items: Vec::new(),
            selected: 0,
            select_all: false,
            matcher: Matcher::new(Config::DEFAULT),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PaletteKey {
    Char(char),
    Backspace,
    Up,
    Down,
    Enter,
    Escape,
    /// Select the entire query (Cmd/Ctrl+A).
    SelectAll,
}

#[derive(Debug, Clone, PartialEq)]
pub enum PaletteEffect {
    None,
    /// Selection moved — render layer announces `announce(item)` via the
    /// accessibility tree without moving real focus.
    Announce(String),
    Execute(CommandId),
    /// Enter on a disabled command: announce the reason, do NOT execute.
    Rejected {
        reason: String,
    },
    Closed,
}

impl PaletteModel {
    pub fn open_with<C>(&mut self, registry: &CommandRegistry<C>, ctx: &C) {
        self.open = true;
        self.query.clear();
        self.selected = 0;
        self.select_all = false;
        self.refilter(registry, ctx);
    }

    pub fn key<C>(
        &mut self,
        key: PaletteKey,
        registry: &CommandRegistry<C>,
        ctx: &C,
    ) -> PaletteEffect {
        if !self.open {
            return PaletteEffect::None;
        }
        match key {
            PaletteKey::Char(c) => {
                // Selection-replace: typing over a select-all clears first.
                if self.select_all {
                    self.query.clear();
                    self.select_all = false;
                }
                self.query.push(c);
                self.selected = 0;
                self.refilter(registry, ctx);
                self.current_announcement()
            }
            PaletteKey::Backspace => {
                if self.select_all {
                    // Backspace over a full selection clears the whole query.
                    self.query.clear();
                    self.select_all = false;
                } else {
                    self.query.pop();
                }
                self.selected = 0;
                self.refilter(registry, ctx);
                self.current_announcement()
            }
            PaletteKey::SelectAll => {
                if self.query.is_empty() {
                    self.select_all = false;
                    return PaletteEffect::Announce("query empty".into());
                }
                self.select_all = true;
                PaletteEffect::Announce(format!("selected query: {}", self.query))
            }
            PaletteKey::Down => {
                self.select_all = false;
                if !self.items.is_empty() {
                    self.selected = (self.selected + 1).min(self.items.len() - 1);
                }
                self.current_announcement()
            }
            PaletteKey::Up => {
                self.select_all = false;
                self.selected = self.selected.saturating_sub(1);
                self.current_announcement()
            }
            PaletteKey::Enter => match self.items.get(self.selected) {
                None => PaletteEffect::None,
                Some(item) => match &item.enablement {
                    Enablement::Enabled => {
                        let id = item.id;
                        self.close();
                        PaletteEffect::Execute(id)
                    }
                    Enablement::Disabled { reason } => PaletteEffect::Rejected {
                        reason: reason.clone(),
                    },
                },
            },
            PaletteKey::Escape => {
                self.close();
                PaletteEffect::Closed
            }
        }
    }

    fn close(&mut self) {
        self.open = false;
        self.query.clear();
        self.items.clear();
        self.selected = 0;
        self.select_all = false;
    }

    fn current_announcement(&self) -> PaletteEffect {
        match self.items.get(self.selected) {
            Some(item) => PaletteEffect::Announce(announce(item)),
            None => PaletteEffect::Announce(format!("no matches for {}", self.query)),
        }
    }

    fn refilter<C>(&mut self, registry: &CommandRegistry<C>, ctx: &C) {
        self.items.clear();
        if self.query.is_empty() {
            // Empty query: full list in registry (deterministic) order.
            for cmd in registry.iter() {
                self.items.push(PaletteItem {
                    id: cmd.id,
                    title: cmd.title.to_string(),
                    category: cmd.category.to_string(),
                    shortcut: cmd.shortcut.map(str::to_owned),
                    enablement: cmd.enablement(ctx),
                    score: 0,
                });
            }
            return;
        }
        let pattern = Pattern::parse(&self.query, CaseMatching::Ignore, Normalization::Smart);
        let mut buf = Vec::new();
        for cmd in registry.iter() {
            let haystack = nucleo_matcher::Utf32Str::new(cmd.title, &mut buf);
            if let Some(score) = pattern.score(haystack, &mut self.matcher) {
                self.items.push(PaletteItem {
                    id: cmd.id,
                    title: cmd.title.to_string(),
                    category: cmd.category.to_string(),
                    shortcut: cmd.shortcut.map(str::to_owned),
                    enablement: cmd.enablement(ctx),
                    score,
                });
            }
        }
        // Stable sort: score desc, then title for deterministic ties.
        self.items
            .sort_by(|a, b| b.score.cmp(&a.score).then(a.title.cmp(&b.title)));
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;
    use crate::command::Command;

    struct Ctx {
        healthy: bool,
    }

    fn registry() -> CommandRegistry<Ctx> {
        let mut r = CommandRegistry::default();
        for (id, title) in [
            ("arc.replay.fixture", "ARC: Replay Event Stream Fixture"),
            ("arc.runs.open", "ARC: Open Runs Panel"),
            ("arc.theme.contrast", "ARC: Toggle High Contrast"),
            ("arc.index.rebuild", "ARC: Rebuild Search Index"),
            ("arc.hitl.queue", "ARC: Open HITL Queue"),
            ("arc.daemon.health", "ARC: Show Daemon Health"),
        ] {
            r.register(Command::new(id, title, "arc")).unwrap();
        }
        r.register(
            Command::new("arc.run.start", "ARC: Start Run", "runs").enabled_when(|c: &Ctx| {
                if c.healthy {
                    Enablement::Enabled
                } else {
                    Enablement::Disabled {
                        reason: "daemon degraded".into(),
                    }
                }
            }),
        )
        .unwrap();
        r
    }

    /// The §6.2 keyboard-only acceptance flow: open → type → arrow → execute.
    #[test]
    fn keyboard_only_open_type_arrow_execute() {
        let reg = registry();
        let ctx = Ctx { healthy: true };
        let mut p = PaletteModel::default();
        p.open_with(&reg, &ctx);
        assert_eq!(p.items.len(), 7); // full list on empty query

        for c in "replay".chars() {
            p.key(PaletteKey::Char(c), &reg, &ctx);
        }
        assert!(p.items[0].title.contains("Replay"), "best match first");

        let eff = p.key(PaletteKey::Enter, &reg, &ctx);
        assert_eq!(eff, PaletteEffect::Execute(CommandId("arc.replay.fixture")));
        assert!(!p.open, "palette closes after execute");
    }

    #[test]
    fn escape_closes_without_execute() {
        let reg = registry();
        let ctx = Ctx { healthy: true };
        let mut p = PaletteModel::default();
        p.open_with(&reg, &ctx);
        assert_eq!(p.key(PaletteKey::Escape, &reg, &ctx), PaletteEffect::Closed);
        assert!(!p.open);
    }

    #[test]
    fn disabled_command_announces_reason_and_does_not_execute() {
        let reg = registry();
        let ctx = Ctx { healthy: false };
        let mut p = PaletteModel::default();
        p.open_with(&reg, &ctx);
        for c in "start run".chars() {
            p.key(PaletteKey::Char(c), &reg, &ctx);
        }
        assert!(p.items[0].title.contains("Start Run"));
        match p.key(PaletteKey::Enter, &reg, &ctx) {
            PaletteEffect::Rejected { reason } => assert!(reason.contains("degraded")),
            other => panic!("expected Rejected, got {other:?}"),
        }
        assert!(p.open, "palette stays open after rejected execute");
    }

    #[test]
    fn arrows_announce_name_category_state_shortcut() {
        let reg = registry();
        let ctx = Ctx { healthy: true };
        let mut p = PaletteModel::default();
        p.open_with(&reg, &ctx);
        match p.key(PaletteKey::Down, &reg, &ctx) {
            PaletteEffect::Announce(a) => {
                assert!(a.contains("ARC:"), "announces name: {a}");
                assert!(a.contains("enabled") || a.contains("disabled"));
            }
            other => panic!("expected Announce, got {other:?}"),
        }
    }

    #[test]
    fn selection_clamps_at_bounds() {
        let reg = registry();
        let ctx = Ctx { healthy: true };
        let mut p = PaletteModel::default();
        p.open_with(&reg, &ctx);
        p.key(PaletteKey::Up, &reg, &ctx);
        assert_eq!(p.selected, 0);
        for _ in 0..100 {
            p.key(PaletteKey::Down, &reg, &ctx);
        }
        assert_eq!(p.selected, p.items.len() - 1);
    }

    #[test]
    fn select_all_then_type_replaces_query() {
        let reg = registry();
        let ctx = Ctx { healthy: true };
        let mut p = PaletteModel::default();
        p.open_with(&reg, &ctx);
        for c in "replay".chars() {
            p.key(PaletteKey::Char(c), &reg, &ctx);
        }
        assert_eq!(p.query, "replay");

        let eff = p.key(PaletteKey::SelectAll, &reg, &ctx);
        assert!(p.select_all, "select_all flag set");
        match eff {
            PaletteEffect::Announce(a) => assert!(a.contains("selected query")),
            other => panic!("expected Announce, got {other:?}"),
        }

        // Typing over the selection replaces the whole query.
        p.key(PaletteKey::Char('r'), &reg, &ctx);
        assert_eq!(p.query, "r", "query replaced, not appended");
        assert!(!p.select_all, "select_all cleared after replace");
    }

    #[test]
    fn select_all_then_backspace_clears_query() {
        let reg = registry();
        let ctx = Ctx { healthy: true };
        let mut p = PaletteModel::default();
        p.open_with(&reg, &ctx);
        for c in "runs".chars() {
            p.key(PaletteKey::Char(c), &reg, &ctx);
        }
        p.key(PaletteKey::SelectAll, &reg, &ctx);
        p.key(PaletteKey::Backspace, &reg, &ctx);
        assert_eq!(p.query, "", "backspace over selection clears query");
        assert!(!p.select_all);
    }

    #[test]
    fn select_all_on_empty_query_is_noop() {
        let reg = registry();
        let ctx = Ctx { healthy: true };
        let mut p = PaletteModel::default();
        p.open_with(&reg, &ctx);
        let eff = p.key(PaletteKey::SelectAll, &reg, &ctx);
        assert!(!p.select_all, "no selection when query empty");
        match eff {
            PaletteEffect::Announce(a) => assert!(a.contains("empty")),
            other => panic!("expected Announce, got {other:?}"),
        }
    }

    #[test]
    fn navigation_clears_select_all() {
        let reg = registry();
        let ctx = Ctx { healthy: true };
        let mut p = PaletteModel::default();
        p.open_with(&reg, &ctx);
        for c in "open".chars() {
            p.key(PaletteKey::Char(c), &reg, &ctx);
        }
        p.key(PaletteKey::SelectAll, &reg, &ctx);
        assert!(p.select_all);
        p.key(PaletteKey::Down, &reg, &ctx);
        assert!(!p.select_all, "arrow navigation deselects the query");
        // Query is preserved — only the selection was cleared.
        assert_eq!(p.query, "open");
    }
}
