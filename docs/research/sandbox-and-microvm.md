# Sandbox And MicroVM Research

Status: research complete for P0 sandbox foundation. MicroVM is preflight/doctor-only; no microVM execution is claimed.

## Research Notes

| Source | Link | What was learned | Implementation consequence | Confidence | Unresolved questions |
|---|---|---|---|---|---|
| Context7 Python subprocess docs | `/python/cpython` | `Popen.communicate(timeout=...)` must catch timeout, kill child, then call `communicate()` again. POSIX supports `start_new_session`/process groups. | `SubprocessIsolationProvider` uses list argv, no shell, `start_new_session=True`, `os.killpg` on timeout. | High | Windows process-tree semantics skipped for this phase. |
| Context7 Typer docs | `/fastapi/typer` | Use `app.add_typer()` for command groups; use `CliRunner` for command tests. | Added `sandbox` and `policy` subapps; tests use `CliRunner`. | High | None. |
| Context7 Pydantic docs | `/pydantic/pydantic` | Use `BaseModel`, `ConfigDict`, `model_dump(mode="json")` for stable model serialization. | Added `SandboxPolicy`, `SandboxDecision`, `SandboxResult`. | High | None. |
| Context7 Pydantic JSON schema docs | `/pydantic/pydantic` | `model_json_schema()` produces schema dictionaries; `extra='forbid'` rejects unknown fields; `model_dump(mode='json')` keeps JSON-compatible output. | Keep sandbox/policy/protocol checks on Pydantic v2 JSON-mode serialization; prefer small parity test before broad codegen. | High | Full TS codegen remains future work. |
| Codex source | https://github.com/openai/codex/blob/main/codex-rs/core/src/safety.rs | Codex separates safety assessment from execution; writable-root checks, rejection reasons, and sandbox-provider availability affect auto-approval. | ARC separates classification/decision from subprocess execution and emits explicit denial events. | Medium | Full Codex command sandboxing spans more files than fetched. |
| Firecracker docs | https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md | Firecracker requires Linux, KVM, `/dev/kvm` rw access, kernel/rootfs setup, usually jailer for production. | P0 only checks binary and `/dev/kvm`; no fake execution. | High | Image lifecycle and jailer config remain future work. |
| Lima docs | https://lima-vm.io/docs/ | Lima runs Linux VMs with file sharing/port forwarding and supports non-macOS hosts. | macOS microVM path targets Lima rather than Docker Desktop. | High | Need safe ephemeral template before execution. |
| Lima VZ docs | https://lima-vm.io/docs/config/vmtype/vz/ | `vz` uses macOS Virtualization.framework, requires macOS >= 13, default since Lima v1.0, architecture caveats. | macOS doctor detects `limactl` and reports `lima-vz` installed/config status. | High | Detecting macOS version/runtime health without creating VM remains future work. |
| Cloud Hypervisor docs | https://www.cloudhypervisor.org/docs/ | Cloud Hypervisor is a lightweight Linux hypervisor with CLI docs. | Linux doctor accepts `cloud-hypervisor` as secondary candidate. | Medium | Workspace mount and network-off templates not implemented. |
| Kata Containers | https://katacontainers.io/ | Kata provides VM-backed container runtime, stronger isolation, integrates with containerd, Firecracker, Cloud Hypervisor. | Treat Kata as later container-runtime integration, not local P0 CLI default. | Medium | Operational overhead for local CLI unclear. |
| macOS sandbox-exec manpage | https://keith.github.io/xcode-man-pages/sandbox-exec.1.html | `sandbox-exec` is deprecated; Apple recommends App Sandbox for apps. | Do not build ARC P0 on `sandbox-exec`; prefer policy/subprocess now and Lima/VZ later. | High | Seatbelt private profile stability remains unsuitable. |
| Web/code search | Query: `Vercel Grep code search sandbox command classification deny matrix path traversal audit JSONL fsync file lock asyncio supervisor timeout protocol parity TypeScript Python Pydantic` | Tool returned `403 PERMISSION_DENIED Verify your account to continue.` | Recorded blocker; used Context7 and local repo evidence. | Low | Retry external Vercel Grep/code search manually before a security-signoff PR. |
| Vercel Grep/code search | Required topics: sandbox command deny matrices, path traversal guards, JSONL fsync/file lock, asyncio timeout/cancellation, TS/Python parity | No dedicated Vercel Grep tool exposed in this runtime; web-backed attempt blocked by 403. | Local implementation uses conservative deny-by-default classification and table tests; confidence lower than with corpus examples. | Low | Run external Vercel Grep manually when available. |

## Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| P0 execution backend | Hardened subprocess provider | MicroVM execution, container execution | Existing abstraction exists; lowest safe incremental change; no broad runtime execution without gates. | `python/src/agent_runtime_cockpit/isolation/subprocess.py` | High |
| MicroVM phase | Doctor/preflight only | Real Firecracker/Lima runs | Real execution needs images, mounts, network controls, cleanup, opt-in integration tests. | `python/src/agent_runtime_cockpit/isolation/microvm.py` | High |
| macOS lightweight VM | Lima/VZ path | Docker Desktop, deprecated `sandbox-exec` | Lima maps to Apple Virtualization.framework; Docker is container fallback, not microVM. | `docs/research/sandbox-and-microvm.md` | High |
| Linux lightweight VM | Firecracker primary, Cloud Hypervisor secondary | Kata as P0 | Firecracker/Cloud Hypervisor are direct hypervisors; Kata is container-runtime integration. | `python/src/agent_runtime_cockpit/security/sandbox.py` | Medium |
| Policy UX | `arc sandbox run`, `arc policy explain` | Reuse existing `isolation` command only | User-facing Codex/Claude-style policy explanation and execution are distinct from provider diagnostics. | `python/src/agent_runtime_cockpit/cli/sandbox.py` | High |
| Adversarial command policy | Conservative deny matrix plus path-intent validation before subprocess execution | Shell/runtime monitoring, syscall sandbox, broad AST evaluator | P0 must not fake syscall containment; deny known risky interpreters/subcommands and block write/read path escapes before execution. | `python/src/agent_runtime_cockpit/security/sandbox.py`, `python/src/agent_runtime_cockpit/cli/sandbox.py` | Medium |
| HMAC audit durability | Parent creation, advisory file lock where available, append flush + `os.fsync`, partial-line verification failure | Atomic rename per append, SQLite ledger, external audit daemon | Preserve existing JSONL chain format while hardening local append semantics. | `python/src/agent_runtime_cockpit/audit/hmac_chain.py` | Medium |
| Supervisor timeout | `asyncio.wait_for(request.timeout_seconds)` around executor callback | Leave cooperative, runtime-specific cancellation only | Central terminal failure prevents active-run leaks when executors hang. | `python/src/agent_runtime_cockpit/orchestration/supervisor.py` | High |

## Current Scope

Real now:
- `arc sandbox doctor --json`
- `arc policy explain -- <cmd...>`
- `arc sandbox run --policy local-safe -- <cmd...>`
- command classification and deny-by-default network/destructive/privileged/install/unknown policy
- adversarial classifier matrix for interpreters, package installs, VCS destructive subcommands, `find`, `tar --overwrite`, `rsync`, `dd`, `truncate`, `chmod`, `chown`
- path-intent validation for known read/write args and Python literal write paths; read-only absolute paths outside workspace deny by default
- approval tokens are stored as hashes for new approvals, include TTL metadata, and use private file mode where supported; legacy plaintext approvals remain readable for compatibility
- Python/TS protocol parity checks now cover typed run-event type lists, audit event discriminators, and ARC envelope required fields
- subprocess env allowlist, secret-key stripping, workspace cwd guard, process-group timeout kill, output caps, JSON result, audit payloads
- microVM preflight/doctor support for Linux/macOS, explicit unsupported status elsewhere
- sandbox audit events persisted to an external hash-chain audit store
- named sandbox policies loaded from `ARC_SANDBOX_POLICY_CONFIG` / `~/.arc/sandbox-policies.json`
- container execution explicitly gated by `ARC_ENABLE_CONTAINER_SANDBOX=1`
- policy discovery: `arc policy list`, `arc policy show <name>`, `arc policy validate`
- sandbox audit verification: `arc sandbox audit-verify`
- sandbox audit listing/filtering: `arc sandbox audit-list`
- sandbox audit chain appends now continue from the previous chain hash across CLI invocations
- sandbox policy config is schema-versioned and rejects unknown fields
- experimental Lima template rendering behind `ARC_MICROVM_EXPERIMENTAL=1`
- `arc sandbox run --ask` can interactively approve only `network`, `install`, and `unknown`; non-interactive defaults still deny
- Firecracker preflight reports binary choice, `jailer`, `/dev/kvm` rw, arch support, and cached kernel/rootfs readiness
- macOS Lima preflight reports macOS version plus bounded `limactl --version` / `limactl list --json` probes; it does not create VMs
- sandbox audit still writes SHA256 chain/raw events and now best-effort mirrors to the existing HMAC audit store when an audit key exists
- HMAC audit append creates parents, locks where portable, writes canonical JSON, flushes and fsyncs, and verification reports partial trailing lines
- supervisor executor callbacks now have a central timeout wrapper that emits terminal `RUN_FAILED`, autopsy, receipt, and clears active state
- path-intent extraction covers more common output/input switches (`--output`, `--outfile`, `--dest`, `--files-from`, `of=`), plus simple `cp`/`mv` destination and archive-output suffixes
- opt-in microVM integration skeleton is gated by `ARC_MICROVM_INTEGRATION=1`; default CI skips it

Design-only now:
- container provider as production fallback
- real microVM execution
- Lima disposable VM session templates
- Firecracker jailer/rootfs/kernel lifecycle

Blocked:
- Google web search tool requires account verification.
- Vercel Grep tool is not exposed in this environment.
- MicroVM execution requires host runtime, image strategy, mount policy, network-off proof, and opt-in integration tests.

## Policy Config

Default path: `~/.arc/sandbox-policies.json`.

Override path: `ARC_SANDBOX_POLICY_CONFIG`.

Example:

```json
{
  "version": 1,
  "policies": [
    {
      "version": 1,
      "name": "net-ok",
      "allow_network": true,
      "allow_install": false,
      "allow_privileged": false,
      "allow_unknown": false,
      "timeout_seconds": 30,
      "max_output_bytes": 65536
    }
  ]
}
```

CLI:

```bash
arc policy list --json
arc policy show net-ok --json
arc policy validate --json
```

Invalid config behavior:

- malformed JSON returns `ok: false` with JSON parser error.
- duplicate policy names are rejected.
- Pydantic schema errors are surfaced with policy index.
- top-level `version` must be `1`.
- policy object `version` must be `1`.
- unknown fields are rejected.

## Audit Persistence

Sandbox commands persist audit artifacts outside the workspace by default:

- chain: `~/.arc/audit/sandbox.audit.jsonl`
- raw events: `~/.arc/audit/sandbox.events.jsonl`
- optional HMAC mirror: same audit directory through `AuditChainStore` when `arc audit key init` has provided a key

Override directory: `ARC_SANDBOX_AUDIT_DIR`.

The CLI response still includes the event payload for immediate UX and tests.

The HMAC mirror is best-effort and never required for `arc sandbox run` success. Missing audit keys keep the existing SHA256 chain as the stable default.

Verification:

```bash
arc sandbox audit-verify --json
arc sandbox audit-verify --audit-dir /tmp/arc-audit --json
arc sandbox audit-list --json --limit 20
arc sandbox audit-list --json --denied --classification network
```

## Container Gate

Container execution is not automatically enabled. `DockerIsolationProvider` returns disabled unless:

```bash
export ARC_ENABLE_CONTAINER_SANDBOX=1
```

This keeps Docker/Podman/OrbStack as an explicit container fallback, not a hidden microVM path.

## Lima Disposable VM Design

Goal: macOS lightweight VM execution through Lima `vz`, not Docker Desktop.

Proposed run flow:

1. Generate a temporary Lima instance name: `arc-sandbox-<nonce>`.
2. Generate a YAML template with `vmType: vz`, minimal Ubuntu/Alpine image, controlled workspace mount at `/workspace`, no writable host mounts outside workspace.
3. Disable/default-deny network by config where Lima supports it; otherwise prove denial with route/DNS checks inside guest before running user argv.
4. Start instance with `limactl start --tty=false <template>`.
5. Run argv via `limactl shell <instance> -- <argv...>` from `/workspace`.
6. Capture stdout/stderr/exit code with same max-output caps/redaction.
7. Stop/delete instance with `limactl delete -f <instance>` in `finally`.
8. Tests remain opt-in behind `ARC_MICROVM_INTEGRATION=1` and skip if `limactl` or macOS VZ is unavailable.

Current prototype:

```bash
ARC_MICROVM_EXPERIMENTAL=1 arc sandbox lima-template --json
```

This renders a template only. It does not create, start, or execute inside a VM.

Network-off proof required before execution can be called real:

- `curl`/DNS route check from guest fails without live network dependency.
- no host port forwarding by default.
- policy-denied network commands never reach VM.

## Firecracker Execution Design

Goal: Linux direct microVM execution with Firecracker, not container fallback.

Proposed run flow:

1. Preflight `firecracker`, `jailer`, `/dev/kvm` read/write, kernel arch, current user KVM permissions.
2. Require a prebuilt ARC rootfs/kernel cache, never download at command runtime.
3. Create per-run temp jail directory and API socket.
4. Use Firecracker jailer where available; otherwise mark `installed_not_configured`, not ready.
5. Mount workspace through a controlled block/virtiofs strategy; read-only/read-write based on policy.
6. Do not configure TAP/NAT for default network-deny policies.
7. Boot guest with an init/agent that receives argv over vsock/serial/SSH-free channel.
8. Capture stdout/stderr/exit code, enforce timeout from host, destroy VM/jail dir in `finally`.
9. Tests remain opt-in behind `ARC_MICROVM_INTEGRATION=1` and skip unless Firecracker runtime and cached images exist.

Current preflight detail:

- `firecracker` or `cloud-hypervisor` binary
- `jailer` binary
- `/dev/kvm` exists
- `/dev/kvm` read/write access
- `ARC_FIRECRACKER_KERNEL` exists
- `ARC_FIRECRACKER_ROOTFS` exists

Blockers before implementation:

- rootfs/kernel provenance and cache management
- jailer profile and non-root permissions
- workspace mount design with symlink/hardlink escape proof
- network-off proof without TAP/NAT
- deterministic teardown on boot failure/timeouts
