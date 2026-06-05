# Workspace Trust / Security Review

## Current ARC Spec

ARC Studio specifies workspace trust as a **hard gate before writes, shell execution, paid provider calls, and runtime execution**. Trust is a first-class concept across CLI, IDE, and backend enforcement.

### Trust Model (ARC_STUDIO_UX_SPEC §7.18, §9 WorkspaceTrustBanner, ADR-006)

**Trust levels:**
- `UNTRUSTED` — default for all new workspaces; read-only chat/context only
- `PARTIAL` — reserved; requires explicit user approval; limited capabilities
- `TRUSTED` — full access to writes, shell, paid calls, runtime execution

**Trust binding:** Canonical path + machine ID + user ID. Symlinked paths resolve before trust check. Moving or cloning a workspace requires a new trust decision.

**Trust storage:** External to workspace at `~/.arc/trusted-workspaces.json`. A committed `.arc/trusted` file is explicitly ignored — the workspace must not self-authorize.

**First-untrusted-workspace flow (§7.18):**
```
┌ workspace trust ───────────────────────────────────────────────────────────┐
│ This workspace is untrusted. ARC Studio can read files but cannot write,   │
│ run, or call paid providers.                                               │
│                                                                            │
│ [Trust this workspace] [Stay untrusted] [Learn more]                       │
└────────────────────────────────────────────────────────────────────────────┘
```
Chat input is disabled until the user chooses. Trust requires explicit Enter/click; no shortcut bypass.

### Untrusted Mode Restrictions (§7.18, §10.8)

When untrusted, ARC Studio:
- **Allows:** Read-only file browsing, chat/context questions, workflow detection (static scan), inspecting traces from previous runs
- **Blocks:** File writes, shell execution, paid provider calls, runtime execution, trust changes, destructive operations

### Trust Component (§9 WorkspaceTrustBanner)

```ts
interface WorkspaceTrustBannerProps {
  workspacePath: string;
  onTrust: () => void;
  onStayUntrusted: () => void;
  onLearnMore: () => void;
}
```

Copy: `This workspace is untrusted. ARC Studio can read files but cannot write, run, or call paid providers.`

### Trust in Config UI (§7.3, §8.6)

- `/config` form shows `Workspace ✓ trusted: /Users/me/project` or untrusted state
- Config tab includes "Workspace Trust" sub-tab for managing trust
- Trust can be revoked from `/config > Workspace Trust`

### Trust in Status (§7.9, §7.14)

- `/status` shows `Trust ✓ workspace trusted` or untrusted badge
- Status bar segment shows trust state with `state.success` or `state.warning` tone

### Approval Policy (§7.13, §10.3)

The `/auto` mode policy explicitly denies trust changes and shell execution even in auto mode:
```yaml
approvals:
  paid_calls: ask
  destructive_writes: ask
  trust_changes: deny    # Cannot be weakened by project policy
  shell_exec: deny       # Cannot be weakened by project policy
  phase_advance: ask
```

Policy precedence: project `.arc/policy.yaml` > user `~/.config/arc-studio/policy.yaml` > built-in safe defaults. Project policy **cannot** weaken user policy for `shell_exec` or `trust_changes`.

### Backend Implementation (trust.py, ADR-006)

**Current implementation** (`python/src/agent_runtime_cockpit/security/trust.py`):
- `resolve_trust()` — advisory; returns `TrustResolution` with level/reason/warning
- `ensure_trusted()` — P2 enforcement; raises `WorkspaceUntrusted` before execution
- `trust_workspace()` / `untrust_workspace()` — CRUD on external trust DB
- `list_trusted()` — list all trusted workspaces
- Trust DB: `~/.arc/trusted-workspaces.json` with `{canonical_path: {trusted: true, note: ""}}`
- `allow_if_no_db` flag for first-run scenarios

**Isolation provider interface** (ADR-006, `isolation/` package):
- `none` / inspect-only — untrusted workspaces; detection/inspection only
- `subprocess` — trusted-local baseline with env allowlist + resource limits
- `docker` — container isolation with bind mounts + network policy
- `orbstack` / `podman` / `colima` — Docker-compatible alternatives
- `firecracker` — Linux/KVM microVM (P5+, deferred)

### Enforcement Phases (IMPLEMENTATION_PLAN)

| Phase | Behavior |
|---|---|
| P1a | Advisory/warn-only: trust status reported but execution not blocked |
| P2 | Enforcement: `ensure_trusted()` called by `JobSupervisor.start_run()` before execution; untrusted workspaces blocked |
| P3 | Docker-compatible isolation for untrusted workspaces that user wants to run with containment |
| P4 | Advanced subprocess hardening, HITL persistence, replay-attack protection |

### Redaction Contract (§10.10)

All surfaces use the same redactor: CLI output, IDE chat, SSE events, Runs summaries, graph inspector, error cards, logs, and advanced command output. Removes API keys, bearer tokens, passwords, provider secrets, cloud credentials, and `.env` values. `/status` shows key provenance (`env`, `keyring`, `file`, `unset`) — never partial key values.

### Unsafe Flags (§10.8)

`--unsafe` requires explicit confirmation and is never implied by advanced mode. `arc-studio advanced <cmd>` still enforces workspace trust and key redaction.

---

## Comparable Products / Research

| Feature | VS Code | Cursor | Claude Code | Codex CLI | GitHub Codespaces | ARC Studio (spec) |
|---|---|---|---|---|---|---|
| **Trust model** | Workspace Trust (Restricted Mode) | Implicit (no explicit trust dialog) | Directory-based permissions | Sandbox + approval modes | Trusted repos setting | Explicit trust levels (UNTRUSTED/PARTIAL/TRUSTED) |
| **Default state** | Restricted Mode (untrusted) on first open | Trusted (no gate) | Read-only for non-version-controlled | `read-only` for non-git, `Auto` for git | Trusted (managed environment) | UNTRUSTED (explicit approval required) |
| **Trust prompt** | Modal dialog on first open | None | Onboarding prompt or `/permissions` | Auto-detects git, recommends mode | Settings UI | Modal banner (§7.18), blocks chat input |
| **Trust storage** | `~/.config/Code/storage.json` (global state) | Not explicit | Not documented | `~/.codex/config.toml` | GitHub repo/org settings | `~/.arc/trusted-workspaces.json` (external to workspace) |
| **Trust binding** | Folder path + parent folder inheritance | N/A | Working directory | Working directory + git status | Repository + org | Canonical path + machine ID + user ID |
| **Self-authorization prevention** | N/A (trust is global state) | N/A | N/A | N/A | N/A (managed env) | ✅ Explicitly ignores `.arc/trusted` in workspace |
| **Restricted mode capabilities** | Edit files, browse code; blocks terminal, tasks, debugging, workspace settings, untrusted extensions | N/A | Read-only: can read files, answer questions | Read-only sandbox: no writes, no network | N/A (always trusted) | Read-only chat/context; blocks writes, shell, paid calls, runtime |
| **Terminal/shell in restricted** | Blocked; prompts to trust first | Always available | Blocked in read-only | Blocked in read-only sandbox | Available | Blocked |
| **Extension/tool gating** | Extensions disabled/limited if not opted into Workspace Trust | N/A | N/A | N/A | N/A | Runtime execution blocked; adapters cannot run |
| **Sandbox enforcement** | None (relies on extension trust declarations) | None | N/A | OS-level: Seatbelt (macOS), bwrap+seccomp (Linux), Windows sandbox | Container isolation | Subprocess env allowlist (P0); Docker (P3); Firecracker (P5+) |
| **Approval modes** | N/A | Agent/Composer toggle | 6 permission modes | `workspace-write`/`read-only`/`danger-full-access` + `on-request`/`untrusted`/`never` | N/A | Plan/Build/Auto with policy YAML |
| **Network controls** | N/A | N/A | N/A | Off by default; configurable per sandbox | Full access | Restricted by trust level; allowed_hosts config |
| **Paid-call gating** | N/A | N/A | Permission rules per tool | N/A | N/A | ✅ Paid-call cards with approval; blocked in untrusted |
| **Parent folder trust** | ✅ Trust parent → all subfolders trusted | N/A | N/A | N/A | N/A | ❌ Not specified |
| **Multi-root workspaces** | Adding untrusted folder → entire workspace switches to Restricted Mode | N/A | N/A | N/A | N/A | ❌ Not specified |
| **Empty window trust** | Trusted by default; configurable | N/A | N/A | N/A | N/A | ❌ Not specified |
| **Trust inheritance** | Parent folder trust cascades to subfolders | N/A | N/A | N/A | Codespaces/dev containers auto-trusted | ❌ Not specified |
| **Trust expiry** | None | N/A | N/A | N/A | N/A | ❌ Not specified |
| **Symlink handling** | Resolves to real path | N/A | N/A | N/A | N/A | ✅ Spec says "symlinked paths resolve before trust check" |
| **Auto-review** | N/A | N/A | N/A | ✅ `auto_review` reviewer agent evaluates approval requests | N/A | ❌ Not specified |
| **Protected paths in trusted** | N/A | N/A | N/A | `.git`, `.agents`, `.codex` read-only even in writable root | N/A | ❌ Not specified |
| **Filesystem deny-reads** | N/A | N/A | N/A | ✅ Glob-based deny-read profiles | N/A | ❌ Not specified |
| **OTel audit trail** | N/A | N/A | N/A | ✅ Opt-in OTel with redacted prompts | N/A | ❌ Not specified (P4 scope) |

**Sources:**
- VS Code: https://code.visualstudio.com/docs/editor/workspace-trust
- Codex CLI: https://developers.openai.com/codex/agent-approvals-security, https://developers.openai.com/codex/concepts/sandboxing
- Claude Code: https://code.claude.com/docs/llms.txt (overview), https://code.claude.com/docs/en/settings (permissions)

---

## Gaps

### Critical Gaps (v0.1 blockers)

1. **No parent folder trust** — VS Code supports trusting a parent folder to cascade trust to all subfolders. ARC requires per-workspace approval, which is tedious for users with many repos under a common directory (e.g., `~/dev/trusted/`). This is a UX friction point.

2. **No multi-root workspace trust** — The spec does not address Theia multi-root workspaces. If a user adds an untrusted folder to a trusted multi-root workspace, the behavior is undefined. VS Code switches the entire workspace to Restricted Mode.

3. **No protected paths within trusted workspaces** — Codex CLI protects `.git`, `.agents`, `.codex` as read-only even in `workspace-write` mode. ARC has no equivalent. A trusted workspace should still protect its own trust/config markers from agent writes.

4. **Trust CLI commands not fully specified** — ADR-006 specifies `arc workspace trust`, `arc workspace untrust`, `arc workspace trust-status`, `arc workspace list`, but the UX spec (§10.4 help text) does not include these commands. They need to appear in `/help` or `arc-studio advanced`.

5. **Machine ID + user ID binding not implemented** — The spec says trust binds to "canonical path + machine ID + user ID" but `trust.py` only stores canonical path. No machine ID or user ID is recorded or verified. This means a trust DB copied to another machine would incorrectly grant trust.

### High-Priority Gaps

6. **No trust expiry** — Trust is permanent once granted. VS Code also has no expiry, but for a high-assurance tool, periodic re-confirmation (e.g., after 90 days or after workspace content changes significantly) would be defensible.

7. **No empty window trust behavior** — VS Code trusts empty windows by default (no folder open). ARC spec does not define behavior when no workspace is open.

8. **No symlink escape detection** — The spec says "symlinked paths resolve before trust check" but does not specify what happens when a trusted workspace contains symlinks to untrusted locations. An agent could follow a symlink to write outside the trusted boundary.

9. **No mounted drive handling** — The spec does not address network-mounted drives, FUSE filesystems, or cloud-synced directories (e.g., iCloud Drive, OneDrive). These present unique trust challenges because content can change remotely.

10. **No remote workspace trust** — The spec does not address remote workspaces (SSH, Dev Containers, Codespaces-like environments). VS Code auto-trusts Codespaces and attached containers as managed environments.

11. **No auto-review for approvals** — Codex CLI has an `auto_review` mode where a reviewer agent evaluates approval requests before surfacing them to the user. ARC has no equivalent, which means every approval is manual.

### Medium-Priority Gaps

12. **No filesystem deny-read profiles** — Codex supports glob-based deny-read profiles (e.g., `**/*.env` = `none`) within otherwise writable workspaces. ARC has no equivalent for sensitive files within trusted workspaces.

13. **No OTel audit trail** — Codex supports opt-in OTel telemetry for security auditing. ARC has no equivalent observability for trust/security events.

14. **Trust banner has no "Trust Parent" option** — VS Code's trust dialog offers "Trust Parent" for cascading trust. ARC's banner only offers "Trust this workspace" and "Stay untrusted".

15. **No trust change audit log** — Trust grants and revocations are not journaled. For high-assurance use, trust changes should be recorded with timestamp, user, and reason.

16. **`allow_if_no_db` is a security hole** — `ensure_trusted()` accepts `allow_if_no_db=True` which allows execution when no trust DB exists. This means first-run on any machine bypasses trust entirely. This contradicts "default is untrusted unless explicit approval."

### Low-Priority Gaps

17. **No trust export/import** — Users cannot export trust settings to sync across machines.

18. **No trust reason history** — When a user trusts a workspace, the `note` field is optional and rarely filled. No structured reason is captured.

19. **No visual distinction for partial trust** — The spec defines `PARTIAL` trust level but does not specify what capabilities it enables or how it differs from untrusted in the UI.

---

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **Add parent folder trust** | Reduces UX friction for users with many repos under a common directory. VS Code has this; it's expected behavior. | v0.1 | Low — parent trust is a read-only cascade, no new security surface | §7.18: add "Trust Parent" button to trust dialog; §9 WorkspaceTrustBanner: add `onTrustParent` prop; trust.py: add parent path resolution |
| **Add machine ID + user ID to trust binding** | Prevents trust DB portability attacks. Without this, copying `~/.arc/trusted-workspaces.json` to another machine grants trust to the same paths on that machine. | v0.1 | Low — machine ID is stable on macOS/Linux; user ID from `os.getuid()` or `whoami` | trust.py: add `machine_id` and `user_id` fields to trust DB entries; `ensure_trusted()`: verify current machine/user matches stored values |
| **Add protected paths within trusted workspaces** | Even trusted workspaces should protect `.arc/`, `.git/`, and trust markers from agent writes. Codex CLI does this. Prevents accidental or malicious self-modification of trust/config. | v0.1 | Low — read-only protection on specific paths is straightforward | ADR-006: add protected paths section; trust.py: add `is_protected_path()` check; adapter execution: enforce protected paths |
| **Add trust CLI to /help** | Trust commands exist in ADR-006 but are absent from §10.4 help text. Users cannot discover trust management. | v0.1 | None — documentation only | §10.4: add `/workspace trust`, `/workspace untrust`, `/workspace trust-status` to help text |
| **Fix `allow_if_no_db` default** | Current default (`allow_if_no_db=False`) is correct, but the parameter exists and could be misused. Remove the parameter or hard-code `False`. | v0.1 | Low — first-run UX needs a trust prompt, not silent bypass | trust.py: remove `allow_if_no_db` parameter; first-run should show trust dialog, not bypass |
| **Define multi-root workspace trust** | Theia supports multi-root workspaces. If an untrusted folder is added, behavior must be defined. Follow VS Code: entire workspace switches to untrusted. | v0.1 | Medium — requires Theia integration | §8.6: add multi-root trust behavior; protocol: add multi-root trust check |
| **Define empty window trust** | When no workspace is open, trust behavior is undefined. Follow VS Code: empty windows are trusted by default (no workspace to protect). | v0.1 | Low — simple default | §7.18: add empty window trust behavior |
| **Add symlink escape detection** | A trusted workspace could contain symlinks to untrusted locations. Agent writes through symlinks bypass trust boundary. | v0.2 | Medium — requires runtime symlink resolution during file operations | ADR-006: add symlink policy; isolation providers: resolve symlinks before write validation |
| **Add trust expiry with re-confirmation** | Permanent trust is risky for workspaces that change hands or are cloned from untrusted sources. 90-day re-confirmation is defensible for high-assurance. | v0.2 | Low — expiry check is simple; re-confirmation uses existing dialog | trust.py: add `trusted_at` timestamp; `resolve_trust()`: check expiry; §7.18: add re-confirmation dialog copy |
| **Add mounted drive warnings** | Network-mounted drives and cloud-synced directories can change remotely. Trust should warn about these and optionally require re-confirmation. | v0.2 | Medium — detection of mount types is platform-specific | trust.py: add mount type detection; §7.18: add mounted drive warning in trust dialog |
| **Add auto-review for approvals** | Codex's `auto_review` mode reduces manual approval burden while maintaining security. ARC should support this for P4 high-assurance. | v0.3 | High — requires LLM-based reviewer agent | §7.13: add auto-review policy option; P4 implementation plan |
| **Add filesystem deny-read profiles** | Sensitive files (`.env`, credentials) within trusted workspaces should be unreadable by agents. Codex supports this. | v0.2 | Low — glob-based deny-list is straightforward | ADR-006: add deny-read profiles; isolation providers: enforce deny-reads |
| **Add trust change audit log** | For compliance, trust grants/revocations should be journaled with timestamp, user, and reason. | v0.2 | Low — append-only log is simple | trust.py: add audit log append on trust/untrust; P4 audit integration |
| **Define remote workspace trust** | SSH, Dev Containers, and remote workspaces need trust semantics. Auto-trust managed environments (like VS Code Codespaces). | v0.3 | Medium — requires remote environment detection | §7.18: add remote workspace trust behavior; ADR-006: add remote trust section |
| **Implement PARTIAL trust level** | Currently defined but not specified. Should allow read + limited write (workspace only) + no shell + no paid calls. | v0.2 | Medium — requires capability gating per trust level | §7.18: define PARTIAL capabilities; trust.py: implement PARTIAL resolution |

---

## Recommended Decisions

### Lock for v0.1

1. **Default is UNTRUSTED** — Confirmed. No change. Every new workspace requires explicit trust approval.
2. **Trust stored outside workspace** — Confirmed. `~/.arc/trusted-workspaces.json`. No `.arc/trusted` self-authorization.
3. **Trust binds to canonical path + machine ID + user ID** — Must implement machine/user ID binding for v0.1. Current implementation only stores path.
4. **Untrusted mode allows read-only chat/context** — Confirmed. Blocks writes, shell, paid calls, runtime execution.
5. **Parent folder trust** — Add for v0.1. Follow VS Code pattern. "Trust Parent" button in trust dialog.
6. **Protected paths within trusted** — Add for v0.1. `.arc/`, `.git/` are read-only even in trusted workspaces.
7. **Trust CLI in /help** — Add trust commands to §10.4 help text for v0.1.
8. **Remove `allow_if_no_db`** — First-run should show trust dialog, not silently bypass. Remove the parameter.
9. **Multi-root workspace trust** — Define for v0.1: adding untrusted folder switches entire workspace to untrusted.
10. **Empty window trust** — Define for v0.1: empty windows (no folder open) are trusted by default.

### Defer to v0.2

11. **Trust expiry** — 90-day re-confirmation. Not a v0.1 blocker.
12. **Symlink escape detection** — Runtime symlink resolution is complex. Defer.
13. **Mounted drive warnings** — Platform-specific detection. Defer.
14. **PARTIAL trust level implementation** — Define capabilities but defer implementation.
15. **Filesystem deny-read profiles** — Useful but not critical for v0.1.
16. **Trust change audit log** — P4 audit integration will cover this.

### Defer to v0.3

17. **Auto-review for approvals** — Requires LLM-based reviewer agent. Complex.
18. **Remote workspace trust** — SSH/Dev Container trust semantics. Requires remote environment detection.
19. **OTel audit trail** — Observability is important but not a v0.1 blocker.

---

## Specific Spec Edits

### ARC_STUDIO_UX_SPEC.md

- **§7.18** (First-Untrusted-Workspace Flow):
  - Add "Trust Parent" button: `[Trust this workspace] [Trust Parent] [Stay untrusted] [Learn more]`
  - Add copy for parent trust: `Trust {parent_path} and all subfolders?`
  - Add empty window behavior: `When no workspace is open, ARC Studio runs in trusted mode. Opening a folder triggers the trust dialog.`
  - Add multi-root behavior: `Adding an untrusted folder to a trusted multi-root workspace switches the entire workspace to untrusted mode.`

- **§7.18** (Trust binding):
  - Change "Trust binds to canonical path + machine ID + user ID" to "Trust binds to canonical path + machine ID (`/etc/machine-id` or `IOPlatformUUID` on macOS) + user ID (`os.getuid()`). Trust entries that do not match the current machine or user are treated as untrusted."

- **§9** (WorkspaceTrustBanner):
  - Add `onTrustParent` prop to `WorkspaceTrustBannerProps`
  - Add `parentPath` prop (optional, shown when parent folder trust is available)

- **§10.3** (Confirmations):
  - Add trust confirmation copy: `Trust {workspace_path}? This allows ARC Studio to write files, run commands, and call paid providers in this workspace.`
  - Add parent trust confirmation: `Trust {parent_path} and all current and future subfolders?`

- **§10.4** (Help Text):
  - Add to "Configuration" section:
    ```
    /workspace trust      mark this workspace as trusted
    /workspace untrust    remove trust for this workspace
    /workspace trust-status  show current trust level
    ```

- **§8.6** (Config):
  - Add "Workspace Trust" tab content: list of trusted workspaces, trust/untrust actions, parent folder trust, trust history

### ADR-006

- **Trust Resolution section**:
  - Add machine ID + user ID binding to `resolve_trust()` code example
  - Add parent folder trust resolution (check parent paths in trust DB)
  - Remove `.arc/trusted` marker check (contradicts external trust storage)

- **Add new section: Protected Paths**:
  ```
  Even in TRUSTED workspaces, the following paths are read-only:
  - {workspace}/.arc/ (recursive)
  - {workspace}/.git/ (recursive)
  - {workspace}/trusted-workspaces.json (if present)
  ```

- **Add new section: Symlink Policy** (deferred to v0.2):
  ```
  Symlinks within trusted workspaces are resolved to their real paths before
  write operations. Writes through symlinks to untrusted locations are blocked.
  ```

### trust.py

- Add `machine_id` and `user_id` fields to trust DB entries
- Add `trusted_at` timestamp to trust DB entries (for future expiry)
- Add `is_protected_path()` function
- Remove `allow_if_no_db` parameter from `ensure_trusted()`
- Add parent folder trust resolution in `resolve_trust()`
- Add trust change audit logging (append to `~/.arc/trust-audit.jsonl`)

---

## Acceptance Criteria

### v0.1 Trust Core

- [ ] New workspace triggers trust dialog before any write/shell/paid-call
- [ ] Trust dialog offers "Trust this workspace", "Trust Parent", "Stay untrusted", "Learn more"
- [ ] Trust stored in `~/.arc/trusted-workspaces.json` (not in workspace)
- [ ] `.arc/trusted` file in workspace is ignored for trust decisions
- [ ] Trust entry includes canonical path, machine ID, user ID, timestamp
- [ ] Trust DB copied to another machine does NOT grant trust on that machine
- [ ] Untrusted mode blocks: file writes, shell execution, paid calls, runtime execution
- [ ] Untrusted mode allows: read-only file browsing, chat questions, static workflow detection
- [ ] Protected paths (`.arc/`, `.git/`) are read-only even in trusted workspaces
- [ ] `/workspace trust`, `/workspace untrust`, `/workspace trust-status` commands work
- [ ] Trust commands appear in `/help`
- [ ] Trust status visible in `/status` and IDE status bar
- [ ] Trust can be revoked from `/config > Workspace Trust`
- [ ] Empty window (no folder) runs in trusted mode
- [ ] Multi-root workspace: adding untrusted folder switches entire workspace to untrusted
- [ ] `allow_if_no_db` parameter removed from `ensure_trusted()`
- [ ] All trust tests pass (existing + new tests for machine/user ID binding)

### v0.1 Trust UI

- [ ] `WorkspaceTrustBanner` renders with correct copy and actions
- [ ] Trust dialog blocks chat input until dismissed
- [ ] Trust changes reflected immediately in status bar and config UI
- [ ] "Trust Parent" cascades to all subfolders
- [ ] Trusted workspaces list visible in Config > Workspace Trust tab

### v0.2 Trust Extensions

- [ ] Trust expiry (90-day) with re-confirmation dialog
- [ ] Symlink escape detection and blocking
- [ ] PARTIAL trust level implemented with defined capabilities
- [ ] Filesystem deny-read profiles for sensitive files
- [ ] Trust change audit log (`~/.arc/trust-audit.jsonl`)
- [ ] Mounted drive detection and warnings

### v0.3 Trust Advanced

- [ ] Auto-review for approval requests
- [ ] Remote workspace trust (SSH, Dev Containers)
- [ ] OTel audit trail for trust/security events
- [ ] Trust export/import for cross-machine sync

---

## Reject / Do Not Build

| Idea | Reason |
|---|---|
| **Trust based on git remote URL** | Git remotes can be changed, forked, or spoofed. Path-based trust is more reliable. |
| **Trust based on file hash/signature** | Impractical for workspaces that change constantly. Signature verification adds complexity without proportional security benefit. |
| **Per-file trust granularity** | Too complex for v0.1. Workspace-level trust is the right granularity for an agent runtime cockpit. File-level trust is a different product (e.g., document-level security). |
| **Trust expiry shorter than 90 days** | Too much UX friction. Users will re-confirm frequently and develop "trust fatigue." 90 days balances security and usability. |
| **Automatic trust for version-controlled folders** | Codex CLI does this but it's risky. A git repo can be cloned from any source. Version control is not evidence of trustworthiness. Keep explicit approval. |
| **Trust inheritance from parent organization (GitHub org, etc.)** | Requires network calls and external identity. Out of scope for a local-first tool. |
| **Biometric/2FA for trust approval** | Overkill for a local development tool. Machine ID + user ID + explicit approval is sufficient for the threat model. |
| **Trust scoring based on workspace content analysis** | Interesting but speculative. Requires ML-based analysis of code quality, dependency trust, etc. Not a v0.1-v0.3 priority. |
| **Workspace trust as a Theia extension** | Trust is a backend security concern, not a UI feature. Theia displays trust status but does not enforce it. Enforcement lives in Python daemon. |
| **Separate trust levels per runtime** | Overly complex. Trust is a workspace-level property, not a runtime-level property. If a workspace is untrusted, no runtime should execute. |
| **Trust delegation (user A trusts workspace, user B inherits)** | Multi-user trust is out of scope. ARC is a local-first, single-user tool. Multi-user scenarios require a different architecture. |
| **`--unsafe` bypass for trust** | The spec already says `--unsafe` requires explicit confirmation. Do not add a `--skip-trust` or `--force-trust` flag. Trust is not optional. |
| **Trust based on workspace age (e.g., auto-trust after 30 days)** | Time is not evidence of trust. A malicious workspace can sit for 30 days unchanged. Keep explicit approval. |
