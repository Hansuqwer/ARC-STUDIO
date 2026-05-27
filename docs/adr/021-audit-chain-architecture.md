# ADR-021: Audit Chain Architecture for EU AI Act Compliance

**Status:** Proposed (draft 2026-05-21)
**Context:** EU AI Act enforcement deadline Aug 2, 2026; Phase 1 (Polish) implementation
**Related:** ADR-020 (desktop-first), ADR-014 (security architecture), ADR-019 (tool trust boundaries)

## Context

The EU AI Act enters enforcement on August 2, 2026 (72 days from v0.1.0-alpha release). ARC Studio, as a developer tool that orchestrates AI agent workflows, falls under the Act's scope. The specific risk tier depends on deployment topology and use case, but even "limited risk" systems have transparency and audit obligations.

ADR-020 locked the desktop-first product path, which substantially reduces compliance surface area compared to SaaS. A locally-run developer tool that doesn't process third-party data, doesn't make automated decisions about people, and doesn't deploy AI in prohibited or high-risk categories (Annex III) is likely "limited risk" or "minimal risk." However, the Act's transparency obligations (users must know they're interacting with AI) and the general principle of accountability still apply.

The deferred-items list from v0.1.0-alpha included "adapter-wide keyed audit" as out of scope. The EU AI Act work naturally subsumes this: a tamper-evident audit chain that logs every agent decision, tool call, and LLM interaction is both good engineering and regulatory compliance.

The audit chain must be designed to satisfy:
1. **Transparency:** Users can inspect what the agent did and why.
2. **Accountability:** Decisions are attributable to specific principals (even if all decisions in 1.0 are attributed to the single local user).
3. **Tamper-evidence:** Audit records cannot be silently modified after creation.
4. **Completeness:** All material agent actions are logged (LLM calls, tool executions, HITL prompts, budget decisions).
5. **Future-proof:** The design doesn't foreclose the SaaS transition (per ADR-020 guardrails).

The audit chain is not a blockchain. It's a cryptographically-signed append-only log stored locally on the user's filesystem. The threat model is "detect tampering," not "prevent tampering" — a determined attacker with filesystem access can delete the entire audit chain, but they cannot silently modify individual records without detection.

## Decision

ARC Studio implements audit chains with SHA-256 compatibility and optional **HMAC-SHA256** keyed verification where a run path writes keyed audit material. Material agent actions should be logged by covered run paths with:
- Event type and timestamp (ISO 8601 UTC)
- Principal identifier (default `"local"` for desktop 1.0)
- Run ID and session ID
- Event-specific payload (request/response, tool name/args/result, etc.)
- HMAC signature over the event plus the previous event's signature (chain linkage)

The audit chain is stored as a JSONL file per run (`~/.arc/audit/<run_id>.audit.jsonl`) alongside the existing trace file. The HMAC key is derived from a per-installation secret stored in `~/.arc/secrets/audit_key` (created on first run, 256-bit random). The key derivation is parameterizable so future per-tenant or per-session keys don't require schema changes.

Verification is a CLI command (`arc audit verify <run_id>`) that recomputes SHA-256 or HMAC signatures and checks chain integrity for persisted audit material. Export is a CLI command (`arc audit export <run_id>`) that produces an audit bundle (audit chain + verification metadata) suitable for external review or SIEM ingestion where material exists.

## Audit Coverage Classification

| Event/source | Persisted audit chain | Verifier support | Coverage class | Reason |
| --- | --- | --- | --- | --- |
| HMAC audit records | Yes, when written by the run path | Yes | HMAC-covered | Per-run keyed chain record with `signature`, `record_hash`, and `prev_hash`. |
| Legacy SHA-256 records | Yes, when written by the run path | Yes | SHA-256-covered | Backward-compatible chain record with `chain_hash`, `event_hash`, and `prev_hash`. |
| `AUDIT_*` schema payloads | Only when embedded in a chain record | Yes | Payload-supported | The verifier accepts the payload shape but verifies the enclosing chain record. |
| Event-bus `session_changed` | No | N/A unless embedded later | Inspect-only / excluded ephemeral | In-memory daemon notification, not persisted as per-run audit material in Phase 48. |
| Failed daemon session mutations | No | N/A | Out-of-scope | No successful state change; no `session_changed` event emitted. |
| Raw event-bus lines without chain fields | No | Rejected by `arc audit verify` | Out-of-scope | Missing SHA-256/HMAC chain envelope. |

SIEM integration is via OpenTelemetry: audit events are emitted as OTel log records with `gen_ai.*` semantic conventions plus custom `arc.audit.*` attributes. Users who want centralized audit logging configure an OTel exporter; the desktop product does not ship with a default remote exporter.

## Audit Event Schema

Every audit event is a JSON object with this structure:

```json
{
  "version": "1",
  "event_type": "llm_request" | "llm_response" | "tool_call" | "tool_result" | "hitl_prompt" | "hitl_response" | "budget_decision" | "run_started" | "run_completed" | "run_failed" | "run_cancelled",
  "timestamp": "2026-05-21T23:30:00.000Z",
  "principal": "local",
  "run_id": "run_abc123",
  "session_id": "session_xyz789",
  "sequence": 42,
  "payload": { /* event-specific data */ },
  "hmac": "hex-encoded HMAC-SHA256 signature",
  "prev_hmac": "hex-encoded HMAC of previous event (or null for first event)"
}
```

### Event Types and Payloads

**`llm_request`:**
```json
{
  "provider": "anthropic",
  "model": "claude-3-5-sonnet-20241022",
  "messages": [ /* redacted or full, configurable */ ],
  "tools": [ /* tool definitions */ ],
  "max_tokens": 4096,
  "temperature": 1.0
}
```

**`llm_response`:**
```json
{
  "provider": "anthropic",
  "model": "claude-3-5-sonnet-20241022",
  "response_id": "msg_abc123",
  "stop_reason": "end_turn" | "tool_use" | "max_tokens",
  "usage": {
    "input_tokens": 1234,
    "output_tokens": 567,
    "cache_creation_tokens": 0,
    "cache_read_tokens": 0
  },
  "content": [ /* assistant message content, redacted or full */ ],
  "cost": {
    "total_cost": "0.01234567",
    "currency": "USD",
    "measured": true
  }
}
```

**`tool_call`:**
```json
{
  "tool_name": "read_file",
  "tool_id": "toolu_abc123",
  "arguments": { "path": "/path/to/file" },
  "trust_level": "trusted" | "untrusted" | "mixed"
}
```

**`tool_result`:**
```json
{
  "tool_name": "read_file",
  "tool_id": "toolu_abc123",
  "result": { /* tool output, redacted or full */ },
  "trust_level": "trusted" | "untrusted" | "mixed",
  "error": null | { "code": "...", "message": "..." }
}
```

**`hitl_prompt`:**
```json
{
  "prompt_id": "hitl_abc123",
  "prompt_text": "Approve this action?",
  "context": { /* relevant context */ },
  "expires_at": "2026-05-21T23:45:00.000Z"
}
```

**`hitl_response`:**
```json
{
  "prompt_id": "hitl_abc123",
  "response": "approved" | "rejected" | "expired",
  "response_text": "User approved via CLI",
  "responded_at": "2026-05-21T23:32:00.000Z"
}
```

**`budget_decision`:**
```json
{
  "decision": "allowed" | "blocked",
  "reason": "within budget" | "budget exhausted" | "no budget configured",
  "budget_state": {
    "run_budget_remaining": "1.50",
    "session_budget_remaining": "10.00",
    "provider_day_budget_remaining": "50.00"
  }
}
```

**`run_started` / `run_completed` / `run_failed` / `run_cancelled`:**
```json
{
  "runtime": "swarmgraph",
  "mode": "provider_backed" | "gated_local" | "fake",
  "profile": "default",
  "isolation": "subprocess",
  "reason": null | "user cancelled" | "budget exhausted" | "error: ..."
}
```

### Redaction Policy

Audit events include full payloads by default (LLM messages, tool arguments/results) because the audit chain is stored locally and the threat model is "detect tampering," not "hide data from the user."

However, users may configure redaction for sensitive data:
- `ARC_AUDIT_REDACT_MESSAGES=true` → LLM messages replaced with `"<redacted>"`
- `ARC_AUDIT_REDACT_TOOL_ARGS=true` → Tool arguments replaced with `"<redacted>"`
- `ARC_AUDIT_REDACT_TOOL_RESULTS=true` → Tool results replaced with `"<redacted>"`

Redaction is applied before HMAC signing, so redacted and non-redacted audit chains have different signatures. This is intentional: the audit chain verifies what was logged, not what was executed.

## HMAC Key Derivation

**Desktop 1.0 (per-installation key):**

On first run, ARC generates a 256-bit random key and stores it in `~/.arc/secrets/audit_key`:
```
~/.arc/secrets/audit_key (mode 0600, owner-only read/write)
```

The key is used directly for HMAC-SHA256 signing. No key rotation in 1.0.

**Future (per-tenant or per-session keys):**

The audit event schema includes a `principal` field (default `"local"`). When SaaS multi-tenancy is added (1.5 or 2.0), the key derivation becomes:
```
tenant_key = HKDF-SHA256(master_key, salt=tenant_id, info="arc-audit-v1")
```

The `principal` field in audit events identifies the tenant, and verification uses the tenant-specific key. This requires no schema changes, only key management changes.

For per-session keys (if compliance review requires key rotation):
```
session_key = HKDF-SHA256(installation_key, salt=session_id, info="arc-audit-v1")
```

The `session_id` field already exists in audit events, so this is also a key management change, not a schema change.

**Open question:** Should 1.0 use per-session keys instead of per-installation keys? Per-session keys provide better forward secrecy (compromising one session's key doesn't compromise other sessions), but they complicate key management (need to store session keys alongside audit chains). **Lean:** per-installation for 1.0 simplicity; revisit if compliance review surfaces a requirement.

## HMAC Signature Computation

Each audit event's HMAC is computed over:
1. The event's JSON payload (excluding `hmac` and `prev_hmac` fields)
2. The previous event's `hmac` value (or empty string for the first event)

```python
def compute_hmac(event: dict, prev_hmac: str, key: bytes) -> str:
    # Canonical JSON serialization (sorted keys, no whitespace)
    event_json = json.dumps(event, sort_keys=True, separators=(',', ':'))

    # Concatenate event JSON + previous HMAC
    message = event_json.encode('utf-8') + prev_hmac.encode('utf-8')

    # Compute HMAC-SHA256
    h = hmac.new(key, message, hashlib.sha256)
    return h.hexdigest()
```

This creates a hash chain: each event's signature depends on the previous event's signature, so tampering with any event breaks the chain.

## Verification

`arc audit verify <run_id>` recomputes HMAC signatures for all events in the audit chain and checks:
1. Each event's `hmac` matches the recomputed HMAC
2. Each event's `prev_hmac` matches the previous event's `hmac`
3. The `sequence` numbers are consecutive (no gaps)
4. The `run_id` is consistent across all events

Verification output:
```
✓ Audit chain verified: 42 events, no tampering detected
  Run: run_abc123
  Principal: local
  Started: 2026-05-21T23:30:00.000Z
  Completed: 2026-05-21T23:35:00.000Z
  Events: 12 llm_request, 12 llm_response, 8 tool_call, 8 tool_result, 2 hitl_prompt, 2 hitl_response
```

If tampering is detected:
```
✗ Audit chain verification failed: tampering detected at event 15
  Expected HMAC: abc123...
  Actual HMAC:   def456...
  Event type: tool_result
  Timestamp: 2026-05-21T23:32:15.000Z
```

## Export

`arc audit export <run_id>` produces a signed audit bundle:
```json
{
  "version": "1",
  "run_id": "run_abc123",
  "principal": "local",
  "exported_at": "2026-05-21T23:40:00.000Z",
  "events": [ /* all audit events */ ],
  "verification": {
    "verified": true,
    "event_count": 42,
    "first_event_timestamp": "2026-05-21T23:30:00.000Z",
    "last_event_timestamp": "2026-05-21T23:35:00.000Z",
    "signature": "hex-encoded HMAC-SHA256 over the entire bundle"
  }
}
```

The bundle signature is computed over the canonical JSON serialization of the `events` array, so external reviewers can verify the bundle's integrity without access to the original audit chain file.

## SIEM Integration (OpenTelemetry)

Audit events are emitted as OpenTelemetry log records with:
- `gen_ai.system` = `"arc-studio"`
- `gen_ai.request.model` = model name (for llm_request/llm_response events)
- `gen_ai.usage.input_tokens` = input tokens (for llm_response events)
- `gen_ai.usage.output_tokens` = output tokens (for llm_response events)
- `arc.audit.event_type` = event type
- `arc.audit.run_id` = run ID
- `arc.audit.principal` = principal
- `arc.audit.hmac` = HMAC signature
- `arc.audit.prev_hmac` = previous HMAC

Users configure an OTel exporter (OTLP, Datadog, Grafana, etc.) to send audit logs to their SIEM. The desktop product does not ship with a default remote exporter; local-only logging is the default.

Example OTel configuration (`~/.arc/config.yaml`):
```yaml
telemetry:
  audit:
    enabled: true
    exporter: otlp
    endpoint: https://otel-collector.example.com:4317
    headers:
      Authorization: Bearer <token>
```

## EU AI Act Compliance Posture

With this audit chain implementation, ARC Studio's compliance posture is:

**Transparency (Article 13):** ✅ Satisfied. Users can inspect the audit chain to see what the agent did and why. The `arc audit verify` and `arc audit export` commands provide transparency.

**Accountability:** ✅ Satisfied. Every action is attributed to a principal (even if all actions in 1.0 are attributed to `"local"`). The audit chain is tamper-evident, so accountability is verifiable.

**Record-keeping (Article 12):** ✅ Satisfied. Audit chains are retained locally for the lifetime of the run. Users can configure retention policies (e.g., delete audit chains older than 90 days) via `arc runs prune --audit-older-than 90d`.

**Risk tier:** Likely **"limited risk"** (Article 52) or **"minimal risk"** (not explicitly regulated). ARC Studio is a developer tool, not a deployed AI system. It doesn't make automated decisions about people, doesn't process biometric data, doesn't deploy in critical infrastructure, and doesn't fall under Annex III prohibited/high-risk categories. The transparency obligation (users must know they're interacting with AI) is trivially satisfied because ARC Studio is explicitly an AI agent tool.

**Incident reporting (Article 73):** ⚠️ Partially satisfied. The audit chain provides the raw material for incident investigation, but ARC Studio doesn't have a built-in incident reporting mechanism. If a user's agent causes harm (e.g., deletes production data via a tool call), the audit chain can be exported and provided to regulators, but the user is responsible for the reporting process. This is acceptable for a desktop developer tool; a SaaS product would need a more formal incident reporting flow.

## Storage and Retention

Audit chains are stored in `~/.arc/audit/<run_id>.audit.jsonl` (one file per run). The file is created when the run starts and appended to as events occur. The file is closed when the run completes/fails/cancels.

Retention policy:
- Audit chains are retained indefinitely by default (same as trace files).
- Users can configure retention via `arc runs prune --audit-older-than <days>`.
- Deleting a run (`arc runs delete <run_id>`) also deletes its audit chain.

Backup and recovery:
- Audit chains are just files; users can back them up with standard filesystem tools.
- The HMAC key (`~/.arc/secrets/audit_key`) must be backed up separately; without the key, audit chains cannot be verified.

## Performance Considerations

HMAC-SHA256 is fast (~100 MB/s on modern CPUs), so audit logging overhead is negligible for typical agent runs (dozens to hundreds of events per run). The bottleneck is filesystem I/O, not cryptography.

Audit chain files are append-only JSONL, so they can be streamed during verification (no need to load the entire file into memory). For very long runs (thousands of events), verification may take a few seconds, but this is acceptable for a CLI command.

## Migration Path

**v0.1.0-alpha → v0.2 (Phase 1):**
- Implement audit chain for one adapter (SwarmGraph) as proof of concept
- Add `arc audit verify` and `arc audit export` CLI commands
- Add OTel audit log exporter (optional, user-configured)

**v0.2 → v0.5 (Phase 1 completion):**
- Extend audit chain to all adapters (LangGraph, CrewAI, OpenAI Agents, AG2, LlamaIndex)
- Add redaction configuration (`ARC_AUDIT_REDACT_*` env vars)
- Add retention policy (`arc runs prune --audit-older-than`)

**v0.5 → v0.9 (Phase 3):**
- External security audit of audit chain implementation
- Compliance documentation (EU AI Act posture, incident reporting guidance)
- SIEM integration examples (Grafana, Datadog, OpenObserve)

**v0.9 → v1.0 (Phase 4):**
- Audit chain is production-ready and documented
- No schema changes expected post-1.0 (only key management changes for SaaS)

## Alternatives Considered

**Alternative 1: Blockchain-based audit chain**

Rejected. Blockchain provides decentralized consensus, which is unnecessary for a single-user desktop tool. HMAC-signed hash chains provide tamper-evidence without the complexity and performance overhead of blockchain.

**Alternative 2: Asymmetric signatures (RSA/ECDSA)**

Rejected for 1.0. Asymmetric signatures allow third-party verification without sharing the signing key, which is useful for SaaS multi-tenancy (tenants can verify their own audit chains without access to other tenants' keys). However, for desktop 1.0 with a single local user, symmetric HMAC is simpler and faster. If SaaS requires asymmetric signatures, the migration path is:
1. Generate per-tenant RSA/ECDSA key pairs
2. Sign audit events with the private key
3. Distribute public keys to tenants for verification

This is a key management change, not a schema change (the `hmac` field becomes a `signature` field).

**Alternative 3: No audit chain, rely on trace files**

Rejected. Trace files are not tamper-evident. A user (or malicious actor with filesystem access) can modify trace files without detection. The EU AI Act's accountability and transparency obligations require verifiable records, not just logs.

**Alternative 4: Audit chain in SQLite, not JSONL**

Considered. SQLite provides ACID guarantees and efficient querying, but it's harder to verify (need to export to a canonical format first) and harder to back up (binary file, not text). JSONL is simpler, more transparent, and easier to integrate with external tools. If query performance becomes a bottleneck, we can add a SQLite index over audit chains (similar to the existing trace index) without changing the canonical JSONL storage.

## Open Questions

1. **Per-installation vs per-session keys?** Lean: per-installation for 1.0 simplicity. Revisit if compliance review surfaces a requirement for key rotation.

2. **Redaction default?** Lean: no redaction by default (full audit chain). Users who need redaction can configure it. The threat model is "detect tampering," not "hide data from the user."

3. **Retention policy default?** Lean: retain indefinitely (same as trace files). Users who need retention limits can configure them.

4. **SIEM exporter default?** Lean: no default remote exporter (local-only logging). Users who need centralized audit logging configure an OTel exporter.

5. **Incident reporting mechanism?** Lean: no built-in mechanism for 1.0. The audit chain provides the raw material for incident investigation, but the user is responsible for the reporting process. Revisit for SaaS (1.5 or 2.0) if regulatory guidance requires a formal incident reporting flow.

## Consequences

### Positive

- **EU AI Act compliance:** Satisfies transparency, accountability, and record-keeping obligations for "limited risk" tier.
- **Tamper-evidence:** Users can verify that audit records haven't been silently modified.
- **Future-proof:** Schema supports per-tenant and per-session keys without breaking changes.
- **SIEM integration:** OTel export allows centralized audit logging for users who need it.
- **Simple implementation:** HMAC-SHA256 is fast, well-understood, and available in all languages.

### Negative

- **Storage overhead:** Audit chains add ~10-20% storage overhead compared to trace files alone (one audit event per trace event, plus HMAC signatures). Acceptable for desktop 1.0; may need optimization for SaaS with high-volume runs.
- **Key management complexity:** Users must back up the HMAC key (`~/.arc/secrets/audit_key`) separately from audit chains. If the key is lost, audit chains cannot be verified. Mitigated by clear documentation and backup guidance.
- **No built-in incident reporting:** Users are responsible for exporting audit chains and reporting incidents to regulators. Acceptable for desktop 1.0; may need a formal flow for SaaS.

### Risks

- **Compliance interpretation:** The EU AI Act is new, and regulatory guidance is still evolving. ARC Studio's "limited risk" classification may be challenged if the tool is used in high-risk contexts (e.g., deploying agents in critical infrastructure). Mitigated by clear documentation of intended use cases and limitations.
- **Key compromise:** If the HMAC key is compromised, an attacker can forge audit events. Mitigated by filesystem permissions (mode 0600, owner-only) and user education (don't share the key).
- **Retroactive compliance:** Runs executed before the audit chain implementation (v0.1.0-alpha) don't have audit chains. Mitigated by documenting the audit chain's introduction date and noting that pre-audit runs are not verifiable.

## Implementation Plan

**Phase 1 (v0.2, weeks 1-4):**
1. Implement audit event schema and HMAC signing
2. Add audit chain storage (`~/.arc/audit/<run_id>.audit.jsonl`)
3. Implement audit chain for SwarmGraph adapter (proof of concept)
4. Add `arc audit verify <run_id>` CLI command
5. Add tests (unit tests for HMAC, integration tests for audit chain)

**Phase 1 (v0.3-v0.5, weeks 5-12):**
1. Extend audit chain to all adapters
2. Add `arc audit export <run_id>` CLI command
3. Add OTel audit log exporter (optional, user-configured)
4. Add redaction configuration (`ARC_AUDIT_REDACT_*` env vars)
5. Add retention policy (`arc runs prune --audit-older-than`)
6. Documentation (user guide, compliance posture, SIEM integration examples)

**Phase 3 (v0.9, weeks 13-20):**
1. External security audit of audit chain implementation
2. Compliance documentation (EU AI Act posture, incident reporting guidance)
3. SIEM integration examples (Grafana, Datadog, OpenObserve)
4. Remediate any security audit findings

**Phase 4 (v1.0):**
1. Audit chain is production-ready and documented
2. No schema changes expected post-1.0

**Target:** Audit chain complete by end of Phase 1 (week 12), well before Aug 2, 2026 deadline (week 10 from now).
