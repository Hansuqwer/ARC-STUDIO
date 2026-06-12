//! Capability vocabulary + deny-by-default grant set (ADR-0003 §capabilities).
//! Deterministic by construction: a grant either exists in the set or the
//! call is denied. No heuristics, no model calls, no ambient grants.

use std::collections::BTreeSet;

/// The ADR-0003 capability vocabulary. Path/host scoping is part of the
/// capability value, so "fs.read for ${workspace}/docs" and "fs.read for /"
/// are DIFFERENT capabilities — a grant never widens implicitly.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum Capability {
    FsRead { path_scope: String },
    FsWrite { path_scope: String },
    Net { host: String },
    UiPanel,
    UiStatusbar,
    LanguageGrammar,
    AgentInvoke,
    McpClient,
}

impl Capability {
    /// Stable audit string (also the grant-store key).
    pub fn audit_key(&self) -> String {
        match self {
            Capability::FsRead { path_scope } => format!("fs.read:{path_scope}"),
            Capability::FsWrite { path_scope } => format!("fs.write:{path_scope}"),
            Capability::Net { host } => format!("net:{host}"),
            Capability::UiPanel => "ui.panel".into(),
            Capability::UiStatusbar => "ui.statusbar".into(),
            Capability::LanguageGrammar => "language.grammar".into(),
            Capability::AgentInvoke => "agent.invoke".into(),
            Capability::McpClient => "mcp.client".into(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DenialReason {
    pub capability: String,
    pub reason: &'static str,
}

/// Per-workspace grant set. Empty by default — deny-by-default is the
/// constructor, not a configuration option.
#[derive(Debug, Default, Clone)]
pub struct CapabilitySet {
    granted: BTreeSet<Capability>,
}

impl CapabilitySet {
    /// Deny-by-default: a new set grants NOTHING.
    pub fn deny_all() -> Self {
        Self::default()
    }

    pub fn grant(&mut self, cap: Capability) {
        self.granted.insert(cap);
    }

    pub fn revoke(&mut self, cap: &Capability) -> bool {
        self.granted.remove(cap)
    }

    /// Exact-match check. Scoped capabilities must match scope exactly —
    /// prefix-widening is the grant UI's job to *ask* for, never the
    /// checker's job to infer.
    pub fn check(&self, cap: &Capability) -> Result<(), DenialReason> {
        if self.granted.contains(cap) {
            Ok(())
        } else {
            Err(DenialReason {
                capability: cap.audit_key(),
                reason: "not granted for this workspace (deny-by-default)",
            })
        }
    }

    pub fn len(&self) -> usize {
        self.granted.len()
    }

    pub fn is_empty(&self) -> bool {
        self.granted.is_empty()
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn deny_by_default_is_the_constructor() {
        let caps = CapabilitySet::deny_all();
        for cap in [
            Capability::FsRead {
                path_scope: "${workspace}/docs".into(),
            },
            Capability::UiPanel,
            Capability::AgentInvoke,
        ] {
            let denial = caps.check(&cap).unwrap_err();
            assert!(denial.reason.contains("deny-by-default"));
        }
    }

    #[test]
    fn scope_is_part_of_the_capability_no_implicit_widening() {
        let mut caps = CapabilitySet::deny_all();
        caps.grant(Capability::FsRead {
            path_scope: "${workspace}/docs".into(),
        });
        assert!(caps
            .check(&Capability::FsRead {
                path_scope: "${workspace}/docs".into()
            })
            .is_ok());
        // same kind, wider scope: DENIED
        assert!(caps
            .check(&Capability::FsRead {
                path_scope: "${workspace}".into()
            })
            .is_err());
        assert!(caps
            .check(&Capability::FsRead {
                path_scope: "/".into()
            })
            .is_err());
        // write is not read
        assert!(caps
            .check(&Capability::FsWrite {
                path_scope: "${workspace}/docs".into()
            })
            .is_err());
    }

    #[test]
    fn revoke_takes_effect_immediately() {
        let mut caps = CapabilitySet::deny_all();
        let cap = Capability::Net {
            host: "api.example.com".into(),
        };
        caps.grant(cap.clone());
        assert!(caps.check(&cap).is_ok());
        assert!(caps.revoke(&cap));
        assert!(caps.check(&cap).is_err(), "revoked grant denies at once");
    }
}
