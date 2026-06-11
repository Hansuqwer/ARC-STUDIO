//! CommandRegistry — id -> {title, category, enabled_when}; the palette and
//! keymap both resolve through this single table (CLI/TUI/IDE parity rule).

use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct CommandId(pub &'static str);

/// Why a command is disabled — the palette must expose *why*, not just grey
/// out (review report §11.2; matters when commands gate on daemon/trust state).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Enablement {
    Enabled,
    Disabled { reason: String },
}

type EnabledWhen<C> = Box<dyn Fn(&C) -> Enablement + Send + Sync>;

pub struct Command<C> {
    pub id: CommandId,
    pub title: &'static str,
    pub category: &'static str,
    pub shortcut: Option<&'static str>,
    enabled_when: Option<EnabledWhen<C>>,
}

impl<C> Command<C> {
    pub fn new(id: &'static str, title: &'static str, category: &'static str) -> Self {
        Self {
            id: CommandId(id),
            title,
            category,
            shortcut: None,
            enabled_when: None,
        }
    }

    pub fn shortcut(mut self, s: &'static str) -> Self {
        self.shortcut = Some(s);
        self
    }

    pub fn enabled_when(mut self, f: impl Fn(&C) -> Enablement + Send + Sync + 'static) -> Self {
        self.enabled_when = Some(Box::new(f));
        self
    }

    pub fn enablement(&self, ctx: &C) -> Enablement {
        match &self.enabled_when {
            None => Enablement::Enabled,
            Some(f) => f(ctx),
        }
    }
}

/// `C` is the shell context the enablement predicates read (daemon state,
/// workspace trust, …). Deterministic: predicates are pure functions of it.
pub struct CommandRegistry<C> {
    commands: BTreeMap<CommandId, Command<C>>,
}

impl<C> Default for CommandRegistry<C> {
    fn default() -> Self {
        Self {
            commands: BTreeMap::new(),
        }
    }
}

impl<C> CommandRegistry<C> {
    /// Duplicate registration is a programming error surfaced immediately.
    pub fn register(&mut self, cmd: Command<C>) -> Result<(), CommandId> {
        let id = cmd.id;
        if self.commands.contains_key(&id) {
            return Err(id);
        }
        self.commands.insert(id, cmd);
        Ok(())
    }

    pub fn get(&self, id: CommandId) -> Option<&Command<C>> {
        self.commands.get(&id)
    }

    /// Deterministic iteration order (BTreeMap) — palette listing is stable.
    pub fn iter(&self) -> impl Iterator<Item = &Command<C>> {
        self.commands.values()
    }

    pub fn len(&self) -> usize {
        self.commands.len()
    }

    pub fn is_empty(&self) -> bool {
        self.commands.is_empty()
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    struct Ctx {
        daemon_healthy: bool,
    }

    fn registry() -> CommandRegistry<Ctx> {
        let mut r = CommandRegistry::default();
        r.register(Command::new(
            "arc.runs.open",
            "ARC: Open Runs Panel",
            "panels",
        ))
        .unwrap();
        r.register(
            Command::new(
                "arc.replay.fixture",
                "ARC: Replay Event Stream Fixture",
                "debug",
            )
            .enabled_when(|c: &Ctx| {
                if c.daemon_healthy {
                    Enablement::Enabled
                } else {
                    Enablement::Disabled {
                        reason: "daemon unavailable (status rail: Degraded)".into(),
                    }
                }
            }),
        )
        .unwrap();
        r
    }

    #[test]
    fn duplicate_registration_rejected() {
        let mut r = registry();
        let err = r
            .register(Command::new("arc.runs.open", "dup", "panels"))
            .unwrap_err();
        assert_eq!(err, CommandId("arc.runs.open"));
    }

    #[test]
    fn enablement_exposes_reason() {
        let r = registry();
        let cmd = r.get(CommandId("arc.replay.fixture")).unwrap();
        assert_eq!(
            cmd.enablement(&Ctx {
                daemon_healthy: true
            }),
            Enablement::Enabled
        );
        match cmd.enablement(&Ctx {
            daemon_healthy: false,
        }) {
            Enablement::Disabled { reason } => assert!(reason.contains("daemon")),
            _ => panic!("expected disabled with reason"),
        }
    }
}
