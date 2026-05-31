# MicroVM P1–P7 Prerequisite Status

**ADR:** docs/adr/ADR-024-microvm-public-execution-contract.md  
**Date:** 2026-05-31
**Branch:** feat/sandbox-lima-execution-docker-hardening-fuzzing  
**Platform checked:** macOS Darwin 26.4, arm64, limactl 2.1.0; direct Apple VZ proof-only path passed once; Firecracker/KVM unavailable on this host

This document records the current status of each ADR-024 prerequisite.
`ARC_MICROVM_EXEC_ENABLED` is recognized only by the Linux/Firecracker gated scaffold and
only when all explicit Linux/KVM proof gates are present. No live Firecracker boot/run/teardown proof has run on this macOS host. macOS Lima remains blocked for strict public execution. Direct Apple VZ proof-only host proof passed once behind `ARC_VZ_PROOF=1`; it is not public microVM execution.

## P1–P7 Status Table

| P# | Description | Status | Evidence | Remaining |
|---|---|---|---|---|
| P1 | Lifecycle proof: create→start→exec→stop/delete completes | **macOS direct VZ proof-only passed once; Linux/Firecracker gated scaffold unproven on this host** | Gated VZ proof booted and stopped a no-NIC guest with teardown ok. Linux scaffold writes no-NIC config, creates a workspace snapshot, starts Firecracker only behind host/env gates, parses proof/result markers, terminates process group, and removes temp dir. Tests fake the Firecracker subprocess. | Promote VZ only after product wiring/failure-mode work. Run opt-in Firecracker test on Linux/KVM. |
| P2 | Network-off proof: guest has no default route before user argv | **macOS direct VZ proof-only passed once; BLOCKED for macOS Lima; scaffold/host-unproven for Linux Firecracker** | VZ proof emitted no guest ethernet, no default route, network tool available, and network probe failure. Lima default user-mode/slirp networking remains documented and no no-network key found. Linux scaffold omits `network-interfaces`, creates no TAP/NAT/bridge, and requires `ARC_FC_PROOF no-default-route=1`, `curl-available=1`, and `network-failure=1`. | Add VZ public provider gates/CI before enabling. Prove Linux markers on Linux/KVM with ARC exec rootfs. |
| P3 | Workspace-mount proof: only workspace accessible, not host home/root | **macOS direct VZ proof-only passed once; scaffold/host-unproven for Linux Firecracker; partial for Lima** | VZ proof emitted workspace mount and sentinel-read markers. Linux scaffold builds a per-run read-only ext4 workspace snapshot and mounts it as `/workspace`; host symlinks are skipped. | Add broader VZ mount escape/failure tests. Prove Firecracker on Linux/KVM. Lima remains low-security harness only. |
| P4 | Teardown proof: cleanup on success/failure/timeout/SIGINT | **macOS direct VZ proof-only passed once; scaffold/host-unproven for Linux Firecracker; partial for Lima** | VZ proof emitted teardown attempted/ok markers. Linux scaffold terminates the Firecracker process group on timeout/finally and uses a temporary directory for socket/config/workspace image. SIGINT/host-crash teardown not proven. | Add VZ timeout/SIGINT cleanup proof. Run real-host Firecracker teardown proof. |
| P5 | Symlink/path-traversal escape denied in guest mount | **macOS direct VZ proof-only passed once; scaffold/host-unproven for Linux Firecracker; blocked for Lima strict use** | VZ proof emitted `symlink-escape-blocked=1` for a host-only target outside workspace. Linux workspace snapshot skips host symlinks and adds `arc-host-escape-link`; guest must emit `symlink-escape-blocked=1`. | Add repeatable VZ host CI. Prove Firecracker on Linux/KVM. |
| P6 | stdout/stderr caps enforced without full buffering | **Satisfied** | `SubprocessIsolationProvider` uses bounded stream readers (replaced `communicate()`). `LimaIntegrationHarness._limactl()` uses `_run_limactl()` which calls `cap_output()` with 65_536 byte cap and returns `stdout_truncated` flag. Existing bounded-output tests pass. | None for code-level. Verify on real Lima VM that large output is truncated without pipe deadlock — can be done with `ARC_LIMA_REAL_EXEC=1`. |
| P7 | Audit event emitted for every execution | **Schema satisfied for blocked attempts, internal harnesses, and Linux/Firecracker scaffold; real host proof pending** | `build_microvm_audit_event()` records command, workspace, runtime, instance, lifecycle, network proof, teardown, timestamps, exit code, truncation flags, `audit_id`, and public execution status. MicroVM blocked-run, harness, and Linux/Firecracker scaffold audit paths include ADR-024 v1 fields: `event=sandbox.microvm.run`, `version`, `microvm_provider`, `platform`, `lifecycle_errors`, `teardown_status`, `start_ts`, `end_ts`, `duration_ms`, and `gate`. | Add/record real-host audit evidence when Linux/KVM proof runs. |

## Decision: ARC_MICROVM_EXEC_ENABLED wiring

**Status: GATED LINUX/FIRECRACKER SCAFFOLD ONLY; MACOS BLOCKED.**

The gate is honored only on Linux when all of these are present:
`ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`, `ARC_FC_REAL_EXEC=1`,
`ARC_FIRECRACKER_KERNEL`, `ARC_FIRECRACKER_ROOTFS`, `firecracker`, `/dev/kvm`
read/write, `mkfs.ext4`, and `truncate`.

On macOS, `MicroVMIsolationProvider.execute()` still raises `NotImplementedError`.
Direct Apple VZ no-NIC proof exists only as a gated proof harness; public provider
wiring remains blocked pending durable artifacts, audit/output caps, timeout/SIGINT
cleanup, host CI, and failure-mode coverage.

## What must happen before wiring

1. On Linux/KVM, build ARC exec rootfs: `cd python && ARC_FC_BUILD_EXEC_ROOTFS=1 uv run arc sandbox firecracker-artifacts --exec-rootfs --output /tmp/arc-fc --json`.
2. Run opt-in proof: `cd python && ARC_MICROVM_INTEGRATION=1 ARC_MICROVM_EXEC_ENABLED=1 ARC_FC_REAL_EXEC=1 ARC_FIRECRACKER_KERNEL=/path/to/vmlinux ARC_FIRECRACKER_ROOTFS=/tmp/arc-fc/arc-fc-exec-rootfs.ext4 uv run pytest tests/isolation/test_firecracker_smoke.py -v`.
3. Update this document and ADR-024 with real-host evidence.
4. For macOS strict execution, promote the direct Apple VZ proof-only harness only after product/provider wiring, artifact provenance, host CI, audit/output caps, timeout/SIGINT cleanup, and failure-mode coverage pass.
