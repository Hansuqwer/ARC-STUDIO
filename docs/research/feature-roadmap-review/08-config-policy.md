# Config / Policy Review

## Current ARC Spec

### Config Model (ADR-001, model.py, loader.py)

ARC Studio uses a YAML-based configuration system with a well-defined schema (`ArcConfig` v1) and 5-level precedence:

1. **CLI arguments** — explicit flags always win
2. **Environment variables** — `ARC_*` prefixed vars override config files
3. **Workspace config** — `<workspace>/.arc/config.yaml` (project-specific)
4. **User config** — `~/.arc/config.yaml` (user-level defaults)
5. **Built-in defaults** — stub backend, dry-run, localhost-only

The `ArcConfig` model (model.py:87-100) contains 11 sub-configs:
- `workspace` — name, trust_level (auto/trusted/partial/untrusted)
- `runtime` — default, auto_detect, fallback
- `execution` — isolation, default_profile, timeout_seconds, allow_paid_calls, background
- `providers` — default_provider, default_model, routing_mode, dry_run, accounts
- `swarmgraph` — provider, base_url, run_backend, cli_path
- `langgraph` — export target
- `crewai` — export target
- `context` — search_provider, token env var references
- `telemetry` — otel_endpoint, otel_genai_experimental
- `ui` — show_mock_warnings, compact_sidebar, auto_open_sidebar
- `security` — redact_secrets, audit_enabled, audit_secret_env, allowed_paths, allowed_hosts

The loader (loader.py) implements deep-merge semantics: user config overlays defaults, workspace overlays user, env overlays workspace. Only 4 env vars are explicitly mapped (`ENV_TO_CONFIG` at loader.py:31-36). The rest are read directly by adapters.

**Secrets policy:** Config files must never contain API keys. All secret references use env var names. `.arc/` is in `.gitignore` but config is designed to be safe to commit.

### Policy Model (Spec only — NOT implemented)

Policy is defined in §7.13.1 and §8.6 of ARC_STUDIO_UX_SPEC.md but **no implementation exists in Python code**. The spec defines:

**Policy file locations:**
- Project: `.arc/policy.yaml`
- User: `~/.config/arc-studio/policy.yaml`

**Policy precedence (3 levels):**
1. Project `.arc/policy.yaml` (highest)
2. User `~/.config/arc-studio/policy.yaml`
3. Built-in safe defaults (lowest)

**Approval policy schema (§7.13.1):**
```yaml
approvals:
  paid_calls: ask
  destructive_writes: ask
  trust_changes: deny
  shell_exec: deny
  phase_advance: ask
```

Allowed values: `ask`, `auto`, `deny`. v0.1 default keeps `trust_changes` and `shell_exec` denied even in Auto mode.

**Security constraint:** Project policy cannot weaken user policy for `shell_exec` or `trust_changes`. User policy can impose stricter limits.

### IDE Config UI (§8.6)

Spec defines a full-panel Config with tabs: Runtime, Model, Providers, Workspace Trust, Profiles, Graph, Advanced. Save writes `.arc/config.yaml`; user-wide changes write `~/.config/arc-studio/config.yaml`. Dirty state shows `config unsaved` in status bar. Validation errors block save.

**Note:** The spec uses `~/.config/arc-studio/config.yaml` for user config, but the implementation (loader.py:28) uses `~/.arc/config.yaml`. This is a **spec/implementation mismatch**.

### CLI Config UI (§7.3)

Interactive `/config` form with radio buttons for runtime, model dropdown, provider status, mode toggle, workspace trust, graph layout, and theme. Keys: arrows move, Space toggles, Enter saves, Esc cancels.

### What's Missing

- **Policy implementation:** Zero Python code for `.arc/policy.yaml` loading, validation, or enforcement
- **Config UI:** No IDE Config tab exists; no CLI `/config` interactive form
- **Schema versioning:** `version: 1` exists but no migration logic
- **Config change detection:** No file watching or hot-reload
- **Config validation errors:** No user-friendly error messages for invalid YAML
- **Policy enforcement:** `RunProfile` in profiles.py is a separate system; not connected to policy.yaml
- **User config path mismatch:** Spec says `~/.config/arc-studio/`, code uses `~/.arc/`

---

## Comparable Products / Research

| Feature | Claude Code | OpenCode | Codex CLI | Cursor | Windsurf | VS Code | ARC Studio (current) |
|---|---|---|---|---|---|---|---|
| **Config format** | JSON (`settings.json`) | JSON/JSONC (`opencode.json`) | TOML (`codex.toml`) | JSON (settings) + `.cursorrules` | JSON (settings) + Memories | JSON (`settings.json`) | YAML (`config.yaml`) |
| **Project config** | `.claude/settings.json` | `opencode.json` in project root | `codex.toml` in project | `.cursorrules` | `.windsurf/rules/` | `.vscode/settings.json` | `.arc/config.yaml` |
| **User config** | `~/.claude/settings.json` | `~/.config/opencode/opencode.json` | `~/.codex/config.toml` | Global settings | Global settings | User settings | `~/.arc/config.yaml` |
| **Local config** | `.claude/settings.local.json` (gitignored) | N/A (project = highest) | N/A | N/A | N/A | N/A | N/A |
| **Managed/org config** | Server-managed, MDM plist/registry, file-based in system dirs | Remote `.well-known/opencode`, file-based in system dirs, MDM `.mobileconfig` | N/A | N/A | N/A | N/A | N/A |
| **Precedence levels** | 5 (managed > CLI > local > project > user) | 8 (remote > global > custom > project > .opencode > inline > managed > MDM) | 3 (CLI > project > user) | 3 (workspace > user > default) | 3 (project > user > default) | 3 (workspace > user > default) | 5 (CLI > env > workspace > user > defaults) |
| **Config merge** | Deep merge across scopes | Deep merge across all sources | Override (not merge) | Override per scope | Override per scope | Deep merge | Deep merge |
| **Interactive config UI** | `/config` TUI with tabs | `/connect` for providers, JSON editing | N/A (TOML editing) | Settings UI + `.cursorrules` editing | Settings UI + Memories | Settings UI with editor | `/config` TUI (spec only) |
| **Schema validation** | `$schema` JSON schema, published at schemastore.org | `$schema` JSON schema at `opencode.ai/config.json` | N/A | N/A | N/A | JSON schema built-in | Pydantic validation only |
| **Policy/permissions** | `permissions.allow/deny` in settings.json, managed-only settings, `autoMode` config | `permission` config with `allow/ask/deny` per tool, granular pattern matching | Approval modes + sandbox | Agent/Composer modes, `.cursorrules` | Code/Chat toggle, Memories | Chat/Agent/Edit modes | `.arc/policy.yaml` (spec only, NOT implemented) |
| **Policy precedence** | Managed rules cannot be overridden; `allowManagedPermissionRulesOnly` blocks user/project rules | Managed settings (MDM/file) override all; per-agent permission overrides | N/A | N/A | N/A | N/A | Project cannot weaken user for `shell_exec`/`trust_changes` (spec only) |
| **Secret storage** | OAuth + keyring, env vars in `env` key | `/connect` + env vars, `{env:VAR}` substitution | Env vars, keychain | Settings UI (encrypted) | Settings UI | Settings sync (encrypted) | Env vars only, keyring planned |
| **Config hot-reload** | No (restart needed) | No (restart needed) | No | Yes (settings.json watched) | Yes | Yes | No |
| **Config migration** | Automatic backup (5 timestamped copies) | N/A | N/A | N/A | N/A | Automatic | None |
| **Env var override** | `env` key in settings.json | `{env:VAR}` substitution in JSON | Direct env vars | N/A | N/A | N/A | `ARC_*` prefix mapping (only 4 mapped) |
| **File variable substitution** | N/A | `{file:path}` for including file contents | N/A | N/A | N/A | N/A | N/A |
| **Config init command** | Automatic on first run | `/init` creates `AGENTS.md` | N/A | N/A | N/A | N/A | `arc config init` (implemented, creates default YAML) |
| **Config show command** | `/config` shows current | `opencode debug config` | N/A | Settings UI | Settings UI | Settings UI | `arc config show` (read-only) |

### Key Patterns Worth Copying

1. **Claude Code's scope system** — Managed > CLI > Local > Project > User with explicit "cannot weaken" rules for managed settings. This is the most mature policy model in the market.
2. **OpenCode's granular permissions** — `permission.bash."git *": "allow"` pattern matching with last-match-wins semantics. Far more useful than ARC's binary `ask/auto/deny` per category.
3. **OpenCode's variable substitution** — `{env:VAR}` and `{file:path}` in config files. Useful for keeping secrets out of config while allowing references.
4. **Claude Code's managed settings** — MDM/registry/file-based managed settings for enterprise deployment. ARC should plan for this in v0.2+.
5. **VS Code's hot-reload** — Settings changes apply immediately without restart. ARC should aim for this for cosmetic config (UI preferences) but require restart for runtime config.
6. **JSON schema validation** — Both Claude Code and OpenCode publish `$schema` URLs for editor autocomplete. ARC should publish a YAML schema.

### Patterns to Avoid

1. **Codex CLI's TOML** — TOML is less readable for nested structures and less common in the AI tooling ecosystem. Stick with YAML (ADR-001).
2. **OpenCode's 8-level precedence** — Overly complex. ARC's 5-level model is sufficient.
3. **Cursor's `.cursorrules`** — Mixing instructions with config creates ambiguity. Keep policy separate from config (ARC already does this correctly).

---

## Gaps

### Critical Gaps (v0.1 blockers)

1. **Policy is entirely unimplemented** — `.arc/policy.yaml` exists only in spec text. No Python loader, no validation, no enforcement. `RunProfile` in profiles.py is a parallel system that doesn't connect to the policy model.
2. **User config path mismatch** — Spec says `~/.config/arc-studio/config.yaml` (§8.6), implementation uses `~/.arc/config.yaml` (loader.py:28). This must be resolved before v0.1.
3. **No IDE Config UI** — §8.6 specifies a full-panel Config with tabs. Nothing exists in `packages/arc-extension`.
4. **No CLI `/config` interactive form** — §7.3 specifies a TUI form. Nothing exists beyond `arc config show` (read-only).
5. **No policy enforcement in execution path** — The `approvals` policy (paid_calls, destructive_writes, trust_changes, shell_exec) is not wired into `JobSupervisor`, adapters, or HITL flow.

### High Gaps (v0.1 should-have)

6. **Only 4 env vars mapped** — `ENV_TO_CONFIG` has 4 entries. ~40+ `ARC_*` env vars exist but are not mapped to config keys, creating a dual-system problem.
7. **No schema versioning/migration** — `version: 1` exists but no migration logic for future schema changes.
8. **No config validation errors for users** — Pydantic validation happens internally but produces stack traces, not user-friendly messages.
9. **No config change detection** — Config is read once at startup. Changes require restart.
10. **Policy "cannot weaken" rule not implemented** — The spec says project policy cannot weaken user policy for `shell_exec`/`trust_changes`, but no code enforces this.

### Medium Gaps (v0.2)

11. **No managed/org config** — No equivalent to Claude Code's managed settings or OpenCode's MDM support.
12. **No local config** — No `.arc/config.local.yaml` for per-user-per-project overrides (gitignored).
13. **No `$schema` URL** — No published YAML schema for editor autocomplete/validation.
14. **No variable substitution** — No `{env:VAR}` or `{file:path}` support like OpenCode.
15. **No config backup** — Claude Code keeps 5 timestamped backups. ARC has nothing.
16. **Policy granularity too coarse** — `ask/auto/deny` per category vs OpenCode's pattern-matching per tool invocation.
17. **No per-agent policy** — OpenCode supports per-agent permission overrides. ARC does not.

### Low Gaps (v0.3+)

18. **No config hot-reload** — VS Code and Cursor watch config files. ARC requires restart.
19. **No config diff/preview** — No way to see what changed before saving.
20. **No config export/import** — No way to share config between workspaces or team members.

---

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **P1: Implement policy.yaml loader** | Policy is spec-only. Must implement `PolicyConfig` model, `load_policy()` loader, and 3-level precedence before any enforcement can work. | v0.1 | Low. Straightforward Pydantic model + YAML loader mirroring config/loader.py. | §8.6: Add explicit policy schema definition. §7.13.1: Confirm `phase_advance` is reserved. |
| **P2: Resolve user config path** | Spec says `~/.config/arc-studio/`, code uses `~/.arc/`. Must pick one. Recommend `~/.config/arc-studio/` for XDG compliance on macOS/Linux. | v0.1 | Medium. Breaks any existing `~/.arc/config.yaml` users. Need migration or dual-read. | ADR-001 §Config File Locations: Update user config path. loader.py: Update `USER_CONFIG_PATH`. |
| **P3: Wire policy into execution path** | Policy must actually block/allow actions. Connect `PolicyConfig` to `JobSupervisor.start_run()`, HITL flow, and shell execution gates. | v0.1 | Medium. Requires careful integration with existing `RunProfile` system. May need to merge or deprecate `RunProfile`. | §7.13.1: Add enforcement points. §8.6: Clarify policy vs profile relationship. |
| **P4: Implement "cannot weaken" enforcement** | Security requirement: project policy cannot weaken user policy for `shell_exec`/`trust_changes`. Must be enforced in code, not just spec text. | v0.1 | Low. Simple comparison logic in policy loader. | §8.6: Add explicit algorithm for "cannot weaken" check. |
| **P5: Add IDE Config tab** | §8.6 specifies full-panel Config. Currently no way to edit config in IDE. | v0.1 | Medium-High. Requires React components, backend service for read/write, validation. | §8.6: Already specified. No edits needed. |
| **P6: Add CLI `/config` interactive form** | §7.3 specifies TUI config editor. Currently only `arc config show` exists. | v0.1 | Medium. Requires rich/Textual TUI. | §7.3: Already specified. No edits needed. |
| **P7: Map all ARC_* env vars to config keys** | 40+ env vars exist but only 4 are mapped. Creates confusion about which system controls what. | v0.1 | Low. Tedious but straightforward mapping exercise. | ADR-001 §Environment Variable Mapping: Add full table. |
| **P8: Add schema version migration** | `version: 1` exists but no migration path. Future schema changes will break existing configs. | v0.2 | Low. Standard migration pattern: detect version, apply transformers, write updated file. | ADR-001 §Migration Path: Add migration algorithm. |
| **P9: Add user-friendly config validation errors** | Pydantic errors are developer-facing. Users need "Invalid value for runtime.default: 'foo' is not a known runtime." | v0.1 | Low. Wrap Pydantic ValidationError with friendly messages. | §8.6: Add validation error examples. |
| **P10: Add local config file** | `.arc/config.local.yaml` for per-user-per-project overrides (gitignored). Matches Claude Code's `settings.local.json`. | v0.2 | Low. Adds one more precedence level. | ADR-001 §Config File Locations: Add local config. |
| **P11: Publish YAML schema** | Enable editor autocomplete via `$schema` or YAML language server. | v0.2 | Low. Generate from Pydantic model. | ADR-001: Add schema URL. |
| **P12: Add granular policy rules** | OpenCode's pattern-matching (`bash."git *": "allow"`) is far more useful than binary per-category rules. | v0.2 | Medium. Requires rule engine, pattern matching, last-match-wins semantics. | §7.13.1: Expand policy schema with granular rules. |
| **P13: Add config file watching** | Hot-reload cosmetic config (UI preferences) without restart. Runtime config still requires restart. | v0.3 | Medium. File watching + selective reload + state invalidation. | §8.6: Add hot-reload behavior description. |
| **P14: Add managed/org config** | Enterprise deployment needs MDM/registry/file-based managed settings. | v0.2 | Medium-High. Platform-specific code (macOS plist, Windows registry). | New section in spec. |
| **P15: Add config backup** | Claude Code keeps 5 timestamped backups. Prevents config loss from bugs. | v0.2 | Low. Simple file copy on save. | §8.6: Add backup behavior. |
| **P16: Separate cosmetic vs runtime config** | UI preferences (theme, density) should hot-reload; runtime config (isolation, providers) should require restart. | v0.2 | Low. Classification + different reload strategies. | §8.6: Add config categories. |

---

## Recommended Decisions

### D1: User config path → `~/.config/arc-studio/`

**Decision:** Move user config from `~/.arc/` to `~/.config/arc-studio/` to match the spec and XDG conventions.

**Migration:** On first load, check both paths. If `~/.arc/config.yaml` exists and `~/.config/arc-studio/config.yaml` does not, read from old path and log a deprecation warning. Do NOT auto-migrate (user may have scripts referencing old path).

**Rationale:**
- The spec already says `~/.config/arc-studio/` (§8.6)
- XDG Base Directory spec recommends `~/.config/` for user config
- macOS/Linux convention
- Windows: `%LOCALAPPDATA%\arc-studio\config.yaml`

**Spec edit:** ADR-001 §Config File Locations: Update user config path from `~/.arc/config.yaml` to `~/.config/arc-studio/config.yaml`.

### D2: Policy is file-only in v0.1, UI in v0.2

**Decision:** Policy is edited via file only in v0.1. No IDE Policy tab or CLI `/policy` command until v0.2.

**Rationale:**
- Policy is security-relevant. File editing forces deliberate review.
- UI editing risks accidental policy changes.
- Claude Code's permission model is also primarily file-based (`settings.json`).
- v0.1 scope is already tight. Policy UI can wait.

**Spec edit:** §8.6: Add note: "Policy is file-only in v0.1. Policy tab reserved for v0.2."

### D3: Project policy CANNOT weaken user policy for security-critical fields

**Decision:** Enforce the spec's "cannot weaken" rule in code. The algorithm:

```python
def merge_policies(user_policy: PolicyConfig, project_policy: PolicyConfig) -> PolicyConfig:
    """Merge policies, preventing project from weakening user security settings."""
    NON_WEAKENABLE = {"shell_exec", "trust_changes"}
    result = project_policy.model_copy()
    for field in NON_WEAKENABLE:
        user_val = getattr(user_policy.approvals, field)
        proj_val = getattr(project_policy.approvals, field)
        # deny > ask > auto in strictness
        strictness = {"deny": 3, "ask": 2, "auto": 1}
        if strictness.get(proj_val, 0) < strictness.get(user_val, 0):
            setattr(result.approvals, field, user_val)
    return result
```

**Rationale:** This is a security requirement. A cloned repo should not be able to self-authorize shell execution or trust changes by committing a permissive `.arc/policy.yaml`.

**Spec edit:** §8.6: Add explicit algorithm. §7.13.1: Add "deny > ask > auto" strictness ordering.

### D4: Keep YAML format (do not switch to JSON/TOML)

**Decision:** Keep YAML for config and policy files, following ADR-001.

**Rationale:**
- Already implemented and tested
- More readable for nested structures than TOML
- Supports comments (unlike JSON)
- Consistent with existing Python ecosystem (SwarmGraph, Docker Compose, Kubernetes)
- ADR-001 already decided this

**No spec edit needed.**

### D5: Config changes require restart for runtime fields, hot-reload for UI fields (v0.2)

**Decision:** In v0.1, all config changes require restart. In v0.2, classify config fields:
- **Hot-reload (cosmetic):** `ui.*`, `theme`
- **Restart required (runtime):** `runtime.*`, `execution.*`, `providers.*`, `swarmgraph.*`, `langgraph.*`, `crewai.*`, `security.*`

**Rationale:**
- v0.1 scope is tight; hot-reload adds complexity
- Runtime config changes mid-execution are dangerous (isolation, provider routing)
- UI preferences are safe to hot-reload

**Spec edit:** §8.6: Add "Config changes require daemon restart for runtime fields. UI preferences apply immediately (v0.2+)."

### D6: Merge RunProfile into Policy system

**Decision:** The existing `RunProfile` system (profiles.py) and the new `PolicyConfig` system should be merged or clearly separated. Recommend: `RunProfile` becomes an execution profile (env allowlist, backend mode), while `PolicyConfig` handles approval gates (paid_calls, shell_exec, trust_changes).

**Rationale:**
- Two overlapping permission systems is confusing
- `RunProfile` is about execution environment (env, network, shell, secrets, backend)
- `PolicyConfig` is about approval workflow (ask/auto/deny per action type)
- They serve different purposes and can coexist if clearly documented

**Spec edit:** §8.6: Add "Profiles tab" description that maps to `RunProfile`. §7.13.1: Clarify policy vs profile separation.

### D7: Add `phase_advance` as reserved in v0.1 policy

**Decision:** `phase_advance` is in the spec's policy schema but is reserved for v0.2 planner integration. Include it in the `PolicyConfig` model but always resolve to `ask` in v0.1.

**Rationale:** Forward-compatible schema without v0.1 scope expansion.

**Spec edit:** §7.13.1: Already says "reserved for v0.2 planner integration." No edit needed.

---

## Specific Spec Edits

### ARC_STUDIO_UX_SPEC.md

- **§7.3 `/config` Form:** Add "Policy tab reserved for v0.2. Policy is edited via `.arc/policy.yaml` file in v0.1."
- **§7.13.1 `/auto` Policy:** Add strictness ordering: "Policy values have strictness: `deny` (3) > `ask` (2) > `auto` (1). Project policy cannot reduce strictness below user policy for `shell_exec` or `trust_changes`."
- **§7.13.1 `/auto` Policy:** Add "`phase_advance` is reserved in v0.1 and always resolves to `ask`. Planner integration in v0.2."
- **§8.6 Config:** Fix user config path from `~/.config/arc-studio/config.yaml` to match implementation decision (D1). Add: "Config changes require daemon restart for runtime fields (`runtime.*`, `execution.*`, `providers.*`, `security.*`). UI preferences (`ui.*`) apply immediately in v0.2+."
- **§8.6 Config:** Add: "Policy is file-only in v0.1. No Policy tab in IDE. Edit `.arc/policy.yaml` directly."
- **§8.6 Config:** Add "Profiles tab shows execution profiles (`RunProfile`): stub, local-safe, local-paid, gateway. Separate from approval policy."
- **§9 Component Library:** Add `PolicyEditor` component stub (reserved v0.2).

### ADR-001

- **§Config File Locations:** Update user config path: `~/.config/arc-studio/config.yaml` (macOS/Linux), `%LOCALAPPDATA%\arc-studio\config.yaml` (Windows). Add migration note for `~/.arc/config.yaml`.
- **§Environment Variable Mapping:** Add full table mapping all 40+ `ARC_*` env vars to config keys.
- **§Migration Path:** Add Phase 6: "Add schema version migration logic (v0.2)."

### CLI_IDE_REDESIGN_PLAN.md

- **§2.5 Config Model:** Update user config path to match D1. Add policy section referencing §7.13.1.

---

## Acceptance Criteria

### v0.1 Config

- [ ] `load_config()` resolves 5-level precedence correctly (CLI > env > workspace > user > defaults)
- [ ] User config path matches spec (`~/.config/arc-studio/config.yaml` or documented migration from `~/.arc/`)
- [ ] All `ArcConfig` fields validate via Pydantic with user-friendly error messages
- [ ] `arc config init` creates valid `.arc/config.yaml` in workspace
- [ ] `arc config show` displays resolved config with source annotations (which level provided each value)
- [ ] Config files never contain API keys (secrets policy enforced)
- [ ] Env var overrides work for all mapped `ARC_*` variables
- [ ] IDE Config tab renders with Runtime, Model, Providers, Workspace Trust, Profiles tabs (P5)
- [ ] CLI `/config` opens interactive TUI form (P6)

### v0.1 Policy

- [ ] `PolicyConfig` Pydantic model exists with `approvals` sub-model (P1)
- [ ] `load_policy()` resolves 3-level precedence (project > user > defaults) (P1)
- [ ] "Cannot weaken" enforcement works for `shell_exec` and `trust_changes` (P4)
- [ ] Policy is wired into `JobSupervisor.start_run()` for paid_calls gate (P3)
- [ ] Policy is wired into HITL flow for trust_changes and shell_exec gates (P3)
- [ ] `phase_advance` is present in model but always resolves to `ask` (D7)
- [ ] Policy is file-only (no IDE Policy tab, no CLI `/policy` command) (D2)
- [ ] Invalid policy YAML produces user-friendly error message

### v0.1 Integration

- [ ] Config and policy are clearly separated in docs and code
- [ ] `RunProfile` and `PolicyConfig` have documented relationship (D6)
- [ ] All 40+ `ARC_*` env vars are mapped or documented as adapter-direct (P7)
- [ ] Python tests: 20+ new tests for config/policy loading, precedence, validation, "cannot weaken" rule

### v0.2 (future)

- [ ] Schema version migration works (v1 → v2)
- [ ] `$schema` YAML schema published for editor autocomplete
- [ ] Local config file (`.arc/config.local.yaml`) supported
- [ ] Hot-reload for UI config fields
- [ ] IDE Policy tab with validation
- [ ] Granular policy rules (pattern matching like OpenCode)
- [ ] Config backup on save (5 timestamped copies)

---

## Reject / Do Not Build

| Idea | Reason |
|---|---|
| **Switch config format to JSON or TOML** | YAML is already implemented, supports comments, and matches the Python ecosystem. ADR-001 decided this. Switching wastes effort. |
| **8-level precedence like OpenCode** | Overly complex. ARC's 5-level model (CLI > env > workspace > user > defaults) covers all practical cases. Remote/org config can be added in v0.2 as a 6th level if needed. |
| **Policy UI in v0.1** | Policy is security-relevant. File-only editing in v0.1 forces deliberate review. UI adds scope and risk of accidental changes. |
| **Config hot-reload in v0.1** | Adds file watching, state invalidation, and race conditions. v0.1 restart-on-change is acceptable. Hot-reload for cosmetic config in v0.2. |
| **Auto-migrate `~/.arc/` to `~/.config/arc-studio/`** | Silent file moves break scripts and aliases. Dual-read with deprecation warning is safer. |
| **Merge policy into config.yaml** | Policy is security-relevant and should be reviewable independently. Separate files enable separate git review, separate permissions, and clearer mental model. The spec already separates them correctly. |
| **Inline secrets in config** | Violates security model. Env vars and keyring are the correct paths. Any inline secret feature would need encryption-at-rest, key management, and audit — out of scope for v0.1. |
| **Per-agent policy in v0.1** | OpenCode supports per-agent permission overrides. Useful but premature. ARC doesn't have a multi-agent UI in v0.1. |
| **Managed/org config in v0.1** | Enterprise MDM/registry support is important for organizations but requires platform-specific code (macOS plist, Windows registry). v0.2 scope. |
| **Variable substitution (`{env:VAR}`, `{file:path}`)** | OpenCode's approach is elegant but adds parsing complexity. Env var override system already covers the primary use case. Can add in v0.2. |
| **Config diff/preview UI** | Useful but not v0.1 critical. File-based config with git diff covers this adequately. |
| **Config export/import/sharing** | Team config sharing is useful but requires org/managed config infrastructure first. v0.2+. |
