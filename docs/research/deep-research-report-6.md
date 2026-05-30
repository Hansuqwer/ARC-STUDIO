# Security and sandbox improvements for ARC Studio

## Framing

Assuming the current ARC controls you listed are accurate, the strongest next step is not to jump straight to “microVM execution”, but to harden ARC into a clearly layered model: a strict default-deny local sandbox for routine work, a separate approval engine for policy exceptions, a full-session wrapper for plugins and helper processes, and only then an experimental VM-backed high-isolation path. That is the pattern visible in the most mature local agent tooling today: Codex separates sandboxing from approvals and uses platform-native enforcement; Claude combines OS-enforced sandboxing with path/domain permissions and an action classifier; Cline and Roo lean heavily on explicit approval UX and rollback ergonomics. citeturn25view0turn25view1turn26view2turn26view3turn29view1turn27view2

The most important conclusion is this: on macOS, the practical command sandbox available **now** is still Seatbelt via `sandbox-exec`, even though Apple marks `sandbox-exec` as deprecated; both Codex and Claude currently document Seatbelt as their macOS sandbox mechanism. On Linux, the practical baseline is **bubblewrap + namespaces + seccomp**, with Landlock layered on top where available. Firecracker is a real option for Linux-host microVM execution, but not for native macOS hosts; on macOS, anything honestly called “microVM execution” would require either a Linux host somewhere else or a nested-virtualisation design that is materially more complex and hardware-constrained. citeturn38search0turn25view1turn26view4turn10view0turn5view0turn4view0turn36search0turn39search3turn16view1

## State of the art in local agent sandboxing

OpenAI Codex’s local model is particularly relevant for ARC because it treats sandboxing and approvals as **separate controls**. Codex applies OS-level sandboxing to spawned commands, uses Seatbelt plus `sandbox-exec` on macOS, and uses `bwrap` plus `seccomp` on Linux. Its default local mode is effectively “workspace-write, network off unless enabled, ask when leaving the boundary”, and it also exposes destination-based network policy via a proxy feature. Codex further protects local configuration by only loading project-scoped config when the project is trusted. citeturn25view0turn25view1turn25view2turn31view0turn31view1

Claude Code adds two useful ideas beyond that baseline. First, it has a **full-session sandbox runtime** in beta that can wrap the whole Claude process, including hooks and MCP servers, rather than only sandboxing Bash subprocesses. Second, its **auto mode** routes actions through a classifier that blocks destructive or out-of-environment actions by default, with explicit configuration for trusted repos, buckets, and domains. Claude also has a mature user-facing permission system with deny/ask/allow precedence, fine-grained tool specifiers, and pre-tool hooks that can block or force prompts but cannot override a deny rule. citeturn26view3turn26view4turn26view1turn26view2turn28view0turn28view3

Cline and Roo are weaker as sandbox references, but strong as approval-UX references. Cline evaluates auto-approval per tool call, distinguishes workspace vs outside-workspace access, warns about long-running commands, and explicitly documents the danger of universal “YOLO” approval. Roo’s UX is even more explicit: it offers a global enable switch that preserves per-permission selections, per-category tiles, two-step MCP approval, and write-delay integration with the editor’s diagnostics pane. Those patterns are worth copying even if ARC adopts a stricter backend than either tool ships today. citeturn29view0turn29view1turn30view0turn27view2

At the primitive level, Linux is ahead. Seccomp reduces kernel attack surface but the kernel docs explicitly say it is **not** a sandbox by itself; it should be used by sandbox developers as one layer. Bubblewrap uses user namespaces and an empty mount namespace to construct an unprivileged sandbox, but its own maintainers also say it is not a complete security policy by itself. Landlock is attractive because it is unprivileged, stackable, and ABI-versioned, with TCP bind/connect restrictions in ABI v4 and device-`ioctl` controls in ABI v5, but it still has important gaps and should be treated as a best-effort additional layer rather than a complete replacement for namespaces and seccomp. citeturn5view0turn10view0turn4view0

On macOS, the situation is more awkward. Apple’s App Sandbox is kernel-enforced and entitlement-driven, and Apple positions it as the way to restrict app access to files, network, and capabilities. Endpoint Security can observe and in some cases authorise sensitive operations such as executes and mounts. Virtualization.framework provides first-party VM APIs for Linux and macOS guests. But none of those directly replace a lightweight per-command CLI sandbox on today’s macOS as neatly as Seatbelt does, which is why both Codex and Claude still use Seatbelt for local command isolation. citeturn34search0turn34search10turn32search2turn34search1turn34search2turn24search0turn24search1

## Recommended sandbox architecture for macOS

### Possible now

For macOS, ARC should adopt a **two-tier architecture**.

The first tier should be the fast default path for most local work: **Seatbelt profiles invoked per command**, with default workspace-only write access, no network by default, explicit protected paths outside the workspace, environment scrubbing, strict process-group kill, output limits, and a hard prompt before any unsandboxed fallback. This is the same practical direction taken by Codex and Claude on macOS. ARC’s current subprocess sandbox provider and command classifier already point in this direction; the missing piece is to make the Seatbelt path the declared primary implementation for macOS rather than treating container or microVM work as if they were ready to replace it. citeturn25view1turn26view4turn24search0turn24search1

The second tier should be a **full-session isolation wrapper** for “untrusted session” mode. The most defensible design is to wrap not just subprocesses, but also hooks, MCP servers, bundled helper tools, and any plugin execution in one OS boundary, following Claude’s sandbox-runtime idea. In ARC terms, this means a distinct “session sandbox” mode that encloses all extension points, not just the shell tool. That closes a common escape hatch in agent products: helper processes that run outside the shell sandbox. citeturn26view3turn26view4

ARC should also add **Endpoint Security-backed audit hooks** on macOS for high-confidence observability. This is not the primary sandbox boundary, but it is well suited to verify exec events, mount events, and other sensitive operations for audit trails or canary enforcement around the ARC process tree. That pairs naturally with ARC’s existing sandbox audit events. citeturn34search1turn34search10turn32search2

If ARC Studio is distributed as a signed macOS app bundle, Apple’s **App Sandbox** is worth considering as an **outer boundary for the application itself**, especially for features such as broad filesystem access and networking. I would not treat App Sandbox as the replacement for per-command Seatbelt policy generation; rather, I would treat it as defence in depth around the host application. That recommendation is partly an inference from Apple’s entitlement model and documentation, so it should be validated against ARC Studio’s packaging and feature set before committing to it. citeturn34search0turn34search3turn34search6turn34search12turn34search18

### Research-only

For higher isolation on macOS, the honest near-term step is **Linux VM execution**, not “microVM execution”. Apple’s Virtualization.framework is the first-party way to run Linux VMs on macOS, and both Lima and Tart build on top of that or QEMU depending on configuration. Lima is convenient but comes with automatic file sharing and port forwarding features, so its defaults are optimised for usability rather than being a minimal security boundary. Tart is attractive on Apple Silicon and uses Virtualization.framework, but it is still a VM toolchain rather than a microVM system, and its default NAT behaviour can still expose host reachability depending on network mode. citeturn34search2turn39search0turn14view0turn15search5turn15search6turn15search7turn15search9turn8search2turn16view1

So the realistic macOS “high isolation” design is: run risky workloads inside an **ephemeral Linux VM** created via Virtualization.framework or a tightly controlled Lima/Tart backend; export only a minimal workspace view; keep network off by default; and use copy-out or patch export instead of broad host mounts. That is **possible now**. Calling it “microVM execution” would still be misleading. citeturn34search2turn39search14turn15search1turn15search7turn16view1

A nested Firecracker design on macOS is **research-only**. Apple documents that nested virtualisation support exists in Virtualization.framework on macOS 15+ and M3-or-later hardware, and Tart notes current practical support only for Linux VMs. Even if nested virtualisation is available, you still need a Linux guest, KVM inside that guest, a Firecracker/host-guest transport design, workspace mount strategy, and teardown guarantees. That is not something ARC should present as a shipping feature until it is tested end-to-end on supported hardware. citeturn39search3turn39search6turn16view1

## Recommended sandbox architecture for Linux

### Possible now

For Linux, ARC should standardise on a **layered baseline sandbox**:

1. **Bubblewrap** to create the mount/user/pid/ipc/uts/network namespaces and construct an empty or near-empty filesystem view.
2. **Seccomp-bpf** with `no_new_privs` to minimise host kernel attack surface.
3. **Landlock** applied at runtime as an additional best-effort policy layer, with ABI detection and graceful degradation.
4. **cgroups and rlimits** for memory, CPU, process count, and file-descriptor control.
5. **Loopback-only network namespace by default**, with optional proxy-mediated egress for approved destinations. citeturn10view0turn5view0turn4view0turn9search0turn9search2turn9search3

This is close to the practice documented by OpenAI and Anthropic already. Codex says Linux uses `bwrap` plus `seccomp`; Claude documents bubblewrap and a proxy relay for sandboxed network access on Linux and WSL2. That is a strong signal that this stack is already the practical state of the art for local developer-machine agent execution. citeturn25view1turn26view4

Landlock is worth adding, but with discipline. The kernel docs are clear that you should query the ABI at runtime and only use the features the running kernel supports. ABI v4 adds TCP bind/connect restrictions. ABI v5 adds `LANDLOCK_ACCESS_FS_IOCTL_DEV`. Newer ABIs add more scope controls, but ARC should target v4/v5 as the portable minimum and degrade cleanly when absent. In practice, Landlock is best used to harden filesystem and some network-port actions after bubblewrap has already reduced visibility. citeturn4view0

NsJail is the main serious alternative if ARC wants an off-the-shelf Linux sandbox provider rather than maintaining its own bubblewrap orchestration. It bundles namespaces, cgroups, rlimits, `pivot_root`/`chroot`, and seccomp-bpf in one tool. That makes it a credible optional provider for an “advanced Linux sandbox” mode, but not obviously better than bubblewrap for ARC’s default path given the ecosystem momentum behind bubblewrap in Codex and Claude. citeturn35view0turn35view1turn25view1turn26view4

### Higher-isolation options

If ARC wants a stronger Linux boundary than plain namespaces, there are four realistic families.

**Firecracker** is the clearest candidate for ARC’s future Linux-only microVM mode. It is purpose-built for secure, multi-tenant microVMs, runs on Linux with KVM, uses a minimal device model, includes a jailer, and applies thread-specific seccomp filters. This is the best fit if ARC eventually wants to say “microVM execution” on Linux. citeturn11view0turn36search0turn36search1

**Cloud Hypervisor** is also serious, but it targets KVM and Microsoft Hypervisor and is better read as a minimal cloud VMM than as the obvious first choice for a local agent microVM provider. It is implemented in Rust and focused on minimal hardware emulation, but the documentation and user model are more VM-oriented than Firecracker’s purpose-built serverless/microVM positioning. citeturn12view0turn13view0

**gVisor** is a compelling middle ground when ARC is already operating in OCI/container workflows. Its user-space kernel, seccomp filtering, and dual-kernel model give materially better isolation than standard containers, and it can run without hardware virtualisation support. For an agent that sometimes runs inside dev containers or CI containers, gVisor is a very strong **container-mode** option, but it is not a native per-command local shell sandbox in the same way bubblewrap is. citeturn17view0turn17view1turn16view0

**Kata Containers** gives VM-backed containers with stronger isolation than standard Linux namespaces, again mainly as an OCI/container-runtime choice. It is a good architectural reference and a possible future integration point for standardised container workflows, but it is probably too heavy as ARC’s primary local command sandbox. citeturn19view0

Docker rootless and Podman rootless are useful **fallback environments**, not primary sandboxes for ARC. Docker rootless removes root from both daemon and containers, and Podman rootless uses user namespaces plus a rootless networking stack such as pasta, but both are broader container systems with more moving parts than ARC needs for single-command isolation. They are excellent for a “run ARC inside a rootless dev container” story; they are not the best default primitive for the local shell sandbox itself. citeturn18view0turn18view1

## Command classification and approval UX

### Command classification improvements

ARC’s command classifier should move from a binary “safe vs dangerous” model to a **multi-axis effect classifier**. The mature tools all separate effect from UI policy in different ways: Codex has sandbox modes plus approval policies and command rules; Claude has deny/ask/allow precedence with command patterns and hooks; Cline has command-level `requires_approval`; Roo distinguishes approved command prefixes from everything else. ARC should combine those lessons into a classifier that scores commands across at least these axes: filesystem mutation, workspace escape, protected-path access, network egress, package/dependency mutation, VCS mutation, persistence/system configuration, privilege change, opaque execution wrapper, and data exfiltration risk. citeturn25view0turn28view0turn29view0turn27view2

The classifier also needs to understand **wrappers and indirect writes**. High-risk shells are often hidden behind `bash -lc`, `sh -c`, `python -c`, `node -e`, `xargs`, `find -exec`, `env VAR=... cmd`, or script runners. Likewise, “read-looking” commands such as `sed -i`, shell redirection, `tee`, `perl -pi`, `tar -xf`, `git checkout`, `git apply`, and archive extraction all mutate state. Claude’s documented command-pattern rules and deny-first precedence are a good model for how ARC should map parsed commands into policy decisions. citeturn28view0

ARC should also split classification into **intent** and **resolved effect**. A command like `pip install` or `npm install` may be normal during setup but still changes dependencies and can run arbitrary install hooks; a `git push` may be ordinary in one repo and an exfil path in another. That means policy should consider the resolved working directory, the target paths after symlink resolution, the destination domains or remotes, and whether the workspace is trusted. Codex’s trusted-project model and Claude’s trusted-infrastructure classifier are direct precedents here. citeturn31view1turn26view2

A practical classification scheme for ARC would therefore have classes such as **read-only**, **workspace-local mutation**, **dependency mutation**, **external communication**, **protected-path access**, **credential touch**, **system mutation**, and **destructive**. The approval engine can then map those classes to allow/prompt/deny depending on current mode. That will be much easier to reason about than a grab-bag of hard-coded command names.

### Approval-policy UX improvements

ARC should adopt a **permission surface that mirrors its risk model**. Roo’s global Enabled switch with preserved per-permission selections, Cline’s per-category auto-approval, and Claude’s `/permissions`-driven deny/ask/allow rules are all better than a single “full auto” toggle. ARC should expose categories such as: read workspace, edit workspace, access outside workspace, run read-only commands, run mutating commands, use network to approved domains, use network to new domains, use connector/MCP tools, and use unsandboxed fallback. citeturn27view2turn29view0turn28view0

The system should also tell the user **why** an approval was required. A simple line such as “Prompted because: writes outside workspace + touches protected path + destination domain not yet trusted” reduces fatigue and trains users to reason about the sandbox. Claude’s effective policy view and Cline/Roo’s category-based UI both point in this direction. citeturn26view4turn29view0turn27view2

For MCP and plugin tools, ARC should copy Roo’s **two-step approval model**: a global setting that enables MCP auto-approval at all, plus a per-tool allow checkbox. For destructive external tools, ARC should follow Codex’s approach and always require approval when the tool advertises destructive side effects. citeturn27view2turn25view2

ARC should also add four guardrails that other tools hint at but do not always combine well. First, **session-scoped grants** by default, with project-scoped persistence only for trusted workspaces. Second, **long-running command notifications** for auto-approved tasks, as Cline does. Third, **checkpoints/rollback hooks** before edit batches, inspired by Cline and Roo. Fourth, an admin-enforceable **fail-closed mode**: if the sandbox is unavailable, ARC should refuse to run mutating commands instead of silently dropping to host execution. Claude explicitly documents a fail-if-unavailable setting; ARC should adopt the same stance. citeturn29view0turn30view0turn27view2turn26view4

## Secrets, network, and filesystem strategy

### Secret redaction and detection improvements

ARC already strips some secrets from the environment. It should extend that into a **three-layer secret programme**.

The first layer is **pre-prompt redaction**. Before code, config, logs, diffs, or environment values are sent to the model, ARC should scan and replace likely secrets with stable fingerprints such as `sk-...<redacted>#abcd`. That preserves debugging value without exposing raw tokens. This should cover environment variables, `.env` files, shell output, URLs with embedded credentials, cloud creds, SSH material, and editor settings. The scanner needs both regex/provider rules and generic high-entropy detection. The serious open-source references here are Gitleaks, detect-secrets, and TruffleHog. Gitleaks supports reports and baseline comparison; detect-secrets is built around baselines and audit workflows; TruffleHog’s distinguishing feature is verification of discovered credentials. citeturn21search0turn21search2turn21search8turn20search11turn21search4turn21search13

The second layer is **pre-write and pre-commit blocking**. ARC should scan generated diffs before writing them, before running `git add`, before `git commit`, and before any push-like operation. The fastest local combination is Gitleaks plus detect-secrets baselines; for higher confidence, a CI or optional on-demand check can run TruffleHog verification against supported providers. The verifier should be opt-in or CI-scoped, because “is this credential live?” is itself a sensitive operation. citeturn21search0turn21search2turn20search3turn21search4turn21search13

The third layer is **artifact and supply-chain hygiene**. ARC’s sandbox helpers, guest images, policy bundles, and provider binaries should be versioned, pinned, and accompanied by machine-verifiable provenance. SLSA’s current framework and provenance spec give the right vocabulary here: signed provenance telling consumers which builder produced which artefacts, from what source, with what recipe and materials. For ARC, that means producing provenance for sandbox helper binaries and any VM image/rootfs artefacts, then verifying those before update or execution. citeturn23view0turn23view1turn22search4

### Network isolation strategy

The default network policy should be **deny all egress**. Both Codex and Claude treat network as a separate permission boundary, and Codex now documents a proxy-enforced destination policy for local commands. ARC should do the same. On Linux, the cleanest baseline is a private network namespace with loopback only. When network is enabled, ARC should force traffic through a local proxy that enforces domain allowlists and logs decisions. Landlock v4 can restrict TCP bind/connect by port, but not by destination hostname, so it is not enough on its own for exfil control. citeturn25view2turn26view4turn4view0

On macOS, ARC should keep the same **policy shape** even if implementation details differ. Seatbelt can deny or permit network operations at the process level, while the actual domain-based policy should be enforced by a host-side proxy. Claude’s secure deployment docs explicitly describe routing macOS traffic through a built-in proxy; Codex documents destination rules through a network proxy feature. ARC should not pretend that per-domain egress control comes “for free” from Seatbelt alone. citeturn24search3turn25view2

In all modes, ARC should block **local-network and host-control channels** unless explicitly needed: loopback escape paths, Docker/Podman sockets, SSH agent sockets, D-Bus/systemd buses, metadata endpoints, cloud instance metadata IPs, and IDE/editor IPC sockets. Bubblewrap maintainers explicitly warn that mounted sockets such as D-Bus can become privilege-escalation paths; the same principle applies to every local control socket. citeturn10view0

### Filesystem isolation strategy

The right filesystem model is **minimal visibility plus ephemeral writes**.

On Linux, bubblewrap already supports the right pattern: create an empty mount namespace, present only the directories the task needs, mount them read-only where possible, and place the writable layer on tmpfs or a scratch area. ARC should mount the workspace itself as either read-only plus overlay, or as a dedicated writable bind mount while keeping everything else absent, read-only, or protected. Private `/tmp`, minimal `/dev`, controlled `/proc`, and no host home directory by default should be the norm. citeturn10view0turn35view0

On macOS, Seatbelt should allow the working tree and a small ARC-controlled scratch/cache area, while explicitly denying well-known sensitive locations such as `~/.ssh`, keychain-related paths, cloud-sync data, app containers, browser profiles, and launch-agent persistence directories. If ARC adopts a VM-backed high-isolation mode on macOS, it should prefer **copy-in / patch-out** or a read-only virtiofs share plus overlay scratch, rather than a broad writable host mount. Lima’s defaults are convenient but still prove the point: its home mount is read-only by default on macOS, and write access is a deliberate widening. citeturn15search1turn15search5turn15search9

Two specific anti-footgun rules matter here. First, `symlink` resolution must be checked against policy before write access is granted; Claude’s docs explicitly discuss symlink behaviour in permission rules, and ARC should emulate that level of care. Second, protected paths should include ARC’s own config and audit directories, version-control internals, credential files, and host-level package or service configuration. citeturn28view1turn25view1

## MicroVM roadmap and claim criteria

### Honest feasibility

ARC should keep the current external statement exactly where it is today: **no production microVM execution claim**.

A reasonable roadmap is:

**Phase one: Linux experimental VM-backed execution.** Choose one Linux-first microVM provider, ideally Firecracker. Build an end-to-end path that boots, runs a command, mounts a workspace view, captures output and exit status, enforces timeouts, tears down cleanly, and leaves the host clean. Do not support multiple VMMs at first. Firecracker is the best first candidate because it is explicitly built for secure microVMs, uses KVM, ships a jailer, and already has a minimal device model and seccomp hardening. citeturn11view0turn36search0turn36search1

**Phase two: Linux hardened mode.** Add signed rootfs/kernel artefacts, measured update and provenance checks, policy-driven networking, and concurrency limits. Only after this phase should ARC consider the wording “experimental microVM execution on supported Linux hosts”. citeturn23view0turn23view1turn11view0

**Phase three: macOS high isolation via Linux VM.** Run the same Linux execution path inside an outer Linux VM on macOS using Virtualization.framework. This can honestly be sold as “VM-isolated execution on macOS”, not “microVM execution on macOS”. citeturn34search2turn39search14

**Phase four: nested microVM on macOS.** Treat this as research-only unless and until ARC proves it on the exact supported hardware/OS matrix. Apple says nested virtualisation support is M3-or-later and macOS 15+; Tart adds the practical note that today this support is only for Linux VMs. That is too constrained to market broadly as a platform capability right now. citeturn39search3turn16view1

Cloud Hypervisor can remain a research branch or a later abstraction point, but ARC should not split scarce engineering effort across Firecracker and Cloud Hypervisor before one works end to end. Kata and gVisor are useful references and optional integrations, but they are not the shortest route to an honest ARC-native microVM claim. citeturn12view0turn13view0turn19view0turn17view0

### Tests required before any microVM execution claim

Before ARC says anything stronger than “microVM preflight/doctor”, it should have automated tests that prove all of the following on every supported host class.

The first set is **run-path testing**: boot the VM, execute a representative command, return exit status, stream stdout/stderr, enforce timeout, and tear down without leaving zombie processes, mounts, tap devices, sockets, or stale state. Firecracker’s own positioning around CI-enforced performance and tested platforms is a good reminder that these claims must be evidence-backed, not aspirational. citeturn11view0

The second set is **mount-path testing**: mount the intended workspace view into the guest, confirm read-only vs read-write policy behaves exactly as documented, confirm writes cannot escape via symlink tricks or `..` traversal, and confirm the host sees only the intended outputs after teardown. Linux’s `chroot` man page is a useful warning here: filesystem isolation claims need real tests because naïve root-directory tricks are not secure boundaries. citeturn9search1

The third set is **network-path testing**: verify that default boot has no outbound network, no inbound host reachability unless explicitly allowed, no access to local metadata or host control sockets, and no direct egress when the policy says “proxy only”. If ARC later adds allowlisted network access, tests must prove both positive and negative cases. Firecracker’s own networking docs also make clear that host network setup is a real part of the implementation, not an incidental detail. citeturn36search2turn25view2

The fourth set is **secret and audit testing**: prove that secrets are absent from environment and logs, that sandbox or microVM audit events are emitted with enough context to reconstruct what happened, and that failures are visible. ARC’s existing secret stripping and audit-event work should be extended, not bypassed, in the VM path.

The fifth set is **supply-chain testing**: verify the signature or provenance of the guest kernel, rootfs image, runtime helper, and policy bundle before execution. This is where SLSA-style provenance matters operationally rather than just as a compliance checkbox. citeturn23view0turn23view1

If ARC does not have those run/mount/network/teardown tests in CI, then it should not use the phrase **“microVM execution”** in release notes, docs, marketing, or UI copy.

### Open questions and limitations

A few Apple documentation pages were only partially accessible in this research environment because they require client-side rendering, so some Apple-specific details were taken from Apple search-result summaries rather than fully opened pages. I have therefore treated App Sandbox and Virtualization.framework mainly as high-confidence capability signals, and I have been more cautious where a recommendation depends on deeper Apple implementation details. citeturn34search0turn34search2turn34search10

## What to avoid

ARC should avoid these patterns:

- **Do not rely on `chroot` as a security boundary.** The Linux man page is explicit that it has historical escape issues and is not sufficient on its own. citeturn9search1
- **Do not rely on seccomp alone.** The kernel docs explicitly say seccomp is not a sandbox by itself. citeturn5view0
- **Do not treat bubblewrap as a policy engine by itself.** Its maintainers say the protection level depends entirely on the arguments passed to it. citeturn10view0
- **Do not make unsandboxed fallback silent or automatic for mutating work.** If sandbox start-up fails, ARC should fail closed or require an explicit high-friction override. Claude documents exactly this distinction with `failIfUnavailable`. citeturn26view4
- **Do not make Docker or Podman rootful or rootless containers the default local shell sandbox.** They are useful outer environments, but they are not the narrowest, simplest boundary for single-command agent execution. citeturn18view0turn18view1
- **Do not give sandboxes broad access to local sockets** such as D-Bus, Docker, SSH agent, or IDE helper sockets. Bubblewrap’s own docs warn that mounted sockets can become privilege-escalation paths. citeturn10view0
- **Do not present Lima or Tart defaults as “secure isolation” without tightening them.** Both are designed for convenient VM development, with automatic sharing or host/guest integration features that need to be narrowed for adversarial workloads. citeturn14view0turn15search5turn16view1
- **Do not depend strategically on `sandbox-exec` as if it were future-proof.** It is deprecated, even if it remains the practical zero-install answer today. Build the provider abstraction so it can be swapped out or downgraded to “fast path only” later. citeturn38search0turn24search1turn24search0
- **Do not ship or encourage universal auto-approval modes.** Cline’s YOLO mode and analogous bypass modes are fine only in explicitly isolated throwaway environments. citeturn29view1turn28view2
- **Do not claim microVM execution until run, mount, network, and teardown tests exist and pass in CI.** citeturn11view0turn36search1

## Feature table

| Feature | Platform | Source | Benefit | Complexity | Security value | Blocking issues | Priority |
|---|---|---|---|---|---|---|---|
| Seatbelt per-command sandbox provider | macOS | Codex and Claude macOS sandbox docs citeturn25view1turn26view4 | Best zero-install practical command sandbox on macOS today | Medium | High | `sandbox-exec` is deprecated, so ARC must treat this as replaceable | P0 |
| Full-session sandbox wrapper for hooks, MCP, helpers | macOS, Linux | Claude sandbox runtime docs citeturn26view3 | Closes the “helper process runs outside shell sandbox” gap | Medium | High | Runtime integration, developer ergonomics, path/domain config | P0 |
| App Sandbox as outer app boundary | macOS | Apple App Sandbox docs citeturn34search0turn34search12turn34search18 | Defence in depth for the ARC Studio app itself | High | Medium | Entitlement friction, packaging constraints, possible feature breakage | P2 |
| Endpoint Security audit integration | macOS | Apple Endpoint Security docs citeturn34search1turn34search10turn32search2 | High-confidence exec/mount observability and policy verification | High | Medium | System-extension complexity and Apple entitlement requirements | P1 |
| Virtualization.framework Linux VM mode | macOS | Apple Virtualization docs citeturn34search2turn39search14 | Honest high-isolation path on macOS without overclaiming microVMs | High | High | VM image lifecycle, workspace sharing, performance, UX | P1 |
| Lima backend for Linux VM mode | macOS, Linux | Lima docs citeturn14view0turn15search6turn15search7 | Faster path to a managed Linux VM backend | Medium | Medium | Defaults favour convenience; must tighten mounts and networking | P2 |
| Tart backend for Apple Silicon VM mode | macOS Apple Silicon | Tart docs citeturn8search2turn16view1 | Good Apple Silicon VM UX, practical host integration | Medium | Medium | Apple Silicon only; host integration defaults need tightening | P2 |
| Bubblewrap + namespaces + seccomp baseline | Linux | Codex/Claude/Linux kernel/bwrap docs citeturn25view1turn26view4turn10view0turn5view0 | Best current default local Linux command sandbox | Medium | High | User namespace availability; careful policy assembly required | P0 |
| Landlock overlay with ABI detection | Linux | Linux kernel Landlock docs citeturn4view0 | Additional unprivileged filesystem and some network-port controls | Medium | Medium-High | Kernel support varies; ABI gaps require graceful degradation | P0 |
| NsJail provider | Linux | NsJail docs citeturn35view0turn35view1 | Battle-tested combined namespaces/cgroups/seccomp tool | Medium | Medium-High | More operational surface area than bwrap baseline | P2 |
| Firecracker microVM provider | Linux | Firecracker docs citeturn11view0turn36search0turn36search1 | Strongest honest route to Linux microVM execution | Very High | Very High | KVM, guest image pipeline, host networking, teardown correctness | P1 |
| Cloud Hypervisor research provider | Linux, MSHV environments | Cloud Hypervisor docs citeturn12view0turn13view0 | Alternative minimal VMM in Rust | Very High | High | Not the shortest path for ARC’s first microVM claim | P3 |
| gVisor container-mode isolation | Linux | gVisor docs citeturn17view0turn17view1turn16view0 | Strong container isolation without requiring hardware virtualisation | High | High | Better as container/developer environment integration than default shell sandbox | P2 |
| Kata Containers integration | Linux | Kata docs citeturn19view0 | VM-backed OCI containers for strong isolation | Very High | High | Heavy runtime/OCI integration for local-agent use | P3 |
| Rootless Podman or Docker fallback | Linux | Podman and Docker rootless docs citeturn18view0turn18view1 | Standardised outer environment when organisations already use dev containers | Medium | Medium | Too broad and operationally heavy as primary command sandbox | P3 |
| Gitleaks local scan and baseline | macOS, Linux | Gitleaks docs citeturn20search0turn21search0 | Fast local secret scanning for repo, diff, and history | Low | High | Tuning false positives and policy exceptions | P0 |
| detect-secrets baseline and audit | macOS, Linux | detect-secrets docs citeturn21search2turn21search8 | Good review workflow and baseline auditing | Low | Medium-High | Baseline upkeep and training users to audit correctly | P1 |
| TruffleHog verified secret scanning | macOS, Linux, CI | TruffleHog docs citeturn20search11turn21search4turn21search13 | Higher-confidence live credential finding and broad-source scanning | Medium | High | Verification can itself be sensitive; best in CI or opt-in mode | P1 |
| SLSA provenance for helpers and VM artefacts | Cross-platform build pipeline | SLSA and OpenSSF docs citeturn23view0turn23view1turn22search4 | Verifiable build provenance for sandbox helpers and images | Medium | High | Build-system changes and signature verification rollout | P1 |

