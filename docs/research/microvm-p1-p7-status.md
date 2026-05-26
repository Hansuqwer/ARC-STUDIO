# MicroVM P1–P7 Prerequisite Status

**ADR:** docs/adr/ADR-024-microvm-public-execution-contract.md  
**Date:** 2026-05-26  
**Branch:** feat/sandbox-lima-execution-docker-hardening-fuzzing  
**Platform checked:** macOS Darwin 25.4.0, limactl 2.1.0  

This document records the current status of each ADR-024 prerequisite.
`ARC_MICROVM_EXEC_ENABLED` must NOT be wired in `execute()` until all
prerequisites are Satisfied (not Partial or Missing).

## P1–P7 Status Table

| P# | Description | Status | Evidence | Remaining |
|---|---|---|---|---|
| P1 | Lifecycle proof: create→start→exec→stop/delete completes | **Partial** | `test_lima_smoke.py::TestLimaSmokeRealHost` added; uses real `_run_limactl` when `ARC_LIMA_REAL_EXEC=1`; code-level lifecycle state machine verified with fake runner (105+ tests). Real VM lifecycle not yet run end-to-end on this host. | Run `ARC_MICROVM_INTEGRATION=1 ARC_LIMA_REAL_EXEC=1 pytest tests/isolation/test_lima_smoke.py::TestLimaSmokeRealHost -v` on a host with limactl + sufficient network for first-run image download. Verify all lifecycle phases complete and exit_code == 0. |
| P2 | Network-off proof: guest has no default route before user argv | **BLOCKED** | Lima 2.x always provides a default user-mode slirp network (192.168.5.0/24) to the guest. No Lima 2.x template config key to disable the default slirp interface was found in Lima docs or source. `LimaIntegrationHarness.run()` checks `ip route \| grep default` — this will ALWAYS fail on Lima 2.x (exit 1 = default route found). `network_proof_passed` will always be `False`. | Find a Lima config or CLI flag to disable the default slirp interface, OR accept Lima as a "low-security" execution context (network present) and remove P2 as a gate. OR build an in-guest iptables/nftables rule that drops all external traffic and prove it via a curl-fails test. Unresolved. |
| P3 | Workspace-mount proof: only workspace accessible, not host home/root | **Partial** | Code-level: `is_path_within_root()` and `check_workspace_escape()` added to `sandbox.py`. `LimaIntegrationHarness.__init__` rejects workspace_root symlinks pointing outside parent. 19 code-level tests pass. Real-host mount proof: `test_real_lima_workspace_sentinel` added (reads `/workspace/arc-sentinel.txt` inside Lima); skipped until `ARC_LIMA_REAL_EXEC=1`. Mount-level gap: virtiofs passes symlinks through to guest — a symlink inside workspace pointing outside will be accessible in the guest. | Run `ARC_LIMA_REAL_EXEC=1` sentinel test to prove workspace is mounted at `/workspace`. Add a guest-side test: create a symlink inside workspace pointing to `/etc/passwd` and verify it is NOT accessible at `/workspace/escape-link` in the guest. This requires a real Lima VM. |
| P4 | Teardown proof: cleanup on success/failure/timeout/SIGINT | **Partial** | `LimaIntegrationHarness.run()` calls `limactl delete -f` in `finally` block. 4+ fake-runner tests verify teardown fires on start failure, network proof failure, and success. `test_real_lima_teardown_on_start_failure` added (real limactl, short timeout). Real teardown skipped until `ARC_LIMA_REAL_EXEC=1`. SIGINT/host-crash teardown not proven. | Run real-host teardown tests. Add SIGINT simulation test: send SIGINT to harness parent process and verify Lima VM is subsequently listed as deleted by `limactl list`. |
| P5 | Symlink/path-traversal escape denied in guest mount | **Partial** | Code-level: `is_path_within_root()` correctly denies dangling, chained, and cross-parent symlinks (19 tests). Lima virtiofs passes symlinks through: a symlink inside workspace pointing to `/etc/passwd` WILL be readable in the guest at `/workspace/link`. Code-level guard in `__init__` only prevents the workspace_root itself from being misdirected. | Add a real-host test: (1) create a symlink inside tmp_path pointing to `/etc/passwd`, (2) start Lima VM, (3) run `cat /workspace/symlink-to-etc-passwd`, (4) assert it fails with permission denied or is not accessible. This requires real Lima VM and is the highest-risk remaining blocker. |
| P6 | stdout/stderr caps enforced without full buffering | **Satisfied** | `SubprocessIsolationProvider` uses bounded stream readers (replaced `communicate()`). `LimaIntegrationHarness._limactl()` uses `_run_limactl()` which calls `cap_output()` with 65_536 byte cap and returns `stdout_truncated` flag. Existing bounded-output tests pass. | None for code-level. Verify on real Lima VM that large output is truncated without pipe deadlock — can be done with `ARC_LIMA_REAL_EXEC=1`. |
| P7 | Audit event emitted for every execution | **Satisfied for internal harnesses; public execution still blocked** | `build_microvm_audit_event()` records Lima/Firecracker harness command, workspace, runtime, instance, lifecycle, network proof, teardown, timestamps, exit code, truncation flags, and `public_execution_enabled=false`. Harness runs persist through `persist_sandbox_audit_event()`. Tests cover Lima allowed/denied and Firecracker allowed audit events. `MicroVMIsolationProvider.execute()` still always raises and therefore has no public execution event path. | Keep P7 as satisfied only for opt-in harnesses. If public execution is ever wired, add end-to-end CLI/provider audit tests before enabling `ARC_MICROVM_EXEC_ENABLED`. |

## Decision: ARC_MICROVM_EXEC_ENABLED wiring

**Status: BLOCKED — do NOT wire.**

Prerequisite P2 (network-off) is not satisfied.
P1, P3, P4, P5 are partially satisfied (code-level proofs exist; real-host
proofs are pending `ARC_LIMA_REAL_EXEC=1`). P7 is satisfied for internal
Lima/Firecracker harness attempts only; public execution remains blocked.

`ARC_MICROVM_EXEC_ENABLED` remains defined in ADR-024 only. It is NOT
read by any code. `MicroVMIsolationProvider.execute()` still always raises
`NotImplementedError`.

## What must happen before wiring

1. **P2**: Resolve Lima network isolation. Options:
   - Find a Lima config to disable slirp (preferred).
   - Accept network-present context and remove P2 requirement (requires explicit decision in ADR-024 revision).
   - Implement in-guest firewall rule and prove it with curl-fails test.
2. **P7**: If public microVM execution is wired, add provider/CLI audit tests for that path.
3. **P1, P3, P4, P5**: Run with `ARC_LIMA_REAL_EXEC=1` on a host with Lima + network access for image download.
4. **P5 mount-level**: Add real-host symlink escape test inside Lima guest.
5. Update this document and ADR-024 with real-host evidence.
6. Only then: wire `ARC_MICROVM_EXEC_ENABLED` in `execute()`.
