# ADR-024 — MicroVM Public Execution Contract

**Status:** Accepted  
**Date:** 2026-05-26  
**Authors:** ARC Studio sandbox team  
**Related:** Phase 37 (R38), `docs/research/sandbox-and-microvm.md`, ADR-014 (security architecture)

---

## Context

ARC Studio has a `MicroVMIsolationProvider` and internal harness
(`LimaIntegrationHarness`, planned `FirecrackerIntegrationHarness`) that
support preflight/doctor and design-proof surfaces for macOS (Lima) and
Linux (Firecracker). As of Phase 37.14 the following is true:

- `MicroVMIsolationProvider.execute()` always raises `NotImplementedError`.
- `arc sandbox run --provider microvm` is blocked at the provider layer.
- Lima harness exists as an internal opt-in helper only.
- Firecracker is preflight/doctor only.
- No real microVM command execution has been proven in tests.

This ADR defines the precise prerequisites, gate mechanism, platform
scoping, and audit event schema that must be satisfied before
`arc sandbox run --provider microvm` can be unblocked for production use.

---

## Decision

### 1. Prerequisites — tests that must pass before execution is unblocked

All of the following must be green in CI or in a documented opt-in host
run before `arc sandbox run --provider microvm` can be enabled:

| # | Proof required | Test file | Gate |
|---|---|---|---|
| P1 | Lifecycle proof: create → start → exec → stop/delete completes without errors | `test_lima_smoke.py` / `test_firecracker_smoke.py` | `ARC_MICROVM_INTEGRATION=1` + binary present |
| P2 | Network-off proof: guest has no default route before user argv runs | network_proof test inside harness | same gate |
| P3 | Workspace-mount proof: only the workspace dir is accessible inside guest; host home/root not reachable | mount isolation test (future) | same gate |
| P4 | Teardown proof: `limactl delete -f` / Firecracker stop executes on success, failure, timeout, and host SIGINT | harness teardown tests | same gate |
| P5 | Symlink/path-traversal escape denied: guest cannot follow symlinks outside /workspace | mount escape test (future) | same gate |
| P6 | stdout/stderr caps enforced: large output is truncated, not buffered into memory | bounded-output test | same gate |
| P7 | Audit event emitted for every microVM execution: stable schema, includes all required fields | audit event test | same gate |

Tests P3 and P5 (workspace-mount isolation and symlink escape) are the
highest-risk blockers and must be completed on a real host before the
gate is opened.

### 2. Unblock gate

When all prerequisites above are met, the execution gate is:

```
ARC_MICROVM_EXEC_ENABLED=1
```

This variable is **not yet honored** by any code. It is defined here as
the future signal so docs, tests, and the provider can reference it.

Implementation when honored:

- `MicroVMIsolationProvider.execute()` reads this env var.
- If unset → raise `NotImplementedError` (current behavior, permanent default).
- If set AND prerequisites are proven → delegate to `LimaIntegrationHarness`
  on macOS or `FirecrackerIntegrationHarness` on Linux.
- The variable must never silently enable execution without all P1–P7 proofs.

### 3. Execution denied by default

`arc sandbox run --provider microvm` must deny execution unless:

1. `ARC_MICROVM_EXEC_ENABLED=1` is explicitly set.
2. The platform-appropriate binary is present (`limactl` / `firecracker`).
3. `ARC_MICROVM_INTEGRATION=1` is also set (keeps the opt-in dual-gate pattern).

Absence of any of the three → `NotImplementedError` with a clear message
referencing this ADR.

### 4. Platform support

| Platform | Provider | Status |
|---|---|---|
| macOS (≥ 13, Apple Silicon or Intel) | Lima / Apple Virtualization.framework | Target; requires limactl + ARC_MICROVM_EXEC_ENABLED=1 |
| Linux (x86_64, aarch64 with KVM) | Firecracker (primary), Cloud Hypervisor (secondary) | Target; requires /dev/kvm + binary + ARC_MICROVM_EXEC_ENABLED=1 |
| Windows | — | **Explicitly unsupported**; emit clear error: "microVM execution is not supported on Windows" |
| Other (FreeBSD, etc.) | — | Blocked; `microvm_preflight()` returns `status: blocked` |

### 5. Teardown failure handling

If teardown fails (e.g. `limactl delete -f` returns non-zero, or
Firecracker process cannot be stopped):

- Surface the teardown error in `IsolationResult.stderr` with prefix
  `"teardown-error: "`.
- Do **not** suppress or ignore teardown errors.
- Mark `IsolationResult.exit_code` as `-1` if teardown failure occurs
  after a successful run (workspace may not be cleaned up).
- Log the instance name / jail path so operators can clean up manually.
- Never claim the result as successful if teardown failed.

### 6. Audit event schema for microVM execution

Every `arc sandbox run --provider microvm` invocation (allowed or denied)
must emit an audit event with this stable JSON schema:

```json
{
  "event": "sandbox.microvm.run",
  "version": 1,
  "command": ["<argv0>", "..."],
  "cwd": "/absolute/workspace/path",
  "provider": "microvm",
  "microvm_provider": "lima|firecracker",
  "platform": "macos|linux",
  "policy": "<policy-name>",
  "classification": "<CommandClassification>",
  "decision": {
    "allowed": true,
    "reason": "<string>"
  },
  "lifecycle": ["template", "start", "network_proof", "run", "teardown"],
  "lifecycle_errors": [],
  "exit_code": 0,
  "stdout_truncated": false,
  "stderr_truncated": false,
  "redaction_applied": false,
  "teardown_status": "ok|failed|skipped",
  "network_proof_passed": true,
  "start_ts": "<ISO-8601>",
  "end_ts": "<ISO-8601>",
  "duration_ms": 1234,
  "gate": "ARC_MICROVM_EXEC_ENABLED=1"
}
```

Fields `lifecycle_errors`, `teardown_status`, and `network_proof_passed`
are mandatory. Missing any of these fields is a schema violation.

---

## Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| Unblock gate env var | `ARC_MICROVM_EXEC_ENABLED=1` | Config flag in `~/.arc/config.yaml`, CLI `--enable-microvm` flag | Env vars are consistent with existing `ARC_MICROVM_INTEGRATION=1` and `ARC_ENABLE_CONTAINER_SANDBOX=1` patterns. Easy to audit in logs. | `isolation/microvm.py` | High |
| Dual gate requirement | Both `ARC_MICROVM_EXEC_ENABLED=1` AND `ARC_MICROVM_INTEGRATION=1` must be set | Single gate | Defense in depth; integration gate proves opt-in intent; exec gate proves explicit production readiness. | `isolation/microvm.py` | High |
| Windows support | Explicitly unsupported with clear error | Deferred silently | Clear error is better UX and prevents confusion about missing microVM behavior on Windows. | `isolation/microvm.py`, `security/sandbox.py` | High |
| Teardown failure | Surface error, mark result failed, log for manual cleanup | Suppress and return run result | Workspace safety requires honest teardown reporting; suppressing leaks resources and may expose host data. | `isolation/microvm.py` | High |
| Audit schema version | `version: 1` stable field | No version field | Schema versioning allows migration without breaking consumers. | `security/sandbox.py` (audit helper) | High |
| Mount proof order | Workspace mount proof must pass before unblocking execution | Mount proof optional | Symlink/hardlink escapes are the highest-risk attack; skipping proof would be a security regression. | Future mount test file | High |

---

## Consequences

### What changes immediately (this ADR)

- `MicroVMIsolationProvider.status()` must include `contract_doc:
  "docs/adr/ADR-024-microvm-public-execution-contract.md"`.
- Error messages from `execute()` must reference this ADR.
- Docs must not claim microVM execution until P1–P7 are proven.

### What does NOT change yet

- `MicroVMIsolationProvider.execute()` still raises `NotImplementedError`.
- `arc sandbox run --provider microvm` still produces a blocked result.
- `ARC_MICROVM_EXEC_ENABLED` is not yet read by any code.
- Lima harness is still internal / not wired to public execution.
- Firecracker is still preflight/doctor only.

### What must be done before unblocking

1. Complete P1–P7 proofs on a real host with Lima installed (macOS).
2. Complete P1–P7 proofs on a real host with Firecracker + `/dev/kvm` (Linux).
3. Add mount escape tests (P3, P5) — these are the highest-risk blockers.
4. Wire `ARC_MICROVM_EXEC_ENABLED` in `MicroVMIsolationProvider.execute()`.
5. Add audit event emission in the harness.
6. Add CI opt-in smoke with host runners that have Lima/Firecracker installed.
7. Update this ADR status from "Accepted (not yet implemented)" to
   "Implemented" with evidence links.

---

## Notes

- This ADR does **not** authorize microVM execution; it only defines the
  gate so future implementation is unambiguous.
- "production-ready microVM sandbox" must not be claimed until all P1–P7
  proofs exist and this ADR is updated to "Implemented" with evidence.
- Container fallback (`ARC_ENABLE_CONTAINER_SANDBOX=1`) is a separate
  code path and is not affected by this ADR.
