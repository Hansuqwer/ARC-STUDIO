# Sandbox And MicroVM Research

Status: research complete for P0 sandbox foundation. MicroVM remains preflight/doctor plus Linux/Firecracker gated scaffold; no live Firecracker boot/run/teardown proof exists on this host. macOS direct Apple VZ no-NIC host proof passed once on this host behind `ARC_VZ_PROOF=1`; public `arc sandbox run --provider microvm` execution remains blocked.

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
| Context7 Firecracker docs | `/firecracker-microvm/firecracker` | Firecracker supports `--config-file` with `boot-source`, `drives`, and `machine-config`; `network-interfaces` is optional and only present when configured. `InstanceStart` is the API action for socket-driven boot. | Added a private Firecracker proof runner that writes a no-NIC config file and starts Firecracker only behind Linux/KVM/binary/env/kernel/rootfs gates. | High | Guest proof commands still require a command channel. |
| Firecracker getting-started docs | https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md | Current getting-started states Firecracker requires Linux KVM, `/dev/kvm` read/write, supported x86_64/aarch64 Linux, a kernel image, and rootfs. Config-file startup starts a VM from JSON. | Proof gates require Linux, `/dev/kvm` rw, `firecracker`, `ARC_MICROVM_INTEGRATION=1`, `ARC_FC_REAL_EXEC=1`, `ARC_FIRECRACKER_KERNEL`, and `ARC_FIRECRACKER_ROOTFS`. | High | Host proof not runnable on this macOS host. |
| Firecracker network setup docs | https://github.com/firecracker-microvm/firecracker/blob/main/docs/network-setup.md | Guest networking requires host TAP/NAT/bridge/namespaced NAT setup plus a Firecracker network-interface config. | Proof config intentionally omits `network-interfaces`, TAP, NAT, and bridge setup. Real P2 still requires guest `ip route` and failed `curl` proof. | High | Need guest command channel to collect `ip route`/`curl`. |
| Firecracker jailer docs | https://github.com/firecracker-microvm/firecracker/blob/main/docs/jailer.md | Jailer cleans env, creates chroot/cgroup/dev nodes, forwards Firecracker args, and cleanup/PID handling are operator responsibilities. | This slice does not enable jailer; proof runner uses direct Firecracker subprocess only and records jailer as future hardening. | High | Add jailer lifecycle before any public execution. |
| Firecracker Actions API docs | https://github.com/firecracker-microvm/firecracker/blob/main/docs/api_requests/actions.md | `InstanceStart` starts the guest OS and can be called once; `SendCtrlAltDel` can trigger shutdown when guest/kernel support exists. | Config-file path avoids API setup for this proof harness. API-socket `InstanceStart` remains an alternative if config-file behavior changes. | High | Need robust boot-ready detection. |
| Context7 Python subprocess docs | `/python/cpython` | `Popen.communicate(timeout=...)` timeout path must kill then call `communicate()` again; POSIX process groups can be created with `start_new_session` and killed with `os.killpg`. | Private proof runner uses argv list only, `start_new_session=True`, timeout kill group, pipe drain, output caps, and redaction. | High | None. |
| Vercel Grep/code search | Required topics: Firecracker Python wrappers, no-NIC config examples, `/dev/kvm` gates, pytest skip patterns, no-network proofs, workspace sentinel/symlink tests | No Vercel Grep/code-search tool is exposed in this runtime. Google-backed code search attempt returned `403 PERMISSION_DENIED`. | Implementation remains conservative and local-test based; no external wrapper pattern was imported. | Low | Run Vercel Grep externally before sign-off. |
| Firecracker serial/rootfs command-channel design | Derived from Firecracker serial stdout behavior and ARC proof constraints | A proof-only rootfs/init agent can emit bounded `ARC_FC_PROOF key=value` markers for `ip route`, failed `curl`, sentinel read, and symlink escape. This is not a broad command execution channel. | Added parser and init-snippet scaffold. The proof runner consumes markers when present but public microVM execution remains blocked. | Medium | Need a real ARC-owned rootfs/init image to emit these markers on Linux/KVM. |
| Context7 Firecracker docs | `/firecracker-microvm/firecracker` | Firecracker needs an uncompressed Linux kernel plus rootfs; config-file boot needs `boot-source` and root drive, while `network-interfaces` are optional. Common boot args use `console=ttyS0 reboot=k panic=1 pci=off`. | Keep the Firecracker proof runner on config-file boot with no `network-interfaces`; proof marker capture relies on serial/stdout from the guest init. | High | Real serial behavior must still be confirmed on Linux/KVM with the ARC proof rootfs. |
| Firecracker getting-started docs | https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md | `/dev/kvm` read/write is mandatory. Firecracker can boot from `--config-file`; guest network requires explicit TAP/NAT and a network-interface config. Reboot inside the guest shuts down Firecracker. | Host-gated proof harness continues to require Linux, `/dev/kvm`, `firecracker`, kernel, rootfs, and env gates; generated config intentionally omits network interfaces. Proof init ends with `reboot -f || poweroff -f || halt -f`. | High | Host runner still unavailable here. |
| Firecracker rootfs/kernel docs | https://github.com/firecracker-microvm/firecracker/blob/main/docs/rootfs-and-kernel-setup.md | Firecracker rootfs is a filesystem image with at least an init system; final boot executes `/sbin/init` for traditional rootfs. Example ext4 generation uses `mkfs.ext4 -d`; support must match the kernel. | Add a proof artifact generator that writes deterministic init and manifest, and only builds ext4 when explicitly gated with local tools. No silent image downloads. | High | Whether target kernels use `/init`, `/sbin/init`, or `init=` override must be pinned per host artifact. |
| Context7 Linux initramfs/rootfs docs | `/torvalds/linux` | Initramfs executes `/init` if present; otherwise kernel mounts root device and executes normal init path. Initramfs configs include `/dev/console`, BusyBox, `/proc`, `/sys`, and `/init`. | Current artifact writes `/init` into the generated rootfs tree; follow-up may need `/sbin/init` symlink or boot arg `init=/init` for host kernels. | Medium | Need real kernel/rootfs boot evidence. |
| Google web search | Required Firecracker rootfs/init, BusyBox/static rootfs, `mkfs.ext4 -d`, shutdown, `/dev/kvm` CI skip patterns | Tool returned `403 PERMISSION_DENIED Verify your account to continue.` | Recorded blocker; used Context7 and direct official docs URLs instead. | Low | Retry external web search before security sign-off. |
| Phase 62 local code audit | Local source/tests | A dead `_execute_lima()` helper could start Lima outside the public provider even though not referenced by CLI. Proof marker names also needed a stable human-readable contract. | Removed `_execute_lima()` and normalized proof parsing around `no-default-route`, `network-failure`, `sentinel-read`, and `symlink-escape-blocked` while preserving old underscore aliases where safe. | High | Real Firecracker serial/rootfs proof still requires Linux/KVM host evidence. |
| Official Python subprocess docs | https://docs.python.org/3/library/subprocess.html | `Popen.wait()` can deadlock when stdout/stderr pipes fill; `communicate()` avoids deadlock but buffers in memory. `start_new_session` creates a POSIX session suitable for process-group cleanup. | Reworked Lima command probing to drain bounded stdout/stderr readers while waiting and preserve timeout process-group kill semantics. | High | Windows process-tree behavior remains unsupported for this microVM phase. |
| Official Typer testing docs | https://typer.tiangolo.com/tutorial/testing/ | `CliRunner.invoke(app, args, input=...)` is the supported CLI testing pattern, including prompt input and exit-code assertions. | Added CLI regressions for blocked microVM audit events and non-JSON interactive approval denial. | High | None. |
| Official Pydantic model docs | https://docs.pydantic.dev/latest/concepts/models/ | Pydantic v2 `BaseModel` supports `model_dump`, `model_copy`, JSON schema, and immutable/configured models. | Used `model_copy(update=...)` to convert a pre-execution decision into a blocked microVM denial audit without mutating the original decision. | High | None. |
| Firecracker network setup docs | https://github.com/firecracker-microvm/firecracker/blob/main/docs/network-setup.md | Firecracker guest networking requires explicit TAP plus host NAT/bridge setup and guest route configuration. | Kept no-NIC Firecracker proof direction; public execution stays blocked and proof markers now distinguish missing `curl` from network denial. | High | Real no-route/no-curl proof still needs Linux/KVM/rootfs evidence. |
| Lima network docs | https://lima-vm.io/docs/config/network/ | Lima has default/named networking modes; docs do not provide a strict no-network proof for ARC's public sandbox contract. | Doctor keeps macOS Lima as low-security harness and reports public execution blocked even if `limactl` is installed. | High | Direct VZ proof-only path now supplies the strict no-network candidate; public execution still needs provider wiring and hardening. |
| Vercel Grep/code search | Required by user for comparable sandbox command policy and microVM wrapper patterns | No Vercel Grep/code-search tool is exposed in this runtime. | Recorded blocker; implementation remains conservative, local-test based, and does not import external wrapper patterns. | Low | Run Vercel Grep externally before security-signoff. |
| Phase 104 Context7 | Required: Lima/VZ, Apple Virtualization.framework, subprocess/Typer/Pydantic | No Context7 tool is exposed in this runtime. | Recorded blocker; used official Lima docs, Apple docs page, local repo, and subagent research. | Low | Re-run Context7 externally before security-signoff. |
| Phase 104 Vercel Grep/code search | Required: Lima wrappers, Apple VZ wrappers, no-network proof examples, sandbox approval UX | No Vercel Grep/code-search tool is exposed in this runtime. | Recorded blocker; no external wrapper pattern imported. | Low | Re-run Vercel Grep externally before security-signoff. |
| Phase 104 orchestrator subagents | Local subagents | Spawned Lima networking, Lima mounts, repo microVM inspection, docs truth-constraints, and test-strategy agents. | Result converged on blocker-safe implementation: keep public microVM blocked, harden Lima proof template/preflight, document P2 blocker. | Medium | Two subagents returned empty outputs; manual local inspection filled gaps. |
| Lima network docs | https://lima-vm.io/docs/config/network/ | Named networks can be attached, but docs describe default/user/VMNet choices and do not expose a `network: none` or no-NIC key. | `networks: []` remains no-extra-network only; it is not strict network-off evidence. | High | Need upstream no-network support or a direct VZ provider. |
| Lima default user-mode network docs | https://lima-vm.io/docs/config/network/user/ | By default Lima enables user-mode/slirp networking on hard-coded `192.168.5.0/24`; guest can reach host `192.168.5.2` and DNS behavior can fall back to slirp/native nameservers. | ADR-024 P2 remains blocked for Lima; DNS/proxy knobs are hardening only. | High | Whether a future Lima release adds no-network mode. |
| Lima filesystem mounts docs | https://lima-vm.io/docs/config/mount/ | VZ uses virtiofs on macOS; virtiofs requires Lima >=0.14 and macOS >=13.0. reverse-sshfs caveat says compromised guest sshfs may access unexposed host dirs. | Mac proof template pins `vmType: vz`, `mountType: virtiofs`, and mounts only the workspace at `/workspace`; symlink escape proof remains host-gated. | High | Real VZ virtiofs symlink escape result must be collected on host. |
| Lima VZ docs | https://lima-vm.io/docs/config/vmtype/vz/ | VZ uses macOS Virtualization.framework, requires macOS >=13.0, default since Lima v1.0, and does not support cross-arch whole VM. | Doctor/preflight reports Lima/VZ as low-security harness; macOS public execution remains blocked. | High | Direct Apple VZ proof-only path now exists outside Lima; public provider wiring remains separate. |
| Lima create docs | https://lima-vm.io/docs/reference/limactl_create/ | `limactl create --name=local -` supports stdin templates; flags include `--plain`, `--mount-none`, `--containerd none`, `--mount-type`, `--vm-type`. | Disposable lifecycle is feasible, but strict no-network is not. Current harness uses generated template/start/delete; no public execution. | High | Cold-start/image download cost remains high. |
| Lima start docs | https://lima-vm.io/docs/reference/limactl_start/ | `limactl start NAME|FILE.yaml|URL`; `--name` is a create flag available through start when creating from a file. | Harness now starts template files with explicit `--name <instance>` so teardown targets the same instance name instead of Lima choosing/suffixing names. | High | Stale old proof instances may need manual cleanup; no automatic prune added. |
| Apple Virtualization docs | https://developer.apple.com/documentation/virtualization | Apple page required JavaScript in this runtime. | Official Apple API detail unavailable here; do not implement direct VZ provider from incomplete docs. | Low | Re-fetch with browser/docs access before direct VZ work. |
| Phase 104 Lima network refresh | https://lima-vm.io/docs/config/network/ and https://lima-vm.io/docs/config/network/user/ | Lima 2.1.0 docs still describe default user-mode/slirp networking (`192.168.5.0/24`) and named networks, but no documented no-NIC/no-network template key. Local `limactl info` reports `vmTypes` includes `vz`; default template still has hostResolver/proxy/user-mode defaults. | Keep macOS public microVM execution blocked. `networks: []` remains no-extra-named-network hardening, not strict network isolation. | High | Direct Apple VZ proof-only path now exists outside Lima; public provider wiring remains separate. |
| Phase 104 Apple VZ docs refresh | https://developer.apple.com/documentation/virtualization/vzvirtualmachineconfiguration | Apple docs page is JavaScript-only in this runtime; direct API signatures and entitlement/build details were not available. | Do not add a Swift helper from incomplete docs. Document missing capability: direct Apple VZ no-NIC helper/rootfs/command channel. | Low | Need Xcode/macOS API research and a tested Swift helper before macOS strict execution. |
| Phase 105 Firecracker docs refresh | https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md | Firecracker requires Linux KVM, `/dev/kvm` read/write, Firecracker binary, kernel, rootfs. `--config-file` can boot with kernel/rootfs config and optional resources. | Public `MicroVMIsolationProvider.execute()` now delegates only to Linux/Firecracker behind `ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`, `ARC_FC_REAL_EXEC=1`, kernel/rootfs, binary, `/dev/kvm`, and local workspace-image tools. | High | Real proof still requires an eligible Linux/KVM host; this macOS host cannot boot Firecracker. |
| Phase 105 Firecracker network docs refresh | https://github.com/firecracker-microvm/firecracker/blob/main/docs/network-setup.md | Firecracker networking requires explicit TAP and `network-interfaces` config; guest default route/DNS setup is separate guest/host work. | ARC execution config omits `network-interfaces`, creates no TAP/NAT/bridge, and requires guest `ARC_FC_PROOF` markers for no default route plus failed curl/wget before returning command output. | High | Need real guest marker evidence on Linux/KVM. |
| Phase 104-106 Context7 refresh | Required: subprocess, Typer, Pydantic, Lima/VZ, Firecracker, Cloud Hypervisor | No Context7 tool is exposed in this runtime. | Recorded blocker; used official docs/web fetch, local repo inspection, and scoped subagents instead. | Low | Re-run Context7 before security-signoff if the tool becomes available. |
| Phase 104-106 Vercel Grep/code search refresh | Required: sandbox classification, VM wrappers, approval UX, provider-worker orchestration | No Vercel Grep/code-search tool is exposed in this runtime. | Recorded blocker; implementation remains conservative and local-test based. | Low | Run external Vercel Grep before security-signoff. |
| Lima default user-mode network refresh | https://lima-vm.io/docs/config/network/user/ | Lima only enables user-mode networking aka slirp by default, with hard-coded `192.168.5.0/24`, guest `192.168.5.15`, host `192.168.5.2`, and DNS via `192.168.5.3`/host resolver behavior. | Keep Lima as low-security developer harness; `networks: []` is not strict no-network proof. | High | Need direct Apple VZ no-NIC or future Lima no-network mode. |
| Lima VZ refresh | https://lima-vm.io/docs/config/vmtype/vz/ | `vmType: vz` uses macOS Virtualization.framework, requires Lima >= 0.14 and macOS >= 13.0, is default on macOS since Lima v1.0, and does not support cross-arch whole VM. | VZ via Lima is a useful harness but inherits Lima network posture; it does not satisfy strict ARC P2. | High | Direct VZ helper still needed for macOS strict no-network. |
| Lima mount refresh | https://lima-vm.io/docs/config/mount/ | Lima supports reverse-sshfs, 9p, and virtiofs; VZ uses virtiofs on macOS >= 13. reverse-sshfs docs warn compromised guest sshfs may access unexposed host dirs. | Keep workspace-only mount strategy and host-gated symlink/mount proof tests; do not treat mount config as proof without guest evidence. | High | Real VZ/virtiofs symlink and host-path behavior still needs host proof. |
| Apple Virtualization.framework docs refresh | https://developer.apple.com/documentation/virtualization and https://developer.apple.com/documentation/virtualization/vzvirtualmachineconfiguration | Apple docs pages require JavaScript in this runtime, so API details could not be verified from official docs here. | Keep `tools/arc-vz-runner.swift` as scaffold; do not claim direct VZ execution/proof from unavailable docs. | Low | Need browser/Xcode docs access plus compiled runner/kernel/initrd. |
| Firecracker jailer refresh | https://github.com/firecracker-microvm/firecracker/blob/main/docs/jailer.md | Jailer isolates Firecracker with chroot/cgroups/resource limits/env cleanup and forwards Firecracker args; inputs are trusted and operator cleanup remains required. | Keep current direct Firecracker path as host-gated proof; jailer lifecycle is a future hardening step before production-grade claim. | High | Need jailer integration/cleanup tests on Linux/KVM. |
| Cloud Hypervisor quick-start refresh | https://www.cloudhypervisor.org/docs/prologue/quick-start/ | Requires Linux/KVM-capable host kernel; boot paths use firmware or direct kernel/disk and examples configure networking with `--net`. | Cloud Hypervisor remains secondary Linux scaffold; no pivot from Firecracker without separate proof path. | Medium | Need no-`--net` boot proof, command channel, mount proof. |
| Kata Containers docs refresh | https://www.katacontainers.io/docs/ | Kata integrates VM-backed containers with Docker/Kubernetes/containerd and supports multiple hypervisors including Firecracker. | Treat Kata as heavier container-runtime integration, not ARC local CLI P0 microVM default. | Medium | Operational cost and local CLI lifecycle remain unresolved. |
| macOS sandbox-exec refresh | https://keith.github.io/xcode-man-pages/sandbox-exec.1.html | `sandbox-exec` is explicitly deprecated; Apple points developers to App Sandbox for apps. | Do not use Seatbelt/sandbox-exec as ARC CLI sandbox foundation. | High | None for current plan. |
| Phase 104-106 orchestrator prompt | `docs/prompts/phase-104-106-orchestrator.md` | The next-three-phase workflow needs explicit research, subagent, verification, e2e, commit, push, and truth-label gates. | Added a reusable prompt that can coordinate up to 8 subagents while preserving blocked/host-unproven/live-smoke-only labels. | High | Real host proof still requires external runtime/keys. |
| Post-Phase-106 Context7 gate | Required: subprocess, Typer, Pydantic, Firecracker, Lima/VZ | No Context7 tool is exposed in this runtime. Official docs were fetched instead for the narrow audit-contract slice. | Do not import new wrapper patterns or claim external corpus validation. Keep changes local-test based. | Low | Re-run Context7 before security-signoff if the tool becomes available. |
| Post-Phase-106 Vercel Grep/code search gate | Required: microVM wrapper/proof patterns and policy approval UX | No Vercel Grep/code-search tool is exposed in this runtime. | Record blocker; do not infer broad proof from local fake-runner tests. | Low | Run external Vercel Grep before security-signoff. |
| Official Python subprocess docs | https://docs.python.org/3/library/subprocess.html | Python docs prefer argv sequences with `shell=False`, warn about `shell=True`, document `start_new_session`, timeout cleanup, and pipe deadlock risk. | Keep existing subprocess/process-group/bounded-reader posture unchanged; no unsafe shell execution added. | High | None for this slice. |
| Official Typer testing docs | https://typer.tiangolo.com/tutorial/testing/ | `CliRunner.invoke(app, [...])` is the documented CLI testing pattern. | Added CLI audit-schema regression with `CliRunner`; no real VM/runtime required. | High | None for this slice. |
| Official Pydantic model docs | https://docs.pydantic.dev/latest/concepts/models/ | Pydantic models support `BaseModel`, `Field(default_factory=...)`, `model_dump`, and structured validation/serialization. | Added optional `IsolationResult.metadata` via `Field(default_factory=dict)` to carry microVM audit contract metadata without changing provider result fields. | High | None for this slice. |
| Firecracker getting-started docs | https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md | Firecracker requires Linux KVM and `/dev/kvm` read/write; `--config-file` can boot from kernel/rootfs config and optional resources. | P7 changes remain audit-schema only; Linux/Firecracker execution remains host-unproven until real KVM boot proof runs. | High | Need eligible Linux/KVM host. |
| Lima network docs | https://lima-vm.io/docs/config/network/ | Lima docs describe default/named network choices and no documented strict no-network template key. | Preserve macOS Lima/VZ as low-security harness only; no macOS public execution claim. | High | Direct Apple VZ proof-only path now exists; public provider wiring remains unresolved. |
| Phase 107 Context7 gate | Required: Python subprocess, Typer, Pydantic, MCP stdio, Firecracker requirements | No Context7 tool is exposed in this runtime. | Recorded blocker; used official docs via web fetch and local repo inspection. | Low | Re-run Context7 externally before security sign-off. |
| Phase 107 Vercel Grep/code search gate | Required: sandbox approval UX, MCP sandbox subprocess patterns, Firecracker/Lima/Cloud Hypervisor wrappers | No Vercel Grep/code-search tool is exposed in this runtime. | Recorded blocker; no external code pattern imported. | Low | Run Vercel Grep externally before security sign-off. |
| Official Python subprocess docs | https://docs.python.org/3/library/subprocess.html | `Popen` should receive argv sequences with `shell=False`; `start_new_session=True` creates a POSIX session; timeout cleanup must kill and drain pipes; `wait()` can deadlock with full pipes. | MCP workbench launch now uses argv, filtered env, workspace cwd, process group cleanup, bounded stderr, and sandbox audit. | High | Windows process-tree semantics skipped. |
| MCP stdio transport spec | https://modelcontextprotocol.io/specification/2025-06-18/basic/transports | MCP stdio clients launch the server as a subprocess, exchange JSON-RPC over stdin/stdout, and may capture stderr logs. | MCP workbench subprocess launch is now treated as sandbox-relevant command execution and policy-gated before launch. | High | Some MCP servers need install/network; users must approve/policy-enable explicitly. |
| Official Typer testing docs | https://typer.tiangolo.com/tutorial/testing/ | `CliRunner.invoke(app, args, input=...)` is the documented CLI regression style. | Added CLI regressions for MCP denials, sandbox audit, and plan approval parity. | High | None. |
| Official Pydantic serialization docs | https://docs.pydantic.dev/latest/concepts/serialization/ | `model_dump(mode="json")` and `model_dump_json()` provide stable JSON-compatible output. | Kept sandbox/plan/MCP result envelopes and audit payloads stable through model dumps. | High | None. |
| Firecracker getting started | https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md | Firecracker requires Linux, supported arch, `/dev/kvm` read/write, binary, kernel image, and rootfs. | Current macOS host cannot prove Firecracker execution; docs now say Linux/Firecracker gated scaffold, host-unproven. | High | Need Linux/KVM host with kernel/rootfs and explicit gates. |
| Lima docs | https://lima-vm.io/docs/ and https://lima-vm.io/docs/config/vmtype/vz/ | Lima launches Linux VMs on macOS; VZ uses Apple Virtualization.framework and requires macOS >= 13, but Lima networking is present by default. | Keep macOS Lima path as low-security harness/template only; no strict public execution claim from Lima. | High | Direct Apple VZ proof-only path now exists; public provider wiring remains unresolved. |
| Cloud Hypervisor quick start | https://www.cloudhypervisor.org/docs/prologue/quick-start/ | Cloud Hypervisor requires KVM-capable Linux host kernel; examples add networking via explicit `--net`. | Keep Cloud Hypervisor secondary Linux scaffold/preflight only. | Medium | Need separate no-`--net` boot proof and workspace sharing proof. |
| Kata Containers docs | https://katacontainers.io/docs/ | Kata integrates VM-backed containers with Docker/Kubernetes/containerd and hypervisors such as Firecracker. | Treat Kata as heavier future container-runtime integration, not ARC local CLI P0. | Medium | Operational overhead for local CLI remains open. |
| macOS sandbox-exec man page | https://keith.github.io/xcode-man-pages/sandbox-exec.1.html | `sandbox-exec` is deprecated; Apple points app developers to App Sandbox. | Do not use Seatbelt/sandbox-exec as ARC CLI sandbox foundation. | High | None. |
| Phase 107 local host check | `uname -a`; `/dev/kvm`; `command -v firecracker jailer cloud-hypervisor limactl`; `limactl --version`; `limactl info`; `limactl list --json` | Host is Darwin arm64; `/dev/kvm` missing; Firecracker/jailer/Cloud Hypervisor missing; Lima 2.1.0 installed with VZ support and stopped old smoke instances. | Live Firecracker proof is blocked on this host. No Linux VM setup can expose KVM from macOS/VZ reliably enough for Firecracker proof; do not claim microVM execution. | High | Need eligible Linux/KVM machine or remote host credentials. |
| Phase 108 Context7 gate | Required: Python subprocess, Typer, Pydantic | Tool is present but returns `Invalid API key. Please check your API key. API keys should start with 'ctx7sk' prefix.` for all three required docs lookups. | Recorded blocker; used official docs, local source, and code search instead. No Context7-derived implementation claim. | Low | Configure a valid Context7 API key before security sign-off. |
| Official Python subprocess docs | https://docs.python.org/3/library/subprocess.html | `Popen` should use argv sequences with `shell=False`; `start_new_session` creates a POSIX session; `wait()` with pipes can deadlock when buffers fill; timeout cleanup requires kill and pipe drain. `cwd` and `env` are explicit child-process boundaries. | Keep bounded pipe readers and process-group timeout kill. Tightened `SubprocessIsolationProvider` so a configured `workspace_root` becomes the default execution cwd when callers omit `cwd`, avoiding parent-cwd inheritance outside the workspace. | High | Windows process-tree semantics remain unsupported/skipped. |
| Official Typer testing docs | https://typer.tiangolo.com/tutorial/testing/ | `CliRunner.invoke(app, args, input=...)` is the documented pattern for CLI commands and prompts. | Continue testing sandbox/policy command decisions through `CliRunner`; no live network/runtime needed. | High | None. |
| Official Pydantic model docs | https://docs.pydantic.dev/latest/concepts/models/ | `BaseModel`, `ConfigDict`, `Field(default_factory=...)`, `model_dump`, and `model_copy` are stable v2 patterns for typed envelopes. | Existing `SandboxPolicy`, `SandboxDecision`, `SandboxResult`, and `IsolationResult.metadata` remain appropriate; no model change needed this slice. | High | None. |
| GitHub code search — Codex sandbox policy | `openai/codex`, query `sandbox policy` | Codex separates approval policy, sandbox policy, permission profiles, network policy, and command execution. Some generated SDK text explicitly distinguishes shell command strings and sandbox policy scope. | ARC should keep classification/decision separate from execution, keep list-argv subprocess execution by default, and avoid claiming OpenCode/Codex parity or shell-string equivalence. | Medium | Need deeper source review before parity claims. |
| GitHub code search — Lima wrapper lifecycle | Query `limactl start --tty=false` | Public Lima scripts commonly use `limactl start --tty=false`, explicit instance names, `limactl shell`, and `limactl delete -f` cleanup. | Existing Lima harness lifecycle shape is consistent, but remains low-security/host-gated because lifecycle examples do not prove strict no-network or mount isolation. | Medium | Real host Lima mount/symlink evidence still needed. |
| GitHub code search — approval UX | Query `status !== 'approval_required'` | Approval-gated tools often return structured `approval_required` status before a separate approval action executes. | ARC's `SandboxDecision.approval_required` plus `--ask`/approval-token flow is a reasonable UX pattern; destructive/privileged remain unapprovable. | Medium | No direct ARC-compatible policy schema found. |
| Firecracker getting-started docs | https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md | Firecracker requires Linux, supported arch, KVM, `/dev/kvm` read/write, Firecracker binary, kernel image, and rootfs. `--config-file` can boot from a JSON config. | Linux/Firecracker scaffold remains host-unproven on this macOS host; real execution still requires explicit gates plus kernel/rootfs and proof markers. | High | Need eligible Linux/KVM host. |
| Firecracker network setup docs | https://github.com/firecracker-microvm/firecracker/blob/main/docs/network-setup.md | Guest networking requires TAP creation, host routing/NAT/bridge/namespace setup, Firecracker `network-interfaces`, and guest route/DNS configuration. | A no-NIC config is still the strict no-network candidate; ARC must not set up TAP/NAT/bridge or accept command output without guest no-default-route and failed-network markers. | High | Need live guest proof. |
| Lima default user-mode network docs | https://lima-vm.io/docs/config/network/user/ | Lima enables user-mode slirp by default on `192.168.5.0/24`, with guest/host/DNS addresses. | macOS Lima remains low-security/network-present harness only; strict public microVM execution remains blocked. | High | Direct Apple VZ proof-only path now exists; future Lima no-network support would be a separate option. |
| Cloud Hypervisor quick start | https://www.cloudhypervisor.org/docs/prologue/quick-start/ | Cloud Hypervisor needs KVM-capable Linux kernel; examples boot with kernel/disk and add networking through explicit `--net` options. | Keep Cloud Hypervisor as secondary Linux scaffold/preflight; no-`--net` plan remains design-only until boot, command channel, and mount proof exist. | Medium | Need direct no-`--net` host proof. |
| macOS sandbox-exec man page | https://keith.github.io/xcode-man-pages/sandbox-exec.1.html | `sandbox-exec` is deprecated and Apple points app developers to App Sandbox. | Do not use Seatbelt/sandbox-exec as ARC CLI sandbox foundation. | High | None. |
| Phase 108 Apple VZ docs | https://developer.apple.com/documentation/virtualization/vzvirtualmachineconfiguration and `vzvirtioblockdeviceconfiguration` | Apple docs pages still require JavaScript in this runtime, so official API detail could not be fully verified here. | Keep direct VZ path proof-only; do not claim public/production behavior from JS-blocked docs. | Low | Re-fetch with browser/Xcode docs before enabling public execution. |
| GitHub code search — Apple VZ config | Queries `VZVirtualMachineConfiguration()`, `VZVirtioNetworkDeviceConfiguration`, `networkDevices = []` | Public Swift VZ examples commonly instantiate `VZVirtualMachineConfiguration`, add NAT/bridged networking through `VZVirtioNetworkDeviceConfiguration`, and at least two examples show empty `networkDevices`/`networkDevices = []` paths. | Existing `tools/arc-vz-runner.swift` source scaffold with `config.networkDevices = []` was a plausible no-NIC candidate and has now passed one gated host proof with local artifacts. | Medium | Need official docs, durable artifact provenance, and repeatable CI/host-runner proof before public execution. |
| Phase 108 VZ local scaffold audit | `vz_provider.py`, `test_vz_proof.py`, `tools/arc-vz-runner.swift` | Existing VZ preflight could report `ready` through PyObjC availability even though no PyObjC execution path exists; proof field wording could be misread as actual no-network proof. | VZ preflight now requires executable `ARC_VZ_RUNNER`, readable `ARC_VZ_KERNEL`, readable `ARC_VZ_INITRD`, and `ARC_VZ_PROOF=1`; PyObjC is reported only as unavailable/available with `pyobjc_runner_implemented=false`; `strict_no_network_proof` remains `not_proven` for preflight because proof requires a gated run. | High | Real boot proof now exists once on this host; repeatability/CI/product wiring remain open. |
| VZ host proof | `cd python && ARC_VZ_PROOF=1 ARC_VZ_RUNNER=/var/folders/dp/1fh07k_922j5qk7xfncn1zv40000gn/T/opencode/arc-vz-runner ARC_VZ_KERNEL=/var/folders/dp/1fh07k_922j5qk7xfncn1zv40000gn/T/opencode/arc-vz-proof/debian-linux ARC_VZ_INITRD=/var/folders/dp/1fh07k_922j5qk7xfncn1zv40000gn/T/opencode/arc-vz-proof/arc-vz-proof-initrd.gz ARC_VZ_TIMEOUT_SECONDS=45 uv run pytest tests/isolation/test_vz_proof.py -v` | On macOS 26.4 arm64, the compiled/signed Swift runner booted a VZ Linux guest with `networkDevices=[]`; guest markers proved boot, no guest ethernet, no default route, network tool available, network probe failure, workspace mount, sentinel read, symlink escape blocked, command result markers, and teardown ok. | Direct VZ is now a real opt-in host-proof path, not just source scaffold. Keep public `MicroVMIsolationProvider.execute()` on macOS blocked until product wiring, audit, artifact provenance, timeout/SIGINT cleanup, output caps, and CI/host-runner policy are implemented. | High | Need durable runner/artifact generation, opt-in CI host, public execution contract updates, and broader failure-mode tests before enabling macOS microVM execution. |

## Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| P0 execution backend | Hardened subprocess provider | MicroVM execution, container execution | Existing abstraction exists; lowest safe incremental change; no broad runtime execution without gates. | `python/src/agent_runtime_cockpit/isolation/subprocess.py` | High |
| Subprocess default cwd | Use `workspace_root` as the execution cwd when a caller omits `cwd` | Inherit parent process cwd; require every caller to pass `cwd` | Provider-level fail-closed behavior prevents direct API callers from accidentally executing outside the configured workspace. CLI already passes cwd, but the provider boundary should not depend on that. | `python/src/agent_runtime_cockpit/isolation/subprocess.py`, `python/tests/isolation/test_isolation.py` | High |
| MicroVM phase | Doctor/preflight only | Real Firecracker/Lima runs | Real execution needs images, mounts, network controls, cleanup, opt-in integration tests. | `python/src/agent_runtime_cockpit/isolation/microvm.py` | High |
| macOS lightweight VM | Lima/VZ as low-security harness only | Docker Desktop, deprecated `sandbox-exec`, public strict microVM | Lima maps to Apple Virtualization.framework but currently exposes user-mode networking; it cannot satisfy strict P2. | `docs/adr/ADR-024-microvm-public-execution-contract.md`, `python/src/agent_runtime_cockpit/security/sandbox.py` | High |
| Direct VZ preflight truth | Treat VZ no-NIC as `ready_to_attempt` only; never mark strict proof as ready before boot evidence | Let PyObjC availability imply readiness; mark `strict_no_network_proof=ready` when gates exist | Prevents doctor output from implying proof. Only a compiled runner plus readable kernel/initrd and explicit gate can make preflight ready, and even then proof remains `not_proven` until `run_proof()` boots and verifies guest evidence. | `python/src/agent_runtime_cockpit/isolation/vz_provider.py`, `python/tests/isolation/test_vz_proof.py` | High |
| Direct VZ host proof | Keep proof-only `VZNoNetworkProof.run_proof()` gated by `ARC_VZ_PROOF=1`; do not wire public macOS microVM execution yet | Claim proof from config only; wire `arc sandbox run --provider microvm` on macOS immediately; use Lima as strict substitute | The host proof now boots and tears down a no-NIC VZ guest with guest markers, but the public sandbox needs product-grade lifecycle, artifact, audit, timeout/SIGINT, output-cap, and CI policy work before execution can be exposed. | `python/src/agent_runtime_cockpit/isolation/vz_provider.py`, `python/tests/isolation/test_vz_proof.py`, `tools/arc-vz-runner.swift`, docs | High |
| Linux lightweight VM | Firecracker primary, Cloud Hypervisor secondary | Kata as P0 | Firecracker/Cloud Hypervisor are direct hypervisors; Kata is container-runtime integration. | `python/src/agent_runtime_cockpit/security/sandbox.py` | Medium |
| Firecracker strict no-network proof | Add no-NIC design/preflight config + host-gated test scaffold; do not wire public execute | Immediate public microVM execution; Cloud Hypervisor pivot | Current host lacks Linux/KVM/rootfs. Config omission can be tested safely now; real proof requires explicit host gates. | `python/src/agent_runtime_cockpit/isolation/microvm.py`, `python/tests/isolation/test_firecracker_smoke.py` | High |
| Firecracker/Cloud Hypervisor proof path | Add shared Linux/KVM host-gated proof-plan surface; keep public provider blocked | Lima strict path; Docker fallback; public microVM execution | Lima is low-security/network-present. Firecracker/Cloud Hypervisor can omit NIC config by construction but still need real KVM boot/run/teardown proof. | `python/src/agent_runtime_cockpit/isolation/microvm.py`, `python/src/agent_runtime_cockpit/security/sandbox.py`, `python/tests/isolation/test_firecracker_smoke.py`, `python/tests/isolation/test_microvm_preflight.py` | High |
| Firecracker proof runner | Private host-gated proof harness with direct Firecracker config-file start; no public provider wiring | Public `arc sandbox run --provider microvm`; Firecracker jailer path; broad arbitrary guest exec | Gives ARC a real Linux/KVM lifecycle/config/teardown proof path while preserving ADR-024 public block. Guest command channel remains explicit blocker. | `python/src/agent_runtime_cockpit/isolation/microvm.py`, `python/tests/isolation/test_firecracker_smoke.py` | Medium |
| Firecracker guest proof channel | Proof-only serial/rootfs init markers (`ARC_FC_PROOF no-default-route`, `network-failure`, `sentinel-read`, `symlink-escape-blocked`) | SSH, arbitrary argv agent, host network channel, unstable underscore-only names | Avoids broad runtime execution and gives the host-gated proof a stable marker contract. Parser keeps safe legacy aliases, but generated init uses hyphenated names. | `python/src/agent_runtime_cockpit/isolation/microvm.py`, `python/tests/isolation/test_firecracker_smoke.py` | Medium |
| Firecracker proof rootfs/init artifact | Deterministic init + manifest generator; optional gated ext4 build with local BusyBox/`mkfs.ext4 -d` only | Download Firecracker CI images; privileged mount/chroot build; public execution gate | Provides a reviewable proof artifact path without silent downloads or broad guest command execution. Normal CI only tests init/manifest and missing-tool blockers. | `python/src/agent_runtime_cockpit/isolation/microvm.py`, `python/tests/isolation/test_firecracker_smoke.py` | Medium |
| Policy UX | `arc sandbox run`, `arc policy explain` | Reuse existing `isolation` command only | User-facing Codex/Claude-style policy explanation and execution are distinct from provider diagnostics. | `python/src/agent_runtime_cockpit/cli/sandbox.py` | High |
| Adversarial command policy | Conservative deny matrix plus path-intent validation before subprocess execution | Shell/runtime monitoring, syscall sandbox, broad AST evaluator | P0 must not fake syscall containment; deny known risky interpreters/subcommands and block write/read path escapes before execution. | `python/src/agent_runtime_cockpit/security/sandbox.py`, `python/src/agent_runtime_cockpit/cli/sandbox.py` | Medium |
| HMAC audit durability | Parent creation, advisory file lock where available, append flush + `os.fsync`, partial-line verification failure | Atomic rename per append, SQLite ledger, external audit daemon | Preserve existing JSONL chain format while hardening local append semantics. | `python/src/agent_runtime_cockpit/audit/hmac_chain.py` | Medium |
| Supervisor timeout | `asyncio.wait_for(request.timeout_seconds)` around executor callback | Leave cooperative, runtime-specific cancellation only | Central terminal failure prevents active-run leaks when executors hang. | `python/src/agent_runtime_cockpit/orchestration/supervisor.py` | High |
| MicroVM public run attempts | Persist `SANDBOX_DENIED` audit for `arc sandbox run --provider microvm`; keep API error response | Silent blocked error without audit | Blocked public microVM attempts are security-relevant and need traceability without claiming execution. | `python/src/agent_runtime_cockpit/cli/sandbox.py`, `python/tests/test_cli_sandbox.py` | High |
| MicroVM doctor truth fields | Always emit `public_execution_enabled=false`, `public_execution_status=blocked`; keep preflight status separate | Use `status=ready` alone; hide preflight readiness | Prevents `ready` from being misread as public execution readiness while still surfacing Linux runtime preflight data. | `python/src/agent_runtime_cockpit/security/sandbox.py`, `python/src/agent_runtime_cockpit/isolation/microvm.py` | High |
| Dynamic unknown commands | Deny unknown shell/interpreter forms before interactive approval | Allow `--ask`/token approval for all unknown commands | Static policy cannot prove workspace write bounds for shell/interpreter code; false approval could write outside workspace. | `python/src/agent_runtime_cockpit/security/sandbox.py`, `python/tests/test_cli_sandbox.py` | High |
| Write path intents | Validate write-output paths across classifications | Validate only `writes_workspace` commands | Policy-enabled network/install commands with output flags can write outside workspace unless checked independently. | `python/src/agent_runtime_cockpit/security/sandbox.py`, `python/tests/test_cli_sandbox.py` | High |
| Firecracker proof markers | Require `curl-available` and `workspace-mount-proven` markers before proof success | Treat failed curl/missing sentinel as proof | Missing guest tools or absent workspace mount must not count as network/workspace isolation proof. | `python/src/agent_runtime_cockpit/isolation/microvm.py`, `python/tests/isolation/test_firecracker_smoke.py` | High |
| Phase 104 macOS path | Keep Lima as low-security proof harness; do not wire public execution | Claim Lima strict no-network; use guest firewall/route deletion as P2; direct Apple VZ provider now | Lima docs prove default slirp/user-mode networking and no documented no-network key. Guest-level denial is not strong enough for ADR-024 P2. | `python/src/agent_runtime_cockpit/security/sandbox.py`, `python/src/agent_runtime_cockpit/isolation/microvm.py`, `python/tests/isolation/test_microvm_preflight.py`, docs | High |
| Phase 105 Linux execution path | Wire Linux/Firecracker execution behind dual public/integration gates plus real host gates; keep macOS blocked | Keep permanent `NotImplementedError`; claim proof from fake runner; use Lima as fallback | Firecracker can be configured no-NIC by construction, and public execution can fail closed unless guest proof/result markers are present. Tests remain skipped off Linux/KVM. | `python/src/agent_runtime_cockpit/isolation/microvm.py`, `python/src/agent_runtime_cockpit/cli/sandbox.py`, `python/tests/isolation/test_firecracker_smoke.py`, `python/tests/isolation/test_microvm_truth_guard.py`, docs | Medium |
| Phase 104-106 orchestration | Dedicated next-three prompt with research/execute/test/repair/e2e/commit/push gates and up to 8 subagents | Rely on generic template only; skip commit/e2e gates; merge all phases into one vague task | The user requested an executable workflow for the next three phases. A concrete prompt prevents overclaiming Phase 104/105 while still letting Phase 106 continue with gated/live-smoke evidence. | `docs/prompts/phase-104-106-orchestrator.md`, `docs/research/sandbox-and-microvm.md`, `docs/roadmap.md`, `docs/phases.md` | High |
| Post-Phase-106 P7 audit contract | Add ADR-024 v1 audit fields to microVM blocked-run, harness, and Linux/Firecracker result audit paths while retaining legacy event fields | Replace legacy `MICROVM_*`/`SANDBOX_*` events; wait for host proof | The safe local gap was schema readiness, not real VM execution. Additive fields make blocked/host-gated paths auditable without claiming execution proof. | `python/src/agent_runtime_cockpit/security/sandbox.py`, `python/src/agent_runtime_cockpit/cli/sandbox.py`, `python/src/agent_runtime_cockpit/isolation/base.py`, `python/src/agent_runtime_cockpit/isolation/microvm.py`, tests, docs | High |

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
- subprocess env allowlist, secret-key stripping, workspace cwd guard, `workspace_root` default cwd when `cwd` is omitted, process-group timeout kill, output caps, JSON result, audit payloads
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
- direct Apple VZ no-NIC proof path exists (`tools/arc-vz-runner.swift` plus `VZNoNetworkProof.run_proof()`); on this macOS 26.4 arm64 host, the gated proof passed with a compiled/signed runner, ARM64 kernel/initrd, `networkDevices=[]`, guest no-ethernet/no-default-route/network-failure markers, workspace sentinel/symlink markers, command result markers, and teardown ok. Doctor/preflight still reports `strict_no_network_proof=not_proven` because preflight alone is not proof; proof is produced only by the gated run.
- macOS Lima preflight now also reports ADR-024 P2 as `blocked`, explicit P2 blockers, `guest_network_default=present_by_lima_slirp`, workspace mount strategy, host-gated mount escape proof posture, and template-hardening knobs.
- sandbox audit still writes SHA256 chain/raw events, includes `audit_id`, best-effort mirrors a typed local/recent `sandbox_command` event to `.arc/events/event-log.jsonl`, and best-effort mirrors to the keyed audit store when an audit key exists
- sandbox audit now has nested query aliases (`arc sandbox audit list/show/verify`) while flat commands remain compatible; malformed raw event lines degrade list output instead of crashing
- keyed audit append creates parents, locks where portable, writes canonical JSON, flushes and fsyncs, and verification reports partial trailing lines
- supervisor executor callbacks now have a central timeout wrapper that emits terminal `RUN_FAILED`, autopsy, receipt, and clears active state
- path-intent extraction covers more common output/input switches (`--output`, `--outfile`, `--dest`, `--files-from`, `of=`), plus simple `cp`/`mv` destination and archive-output suffixes
- public `MicroVMIsolationProvider.execute()` has a Linux/Firecracker-only gated scaffold behind `ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`, `ARC_FC_REAL_EXEC=1`, Linux, `/dev/kvm`, `firecracker`, kernel/rootfs env vars, and local `mkfs.ext4`/`truncate` workspace snapshot tools. It is host-unproven and still fails closed unless guest proof markers show no default route, failed network probe, workspace sentinel readable, symlink escape blocked, and command result markers are present.
- Lima/Firecracker harness attempts emit persisted `MICROVM_COMMAND`/`MICROVM_DENIED` sandbox audit events with `public_execution_enabled=false`
- microVM blocked-run, internal harness, and Linux/Firecracker result audit paths now include additive ADR-024 v1 fields: `event=sandbox.microvm.run`, `version`, `microvm_provider`, `platform`, `lifecycle`, `lifecycle_errors`, `teardown_status`, `network_proof_passed`, `start_ts`, `end_ts`, `duration_ms`, and `gate`. Legacy `SANDBOX_*`/`MICROVM_*` fields are retained.
- Private Firecracker proof runner scaffold gates on Linux, `/dev/kvm` rw, `firecracker`, `ARC_MICROVM_INTEGRATION=1`, `ARC_FC_REAL_EXEC=1`, `ARC_FIRECRACKER_KERNEL`, and `ARC_FIRECRACKER_ROOTFS`; fake-runner tests cover config/lifecycle/audit shape, but no live Firecracker process was started here.
- Firecracker execution artifact tooling can generate `arc-fc-exec-init.sh` and, when `ARC_FC_BUILD_EXEC_ROOTFS=1` plus local tools are present, `arc-fc-exec-rootfs.ext4`. This rootfs/init contract emits `ARC_FC_PROOF` and `ARC_FC_RESULT` serial markers required before any future Linux/Firecracker execution proof can be trusted.
- Firecracker guest proof marker parser and proof-only init snippet exist for stable `ARC_FC_PROOF no-default-route`, `network-failure`, `sentinel-read`, and `symlink-escape-blocked` markers. The parser accepts legacy underscore aliases where safe.
- Phase 68 hardens the private proof runner so proof success requires both network and workspace markers and temporary sentinel/symlink files are cleaned after the attempt.
- Firecracker proof rootfs/init artifact tooling exists: `generate_firecracker_proof_artifacts()` writes `arc-fc-proof-init.sh` and `rootfs-manifest.json`; optional ext4 build is opt-in via `ARC_FC_BUILD_PROOF_ROOTFS=1` and local `busybox`, `mkfs.ext4`, and `truncate` only. The scaffold now includes `/init`, `/sbin/init`, `/dev/console`, `/dev/null`, and proc/sysfs mount checks in manifest validation.
- Firecracker proof manifests now include generator/marker contract metadata, host OS/arch, proof commands, no-network metadata, rootfs size, and tool paths. Static validation rejects unsafe init content and network-interface metadata.
- Sandbox classifier/path-intent hardening now denies read-only relative path escapes and adds regressions for shell/Git/package/Python write variants. This remains static policy enforcement, not a syscall sandbox.
- Phase 94-96 sandbox/security continuation adds microVM blocked-run denial audit events, public-execution truth fields in doctor output, write-path validation across all classifications, denial of dynamic unknown shell/interpreter approvals, Lima bounded-output drain, and Firecracker proof marker truth guards for `curl-available` and `workspace-mount-proven`.
- Phase 107 hardening routes MCP workbench `inspect` and `session-start` user commands through workspace trust, sandbox policy, path validation, filtered env, workspace cwd, process-group cleanup, and sandbox audit.
- Phase 107 hardening emits sandbox audit for `validate_command_paths()` denials and `--stream-json` final results.
- Phase 107 hardening aligns `arc plan apply` approval semantics: `network`, `install`, and `unknown` need policy allowance or matching sandbox approval token; generic plan/direct confirmation is not enough.
- Phase 107 hardening marks `NoneIsolationProvider` diagnostics-only and adds env filtering, secret stripping, process-group timeout kill, output caps, cwd guard when a workspace root is provided, and output redaction.

Design-only now:
- container provider as production fallback
- macOS public microVM execution
- Linux/Firecracker execution on this macOS host; code path exists but real boot proof requires eligible Linux/KVM host
- real Firecracker boot/no-default-route/curl-fails proof
- Real Firecracker guest proof remains blocked on this macOS host; ARC now owns an exec init/rootfs artifact generator, but the rootfs has not been booted on Linux/KVM here.
- Firecracker proof rootfs/init artifact ext4 build remains unproven on this macOS host; normal CI validates manifest/init generation, boot-entrypoint/device metadata, proc/sysfs mount checks, and missing-tool blockers only.
- Firecracker proof markers now explicitly fail proof when guest `curl` is missing or workspace mount proof is absent; this prevents false-positive network/workspace proof but still does not prove real boot on this host.
- real Cloud Hypervisor boot/no-default-route/curl-fails proof
- Lima disposable VM session templates as low-security harness only
- Phase 104 direct Apple VZ strict no-network host proof passed behind `ARC_VZ_PROOF=1`, but macOS public microVM execution remains design-only/blocked. Lima remains low-security/network-present because default user-mode/slirp networking is documented and no no-network template key was found.
- Firecracker jailer/rootfs/kernel lifecycle
- Cloud Hypervisor kernel/disk/workspace-mount lifecycle

Blocked:
- Google web search tool requires account verification.
- Context7 is blocked in this environment by invalid API key (`ctx7sk` key required).
- Vercel/GitHub code search is available but partial; several wrapper/classification queries returned no hits, so no broad external corpus sign-off is claimed.
- macOS public microVM execution requires wiring the direct VZ proof path into the sandbox provider with stable artifacts, audit, output caps, timeout/SIGINT cleanup, policy gates, and opt-in host CI.
- macOS VZ proof assets are local host artifacts, not distributed or provenance-pinned yet.
- Linux Firecracker execution proof requires a Linux/KVM host with `/dev/kvm` read/write, `firecracker`, compatible kernel, ARC exec rootfs, and explicit env gates.

## Phase 37.6 MicroVM Execution Blocker Detail

Status: macOS direct VZ strict no-network host proof passed once behind `ARC_VZ_PROOF=1`; macOS public microVM execution remains blocked. Linux/Firecracker gated scaffold exists behind explicit host gates, but no real Firecracker boot proof has run on this macOS host.

Current design-proof harness:

- `arc sandbox microvm-plan --json --provider lima -- <cmd...>` renders a non-executing Lima run plan.
- `arc sandbox microvm-plan --json --provider firecracker -- <cmd...>` renders a non-executing Firecracker run plan.
- Plans include lifecycle, workspace mount, network-default-deny, run, teardown, and blocker fields.
- Plan generation does not call `limactl`, `firecracker`, `cloud-hypervisor`, or `jailer` and does not create VMs.
- `execution_enabled` in plans remains `false`; plans are still non-executing.

Current opt-in Lima harness:

- `LimaIntegrationHarness` exists as an internal helper only; it is not wired to `arc sandbox run --provider microvm`.
- It requires `ARC_MICROVM_INTEGRATION=1`, macOS, and `limactl` by default; unit tests pass `require_gate=False` with a fake runner.
- Fake-runner tests prove lifecycle order, mandatory network proof before user argv, no user command after failed network proof, and `limactl delete -f` teardown after start failure.
- `proof_mode="mount"` can bypass only the known-failed Lima network proof so developers can collect `/workspace` mount/symlink evidence. This is Lima low-security developer harness behavior, not strict microVM sandbox execution.
- Host-gated symlink proof now tests whether `/workspace` symlinks can read host paths; if readable, Lima P5 is permanently blocked for strict sandbox use.

### Rootfs/Kernel Lifecycle
- Firecracker needs a kernel vmlinux binary and a rootfs image. ARC does not download images at command runtime.
- `arc sandbox firecracker-artifacts --exec-rootfs --output <dir> --json` writes `arc-fc-exec-init.sh`; with `ARC_FC_BUILD_EXEC_ROOTFS=1` and local `busybox`, `mkfs.ext4`, and `truncate`, it builds `arc-fc-exec-rootfs.ext4`.
- Lima VM templates exist as rendered YAML and internal host-gated harnesses only. Lima is not wired to public strict execution.

- Firecracker: Linux gated scaffold creates a per-run read-only ext4 snapshot of the workspace and attaches it as a second block drive. Host symlinks are not copied into that snapshot; a proof symlink marker is added and must be unreadable in the guest.
- Lima: host-mounted directories are shared via `mounts` in template YAML. `~` and sensitive host paths must be excluded.
- The Firecracker workspace snapshot is read-only in the guest; write-back semantics are not implemented.

### Network-Off Proof
- No public provider proves strict guest no-network access on this macOS host.
- Direct Apple VZ proof-only path proved strict guest no-network once on this macOS host behind `ARC_VZ_PROOF=1`; this is not public provider execution.
- Firecracker: Linux gated scaffold emits a config with no `network-interfaces`, creates no TAP/NAT/bridge, and requires guest `ARC_FC_PROOF no-default-route=1`, `curl-available=1`, and `network-failure=1` before any future command output can be trusted.
- Lima: default slirp/user-mode networking is documented; `user-v2` is also user-mode networking. ARC treats Lima as low-security/network-present, not strict P2 evidence.
- Proposed strict proof: boot Firecracker/Cloud Hypervisor without guest NIC/default route, then verify `ip route` has no default route and `curl --connect-timeout 1 http://example.com` fails before user argv.
- Current strict proof status: direct macOS VZ proof-only path passed once; Linux/Firecracker remains scaffold/host-unproven. No real Firecracker boot was executed on this macOS host.

### Teardown Guarantees
- Firecracker: VM is destroyed by terminating the Firecracker process group in normal, error, timeout, and finally paths; temp jail/config/workspace image live in a per-run temporary directory.
- Lima: `limactl delete -f` after run. No cleanup on host crash/reboot.
- Host crash cleanup is not proven.

### Integration Gate
- Tests exist at `python/tests/isolation/test_microvm_preflight.py` — 4 tests covering all 4 preflight states.
- A skeleton integration test exists at `python/tests/test_cli_sandbox.py::test_microvm_integration_skeleton_doctor_only`, gated by `ARC_MICROVM_INTEGRATION=1`.
- Design-proof plan tests cover Lima and Firecracker plan shape and assert CLI plan generation does not run subprocess probes.
- CI does not set `ARC_MICROVM_INTEGRATION=1`, `ARC_MICROVM_EXEC_ENABLED=1`, or `ARC_FC_REAL_EXEC=1` — no microVM runtime in normal CI.

### Summary
| Component | Status | What's missing |
|---|---|---|
| Preflight/doctor | Real | All 4 states tested: unavailable/installed_not_configured/ready/blocked |
| Design-proof plan | Real | Non-executing plan only; no VM creation/start/run/delete |
| Opt-in Lima harness | Internal low-security developer harness only | Fake-runner lifecycle tests pass; mount-proof mode can bypass only network proof for evidence collection; not wired to public microVM execution |
| Lima smoke/mount proof | Added (CI-skip) | `python/tests/isolation/test_lima_smoke.py`; real-host tests skipped unless macOS + limactl + ARC_MICROVM_INTEGRATION=1 + ARC_LIMA_REAL_EXEC=1; symlink escape proof records whether host paths are readable through `/workspace` symlinks |
| MicroVM truth guard | Updated | `test_microvm_truth_guard.py`: default/macOS execution blocked, Linux/Firecracker all-gates path delegates to runner, status includes ADR-024 and gate state; `arc sandbox run --provider microvm` remains blocked by default |
| Firecracker harness | Design/preflight only | `FirecrackerIntegrationHarness` added with fake-runner tests; no real Firecracker execution; `firecracker_doctor()` expanded with jailer/cache/kvm fields |
| Firecracker execution | Gated scaffold behind explicit Linux/KVM gates; unproven on this macOS host | Real Linux/KVM proof run with kernel + ARC exec rootfs, no-default-route/curl-fails markers, command result markers, teardown evidence |
| Direct Apple VZ host proof | Passed once behind `ARC_VZ_PROOF=1` on macOS 26.4 arm64 | Durable runner/kernel/initrd artifact provenance, opt-in CI host, public provider wiring, audit/output caps, timeout/SIGINT cleanup, and broader failure-mode tests |
| Lima strict execution | Not implemented | Lima is explicitly low-security/network-present; strict public `microvm` remains blocked |
| Integration test skeleton | Real (gated) | Tests exist but require local runtime; CI skips |
| Harness audit events | Real for internal harnesses and Linux/Firecracker scaffold | `MICROVM_COMMAND`/`MICROVM_DENIED` persisted for Lima/Firecracker harness attempts and Linux/Firecracker gated scaffold attempts; macOS public execution remains blocked |
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
