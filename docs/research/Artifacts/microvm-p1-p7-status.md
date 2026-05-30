# MicroVM P1–P7 Prerequisite Status

**ADR:** docs/adr/ADR-024-microvm-public-execution-contract.md  
**Date:** 2026-05-26  
**Branch:** feat/sandbox-lima-execution-docker-hardening-fuzzing  
**Platform checked:** macOS Darwin 25.4.0, limactl 2.1.0; Firecracker/KVM unavailable on this host  

This document records the current status of each ADR-024 prerequisite.
`ARC_MICROVM_EXEC_ENABLED` must NOT be wired in `execute()` until all
prerequisites are Satisfied (not Partial or Missing).

## P1–P7 Status Table

| P# | Description | Status | Evidence | Remaining |
|---|---|---|---|---|
| P1 | Lifecycle proof: create→start→exec→stop/delete completes | **Partial** | `test_lima_smoke.py::TestLimaSmokeRealHost` added; uses real `_run_limactl` when `ARC_LIMA_REAL_EXEC=1`; code-level lifecycle state machine verified with fake runner (105+ tests). `FirecrackerProofRunner` now has a private host-gated proof harness that writes a config, starts Firecracker as a process-group subprocess, parses proof-only guest markers, tears down, and cleans temporary sentinel/symlink files. Firecracker proof rootfs/init artifact tooling now writes deterministic init + manifest with generator/marker contract metadata, host OS/arch, proof commands, no-network metadata, rootfs size, and tool paths; optional ext4 build is gated and validates `/init`, `/sbin/init`, `/dev/console`, `/dev/null`, proc/sysfs mount setup. Real VM lifecycle not yet run end-to-end on this host. | Build/run the ARC Firecracker proof rootfs/init artifact on Linux/KVM. Then record host-gated proof evidence. |
| P2 | Network-off proof: guest has no default route before user argv | **Firecracker/Cloud Hypervisor proof path added; strict public microVM still BLOCKED** | Lima remains low-security/network-present. Firecracker has a no-NIC design config model that omits `network-interfaces`; Cloud Hypervisor has a no-`--net` argv/config scaffold. `FirecrackerProofRunner` creates a no-NIC config and can parse stable `ARC_FC_PROOF no-default-route=1` plus `network-failure=1` markers. `generate_firecracker_proof_artifacts()` creates a marker init/manifest with proc/sysfs setup checks, but no real guest `ip route`/`curl` proof has run here. | Build rootfs/init marker image with `ARC_FC_BUILD_PROOF_ROOTFS=1` on a suitable Linux host, then run host-gated Firecracker proof and verify no default route + network failure. Do not wire `ARC_MICROVM_EXEC_ENABLED`. |
| P3 | Workspace-mount proof: only workspace accessible, not host home/root | **Partial** | Code-level: `is_path_within_root()` and `check_workspace_escape()` added to `sandbox.py`. `LimaIntegrationHarness.__init__` rejects workspace_root symlinks pointing outside parent. 19 code-level tests pass. Real-host mount proof: `test_real_lima_workspace_sentinel` added (reads `/workspace/arc-sentinel.txt` inside Lima); skipped until `ARC_LIMA_REAL_EXEC=1`. Mount-level gap: virtiofs passes symlinks through to guest — a symlink inside workspace pointing outside will be accessible in the guest. | Run `ARC_LIMA_REAL_EXEC=1` sentinel test to prove workspace is mounted at `/workspace`. Add a guest-side test: create a symlink inside workspace pointing to `/etc/passwd` and verify it is NOT accessible at `/workspace/escape-link` in the guest. This requires a real Lima VM. |
| P4 | Teardown proof: cleanup on success/failure/timeout/SIGINT | **Partial** | `LimaIntegrationHarness.run()` calls `limactl delete -f` in `finally` block. 4+ fake-runner tests verify teardown fires on start failure, network proof failure, and success. `test_real_lima_teardown_on_start_failure` added (real limactl, short timeout). Real teardown skipped until `ARC_LIMA_REAL_EXEC=1`. SIGINT/host-crash teardown not proven. | Run real-host teardown tests. Add SIGINT simulation test: send SIGINT to harness parent process and verify Lima VM is subsequently listed as deleted by `limactl list`. |
| P5 | Symlink/path-traversal escape denied in guest mount | **Blocked by Lima P2; real-host proof scaffold corrected** | Code-level: `is_path_within_root()` correctly denies dangling, chained, and cross-parent symlinks (19 tests). `test_real_lima_symlink_escape_blocked` creates a workspace symlink to `/etc/passwd`, runs `cat /workspace/arc-host-passwd-link` inside Lima, and fails if `root:` is readable. On this macOS host, `ARC_MICROVM_INTEGRATION=1 ARC_LIMA_REAL_EXEC=1 uv run pytest tests/isolation/test_lima_smoke.py::TestLimaSmokeRealHost::test_real_lima_symlink_escape_blocked -q` xfailed because Lima P2 network proof blocked user argv before the symlink command could run. | P5 remains unproven for Lima. Either add a dedicated mount-proof harness mode that can safely bypass only P2 for proof collection, or prioritize Linux Firecracker/Cloud Hypervisor where strict no-network can be proven first. |
| P6 | stdout/stderr caps enforced without full buffering | **Satisfied** | `SubprocessIsolationProvider` uses bounded stream readers (replaced `communicate()`). `LimaIntegrationHarness._limactl()` uses `_run_limactl()` which calls `cap_output()` with 65_536 byte cap and returns `stdout_truncated` flag. Existing bounded-output tests pass. | None for code-level. Verify on real Lima VM that large output is truncated without pipe deadlock — can be done with `ARC_LIMA_REAL_EXEC=1`. |
| P7 | Audit event emitted for every execution | **Satisfied for internal harnesses; public execution still blocked** | `build_microvm_audit_event()` records Lima/Firecracker harness command, workspace, runtime, instance, lifecycle, network proof, teardown, timestamps, exit code, truncation flags, `audit_id`, and `public_execution_enabled=false`. Harness runs persist through `persist_sandbox_audit_event()` and best-effort mirror a local/recent `sandbox_command` event. Tests cover Lima allowed/denied, Firecracker allowed audit events, Firecracker proof-runner blocked attempts, and sandbox audit list/show. `MicroVMIsolationProvider.execute()` still always raises and therefore has no public execution event path. | Keep P7 as satisfied only for opt-in/private harnesses. If public execution is ever wired, add end-to-end CLI/provider audit tests before enabling `ARC_MICROVM_EXEC_ENABLED`. |

## Decision: ARC_MICROVM_EXEC_ENABLED wiring

**Status: BLOCKED — do NOT wire.**

Strict prerequisite P2 (network-off) is not satisfied for any public provider.
Firecracker/Cloud Hypervisor are proof-path candidates only; a private Firecracker host-gated proof harness and proof-marker parser exist, but no real guest no-route/network-failure proof has run.
Firecracker proof rootfs/init artifact tooling exists and now validates boot entrypoints/device placeholders/proc/sysfs setup, but ext4 build and real boot are not proven on this macOS host.
P1, P3, P4, P5 are partially satisfied (code-level proofs exist; real-host
proofs are pending `ARC_LIMA_REAL_EXEC=1`). P7 is satisfied for internal
Lima/Firecracker harness attempts only; public execution remains blocked.

`ARC_MICROVM_EXEC_ENABLED` remains defined in ADR-024 only. It is NOT
read by any code. `MicroVMIsolationProvider.execute()` still always raises
`NotImplementedError`.

## What must happen before wiring

1. **P2**: Prove strict network-off with the Firecracker/Cloud Hypervisor proof path or another provider. Lima is now explicitly low-security/network-present only.
2. **P7**: If public microVM execution is wired, add provider/CLI audit tests for that path.
3. **P1, P3, P4, P5**: Run with `ARC_LIMA_REAL_EXEC=1` on a host with Lima + network access for image download.
4. **P5 mount-level**: Decide whether to add a proof-only Lima mount test mode that bypasses P2, or leave Lima P5 unproven and pivot strict execution work to Firecracker/Cloud Hypervisor.
5. Update this document and ADR-024 with real-host evidence.
6. Only then: wire `ARC_MICROVM_EXEC_ENABLED` in `execute()`.
