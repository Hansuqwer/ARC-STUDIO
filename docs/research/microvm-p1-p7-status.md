# MicroVM P1–P7 Prerequisite Status

**ADR:** docs/adr/ADR-024-microvm-public-execution-contract.md  
**Date:** 2026-05-31
**Branch:** feat/sandbox-lima-execution-docker-hardening-fuzzing  
**Platform checked:** macOS Darwin 26.4, arm64, limactl 2.1.0; direct Apple VZ gated `arc sandbox run --provider microvm -- pwd` passed once with local hash-pinned artifacts; VZ exec-init contract generator exists; Firecracker/KVM unavailable on this host

This document records the current status of each ADR-024 prerequisite.
`ARC_MICROVM_EXEC_ENABLED` is recognized by Linux/Firecracker only when all explicit Linux/KVM proof gates are present, and by macOS direct Apple VZ only when `ARC_MICROVM_INTEGRATION=1`, `ARC_VZ_REAL_EXEC=1`, a valid `ARC_VZ_ARTIFACT_MANIFEST`, a signed runner, readable kernel/initrd, guest proof markers, exact argv hash, teardown, and audit all pass. No live Firecracker boot/run/teardown proof has run on this macOS host. macOS Lima remains blocked for strict public execution. Direct Apple VZ has one gated public CLI proof for guest-available `pwd`; this is not production-grade or arbitrary host-command microVM execution.

## P1–P7 Status Table

| P# | Description | Status | Evidence | Remaining |
|---|---|---|---|---|
| P1 | Lifecycle proof: create→start→exec→stop/delete completes | **macOS direct VZ gated public CLI proof passed once for guest-available `pwd`; Linux/Firecracker gated scaffold unproven on this host** | `arc sandbox run --provider microvm -- pwd` booted VZ, ran guest argv, returned `/workspace`, and stopped with teardown ok. `arc sandbox vz-artifacts` can compile/sign/hash-pin the runner and inputs. `arc sandbox vz-artifacts --exec-init` writes the reviewable guest init contract/manifest. Linux scaffold writes no-NIC config, creates a workspace snapshot, starts Firecracker only behind host/env gates, parses proof/result markers, terminates process group, and removes temp dir. Tests fake the Firecracker subprocess. | Add repeatable host CI, real SIGINT/failure proofs, and packaged initrd/artifact provenance. Run opt-in Firecracker test on Linux/KVM. |
| P2 | Network-off proof: guest has no default route before user argv | **macOS direct VZ gated public CLI proof passed once; BLOCKED for macOS Lima; scaffold/host-unproven for Linux Firecracker** | VZ public CLI proof emitted no guest ethernet, no default route, network tool available, and network probe failure before accepting result markers. Lima default user-mode/slirp networking remains documented and no no-network key found. Linux scaffold omits `network-interfaces`, creates no TAP/NAT/bridge, and requires `ARC_FC_PROOF no-default-route=1`, `curl-available=1`, and `network-failure=1`. | Repeat VZ proof in host CI. Prove Linux markers on Linux/KVM with ARC exec rootfs. |
| P3 | Workspace-mount proof: only workspace accessible, not host home/root | **macOS direct VZ gated public CLI proof passed once; scaffold/host-unproven for Linux Firecracker; partial for Lima** | VZ public CLI proof emitted workspace mount and sentinel-read markers and returned guest cwd `/workspace`. Linux scaffold builds a per-run read-only ext4 workspace snapshot and mounts it as `/workspace`; host symlinks are skipped. | Add broader VZ mount escape/failure tests. Prove Firecracker on Linux/KVM. Lima remains low-security harness only. |
| P4 | Teardown proof: cleanup on success/failure/timeout/SIGINT | **macOS direct VZ gated public CLI proof passed once for success; scaffold/host-unproven for Linux Firecracker; partial for Lima** | VZ public CLI proof emitted teardown attempted/ok markers; fake-runner tests cover timeout, interrupt, missing argv hash, proof failure, and teardown failure paths with process-group kill and failed results. Linux scaffold terminates the Firecracker process group on timeout/finally and uses a temporary directory for socket/config/workspace image. Real SIGINT/host-crash teardown not proven. | Add real VZ timeout/SIGINT cleanup proof. Run real-host Firecracker teardown proof. |
| P5 | Symlink/path-traversal escape denied in guest mount | **macOS direct VZ gated public CLI proof passed once; scaffold/host-unproven for Linux Firecracker; blocked for Lima strict use** | VZ public CLI proof emitted `symlink-escape-blocked=1` for a host-only target outside workspace. Linux workspace snapshot skips host symlinks and adds `arc-host-escape-link`; guest must emit `symlink-escape-blocked=1`. | Add repeatable VZ host CI. Prove Firecracker on Linux/KVM. |
| P6 | stdout/stderr caps enforced without full buffering | **Satisfied** | `SubprocessIsolationProvider` uses bounded stream readers (replaced `communicate()`). `LimaIntegrationHarness._limactl()` uses `_run_limactl()` which calls `cap_output()` with 65_536 byte cap and returns `stdout_truncated` flag. Existing bounded-output tests pass. | None for code-level. Verify on real Lima VM that large output is truncated without pipe deadlock — can be done with `ARC_LIMA_REAL_EXEC=1`. |
| P7 | Audit event emitted for every execution | **macOS direct VZ gated public CLI audit proven once; schema satisfied for blocked attempts, internal harnesses, and Linux/Firecracker scaffold** | VZ public CLI proof emitted `sandbox.microvm.run` audit with command/cwd/classification/decision/provider, proof markers, gates, manifest path, artifact hashes, lifecycle, teardown, timestamps, exit code, truncation/redaction flags, and `public_execution_enabled=true` for the gated run. Blocked-run, harness, and Linux/Firecracker scaffold audit paths include ADR-024 v1 fields. | Add/record real-host audit evidence when Linux/KVM proof runs; repeat macOS VZ audit in host CI. |

## Decision: ARC_MICROVM_EXEC_ENABLED wiring

**Status: GATED LINUX/FIRECRACKER SCAFFOLD; GATED MACOS DIRECT VZ PUBLIC PATH PROVEN ONCE FOR `pwd`; DEFAULT OFF.**

The gate is honored on Linux when all of these are present:
`ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`, `ARC_FC_REAL_EXEC=1`,
`ARC_FIRECRACKER_KERNEL`, `ARC_FIRECRACKER_ROOTFS`, `firecracker`, `/dev/kvm`
read/write, `mkfs.ext4`, and `truncate`.

On macOS, `MicroVMIsolationProvider.execute()` delegates only to direct Apple VZ
and only when `ARC_MICROVM_EXEC_ENABLED=1`,
`ARC_MICROVM_INTEGRATION=1`, `ARC_VZ_REAL_EXEC=1`, and a valid
`ARC_VZ_ARTIFACT_MANIFEST` point at local signed/readable artifacts. Success still
requires guest proof markers, exact requested argv hash, teardown ok, and audit.
The only real public CLI evidence is guest-available `pwd`; `python -c` remains
unproven unless the guest artifact bundles Python.
`arc sandbox vz-artifacts --exec-init` writes the reviewable VZ guest init
contract and manifest only; it does not package an initrd or download/bundle
guest runtimes.

## What must happen before wiring

1. On Linux/KVM, build ARC exec rootfs: `cd python && ARC_FC_BUILD_EXEC_ROOTFS=1 uv run arc sandbox firecracker-artifacts --exec-rootfs --output /tmp/arc-fc --json`.
2. Run opt-in proof: `cd python && ARC_MICROVM_INTEGRATION=1 ARC_MICROVM_EXEC_ENABLED=1 ARC_FC_REAL_EXEC=1 ARC_FIRECRACKER_KERNEL=/path/to/vmlinux ARC_FIRECRACKER_ROOTFS=/tmp/arc-fc/arc-fc-exec-rootfs.ext4 uv run pytest tests/isolation/test_firecracker_smoke.py -v`.
3. Update this document and ADR-024 with real-host evidence.
4. For macOS strict execution, repeat the direct VZ public path in host CI, add real timeout/SIGINT/failure proofs, and define kernel/initrd distribution/provenance policy before any production-grade or broad arbitrary-command claim.
