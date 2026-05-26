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
| P1 | Lifecycle proof: create→start→exec→stop/delete completes | **Partial** | `test_lima_smoke.py::TestLimaSmokeRealHost` added; uses real `_run_limactl` when `ARC_LIMA_REAL_EXEC=1`; code-level lifecycle state machine verified with fake runner (105+ tests). `FirecrackerProofRunner` now has a private host-gated proof harness that writes a config, starts Firecracker as a process-group subprocess, and tears down, but guest exec remains blocked by missing command channel. Real VM lifecycle not yet run end-to-end on this host. | Run `ARC_MICROVM_INTEGRATION=1 ARC_FC_REAL_EXEC=1 ARC_FIRECRACKER_KERNEL=<path> ARC_FIRECRACKER_ROOTFS=<path> uv run pytest tests/isolation/test_firecracker_smoke.py -q -v` on Linux/KVM. Add/validate guest command channel before claiming exec. |
| P2 | Network-off proof: guest has no default route before user argv | **Firecracker/Cloud Hypervisor proof path added; strict public microVM still BLOCKED** | Lima remains low-security/network-present. Firecracker has a no-NIC design config model that omits `network-interfaces`; Cloud Hypervisor has a no-`--net` argv/config scaffold. `FirecrackerProofRunner` creates a no-NIC config and starts only behind all host gates. Real guest `ip route` and failed `curl` are not proven because the command channel/rootfs agent is not implemented. | Implement rootfs/init/vsock/serial command channel, then run host-gated Firecracker proof on Linux/KVM and verify no default route + curl failure. Do not wire `ARC_MICROVM_EXEC_ENABLED`. |
| P3 | Workspace-mount proof: only workspace accessible, not host home/root | **Partial** | Code-level: `is_path_within_root()` and `check_workspace_escape()` added to `sandbox.py`. `LimaIntegrationHarness.__init__` rejects workspace_root symlinks pointing outside parent. 19 code-level tests pass. Real-host mount proof: `test_real_lima_workspace_sentinel` added (reads `/workspace/arc-sentinel.txt` inside Lima); skipped until `ARC_LIMA_REAL_EXEC=1`. Mount-level gap: virtiofs passes symlinks through to guest — a symlink inside workspace pointing outside will be accessible in the guest. | Run `ARC_LIMA_REAL_EXEC=1` sentinel test to prove workspace is mounted at `/workspace`. Add a guest-side test: create a symlink inside workspace pointing to `/etc/passwd` and verify it is NOT accessible at `/workspace/escape-link` in the guest. This requires a real Lima VM. |
| P4 | Teardown proof: cleanup on success/failure/timeout/SIGINT | **Partial** | `LimaIntegrationHarness.run()` calls `limactl delete -f` in `finally` block. 4+ fake-runner tests verify teardown fires on start failure, network proof failure, and success. `test_real_lima_teardown_on_start_failure` added (real limactl, short timeout). Real teardown skipped until `ARC_LIMA_REAL_EXEC=1`. SIGINT/host-crash teardown not proven. | Run real-host teardown tests. Add SIGINT simulation test: send SIGINT to harness parent process and verify Lima VM is subsequently listed as deleted by `limactl list`. |
| P5 | Symlink/path-traversal escape denied in guest mount | **Blocked by Lima P2; real-host proof scaffold corrected** | Code-level: `is_path_within_root()` correctly denies dangling, chained, and cross-parent symlinks (19 tests). `test_real_lima_symlink_escape_blocked` creates a workspace symlink to `/etc/passwd`, runs `cat /workspace/arc-host-passwd-link` inside Lima, and fails if `root:` is readable. On this macOS host, `ARC_MICROVM_INTEGRATION=1 ARC_LIMA_REAL_EXEC=1 uv run pytest tests/isolation/test_lima_smoke.py::TestLimaSmokeRealHost::test_real_lima_symlink_escape_blocked -q` xfailed because Lima P2 network proof blocked user argv before the symlink command could run. | P5 remains unproven for Lima. Either add a dedicated mount-proof harness mode that can safely bypass only P2 for proof collection, or prioritize Linux Firecracker/Cloud Hypervisor where strict no-network can be proven first. |
| P6 | stdout/stderr caps enforced without full buffering | **Satisfied** | `SubprocessIsolationProvider` uses bounded stream readers (replaced `communicate()`). `LimaIntegrationHarness._limactl()` uses `_run_limactl()` which calls `cap_output()` with 65_536 byte cap and returns `stdout_truncated` flag. Existing bounded-output tests pass. | None for code-level. Verify on real Lima VM that large output is truncated without pipe deadlock — can be done with `ARC_LIMA_REAL_EXEC=1`. |
| P7 | Audit event emitted for every execution | **Satisfied for internal harnesses; public execution still blocked** | `build_microvm_audit_event()` records Lima/Firecracker harness command, workspace, runtime, instance, lifecycle, network proof, teardown, timestamps, exit code, truncation flags, and `public_execution_enabled=false`. Harness runs persist through `persist_sandbox_audit_event()`. Tests cover Lima allowed/denied, Firecracker allowed audit events, and Firecracker proof-runner blocked attempts. `MicroVMIsolationProvider.execute()` still always raises and therefore has no public execution event path. | Keep P7 as satisfied only for opt-in/private harnesses. If public execution is ever wired, add end-to-end CLI/provider audit tests before enabling `ARC_MICROVM_EXEC_ENABLED`. |

## Decision: ARC_MICROVM_EXEC_ENABLED wiring

**Status: BLOCKED — do NOT wire.**

Strict prerequisite P2 (network-off) is not satisfied for any public provider.
Firecracker/Cloud Hypervisor are proof-path candidates only; a private Firecracker host-gated proof harness exists, but no real guest no-route/curl-fails proof has run.
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
