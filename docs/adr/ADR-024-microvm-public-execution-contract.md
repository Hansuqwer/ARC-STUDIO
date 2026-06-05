# ADR-024 — MicroVM Public Execution Contract

**Status:** Accepted — macOS direct VZ gated public path proven once for guest-available `pwd`; default-off and not production-grade; Linux/Firecracker gated scaffold is host-unproven
**Date:** 2026-05-26  
**Last updated:** 2026-05-31 — direct macOS VZ `arc sandbox run --provider microvm -- pwd` passed once behind `ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`, `ARC_VZ_REAL_EXEC=1`, and a valid local artifact manifest; `arc sandbox vz-artifacts` adds local SHA256 provenance for proof inputs, and `--exec-init --pack-initrd --busybox <path>` can package the reviewable guest init contract with static local BusyBox/`cpio` only. The packed-initrd path is now reproducible end to end via `tools/build-arc-vz-busybox.sh` + `tools/arc-vz-bringup.sh` (static aarch64 BusyBox + open-source Kata `vmlinux.container` 6.18.28 kernel + the `/proc` mount-point init fix); the gated `pwd` proof passes on macOS 26.4 arm64 under ad-hoc signing (default-off; not production-grade). Linux/Firecracker remains a gated scaffold with no live Linux/KVM boot proof from this host.
**Authors:** ARC Studio sandbox team  
**Related:** Phase 37 (R38), `docs/research/sandbox-and-microvm.md`, `docs/research/microvm-p1-p7-status.md`, ADR-014 (security architecture)

---

## Context

ARC Studio has a `MicroVMIsolationProvider` and internal harness
(`LimaIntegrationHarness`, planned `FirecrackerIntegrationHarness`) that
support preflight/doctor and design-proof surfaces for macOS (Lima) and
Linux (Firecracker). As of Phase 37.14 the following is true:

- `MicroVMIsolationProvider.execute()` still raises on Windows, unsupported platforms, Linux when any explicit Firecracker gate is missing, and macOS when any explicit VZ gate/proof requirement is missing.
- `arc sandbox run --provider microvm` has a Linux/Firecracker gated scaffold only; no eligible-host boot/run/teardown proof is recorded yet.
- Lima harness exists as an internal opt-in helper only.
- Direct Apple VZ public path exists behind `ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`, `ARC_VZ_REAL_EXEC=1`, and `ARC_VZ_ARTIFACT_MANIFEST`; one macOS 26.4 arm64 host run booted a no-NIC guest, proved no ethernet/default route/network probe failure, workspace sentinel/symlink markers, exact requested argv hash, teardown ok, and returned `pwd` stdout `/workspace` through `arc sandbox run --provider microvm`.
- Firecracker has a private Linux/KVM host-gated proof harness, proof-only `ARC_FC_PROOF` marker parser, and deterministic proof init/manifest artifact scaffold; Cloud Hypervisor remains scaffold/preflight only.
- No real Firecracker boot was proven on the current macOS host.

This ADR defines the precise prerequisites, gate mechanism, platform
scoping, and audit event schema that must be satisfied before
`arc sandbox run --provider microvm` can be described as production-grade or
broad arbitrary-command microVM execution.

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

This variable is honored by the Linux/Firecracker provider path and by the
macOS direct Apple VZ path only when the additional VZ gates below are also
present. It remains default-off and never enables Lima, Docker Desktop, or
Windows microVM execution.

Implementation when honored:

- `MicroVMIsolationProvider.execute()` reads this env var on Linux and macOS direct VZ only.
- If unset → raise `NotImplementedError` (current behavior, permanent default).
- If set AND all Linux/Firecracker gates are present → delegate to
  `FirecrackerExecutionRunner` on Linux.
- If set AND `ARC_MICROVM_INTEGRATION=1`, `ARC_VZ_REAL_EXEC=1`, valid
  `ARC_VZ_ARTIFACT_MANIFEST`, signed runner, readable kernel/initrd, guest
  proof markers, exact argv hash, teardown, and audit pass → delegate to direct
  Apple VZ on macOS.
- The variable must never silently enable execution without all P1–P7 proofs.

### 3. Execution denied by default

`arc sandbox run --provider microvm` must deny execution unless:

1. `ARC_MICROVM_EXEC_ENABLED=1` is explicitly set.
2. The platform-appropriate binary is present (`firecracker` on Linux, signed ARC VZ runner on macOS).
3. `ARC_MICROVM_INTEGRATION=1` is also set (keeps the opt-in dual-gate pattern).
4. On macOS direct VZ, `ARC_VZ_REAL_EXEC=1` and a valid `ARC_VZ_ARTIFACT_MANIFEST` are present.

Absence of any of the three → `NotImplementedError` with a clear message
referencing this ADR.

### 4. Platform support

| Platform | Provider | Status |
|---|---|---|
| macOS (≥ 13, Apple Silicon or Intel) | Direct Apple Virtualization.framework VZ runner | **Gated direct VZ public CLI proof passed once for guest-available `pwd`**; default-off; exact argv hash required; Lima default/user-v2 networking is network-present and remains low-security |
| Linux (x86_64, aarch64 with KVM) | Firecracker (primary), Cloud Hypervisor (secondary) | Firecracker gated scaffold behind `/dev/kvm` + binary + kernel/rootfs + dual env gates + proof markers; real boot proof pending |
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
  "microvm_provider": "vz|firecracker",
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
- Docs must not claim production-grade or broad arbitrary-command microVM execution until P1–P7 are repeated and proven for the target provider/host class.

### What does NOT change yet

- `MicroVMIsolationProvider.execute()` still raises on macOS unless all VZ gates/proofs are present, and on Linux unless all Firecracker gates are present.
- `arc sandbox run --provider microvm` remains blocked by default.
- `ARC_MICROVM_EXEC_ENABLED` is read by Linux/Firecracker and macOS/direct-VZ paths only.
- Lima harness is still internal / not wired to public execution.
- Direct Apple VZ public execution is opt-in only via `ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`, `ARC_VZ_REAL_EXEC=1`, and a valid local manifest. Current real CLI evidence is `pwd` only; guest artifacts must contain the requested command/runtime.
- `arc sandbox vz-artifacts` can compile/sign the local VZ runner and hash-pin source, entitlements, runner, kernel, and initrd into `vz-artifacts-manifest.json` without downloading assets or booting a VM.
- `arc sandbox vz-artifacts --exec-init` can write the reviewable guest init contract and manifest. `--pack-initrd --busybox <path>` can package a gzip `newc` initramfs with static local BusyBox/`cpio`. It does not download assets or include Python. Dynamically linked BusyBox is rejected unless a future policy also packages the loader/libs. The packed initrd is not execution evidence until a gated VZ host run uses it.
- Firecracker gated scaffold exists and requires stable proof markers (`no-default-route`, `network-failure`, `sentinel-read`, `workspace-mount-proven`, `symlink-escape-blocked`) plus command result markers before any future command output can be trusted. No real Linux/KVM boot proof has run on the current host.

### What must be done before unblocking

1. Complete P1–P7 Linux proof on a real host with Firecracker + `/dev/kvm`.
2. Add CI opt-in smoke with host runners that have Firecracker installed.
3. For macOS, repeat the direct Apple VZ gated path in host CI and add real timeout/SIGINT/failure proofs plus upstream kernel/initrd/static-BusyBox provenance/distribution policy before any production-grade or broad arbitrary-command claim.
4. Update this ADR status from "Accepted" to "Implemented" only after real host evidence links exist.

---

## Current P1–P7 Status (2026-05-26 evaluation)

Full detail: `docs/research/microvm-p1-p7-status.md`

| P# | Description | Status |
|---|---|---|
| P1 | Lifecycle proof | macOS direct VZ gated public CLI path passed once for `pwd`; Linux/Firecracker gated scaffold exists, real Linux host proof pending |
| P2 | Network-off proof | macOS direct VZ gated public CLI path passed once; macOS Lima blocked; Linux/Firecracker scaffold requires no-NIC config plus guest no-default-route/network-failure markers, real Linux host proof pending |
| P3 | Workspace-mount proof | macOS direct VZ gated public CLI path passed once with sentinel marker and guest cwd `/workspace`; Linux scaffold uses read-only ext4 workspace snapshot and sentinel marker, real Linux host proof pending |
| P4 | Teardown proof | macOS direct VZ gated public CLI path passed once with teardown ok; Linux scaffold terminates Firecracker process group and temp dir, real Linux host proof pending |
| P5 | Symlink-escape proof | macOS direct VZ gated public CLI path passed once with symlink escape blocked; Linux scaffold skips host symlinks in snapshot and requires symlink-escape marker, real Linux host proof pending |
| P6 | stdout/stderr caps | **Satisfied** — bounded stream readers + cap tests pass |
| P7 | Audit event emitted | **macOS direct VZ gated public CLI audit proven once; schema satisfied for blocked attempts/internal harnesses/gated scaffold** — Linux real host proof pending |

**ARC_MICROVM_EXEC_ENABLED wiring: Linux/Firecracker gated scaffold; macOS direct VZ gated path default-off and proven once for `pwd`.**

### P2 Lima posture decision

Context7 and Lima docs confirm default Lima networking is user-mode/slirp with
hard-coded `192.168.5.0/24`. Lima `user-v2` disables the default user-mode
network but replaces it with another user-mode network; it is not a no-network
configuration. Therefore ARC treats Lima as a low-security developer harness,
not the strict public `microvm` sandbox provider.

Firecracker remains the preferred strict Linux path because its documented
network setup requires explicit TAP/NAT/bridge configuration. A Firecracker VM
with no network interface configured is the next candidate for P2 proof. ARC now
has a no-NIC design/preflight config model, but has not run a real
boot/no-default-route/curl-fails proof yet.

### Lima mount-proof mode decision

ARC now treats Lima as a **low-security developer harness**, not a strict
microVM sandbox candidate. `LimaIntegrationHarness.run(..., proof_mode="mount")`
exists only to collect guest-side mount evidence when Lima's known slirp default
route would otherwise block user argv. This mode bypasses only the network proof;
it does not wire `ARC_MICROVM_EXEC_ENABLED`, does not claim strict network
isolation, and does not enable `arc sandbox run --provider microvm`.

If the host-gated Lima symlink proof can read host `/etc/passwd` through a
symlink inside `/workspace`, ADR-024 P5 is permanently blocked for Lima strict
sandbox use. Lima may remain useful as a low-security developer harness, but not
as the strict public `microvm` provider.

### Firecracker/Cloud Hypervisor no-network design/preflight status

Current Linux/Firecracker gated scaffold emits `strict_network_candidate=true`,
requires guest proof markers, and intentionally omits `network-interfaces`.
The generated Cloud Hypervisor argv intentionally omits `--net` options.
Host-gated Firecracker execution remains blocked unless all are present:
`ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`,
`ARC_FC_REAL_EXEC=1`, Linux, `/dev/kvm` read/write, `firecracker`,
`ARC_FIRECRACKER_KERNEL`, `ARC_FIRECRACKER_ROOTFS`, `mkfs.ext4`, and `truncate`.
Host-gated Cloud Hypervisor real proof remains blocked unless all are present:
`ARC_MICROVM_INTEGRATION=1`, `ARC_CH_REAL_EXEC=1`, Linux, `/dev/kvm` read/write,
`cloud-hypervisor`, `ARC_CLOUDHYPERVISOR_KERNEL`, and `ARC_CLOUDHYPERVISOR_DISK`.

---

## Notes

- This ADR authorizes only the gated Linux/Firecracker and macOS direct-VZ paths
  described above. Lima, Docker Desktop-as-microVM, Windows, and Cloud Hypervisor
  public execution remain blocked/design-only.
- "production-ready microVM sandbox" must not be claimed until all P1–P7
  proofs exist and this ADR is updated to "Implemented" with evidence.
- Container fallback (`ARC_ENABLE_CONTAINER_SANDBOX=1`) is a separate
  code path and is not affected by this ADR.
