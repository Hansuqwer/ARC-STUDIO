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
| Context7 Python subprocess docs | `/python/cpython` | Timeout cleanup must kill child/process, then drain pipes; POSIX `start_new_session` creates a process group/session. | Lima command runner keeps process-group kill and bounded capture behavior. | High | Windows skipped for microVM. |
| Context7 Typer docs | `/fastapi/typer` | `CliRunner` supports CLI tests; nested Typer commands and options are standard. | Keep experimental surfaces testable via existing CLI pattern without shelling out. | High | None. |
| Context7 Pydantic docs | `/pydantic/pydantic` | `ConfigDict(frozen=True)` and `model_dump(mode="json")` support stable immutable envelopes. | Harness/result models use Pydantic envelopes for stable JSON/testing. | High | None. |
| Lima limactl docs | https://lima-vm.io/docs/reference/limactl/ | `limactl` supports `start`, `shell`, `delete`; `--tty=false`/`--yes` are automation-oriented. | Harness command sequence uses `limactl start --tty=false`, `limactl shell --tty=false`, and `limactl delete -f`. | High | Exact behavior depends on installed Lima version. |
| Lima network docs | https://lima-vm.io/docs/config/network/ | Lima has default/user/VMNet networking and named networks can be attached via `networks`. | Harness requires an in-guest default-route proof before user argv; template still needs stronger network-off config proof. | Medium | Need real host validation that `networks: []` disables default route for chosen Lima/VZ version. |
| Lima mount docs | https://lima-vm.io/docs/config/mount/ | Lima mount behavior varies by mount type; VZ uses virtiofs on modern Lima/macOS, with caveats. | Harness keeps workspace-only `/workspace` mount, but still treats symlink/hardlink escape proof as blocker. | High | Need real mount escape tests with symlinks/hardlinks in a guest. |
| Web/code search | Query: `Vercel Grep code search sandbox command classification deny matrix path traversal audit JSONL fsync file lock asyncio supervisor timeout protocol parity TypeScript Python Pydantic` | Tool returned `403 PERMISSION_DENIED Verify your account to continue.` | Recorded blocker; used Context7 and local repo evidence. | Low | Retry external Vercel Grep/code search manually before a security-signoff PR. |
| Vercel Grep/code search | Required topics: sandbox command deny matrices, path traversal guards, JSONL fsync/file lock, asyncio timeout/cancellation, TS/Python parity | No dedicated Vercel Grep tool exposed in this runtime; web-backed attempt blocked by 403. | Local implementation uses conservative deny-by-default classification and table tests; confidence lower than with corpus examples. | Low | Run external Vercel Grep manually when available. |
| Context7 Lima network docs | `/lima-vm/lima` | Default Lima networking is user-mode/slirp on hard-coded `192.168.5.0/24`; `user-v2` disables default user-mode network but is still user-mode networking. | ADR-024 P2 revised: Lima is low-security network-present harness only, not strict public microVM sandbox. | High | Need a non-Lima macOS option or future Lima no-network feature for strict macOS microVM. |
| Context7 Lima mount docs | `/lima-vm/lima` | Lima templates can mount specific host directories, choose mount types such as `virtiofs`, `9p`, or `sshfs`, and SSHFS exposes a `followSymlinks` option. | Added a host-gated Lima P5 test that proves whether `/workspace` symlinks can reach host files before any public execution is wired. | Medium | Real-host result pending; if virtiofs follows host symlink targets, Lima cannot satisfy strict P5. |
| Lima default user-mode network docs | https://lima-vm.io/docs/config/network/user/ | Docs state Lima only enables user-mode networking aka slirp by default, with `192.168.5.0/24`, host IP, and DNS. | `networks: []` cannot be treated as proof of no default route; keep in-guest route proof and block argv if route exists. | High | Need real-host validation for any future template change. |
| Lima user-v2 network docs | https://lima-vm.io/docs/config/network/user-v2/ | `user-v2` disables the default user-mode network but provides another user-mode network and VM-to-VM communication. | Do not use `user-v2` as network-off proof. | High | None for current decision. |
| Firecracker network docs | https://github.com/firecracker-microvm/firecracker/blob/main/docs/network-setup.md | Firecracker networking requires explicit TAP device plus NAT/bridge/namespaced NAT setup; guest default route is configured by setup steps. | Firecracker/Cloud Hypervisor remain better strict no-network candidates because omitting network configuration can be proven. | Medium | Need real boot/rootfs implementation to prove guest has no NIC/default route. |
| Google web search | Required topics: Lima no-network, Apple VZ no-network, Firecracker no-network | Tool returned `403 PERMISSION_DENIED Verify your account to continue.` | Recorded blocker; used Context7 and direct docs URLs. | Low | Retry Google search externally before security sign-off. |
| Context7 Firecracker docs | `/firecracker-microvm/firecracker` | Firecracker config files require boot source and drives; `network-interfaces` is an explicit optional resource. | Added a design-proof no-NIC config model that omits `network-interfaces` entirely and marks proof `not_proven`. | High | Need a Linux/KVM host plus kernel/rootfs to boot and verify guest route/curl behavior. |
| Firecracker getting started | https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md | Firecracker requires Linux, supported arch, `/dev/kvm` rw, binary, kernel image, and rootfs; config-file boot can start a VM from JSON. | Host-gated real proof requires `ARC_MICROVM_INTEGRATION=1`, `ARC_FC_REAL_EXEC=1`, `ARC_FIRECRACKER_KERNEL`, `ARC_FIRECRACKER_ROOTFS`, Linux, Firecracker, and `/dev/kvm`. | High | No guest command channel implemented yet for route/curl proof capture. |
| Firecracker jailer docs | https://github.com/firecracker-microvm/firecracker/blob/main/docs/jailer.md | Jailer creates chroot/cgroup/devices, cleans env, and needs explicit cleanup; daemonized jailer PID handling is subtle. | This phase does not enable jailer execution; teardown remains design-plan plus blocked harness audit. | High | Need a follow-up jailer lifecycle implementation before public execution. |
| Cloud Hypervisor docs | https://www.cloudhypervisor.org/docs/ | Cloud Hypervisor remains a lightweight Linux alternative but would require separate CLI/config/proof semantics. | No pivot; Firecracker remains primary for ADR-024 P2 unless a new ADR changes it. | Medium | Direct no-NIC run pattern still unimplemented for ARC. |
| Context7 Firecracker docs | `/firecracker-microvm/firecracker` | Firecracker network interfaces are configured explicitly through `network-interfaces`/TAP setup; boot config can include boot source, drives, and machine config without a network interface. | Keep Firecracker proof path no-NIC by construction; test config omits `network-interfaces`; real host must still prove `ip route` has no default route and curl fails. | High | Guest command channel, rootfs provenance, jailer lifecycle, and workspace mount proof remain open. |
| Context7 Cloud Hypervisor docs | `/cloud-hypervisor/cloud-hypervisor` | Cloud Hypervisor network is configured through explicit `--net` options; disk/kernel boot can be represented without `--net`; virtiofs sharing requires `--fs` plus shared memory. | Add Cloud Hypervisor proof scaffold whose argv omits `--net`; workspace mount remains design-only until virtiofs/agent strategy is proven. | High | Need host Linux/KVM proof plus symlink behavior validation for chosen sharing strategy. |
| Context7 Python subprocess docs | `/python/cpython` | Timeout cleanup should kill the process then drain pipes; POSIX `start_new_session` creates a separate session and `os.killpg` can kill the process group. | Keep host-gated proof harnesses process-group bounded; no broad runner change this slice. | High | None for current scaffold. |
| Vercel Grep/code search | Required topics: Firecracker wrappers, Cloud Hypervisor wrappers, KVM preflight, no-NIC/no-network proofs, mount isolation tests | No Vercel Grep/code-search tool is exposed in this runtime. | Record blocker; rely on official docs + local tests for scaffold only. | Low | Run external Vercel Grep before security sign-off. |
| Google web search | Firecracker/Cloud Hypervisor KVM requirements, `/dev/kvm` perms, virtiofs symlink security, CI skip patterns | Tool returned `403 PERMISSION_DENIED Verify your account to continue.` | No web-derived implementation claim; docs and code stay at host-gated proof harness/preflight only. | Low | Retry externally before security sign-off. |

## Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| P0 execution backend | Hardened subprocess provider | MicroVM execution, container execution | Existing abstraction exists; lowest safe incremental change; no broad runtime execution without gates. | `python/src/agent_runtime_cockpit/isolation/subprocess.py` | High |
| MicroVM phase | Doctor/preflight only | Real Firecracker/Lima runs | Real execution needs images, mounts, network controls, cleanup, opt-in integration tests. | `python/src/agent_runtime_cockpit/isolation/microvm.py` | High |
| macOS lightweight VM | Lima/VZ as low-security harness only | Docker Desktop, deprecated `sandbox-exec`, public strict microVM | Lima maps to Apple Virtualization.framework but currently exposes user-mode networking; it cannot satisfy strict P2. | `docs/adr/ADR-024-microvm-public-execution-contract.md`, `python/src/agent_runtime_cockpit/security/sandbox.py` | High |
| Linux lightweight VM | Firecracker primary, Cloud Hypervisor secondary | Kata as P0 | Firecracker/Cloud Hypervisor are direct hypervisors; Kata is container-runtime integration. | `python/src/agent_runtime_cockpit/security/sandbox.py` | Medium |
| Firecracker strict no-network proof | Add no-NIC design/preflight config + host-gated test scaffold; do not wire public execute | Immediate public microVM execution; Cloud Hypervisor pivot | Current host lacks Linux/KVM/rootfs. Config omission can be tested safely now; real proof requires explicit host gates. | `python/src/agent_runtime_cockpit/isolation/microvm.py`, `python/tests/isolation/test_firecracker_smoke.py` | High |
| Firecracker/Cloud Hypervisor proof path | Add shared Linux/KVM host-gated proof-plan surface; keep public provider blocked | Lima strict path; Docker fallback; public microVM execution | Lima is low-security/network-present. Firecracker/Cloud Hypervisor can omit NIC config by construction but still need real KVM boot/run/teardown proof. | `python/src/agent_runtime_cockpit/isolation/microvm.py`, `python/src/agent_runtime_cockpit/security/sandbox.py`, `python/tests/isolation/test_firecracker_smoke.py`, `python/tests/isolation/test_microvm_preflight.py` | High |
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
- Firecracker no-network design/preflight support emits a config-plan with `strict_network_candidate=true`, `strict_network_proof=not_proven`, and `network_interfaces_configured=false`
- Cloud Hypervisor proof scaffold emits no-`--net` argv/config, kernel/disk env diagnostics, and host gates; no VM is started by normal tests
- macOS Lima preflight reports macOS version plus bounded `limactl --version` / `limactl list --json` probes; it does not create VMs
- macOS Lima preflight reports `strict_network_isolation=false` and `security_posture=low_security_network_present`
- sandbox audit still writes SHA256 chain/raw events and now best-effort mirrors to the keyed audit store when an audit key exists
- keyed audit append creates parents, locks where portable, writes canonical JSON, flushes and fsyncs, and verification reports partial trailing lines
- supervisor executor callbacks now have a central timeout wrapper that emits terminal `RUN_FAILED`, autopsy, receipt, and clears active state
- path-intent extraction covers more common output/input switches (`--output`, `--outfile`, `--dest`, `--files-from`, `of=`), plus simple `cp`/`mv` destination and archive-output suffixes
- opt-in microVM integration skeleton exists as private code only; public `MicroVMIsolationProvider.execute()` remains disabled until proof exists
- Lima/Firecracker harness attempts emit persisted `MICROVM_COMMAND`/`MICROVM_DENIED` sandbox audit events with `public_execution_enabled=false`

Design-only now:
- container provider as production fallback
- real microVM execution
- real Firecracker boot/no-default-route/curl-fails proof
- real Cloud Hypervisor boot/no-default-route/curl-fails proof
- Lima disposable VM session templates as low-security harness only
- Firecracker jailer/rootfs/kernel lifecycle
- Cloud Hypervisor kernel/disk/workspace-mount lifecycle

Blocked:
- Google web search tool requires account verification.
- Vercel Grep tool is not exposed in this environment.
- MicroVM execution requires host runtime, image strategy, mount policy, network-off proof, and opt-in integration tests.

## Phase 37.6 MicroVM Execution Blocker Detail

Status: Blocked. Preflight/doctor only. No microVM execution exists.

Current design-proof harness:

- `arc sandbox microvm-plan --json --provider lima -- <cmd...>` renders a non-executing Lima run plan.
- `arc sandbox microvm-plan --json --provider firecracker -- <cmd...>` renders a non-executing Firecracker run plan.
- Plans include lifecycle, workspace mount, network-default-deny, run, teardown, and blocker fields.
- Plan generation does not call `limactl`, `firecracker`, `cloud-hypervisor`, or `jailer` and does not create VMs.
- `execution_enabled` is always `false`; public `MicroVMIsolationProvider.execute()` remains blocked.

Current opt-in Lima harness:

- `LimaIntegrationHarness` exists as an internal helper only; it is not wired to `arc sandbox run --provider microvm`.
- It requires `ARC_MICROVM_INTEGRATION=1`, macOS, and `limactl` by default; unit tests pass `require_gate=False` with a fake runner.
- Fake-runner tests prove lifecycle order, mandatory network proof before user argv, no user command after failed network proof, and `limactl delete -f` teardown after start failure.
- Real Lima execution remains unproven until host opt-in tests are run against a local Lima/VZ install.

### Rootfs/Kernel Lifecycle
- Firecracker needs a kernel vmlinux binary and a rootfs image. No automated download/cache mechanism exists.
- Lima VM templates exist as rendered YAML only; no `limactl start/create/delete` lifecycle is implemented.
- Proposed: manage a local cache dir (`~/.arc/microvm/`) with versioned images. Not implemented.

### Workspace Mount Policy
- Firecracker: needs virtiofs or block device mapping. No safety analysis for symlink/hardlink escapes in guest mounts.
- Lima: host-mounted directories are shared via `mounts` in template YAML. `~` and sensitive host paths must be excluded.
- Proposed: only mount the workspace directory read-only by default; read-write only with explicit policy opt-in. Not implemented.

### Network-Off Proof
- No public provider proves strict guest no-network access.
- Firecracker: no TAP/NAT interfaces configured by default, but no boot/proof verifies guest isolation yet.
- Lima: default slirp/user-mode networking is documented; `user-v2` is also user-mode networking. ARC treats Lima as low-security/network-present, not strict P2 evidence.
- Proposed strict proof: boot Firecracker/Cloud Hypervisor without guest NIC/default route, then verify `ip route` has no default route and `curl --connect-timeout 1 http://example.com` fails before user argv.
- Current strict proof status: design/preflight only. `build_firecracker_no_network_run_plan()` emits a Firecracker config dictionary with no `network-interfaces` key and the required proof commands (`ip route`, `curl --connect-timeout 2 https://example.com`). No real boot was executed on this macOS host.

### Teardown Guarantees
- Firecracker: VM is destroyed by stopping the Firecracker process. No timeout/safety net for boot-failure hangs.
- Lima: `limactl delete -f` after run. No cleanup on host crash/reboot.
- Proposed: use a context timeout + defer block with force-cleanup. Not implemented.

### Integration Gate
- Tests exist at `python/tests/isolation/test_microvm_preflight.py` — 4 tests covering all 4 preflight states.
- A skeleton integration test exists at `python/tests/test_cli_sandbox.py::test_microvm_integration_skeleton_doctor_only`, gated by `ARC_MICROVM_INTEGRATION=1`.
- Design-proof plan tests cover Lima and Firecracker plan shape and assert CLI plan generation does not run subprocess probes.
- CI does not set `ARC_MICROVM_INTEGRATION=1` — no microVM runtime in CI.

### Summary
| Component | Status | What's missing |
|---|---|---|
| Preflight/doctor | Real | All 4 states tested: unavailable/installed_not_configured/ready/blocked |
| Design-proof plan | Real | Non-executing plan only; no VM creation/start/run/delete |
| Opt-in Lima harness | Internal helper only | Fake-runner lifecycle tests pass; Lima smoke test added (CI-skipped; real host proof pending) |
| Lima smoke test | Added (CI-skip) | `python/tests/isolation/test_lima_smoke.py`; skipped unless macOS + limactl + ARC_MICROVM_INTEGRATION=1; CI does not set gate; real Lima execution NOT claimed on this host |
| MicroVM truth guard | Added | `test_microvm_truth_guard.py` (10 tests): execute() always raises, both gates set still raises, status()["available"]=False, contract_doc references ADR-024, CLI run blocked; arc sandbox run --provider microvm: blocked |
| Firecracker harness | Design/preflight only | `FirecrackerIntegrationHarness` added with fake-runner tests; no real Firecracker execution; `firecracker_doctor()` expanded with jailer/cache/kvm fields |
| Firecracker execution | Not implemented | Kernel/rootfs lifecycle, mount policy, network-off proof, jailer config, teardown |
| Lima strict execution | Not implemented | Lima is explicitly low-security/network-present; strict public `microvm` remains blocked |
| Integration test skeleton | Real (gated) | Tests exist but require local runtime; CI skips |
| Harness audit events | Real for internal harnesses | `MICROVM_COMMAND`/`MICROVM_DENIED` persisted for Lima/Firecracker harness attempts; public execution remains blocked |
| Production-ready claim | Not claimed | Would need full execution + opt-in CI tests + network-off proof |

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
- optional keyed mirror: same audit directory through `AuditChainStore` when `arc audit key init` has provided a key

Override directory: `ARC_SANDBOX_AUDIT_DIR`.

The CLI response still includes the event payload for immediate UX and tests.

The keyed mirror is best-effort and never required for `arc sandbox run` success. Missing audit keys keep the existing SHA256 chain as the stable default.

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

Design-proof plan:

```bash
arc sandbox microvm-plan --json --provider lima -- pwd
```

This renders lifecycle/mount/network/run/teardown steps and blockers only. It does not call `limactl`.

Public provider guard:

- `MicroVMIsolationProvider.execute()` raises `NotImplementedError` even when `ARC_MICROVM_INTEGRATION=1` is set.
- `MicroVMIsolationProvider.describe()` reports `gated_unproven` when the gate and `limactl` are present, never `implemented`.
- Real execution requires a later integration-proof PR covering lifecycle, mount policy, network-off proof, teardown, and opt-in tests.

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

---

## Credential Storage & OAuth (Phase 36.2 / R37 Phase 2)

**Status:** Baseline Complete + OAuth/Keychain hardening follow-up | 57 auth tests passing | 2319 total Python tests passing

### Research Notes

| Source | Link | What was learned | Implementation consequence | Confidence | Unresolved questions |
|---|---|---|---|---|---|
| Context7 Fernet docs | `/python/cpython` | `cryptography.fernet.Fernet` provides symmetric authenticated encryption with nonce-based uniqueness. Keys are 32-byte base64-encoded. | Used `Fernet.generate_key()` and `Fernet(key).encrypt()` for credential storage at rest. Each encryption produces unique ciphertext. | High | Key rotation strategy not implemented; single machine-local key. |
| Context7 Typer docs | `/fastapi/typer` | `app.add_typer()` for subcommands; `CliRunner` for isolated CLI tests; `monkeypatch.setattr()` for mocking module attributes. | Added `arc providers remove` subcommand; CLI tests use `CliRunner` with monkeypatched `AUTH_PATH`. | High | `monkeypatch.setattr` requires direct module object reference, not dotted string path, for module-scoped lookups. |
| Pydantic v2 model_dump_json | `/pydantic/pydantic` | `model_dump_json()` produces compact JSON (no spaces after colons). | Audit log parsing must match compact JSON format (`"success":false` not `"success": false`). | High | None. |
| Web search | Fernet key management | Fernet keys are stored alongside credentials; macOS Keychain is preferable where available. | Keys stored at `~/.local/share/arc-studio/.auth-key` with `0o600` permissions; optional `keyring` backend added for system Keychain. | Medium | Key rotation strategy remains deferred. |
| Context7 keyring docs | `/jaraco/keyring` | `keyring.set_password`, `get_password`, and `delete_password` provide platform-native secure storage, including macOS Keychain where available. | Added optional keyring helpers and `arc providers add --keychain`; falls back to Fernet when keyring unavailable. | High | CI uses monkeypatched keyring; real Keychain manual smoke still needed on macOS. |
| Code/OAuth research | Python stdlib + OAuth PKCE pattern | Local callback should use dynamic port allocation, validate `state`, and include PKCE `code_challenge` / `code_verifier` for CLI OAuth. | OAuth flow now defaults to port `0` dynamic allocation, validates `state`, and sends S256 PKCE verifier/challenge. | High | Real provider OAuth endpoint compatibility still requires live-provider testing. |
| Code search | `provider_statuses()` in `provider_action.py` | Existing function only checks env vars; no stored credential fallback. | Added optional `check_stored_creds` parameter; defaults to False (env-only). | High | Stored credential check is opt-in to preserve existing CLI test behavior. |
| Code search | Phase 23 trust enforcement | `ensure_trusted()` / `resolve_trust()` in `security/trust.py` governs workspace trust. | Auth module uses lenient trust check (default trusted); real enforcement at CLI/action layer. | High | Mock-based trust enforcement tests require `unittest.mock.patch.object` for reliable attribute patching. |
| Code search | Audit infrastructure | Audit events use `ok()` envelope with `model_dump_json()`. | Credential audit events written to `.arc/audit/auth.events.jsonl` in compact JSONL format. | High | Audit events are best-effort; failures are caught and logged. |

### Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| Credential encryption | Fernet default + optional system Keychain | Env vars only, asymmetric encryption, Keychain-only | Fernet stays cross-platform/offline; Keychain is optional for macOS users with `keyring` available. | `auth/manager.py` | High |
| Storage path | `~/.local/share/arc-studio/auth.json` | `~/.arc/`, XDG config home | Follows existing ARC data directory convention; `0o600` permissions enforced. | `auth/manager.py` | High |
| Trust enforcement | Lenient default (trusted), opt-in enforcement via `trust_check` parameter | Hard gate on all access | Credential storage must remain usable during first-run/trust-setup flows. Full gate at CLI/action layer. | `auth/manager.py` | High |
| Audit logging | Best-effort JSONL to `.arc/audit/auth.events.jsonl` | Centralized audit store, no logging | Lightweight per-workspace audit trail; failures don't block credential access. | `auth/manager.py` | High |
| OAuth token refresh | `refresh_oauth_token()` with `refresh_token` preservation | Always force re-auth | Servers may not return new refresh token; preserve old one. | `auth/oauth.py` | High |
| OAuth callback security | Dynamic localhost port + `state` validation + PKCE S256 | Static port 8080, no PKCE, no state check | Avoids port conflicts, prevents CSRF-style callback mismatch, aligns CLI OAuth with modern provider guidance. | `auth/oauth.py` | High |
| Keychain support | Optional `keyring` backend behind `--keychain` | Always store in Keychain, Fernet only | Keeps CI deterministic and preserves Linux/macOS fallback while enabling platform-native storage. | `auth/manager.py`, `cli/providers.py` | High |
| Env var fallback | `provider_statuses(check_stored_creds=False)` by default | Always check stored creds | Preserves existing CLI behavior; opt-in for credential-aware paths. | `provider_action.py` | High |
| CLI path resolution | `Optional[Path] = None` with dynamic `_resolve_path()` | Default argument `path: Path = AUTH_PATH` | Default arguments are evaluated at function definition time; dynamic lookup supports monkeypatching in tests. | `auth/manager.py` | High |

### Current Scope

Real now:
- Fernet encrypt/decrypt roundtrip for API keys and OAuth tokens
- `arc providers add --api-key <key>` stores encrypted credential
- `arc providers add --oauth` starts OAuth flow with local callback server
- OAuth callback uses dynamic localhost port allocation (`redirect_port=0` default)
- OAuth callback validates `state` and supports PKCE S256
- `arc providers remove <provider>` removes stored credentials
- OAuth token refresh with `refresh_oauth_token()`
- Expired OAuth credentials can auto-refresh when a refresh token and client config are available
- Optional macOS Keychain/system keyring storage via `arc providers add --keychain`
- Environment variable fallback: env vars take precedence over stored creds
- Workspace trust enforcement: credential access gated by `trust_check` parameter
- Audit log: credential access/denial events written to `.arc/audit/auth.events.jsonl`
- 57 comprehensive tests covering all paths

Design-only:
- Key rotation strategy
- Multi-user/multi-workspace credential separation
- Credential expiry notifications

Blocked:
- Real OAuth flow requires live provider endpoints (tests use monkeypatched HTTP)
- Real macOS Keychain smoke requires a macOS user session with unlocked Keychain; CI uses monkeypatched `keyring`.
- Trust enforcement mocking with `monkeypatch.setattr` is unreliable with string paths; use `unittest.mock.patch.object` for test-time attribute patching.

---

## Step 1–5 Research (2026-05-26)

### Host Pre-Check Results

| Tool | Result |
|---|---|
| `which limactl` | `/opt/homebrew/bin/limactl` — **present** |
| `limactl --version` | `limactl version 2.1.0` |
| `which firecracker` | `firecracker not found` — **absent** |
| `ls -la /dev/kvm` | `No such file or directory` — **absent** (Darwin/macOS, no KVM) |
| `uname -sr` | `Darwin 25.4.0` |

Consequence: Step 1 (Lima lifecycle proof) **can proceed** on this host. Steps 4 (Firecracker real-host) is **host-skipped**.

### Research Notes

| Source | Link | What was learned | Implementation consequence | Confidence | Unresolved questions |
|---|---|---|---|---|---|
| Context7 Python subprocess | `/python/cpython` | `os.killpg(pgid, sig)` sends signal to entire process group. `start_new_session=True` calls `setsid()` in child before exec. After `TimeoutExpired`, call `proc.kill()` then `proc.communicate()` to drain pipes — do NOT call `wait()` after timeout. | LimaIntegrationHarness already uses `start_new_session=True` + `os.killpg` + drain; pattern is correct. | High | None. |
| Context7 Python pathlib | `/python/cpython` | `Path.resolve(strict=False)` resolves symlinks and eliminates `..` components; works even for missing paths. `Path.is_symlink()` returns True for broken symlinks. | Use `Path.resolve()` for workspace escape detection; handles dangling symlinks safely. | High | Python 3.13 changed symlink loop handling; project uses 3.11, so `strict=False` resolves as far as possible — safe for our use. |
| Context7 Python os.path | `/python/cpython` | `os.path.realpath(path, strict=False)` returns canonical path eliminating symlinks; `strict=True` raises OSError for missing or loop. `strict` added in 3.10. | Use `Path.resolve()` (wraps realpath) for escape check; consistent API across 3.11+. | High | None. |
| Lima network docs | `https://lima-vm.io/docs/config/network/` | Default Lima network is user-mode slirp (192.168.5.0/24). `networks: []` only removes named VMNet networks — it does NOT disable the built-in slirp default route. | **Critical**: our network-off strategy of checking `ip route | grep default` in guest is correct BUT the guest will always have a slirp default route unless we use a Lima version / config that explicitly disables the slirp interface. No known `vmType: vz` config key to disable slirp in Lima 2.1.0. | High | Is there a Lima 2.x config key to disable default slirp networking? Need to check Lima source / issue tracker. Unresolved: cannot claim network isolation until this is proven. |
| Lima network user-mode docs | `https://lima-vm.io/docs/config/network/user/` | Subnet 192.168.5.0/24 is hard-coded. Guest IP is 192.168.5.15. Host IP (loopback) is 192.168.5.2. DNS is 192.168.5.3. `hostResolver.enabled` controls DNS forwarding. No config key to disable slirp entirely documented. | Network-off via `networks: []` is insufficient. Must either (a) find a Lima 2.x option to disable slirp, or (b) accept that the guest WILL have a default route, and instead prove denial at the policy layer before reaching the VM. This changes our network-off proof strategy. | High | Unresolved: does Lima 2.x support disabling the default slirp interface via any template config? |
| Lima mount docs | `https://lima-vm.io/docs/config/mount/` | VZ default mount type is virtiofs (Apple Virtualization.Framework shared directory). `followSymlinks` option exists for reverse-sshfs but not for virtiofs. virtiofs passes symlinks through — guest sees host symlinks as symlinks. | Symlinks inside the workspace mount will appear as symlinks in the guest. A symlink inside /workspace pointing to a host path outside workspace will be accessible from the guest via virtiofs. This is the mount escape vector. Must test explicitly. | High | Does virtiofs restrict symlink traversal to the declared mount root? Docs do not state this. Need real host test. |
| Google web search | blocked | All Google search queries returned 403 PERMISSION_DENIED. | Recorded as tool unavailable. Used direct Lima docs + Context7 instead. | N/A | Retry external web search manually before security-signoff PR. |
| Vercel Grep / code search | N/A — tool not exposed | No Vercel Grep tool available in this runtime. Attempted web-backed search blocked by 403. | Conservative implementation: use local repo evidence and Lima docs. | Low | Run external Vercel Grep manually when available. |

### Key Implementation Consequences for Steps 1–5

1. **Lima network-off (P2): NOT provable as "network completely off"** — Lima 2.1.0 always gives the guest a slirp default route. The current harness checks `ip route | grep default` and expects exit 1 (no default route). This will FAIL on a real Lima VM because the default route exists. **The network proof strategy must change**: either (a) accept that Lima's default slirp provides outbound network and remove the network-off claim, documenting this as a known limitation, or (b) find a Lima config to disable the slirp interface before claiming P2 satisfied.

2. **Lima mount isolation (P3/P5)**: virtiofs passes symlinks through. The host-side check (`is_path_within_root`) prevents the workspace_root from being a symlink to somewhere dangerous. But a symlink INSIDE the workspace, pointing outside, will be accessible in the guest. Must document this as a known gap.

3. **Step 1 feasibility**: limactl 2.1.0 is present. However, real Lima VM start takes 60–300 seconds for first-time image download + boot. The smoke tests must handle this in CI with very generous timeouts. The network_proof test will need adjustment given finding (1) above.

4. **Firecracker (Step 4)**: absent on this host. Step 4 code and docs can be written but tests will always skip here.
