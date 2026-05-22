# AG-UI event-type parity audit

| Python event             | Wire string            | TS enum (current/proposed) | UI surface          | Status     |
|--------------------------|------------------------|----------------------------|---------------------|------------|
| RUN_STARTED              | `RUN_STARTED`          | RUN_STARTED                | TraceWidget         | ✅ existing |
| RUN_COMPLETED            | `RUN_COMPLETED`        | RUN_COMPLETED              | TraceWidget         | ✅ existing |
| RUN_FAILED               | `RUN_FAILED`           | RUN_FAILED                 | TraceWidget         | ✅ existing |
| RUN_CANCELLED            | `RUN_CANCELLED`        | RUN_CANCELLED              | TraceWidget         | ✅ existing |
| STEP_STARTED             | `STEP_STARTED`         | STEP_STARTED               | TraceWidget         | ✅ existing |
| STEP_COMPLETED           | `STEP_COMPLETED`       | StepCompleted              | TraceWidget         | ❌ missing  |
| STEP_FAILED              | `STEP_FAILED`          | StepFailed                 | TraceWidget         | ❌ missing  |
| AGENT_START              | `AGENT_START`          | AgentStart                 | TraceWidget         | ❌ missing  |
| AGENT_END                | `AGENT_END`            | AgentEnd                   | TraceWidget         | ❌ missing  |
| TOOL_CALL                | `TOOL_CALL`            | ToolCall                   | TraceWidget         | ❌ missing  |
| TOOL_CALL_START          | `TOOL_CALL_START`      | TOOL_CALL_START            | TraceWidget         | ✅ existing |
| TOOL_CALL_ARGS           | `TOOL_CALL_ARGS`       | TOOL_CALL_ARGS             | TraceWidget         | ✅ existing |
| TOOL_CALL_END            | `TOOL_CALL_END`        | TOOL_CALL_END              | TraceWidget         | ✅ existing |
| TOOL_CALL_RESULT         | `TOOL_CALL_RESULT`     | TOOL_CALL_RESULT           | TraceWidget         | ✅ existing |
| TOOL_CALL_ERROR          | `TOOL_CALL_ERROR`      | ToolCallError              | TraceWidget         | ❌ missing  |
| TOOL_END                 | `TOOL_END`             | ToolEnd                    | TraceWidget         | ❌ missing  |
| HANDOFF                  | `HANDOFF`              | Handoff                    | TraceWidget         | ❌ missing  |
| NODE_STARTED             | `NODE_STARTED`         | NodeStarted                | TopologyWidget      | ❌ missing  |
| NODE_UPDATE              | `NODE_UPDATE`          | NodeUpdate                 | TopologyWidget      | ❌ missing  |
| NODE_FAILED              | `NODE_FAILED`          | NodeFailed                 | TopologyWidget      | ❌ missing  |
| MESSAGE                  | `MESSAGE`              | Message                    | TraceWidget         | ❌ missing  |
| MESSAGE_CHUNK            | `MESSAGE_CHUNK`        | MessageChunk               | TraceWidget         | ❌ missing  |
| TEXT_MESSAGE_START       | `TEXT_MESSAGE_START`   | TEXT_MESSAGE_START         | TraceWidget         | ✅ existing |
| TEXT_MESSAGE_CONTENT     | `TEXT_MESSAGE_CONTENT` | TEXT_MESSAGE_CONTENT       | TraceWidget         | ✅ existing |
| TEXT_MESSAGE_END         | `TEXT_MESSAGE_END`     | TEXT_MESSAGE_END           | TraceWidget         | ✅ existing |
| TEXT_MESSAGE_CHUNK       | `TEXT_MESSAGE_CHUNK`   | TEXT_MESSAGE_CHUNK         | TraceWidget         | ✅ existing |
| STATE_SNAPSHOT           | `STATE_SNAPSHOT`       | STATE_SNAPSHOT             | TraceWidget         | ✅ existing |
| SWARMGRAPH_TOPOLOGY      | `SWARMGRAPH_TOPOLOGY`  | SwarmGraphTopology         | TopologyWidget      | ❌ missing  |
| SWARMGRAPH_CONSENSUS     | `SWARMGRAPH_CONSENSUS` | SwarmGraphConsensus        | TraceWidget         | ❌ missing  |
| SWARMGRAPH_COST          | `SWARMGRAPH_COST`      | SwarmGraphCost             | CostPanel           | ❌ missing  |
| HITL_PROMPT              | `HITL_PROMPT`          | HitlPrompt                 | HitlWidget          | ❌ missing  |
| HITL_RESPONSE            | `HITL_RESPONSE`        | HitlResponse               | HitlWidget          | ❌ missing  |
| HITL_TIMEOUT             | `HITL_TIMEOUT`         | HitlTimeout                | HitlWidget          | ❌ missing  |
| CONTRACT_PROPOSED        | `CONTRACT_PROPOSED`    | ContractProposed           | TraceWidget         | ❌ missing  |
| CONTRACT_ACCEPTED        | `CONTRACT_ACCEPTED`    | ContractAccepted           | TraceWidget         | ❌ missing  |
| CONTRACT_FULFILLED       | `CONTRACT_FULFILLED`   | ContractFulfilled          | TraceWidget         | ❌ missing  |
| CONTRACT_VIOLATED        | `CONTRACT_VIOLATED`    | ContractViolated           | TraceWidget         | ❌ missing  |
| RECEIPT_GENERATED        | `RECEIPT_GENERATED`    | ReceiptGenerated           | CostPanel           | ❌ missing  |
| FAILURE_AUTOPSY_GENERATED| `FAILURE_AUTOPSY_GENERATED` | FailureAutopsyGenerated | TraceWidget    | ❌ missing  |
| EVIDENCE_REF_CREATED     | `EVIDENCE_REF_CREATED` | EvidenceRefCreated         | TraceWidget         | ❌ missing  |
| RAW                      | `RAW`                  | RAW                        | TraceWidget         | ✅ existing |
| CUSTOM                   | `CUSTOM`               | CUSTOM                     | TraceWidget         | ✅ existing |

> ⚠️ Before editing this file: run `rg -n "EVENT_TYPES|class.*Event\(" python/src/agent_runtime_cockpit/protocol/` and
> reconcile any names that differ from the table above. Wire strings come from Python; copy them, do not retype.
