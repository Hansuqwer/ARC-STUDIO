# 13 — Graph/Chat/Evidence Cross-Linking

## Summary

Cross-surface linking means: selecting a graph node highlights related chat messages, tool cards, approvals, and receipts. Clicking a cited chat message focuses the originating graph node. This makes the cockpit feel cohesive rather than having separate, disconnected panels.

**Spec:** `ARC_STUDIO_UX_SPEC.md:11.9.1`
**Status:** [MISSING] — no cross-linking code exists

## Stable IDs

For cross-linking to work, all surfaces must carry stable IDs:

| ID Type | Format | Carried by |
|---------|--------|------------|
| `message_id` | `msg_<ulid>` | Chat messages |
| `decision_id` | `dec_<ulid>` | Router decisions, approval decisions |
| `approval_id` | `apr_<ulid>` | HITL approvals |
| `policy_decision_id` | `pd_<ulid>` | Policy enforcement decisions |
| `node_id` | `<workflow>.<node_name>` | Graph nodes |
| `tool_call_id` | `tc_<ulid>` | Tool call events |
| `edge_id` | `<from>→<to>` | Graph edges |
| `run_id` | `run_<ulid>` | Run records |
| `contract_id` | `ctr_<ulid>` | Run contracts |
| `receipt_id` | `rcpt_<ulid>` | Run receipts |
| `evidence_id` | `ev_<ulid>` | Evidence refs |
| `session_id` | ULID | Sessions |

## Linking Data

Events carry cross-references:

```json
{
  "type": "TOOL_CALL",
  "data": {
    "node_id": "reviewer_001",
    "tool_call_id": "tc_01J...",
    "message_id": "msg_01J...",
    "evidence_refs": [{"evidenceId": "ev_001", "kind": "tool_output", "target": "..."}]
  }
}
```

## v0.1 Cross-Linking Operations

| Operation | From → To | Implementation |
|-----------|-----------|----------------|
| Select graph node | Graph → Chat | Highlight chat messages with matching `node_id` |
| Select graph node | Graph → Evidence | Highlight evidence chips with matching `node_id` |
| Click evidence chip | Evidence → File | Open file in Theia editor at line range |
| Click evidence chip | Evidence → Run | Navigate to run detail in Runs tab |
| Click receipt link | Receipt → Run | Navigate to run detail |
| Click message link | Chat → Graph | Focus graph node with matching `node_id` |

## Implementation

### Event Enrichment

In `python/src/agent_runtime_cockpit/protocol/events.py`, ensure every event type carries:
- `node_id` when applicable
- `message_id` when applicable
- `tool_call_id` when applicable
- `evidence_refs` list

### Cross-Linking Service

**Create file:** `python/src/agent_runtime_cockpit/orchestration/cross_linker.py`

```python
class CrossLinker:
    """
    Builds a cross-reference index of all entities in a session.
    Links: messages ↔ graph nodes ↔ tool calls ↔ approvals ↔ receipts.
    """

    def __init__(self):
        self._msg_to_node: dict[str, set[str]] = {}
        self._node_to_msg: dict[str, set[str]] = {}
        self._node_to_evidence: dict[str, set[str]] = {}

    def index_event(self, event: RunEvent):
        """Index an event for cross-referencing."""
        node_id = event.data.get('node_id')
        message_id = event.data.get('message_id')
        evidence_refs = event.data.get('evidence_refs', [])

        if node_id and message_id:
            self._msg_to_node.setdefault(message_id, set()).add(node_id)
            self._node_to_msg.setdefault(node_id, set()).add(message_id)

        if node_id and evidence_refs:
            for ref in evidence_refs:
                self._node_to_evidence.setdefault(node_id, set()).add(ref['evidenceId'])

    def get_linked_messages(self, node_id: str) -> list[str]:
        return list(self._node_to_msg.get(node_id, []))

    def get_linked_nodes(self, message_id: str) -> list[str]:
        return list(self._msg_to_node.get(message_id, []))

    def get_linked_evidence(self, node_id: str) -> list[str]:
        return list(self._node_to_evidence.get(node_id, []))
```

### Frontend Cross-Linking

In the Theia frontend, the `ArcStudioWidget` manages cross-surface state:

```typescript
interface CrossLinkState {
  selectedNodeId: string | null;
  highlightedMessageIds: string[];
  highlightedEvidenceIds: string[];
}

// When user selects a graph node:
function onNodeSelected(nodeId: string) {
  // 1. Get linked messages from CrossLinker
  // 2. Highlight those messages in ChatTab
  // 3. Get linked evidence from CrossLinker
  // 4. Highlight those evidence chips
}
```

## Entry Points to Extend

| File | What to Change |
|------|----------------|
| `protocol/events.py` | Add `node_id`, `message_id`, `tool_call_id`, `evidence_refs` to event data |
| `orchestration/cross_linker.py` | NEW: cross-reference index |
| `orchestration/event_broker.py` | Feed events to CrossLinker on publish |
| `adapters/base.py` | Adapters should emit enriched events |
| `web/routes.py` | Add `GET /api/runs/{id}/links` endpoint |
| `browser/arc-studio-widget.tsx` | Manage CrossLinkState across tabs |
| `browser/components/EvidenceChip.tsx` | Click handler navigates to target |
| `browser/components/ChatMessage.tsx` | Highlight when linked node selected |
| `browser/components/GraphNode.tsx` | emit onNodeSelected callback |

## Acceptance Criteria

- [ ] All events carry stable IDs (node_id, message_id, etc.)
- [ ] Selecting a graph node highlights related chat messages
- [ ] Clicking a cited chat message focuses originating graph node
- [ ] Evidence chips are clickable and navigate to evidence target
- [ ] Receipt links navigate to run detail
- [ ] CrossLinker builds correct index from event stream
- [ ] All tests pass

## Do Not Implement Yet

- Graph explorer command "Explain edge" — v0.1 reserving the read-only command, implementation deferred
- Graph explorer command "Show evidence" — v0.1 reserving, implementation deferred
- Mutating graph commands (Rerun node, Pause, Force handoff) — need checkpoint support [RESERVED v0.2+]
- Run comparison via graph overlay — v0.2
- Replay scrubber with graph state — v0.2
