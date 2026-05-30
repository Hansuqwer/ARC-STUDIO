# MicroVM P1–P7 Prerequisite Status

**ADR:** docs/adr/ADR-024-microvm-public-execution-contract.md  
**Date:** 2026-05-29
**Branch:** feat/sandbox-lima-execution-docker-hardening-fuzzing  
**Platform checked:** macOS Darwin 26.4, arm64, limactl 2.1.0; Firecracker/KVM unavailable on this host

This document records the current status of each ADR-024 prerequisite.
`ARC_MICROVM_EXEC_ENABLED` is now wired only for the Linux/Firecracker path and
only when all explicit Linux/KVM proof gates are present. macOS Lima remains
blocked for strict public execution.

## P1–P7 Status Table

| P# | Description | Status | Evidence | Remaining |
|---|---|---|---|---|
| P1 | Lifecycle proof: create→start→exec→stop/delete completes | **Implemented for Linux/Firecracker; unproven on this host** | `MicroVMIsolationProvider.execute()` delegates to `FirecrackerExecutionRunner` only on Linux. It writes no-NIC config, creates a workspace snapshot, starts Firecracker as a process-group subprocess, parses proof/result markers, terminates process group, and removes temp dir. Tests fake the Firecracker subprocess; real VM lifecycle not run on macOS. | Run opt-in test on Linux/KVM. |
| P2 | Network-off proof: guest has no default route before user argv | **BLOCKED for macOS Lima; implemented/host-unproven for Linux Firecracker** | Lima default user-mode/slirp networking remains documented and no no-network key found. Linux path omits `network-interfaces`, creates no TAP/NAT/bridge, and requires `ARC_FC_PROOF no-default-route=1`, `curl-available=1`, and `network-failure=1` before returning command output. | Prove markers on Linux/KVM with ARC exec rootfs. |
| P3 | Workspace-mount proof: only workspace accessible, not host home/root | **Implemented/host-unproven for Linux Firecracker; partial for Lima** | Linux path builds a per-run read-only ext4 workspace snapshot and mounts it as `/workspace`; host symlinks are skipped. Guest must emit `sentinel-read=1` and `workspace-mount-proven=1`. | Prove on Linux/KVM. Lima remains low-security harness only. |
| P4 | Teardown proof: cleanup on success/failure/timeout/SIGINT | **Implemented/host-unproven for Linux Firecracker; partial for Lima** | Linux runner terminates the Firecracker process group on timeout/finally and uses a temporary directory for socket/config/workspace image. SIGINT/host-crash teardown not proven. | Run real-host teardown proof and add SIGINT proof if required. |
| P5 | Symlink/path-traversal escape denied in guest mount | **Implemented/host-unproven for Linux Firecracker; blocked for Lima strict use** | Linux workspace snapshot skips host symlinks and adds `arc-host-escape-link`; guest must emit `symlink-escape-blocked=1`. | Prove on Linux/KVM. |
| P6 | stdout/stderr caps enforced without full buffering | **Satisfied** | `SubprocessIsolationProvider` uses bounded stream readers (replaced `communicate()`). `LimaIntegrationHarness._limactl()` uses `_run_limactl()` which calls `cap_output()` with 65_536 byte cap and returns `stdout_truncated` flag. Existing bounded-output tests pass. | None for code-level. Verify on real Lima VM that large output is truncated without pipe deadlock — can be done with `ARC_LIMA_REAL_EXEC=1`. |
| P7 | Audit event emitted for every execution | **Satisfied for blocked attempts, internal harnesses, and Linux/Firecracker path; real host proof pending** | `build_microvm_audit_event()` records command, workspace, runtime, instance, lifecycle, network proof, teardown, timestamps, exit code, truncation flags, `audit_id`, and public execution status. MicroVM blocked-run, harness, and Linux/Firecracker result audit paths also include ADR-024 v1 fields: `event=sandbox.microvm.run`, `version`, `microvm_provider`, `platform`, `lifecycle_errors`, `teardown_status`, `start_ts`, `end_ts`, `duration_ms`, and `gate`. Linux/Firecracker runner persists audit events after proof/run completion; CLI also audits blocked attempts. | Add/record real-host audit evidence when Linux/KVM proof runs. |

## Decision: ARC_MICROVM_EXEC_ENABLED wiring

**Status: WIRED FOR LINUX/FIRECRACKER ONLY; MACOS BLOCKED.**

The gate is honored only on Linux when all of these are present:
`ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`, `ARC_FC_REAL_EXEC=1`,
`ARC_FIRECRACKER_KERNEL`, `ARC_FIRECRACKER_ROOTFS`, `firecracker`, `/dev/kvm`
read/write, `mkfs.ext4`, and `truncate`.

On macOS, `MicroVMIsolationProvider.execute()` still raises `NotImplementedError`
because Lima/VZ cannot satisfy strict P2, and no direct Apple Virtualization.framework
no-NIC helper is implemented.

## What must happen before wiring

1. On Linux/KVM, build ARC exec rootfs: `cd python && ARC_FC_BUILD_EXEC_ROOTFS=1 uv run arc sandbox firecracker-artifacts --exec-rootfs --output /tmp/arc-fc --json`.
2. Run opt-in proof: `cd python && ARC_MICROVM_INTEGRATION=1 ARC_MICROVM_EXEC_ENABLED=1 ARC_FC_REAL_EXEC=1 ARC_FIRECRACKER_KERNEL=/path/to/vmlinux ARC_FIRECRACKER_ROOTFS=/tmp/arc-fc/arc-fc-exec-rootfs.ext4 uv run pytest tests/isolation/test_firecracker_smoke.py -v`.
3. Update this document and ADR-024 with real-host evidence.
4. For macOS strict execution, implement/test direct Apple VZ no-NIC helper or wait for a Lima no-network feature.
