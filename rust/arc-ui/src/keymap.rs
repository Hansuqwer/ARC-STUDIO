//! Keymap — chords -> CommandId, with import/export for parity tests
//! (brief facade sketch). Plain-text format so keybindings round-trip and
//! diffs stay reviewable; conflicts are errors, not last-write-wins.

use crate::command::CommandId;
use std::collections::BTreeMap;
use std::fmt;

/// A normalized chord like "ctrl+shift+p" or "f6". Modifier order is
/// canonicalized (ctrl, alt, shift, cmd) so "shift+ctrl+p" == "ctrl+shift+p".
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Chord(String);

#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum KeymapError {
    #[error("empty chord")]
    Empty,
    #[error("conflict: {chord} already bound to {existing}")]
    Conflict { chord: String, existing: String },
    #[error("parse error at line {line}: {msg}")]
    Parse { line: usize, msg: String },
}

impl Chord {
    pub fn parse(s: &str) -> Result<Self, KeymapError> {
        let parts: Vec<&str> = s
            .split('+')
            .map(str::trim)
            .filter(|p| !p.is_empty())
            .collect();
        if parts.is_empty() {
            return Err(KeymapError::Empty);
        }
        let mut mods = Vec::new();
        let mut key = None;
        for p in &parts {
            match p.to_ascii_lowercase().as_str() {
                m @ ("ctrl" | "alt" | "shift" | "cmd") => mods.push(m.to_string()),
                k => key = Some(k.to_string()),
            }
        }
        let key = key.ok_or(KeymapError::Empty)?;
        mods.sort_by_key(|m| match m.as_str() {
            "ctrl" => 0,
            "alt" => 1,
            "shift" => 2,
            _ => 3, // cmd
        });
        let mut out = mods.join("+");
        if !out.is_empty() {
            out.push('+');
        }
        out.push_str(&key);
        Ok(Chord(out))
    }
}

impl fmt::Display for Chord {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

#[derive(Debug, Default)]
pub struct Keymap {
    bindings: BTreeMap<Chord, CommandId>,
}

impl Keymap {
    pub fn bind(&mut self, chord: Chord, cmd: CommandId) -> Result<(), KeymapError> {
        if let Some(existing) = self.bindings.get(&chord) {
            return Err(KeymapError::Conflict {
                chord: chord.to_string(),
                existing: existing.0.to_string(),
            });
        }
        self.bindings.insert(chord, cmd);
        Ok(())
    }

    pub fn resolve(&self, chord: &Chord) -> Option<CommandId> {
        self.bindings.get(chord).copied()
    }

    /// Export: one `chord = command.id` per line, sorted (parity-test stable).
    pub fn export(&self) -> String {
        self.bindings
            .iter()
            .map(|(c, id)| format!("{c} = {}\n", id.0))
            .collect()
    }

    /// Import the export format. `command_lookup` maps ids back to static ids
    /// registered in the CommandRegistry (unknown ids are line errors).
    pub fn import(
        text: &str,
        command_lookup: impl Fn(&str) -> Option<CommandId>,
    ) -> Result<Self, KeymapError> {
        let mut km = Self::default();
        for (i, line) in text.lines().enumerate() {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            let (chord_s, cmd_s) = line.split_once('=').ok_or(KeymapError::Parse {
                line: i + 1,
                msg: "expected `chord = command.id`".into(),
            })?;
            let chord = Chord::parse(chord_s.trim()).map_err(|e| KeymapError::Parse {
                line: i + 1,
                msg: e.to_string(),
            })?;
            let cmd = command_lookup(cmd_s.trim()).ok_or(KeymapError::Parse {
                line: i + 1,
                msg: format!("unknown command id: {}", cmd_s.trim()),
            })?;
            km.bind(chord, cmd)?;
        }
        Ok(km)
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    const IDS: &[&str] = &["arc.palette.open", "arc.focus.next"];

    fn lookup(s: &str) -> Option<CommandId> {
        IDS.iter().find(|i| **i == s).map(|i| CommandId(i))
    }

    #[test]
    fn chord_normalization() {
        assert_eq!(
            Chord::parse("shift+ctrl+P").unwrap(),
            Chord::parse("ctrl+shift+p").unwrap()
        );
    }

    #[test]
    fn conflicts_are_errors() {
        let mut km = Keymap::default();
        km.bind(Chord::parse("f6").unwrap(), CommandId("arc.focus.next"))
            .unwrap();
        let err = km
            .bind(Chord::parse("F6").unwrap(), CommandId("arc.palette.open"))
            .unwrap_err();
        assert!(matches!(err, KeymapError::Conflict { .. }));
    }

    #[test]
    fn export_import_round_trip() {
        let mut km = Keymap::default();
        km.bind(
            Chord::parse("ctrl+shift+p").unwrap(),
            CommandId("arc.palette.open"),
        )
        .unwrap();
        km.bind(Chord::parse("f6").unwrap(), CommandId("arc.focus.next"))
            .unwrap();
        let text = km.export();
        let km2 = Keymap::import(&text, lookup).unwrap();
        assert_eq!(km2.export(), text, "round-trip stable");
        assert_eq!(
            km2.resolve(&Chord::parse("ctrl+shift+p").unwrap()),
            Some(CommandId("arc.palette.open"))
        );
    }
}
