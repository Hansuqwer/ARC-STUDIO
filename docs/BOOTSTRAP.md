# Bootstrap Guide

This guide provides instructions for bootstrapping a fresh ARC Studio environment from a clean clone.

## Prerequisites

- **Node.js** `20.18.0`
- **pnpm** `9.15.9`
- **Python** `3.11.10`
- **uv** — Python dependency manager ([installation guide](https://github.com/astral-sh/uv))
- **Git** 

See [`.tool-versions`](../.tool-versions) for exact pinned versions.

## Environment Checks

Before installing, verify your environment:

```bash
bash scripts/check-env.sh
```

This script checks:
- OS compatibility
- Node version
- Package manager version
- Python version
- uv version
- Git version
- Lockfile existence
- Python environment usability
- Playwright browsers (if e2e required)
- SwarmGraph companion repo presence
- Current git branch

## Quick Start

Get ARC Studio running in three steps:

```bash
# 1. Checkout correct branch
git checkout build/no-mockups-handoff

# 2. Check environment
bash scripts/check-env.sh

# 3. Bootstrap development environment
bash scripts/bootstrap-dev.sh
```

## Daemon URL Configuration

The Python daemon can be reached via three fallback methods:

### 1. Explicit Environment Variable (Priority 1)

```bash
export ARC_PYTHON_DAEMON_URL="http://127.0.0.1:7777"
```

### 2. Theia Backend Auto-Probe (Priority 2)

The Theia backend automatically probes `http://127.0.0.1:7777` for the daemon.
This works if the daemon is running with default settings.

### 3. Manual Configuration (Priority 3)

In the IDE Config tab, users can manually enter the daemon URL.

### Starting the Daemon

```bash
# Default (localhost:7777)
arc serve

# Custom port
arc serve --port 8888

# Custom host
arc serve --host 0.0.0.0 --port 8888
```

### Verification

```bash
# Check daemon health
curl http://127.0.0.1:7777/health

# From Theia, check Config tab for "Daemon Connected" status
```

## Verification Commands

After bootstrapping, verify everything works:

```bash
# Python tests
cd python && uv run pytest -q

# Python linting
cd python && uv run ruff check src tests

# TypeScript build
pnpm build

# TypeScript typecheck
pnpm typecheck

# Run all tests
pnpm test

# Start browser app
pnpm start:browser
```

## Troubleshooting

### Environment Issues

- **Node version mismatch**: Use `nvm` to install correct version
- **pnpm not found**: Install via `npm install -g pnpm@9.15.9`
- **uv not found**: Install via `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Daemon Connection Issues

- Check if daemon is running: `ps aux | grep arc serve`
- Verify daemon URL: `curl http://127.0.0.1:7777/health`
- Check port availability: `lsof -i :7777`

### Test Failures

- Run Python tests with verbose output: `cd python && uv run pytest -v`
- Check TypeScript errors: `pnpm typecheck`
- Review logs: Check `.arc/traces/` for run traces

## Next Steps

After successful bootstrap:

1. Read [DEVELOPMENT.md](./DEVELOPMENT.md) for contribution guidelines
2. Review [ROADMAP.md](./roadmap.md) for project status
3. Explore the [ARCHITECTURE](./architecture/overview.md) documentation
4. Run the quickstart tutorial

---

**Last Updated:** 2026-05-31
**Status:** Alpha
# Sandbox Bootstrap

Useful local checks:

```bash
cd python
uv run arc sandbox doctor --json
uv run arc policy explain -- ls -la
uv run arc sandbox run --policy local-safe -- pwd
uv run arc sandbox run --policy local-safe --ask -- true
uv run arc policy list --json
uv run arc policy validate --json
uv run arc sandbox audit-verify --json
uv run arc sandbox audit-list --json --limit 20
uv run arc sandbox vz-artifacts --json --output /tmp/arc-vz-artifacts --kernel /path/to/arm64-linux-kernel --initrd /path/to/arc-vz-proof-initrd.gz --build-runner
```

Opt-in macOS direct VZ proof run, using local artifacts only:

```bash
cd python
ARC_MICROVM_EXEC_ENABLED=1 \
ARC_MICROVM_INTEGRATION=1 \
ARC_VZ_REAL_EXEC=1 \
ARC_VZ_ARTIFACT_MANIFEST=/path/to/vz-artifacts-manifest.json \
uv run arc sandbox run --json --provider microvm --policy local-safe -- pwd
```

Expected proven stdout for the current proof initrd is `/workspace`. Do not use this as evidence for `python -c` or arbitrary host-command execution unless the guest artifact actually contains that runtime and emits the matching `ARC_VZ_RESULT command_sha256` marker.

Expected defaults:

- `curl https://example.com` is denied as `network`.
- `rm -rf .` is denied as `destructive`.
- MicroVM doctor may report `unavailable` until Firecracker/Cloud Hypervisor plus `/dev/kvm` exist on Linux, or `limactl` exists on macOS.
- Linux/Firecracker microVM remains a gated scaffold, blocked by default, and requires `ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`, `ARC_FC_REAL_EXEC=1`, kernel/rootfs env vars, `firecracker`, `/dev/kvm` rw, and workspace snapshot tools. It is not proven on this macOS host.
- macOS Lima remains a low-security harness only; strict no-network public execution is blocked for Lima. Direct Apple VZ has a default-off gated path requiring `ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`, `ARC_VZ_REAL_EXEC=1`, valid `ARC_VZ_ARTIFACT_MANIFEST`, signed runner, readable kernel/initrd, guest no-network/workspace/symlink markers, exact argv hash, teardown, and audit. One local host proof passed for guest-available `pwd` with stdout `/workspace`. `arc sandbox vz-artifacts` creates a local hash-pinned artifact set without downloading assets or booting a VM. This is not production-grade or arbitrary host-command microVM execution.
- `arc mcp workbench inspect` and `session-start` route user-supplied server commands through sandbox policy, workspace trust, env filtering, cwd bounds, and sandbox audit.
- Direct `SubprocessIsolationProvider(workspace_root=...)` callers execute from that workspace root when `cwd` is omitted; no parent-cwd inheritance across that provider boundary.
- `arc plan apply` no longer treats generic plan/direct approval as approval for `network`, `install`, or `unknown`; use policy allowance or a matching sandbox approval token.
- Sandbox audit logs are written to `~/.arc/audit/` unless `ARC_SANDBOX_AUDIT_DIR` is set.
- `--ask` only applies to `network`, `install`, and `unknown`; non-interactive runs still deny by default.
- Named sandbox policies can be loaded from `ARC_SANDBOX_POLICY_CONFIG` or `~/.arc/sandbox-policies.json`.
- Container execution is disabled unless `ARC_ENABLE_CONTAINER_SANDBOX=1` is set.
- Lima template rendering requires `ARC_MICROVM_EXPERIMENTAL=1`; it does not execute a VM.
- Firecracker execution artifact generation: `ARC_FC_BUILD_EXEC_ROOTFS=1 uv run arc sandbox firecracker-artifacts --exec-rootfs --output /tmp/arc-fc --json`.
- Next-three phase orchestration prompt: `docs/prompts/phase-104-106-orchestrator.md`. It includes research, up-to-8-subagent workflow, e2e, commit, and push gates while preserving Blocked/host-unproven labels.
