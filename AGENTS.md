You are taking over ARC Studio to implement the next sandbox/security phase.

Repository:
https://github.com/Hansuqwer/arc-theia-studio

Branch:
build/no-mockups-handoff

User approval:
Approved to research and implement. Use Context7, Vercel Grep/code search, and web search before coding.

Primary goal:
Turn ARC Studio's existing trust/isolation/security foundation into a production-grade CLI sandbox foundation, with a path to lightweight microVM execution on macOS and Linux. Skip Windows for now.

Do not fake completion.
Do not claim production-grade microVM execution until it actually exists and tests prove it.
Do not implement broad unsafe runtime execution without explicit gates.
Do not remove existing alpha/mock/fallback labeling.

Current known foundation:
- `python/src/agent_runtime_cockpit/security/trust.py`
- `python/src/agent_runtime_cockpit/security/profiles.py`
- `python/src/agent_runtime_cockpit/security/enforcement.py`
- `python/src/agent_runtime_cockpit/isolation/base.py`
- `python/src/agent_runtime_cockpit/isolation/none.py`
- `python/src/agent_runtime_cockpit/isolation/subprocess.py`
- `python/src/agent_runtime_cockpit/orchestration/supervisor.py`
- `python/src/agent_runtime_cockpit/cli/_helpers.py`
- `docs/security/enforcement-surfaces.md`
- `docs/roadmap.md` R16

Target outcome:
Implement a first-class `arc sandbox` CLI and policy layer now. Design microVM provider interface now. Implement lightweight microVM support only if feasible with clear macOS/Linux constraints and tests. If not feasible, document exact blockers and land the provider stub with doctor/preflight only.

Research-first gate:
Before implementation, research and record notes in docs.

Required research sources:
1. Context7 docs:
   - Python subprocess/process-group timeout best practices
   - Typer CLI subcommands/testing patterns
   - Pydantic config/model patterns
2. Vercel Grep/code search:
   - Examples of CLI sandbox command classification
   - Examples of Firecracker/Lima/Cloud Hypervisor wrapper patterns
   - Examples of policy-based command approval UX
3. Web search:
   - Codex CLI sandbox architecture: macOS Seatbelt, Linux Landlock/seccomp/namespaces, approval policies
   - Firecracker current Linux requirements and limitations
   - Lima/Apple Virtualization.framework options for macOS lightweight VM execution
   - Cloud Hypervisor lightweight Linux VM usage
   - Kata Containers tradeoffs
   - macOS sandbox-exec/Seatbelt status and limitations

Docs to create/update:
- `docs/research/sandbox-and-microvm.md`
- `docs/security/enforcement-surfaces.md`
- `docs/architecture/overview.md`
- `docs/BOOTSTRAP.md`
- `docs/roadmap.md` only if status genuinely changes
- `docs/phases.md` only if phase status genuinely changes

Research notes must include:
- source
- link
- what was learned
- implementation consequence
- confidence
- unresolved questions

Implementation decision table:
Create/update `docs/adr/` if ADR pattern exists, otherwise add a section in `docs/research/sandbox-and-microvm.md`.

Decision table format:
| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |

Required architecture:
Add/extend a sandbox abstraction with these conceptual providers:

```text
IsolationProvider
├── none
├── subprocess
├── container     # design only unless already present and safe
└── microvm       # macOS/Linux design; implementation only if feasible
```

Core implementation scope P0:
1. Add a user-facing CLI:
   - `arc sandbox doctor`
   - `arc sandbox run --policy <profile> -- <cmd...>`
   - `arc policy explain -- <cmd...>` or equivalent if command group already exists
2. Add/extend models:
   - `SandboxPolicy`
   - `SandboxDecision`
   - `CommandClassification`
   - `SandboxResult`
3. Command classification categories:
   - `read_only`
   - `writes_workspace`
   - `network`
   - `install`
   - `destructive`
   - `privileged`
   - `unknown`
4. Policy behavior:
   - auto-allow safe read-only commands
   - deny destructive/privileged by default
   - network denied by default unless policy enables it
   - writes allowed only inside workspace
   - package install requires explicit approval/policy flag
5. Harden subprocess provider:
   - workspace-bound cwd
   - symlink/path traversal guard
   - env allowlist only
   - remove secret-looking env vars
   - timeout
   - kill process group/tree on timeout
   - max stdout/stderr bytes
   - structured JSON result
   - no shell by default; list argv only
6. Emit trace/audit events for sandbox commands:
   - command
   - cwd
   - classification
   - decision
   - policy
   - sandbox provider
   - allowed/denied reason
   - start/end timestamps
   - exit code
   - stdout/stderr truncation flags
   - redaction applied flag

MicroVM requirement:
User prefers lightweight microVM for macOS/Linux, skip Windows.

Research and implement as follows:

Linux preferred candidates:
- Firecracker
- Cloud Hypervisor
- Kata Containers only if it fits local CLI use

macOS preferred candidates:
- Lima/Apple Virtualization.framework
- Tart if research supports it
- Avoid Docker Desktop as "microVM" unless documented as container fallback only

MicroVM P0 implementation decision:
If full microVM execution is too large for this phase, implement:
- `MicroVMIsolationProvider` as preflight/doctor-only
- provider detection:
  - Linux: check `firecracker`, `/dev/kvm`, kernel support
  - macOS: check `limactl`, virtualization support where detectable
- clear status:
  - unavailable
  - installed_not_configured
  - ready
  - blocked
- no fake run success
- tests for doctor/preflight states

If feasible to implement minimal real run:
- create disposable VM/session
- mount workspace through controlled path
- network disabled by default
- run argv command
- collect stdout/stderr/exit code
- destroy VM/session
- tests must be opt-in and skipped unless local runtime is installed
- normal CI must not require microVM runtime

CLI examples desired:

```bash
arc sandbox doctor --json

arc policy explain -- ls -la

arc sandbox run --policy local-safe -- ls -la

arc sandbox run --policy local-safe -- python -c "print('hello')"

arc sandbox run --policy local-safe -- curl https://example.com
# should deny network by default

arc sandbox run --policy local-safe -- rm -rf .
# should deny destructive by default
```

Test requirements:
Add Python tests covering:
1. read-only command allowed
2. network command denied by default
3. destructive command denied by default
4. command writing outside workspace denied
5. symlink escape denied
6. env secret stripped
7. timeout kills process
8. stdout/stderr capped
9. JSON output stable
10. audit/trace event emitted for allowed command
11. denial event emitted for denied command
12. microVM doctor reports unavailable gracefully if no runtime installed
13. Linux microVM preflight checks `/dev/kvm` and binary presence
14. macOS microVM preflight checks `limactl` or selected runtime
15. Windows explicitly unsupported with clear message

Do not depend on live network in tests.
Do not require Docker/Firecracker/Lima in CI.
Use monkeypatch/fakes for doctor/preflight tests.

Code quality:
- Keep changes small and reviewable.
- Prefer extending existing `isolation/` and `security/` modules instead of creating parallel systems.
- Preserve existing CLI behavior.
- Do not break existing tests.
- Maintain stable JSON envelopes.
- Use existing `ok(...)` / `err(...)` envelope patterns if available.
- Use existing redaction utilities.

Verification commands:
Run all:

```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
pnpm build
pnpm typecheck
```

If any command fails:
- fix it if in scope
- otherwise document exact failure and reason
- do not hide failures

Expected deliverables:
1. Research doc: `docs/research/sandbox-and-microvm.md`
2. CLI commands implemented:
   - `arc sandbox doctor`
   - `arc sandbox run`
   - `arc policy explain` or documented equivalent
3. Sandbox models/provider hardening
4. MicroVM provider/preflight/doctor for macOS/Linux
5. Tests listed above
6. Docs updated
7. Final report:
   - files changed
   - commands run
   - pass/fail matrix
   - what is real
   - what is design-only
   - what remains blocked
   - next PR queue

Important wording:
- "microVM preflight/doctor support" if only detection is implemented.
- "microVM execution" only if commands actually run inside microVM and tests prove it.
- "container fallback" only if Docker/Podman path exists.
- "production-ready foundation" is okay.
- "production-ready sandbox" only if subprocess/container/microVM isolation is complete and verified.

Active sandbox truth constraints:
- No microVM execution exists yet.
- Lima remains template-only unless a later implementation actually creates/runs/destroys a VM and tests prove it.
- Firecracker remains preflight-only unless a later implementation actually boots/runs/destroys a microVM and tests prove it.
- Container remains a gated fallback only; it is disabled unless `ARC_ENABLE_CONTAINER_SANDBOX=1` is set.
