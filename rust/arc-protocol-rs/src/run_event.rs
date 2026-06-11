//! RunEvent — mirrors the registry at `protocol/fixtures/run-event-registry.json`
//! (source: `python/src/agent_runtime_cockpit/protocol/events.py` EVENT_TYPES).
//!
//! Shape (fixture `run-event/agent-end.json`):
//! `{"schema_version":2,"type":"AGENT_END","timestamp":"…","run_id":"01HV…","sequence":100,"data":{…}}`

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RunEvent {
    pub schema_version: u32,
    /// SCREAMING_SNAKE registry name; unknown kinds are tolerated (additive rule).
    #[serde(rename = "type")]
    pub kind: String,
    /// RFC3339; kept as string, parsed lazily.
    pub timestamp: String,
    /// ULID.
    pub run_id: String,
    /// Ordered-stream resume key; gap detection => `Stale` surface state, never silence.
    pub sequence: u64,
    #[serde(default)]
    pub data: Map<String, Value>,
    /// Unknown-field tolerance (additive rule): retained, re-encoded.
    #[serde(flatten)]
    pub extra: Map<String, Value>,
}

/// Typed projections for kinds the UI renders specially; everything else stays raw.
#[derive(Debug, Clone)]
pub enum KnownRunEvent {
    AgentStart {
        agent_name: String,
    },
    AgentEnd {
        agent_name: String,
        output: Option<String>,
    },
    /// NEVER an error — forward compatibility. 52 of 69 registered kinds have
    /// no fixture yet (see reports/fixture-coverage.md); they all land here
    /// until typed projections are justified by a panel that renders them.
    Unknown(RunEvent),
}

impl From<RunEvent> for KnownRunEvent {
    fn from(e: RunEvent) -> Self {
        let s = |k: &str| e.data.get(k).and_then(Value::as_str).map(str::to_owned);
        match e.kind.as_str() {
            "AGENT_START" => Self::AgentStart {
                agent_name: s("agent_name").unwrap_or_default(),
            },
            "AGENT_END" => Self::AgentEnd {
                agent_name: s("agent_name").unwrap_or_default(),
                output: s("output"),
            },
            _ => Self::Unknown(e),
        }
    }
}
