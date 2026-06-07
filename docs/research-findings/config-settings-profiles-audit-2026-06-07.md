# ARC Studio Config / Settings / Profiles Architecture Audit — 2026-06-07

> **Scope:** ConfigService, profile schema, workspace trust, runtime settings, isolation settings, provider settings, safe-save, IDE ConfigTab, TUI settings, CLI config  
> **Source:** Synthesized from prior sessions (security, provider/budget, Theia IDE, TUI audits) + direct read of ConfigService

---

## 1. Config Architecture Map

```
┌─────────────────────────────────────────────────────────────────────┐
│              ARC STUDIO CONFIG ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────┤
│  CONFIG FILES (all local, never uploaded)                            │
│                                                                      │
│  ~/.arc/config.yaml (or ARC_CONFIG_PATH override)                   │
│  ├── runtime.default: "swarmgraph"                                  │
│  ├── runtime.auto_detect: true                                      │
│  ├── runtime.fallback: "stub"                                       │
│  ├── execution.isolation: "none"|"subprocess"|"docker"|"microvm"   │
│  ├── execution.timeout_seconds: 300                                 │
│  ├── execution.allow_paid_calls: false                              │
│  ├── execution.mode: "build"|"plan"|"auto"                         │
│  ├── providers.dry_run: true                                        │
│  ├── providers.routing_mode: "manual"                               │
│  └── profiles.selected_profile: "local-safe"                       │
│                                                                      │
│  ~/.arc/profiles.json (schema v2; ARC_PROFILE_CONFIG override)     │
│  ├── version: 2                                                     │
│  └── profiles[]: {id, name, allow_paid_calls, allow_network,       │
│       allow_shell, allow_secrets, env_allowlist, backend, extra}   │
│  ⚠️ load_custom_profiles() reads without schema version check      │
│  ⚠️ v1 profiles loaded without migration (silent)                  │
│                                                                      │
│  ~/.arc/providers.json                                              │
│  ├── account records: {id, provider, label, key_env_var, ...}      │
│  └── ⚠️ NEVER stores raw API keys; stores env var name only        │
│  ⚠️ No advisory lock on concurrent writes                          │
│                                                                      │
│  ~/.arc/provider-routing.json                                       │
│  └── mode, default_provider, default_model, dry_run: true          │
│                                                                      │
│  ~/.arc/trusted-workspaces.json                                     │
│  └── trusted workspace paths list                                   │
│                                                                      │
│  ~/.arc/approvals.json (sandbox approval tokens)                   │
│  └── token hash, command hash, expires_at per entry                 │
├─────────────────────────────────────────────────────────────────────┤
│  NODE BACKEND (ConfigService)                                        │
│                                                                      │
│  getConfigStatus() → ConfigStatus                                   │
│  ├── arc providers status --json (providers list)                   │
│  ├── arc config show --json (runtime/execution/providers/profiles)  │
│  ├── Returns: workspace (TrustStatus), runtime (SafeRuntimeConfig), │
│  │   providers[], mode, selectedProfile, backendAvailable           │
│  └── Defaults: allowPaidCalls=false, dryRun=true, isolation="none" │
│                                                                      │
│  saveConfig(SafeConfigUpdate) → safe-save                          │
│  ├── SAFE_CONFIG_KEYS allowlist enforced                            │
│  ├── UNSAFE_CONFIG_KEY_PATTERN regex check                          │
│  └── arc config set runtime.default=X ... (all in one call)        │
│  ⚠️ Uses execFileSync (blocks Node backend main thread)            │
│                                                                      │
│  listProfiles() → ArcProfileInfo[]                                 │
│  └── arc profiles list --json; falls back to 2 hardcoded entries   │
│                                                                      │
│  getIsolationStatus() → IsolationStatus                            │
│  └── arc isolation status --json                                    │
│                                                                      │
│  Provider methods: getProviderStatus, getProviderCatalog,          │
│  getProviderDiagnostics, getProviderQuota, resetProviderQuota,      │
│  setProviderKeyRef, unsetProviderKeyRef, testProvider,              │
│  listProviderModels, getProviderAccount, updateProviderAccount      │
│  ⚠️ getProviderCatalog/setProviderKeyRef/unsetProviderKeyRef:      │
│     NO try/catch — exceptions propagate unhandled through RPC      │
│  ⚠️ getProviderAccount/updateProviderAccount bypass                 │
│     DaemonDiscoveryService loopback validation                      │
├─────────────────────────────────────────────────────────────────────┤
│  SAFE-SAVE (SafeConfigUpdate allowlist)                             │
│                                                                      │
│  SAFE_CONFIG_KEYS (from arc-cli-utils.ts):                         │
│  ['defaultRuntime', 'mode', 'isolation', 'allowPaidCalls', 'dryRun',│
│   'routingMode', 'selectedProfile']                                 │
│                                                                      │
│  UNSAFE_CONFIG_KEY_PATTERN:                                         │
│  /(secret|token|password|api[_-]?key|raw.*key|credential)/i         │
│                                                                      │
│  saveConfig REJECTS:                                                │
│  - Unknown keys (not in allowlist)                                  │
│  - Keys matching unsafe pattern                                     │
│  - Empty update                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Profile / Trust Data Flow

```
arc workspace trust <workspace>
  → ~/.arc/trusted-workspaces.json (adds workspace path)
  → resolve_trust(workspace) → TrustLevel.TRUSTED

arc workspace untrust <workspace>
  → removes from trusted-workspaces.json
  → resolve_trust(workspace) → TrustLevel.UNTRUSTED

arc profiles create <id> [--allow-paid-calls] [--allow-network] [...]
  → writes ~/.arc/profiles.json (schema v2)

arc profiles list --json
  → lists builtin (stub/local-safe/local-paid/gateway) + custom

resolve_profile(id) → RunProfile
  → silent fallback to 'stub' on unknown ID
  → resolve_profile_strict(id) → raises ProfileNotFound

Workspace trust → enforcement surface effects:
  ✅ HTTP routes: POST/DELETE/PATCH /api/sessions/*, /api/providers/*, 
     /api/runs/start, /api/runs/{id}, /api/arena/* — all trust-gated
  ✅ MCP tools: ensure_trusted() per tool/resource call
  ✅ TUI shell escape: resolve_trust() before sandbox decision
  ✅ arc workspace init: no trust gate (creates config only)
  ❌ arc workspace inventory/search: NO trust gate
  ❌ arc workspace show: NO trust gate  

Profile → EnforcementContext effects:
  ✅ allow_paid_calls → enforce_paid_call_gate()
  ✅ allow_shell → enforce_shell_gate()
  ✅ allow_network → enforce_network_gate()
  ✅ allow_secrets → (future; not yet in enforcement)
  TUI default: allow_paid=True (getattr fallback bug — see security audit)
```

---

## 3. Safe-Save Review

### What is safe to save (allowlisted)

| Key | Maps to | Safe? | Notes |
|---|---|---|---|
| `defaultRuntime` | `runtime.default` | ✅ | "swarmgraph"/"langgraph"/etc |
| `mode` | `execution.mode` | ✅ | "build"/"plan"/"auto" |
| `isolation` | `execution.isolation` | ✅ | "none"/"subprocess"/"docker"/"microvm" |
| `allowPaidCalls` | `execution.allow_paid_calls` | ✅ | bool; shown in status bar |
| `dryRun` | `providers.dry_run` | ✅ | bool |
| `routingMode` | `providers.routing_mode` | ✅ | "manual"/"priority"/"fallback" |
| `selectedProfile` | `profiles.selected_profile` | ✅ | string |

### What is never saved through ConfigService

| Data | Why | Mechanism |
|---|---|---|
| Raw API keys | Explicitly blocked | Direct key storage raises `RuntimeError` |
| Provider `api_key` | Blocked by UNSAFE_CONFIG_KEY_PATTERN | Rejected before CLI call |
| Secrets/tokens | Blocked by UNSAFE_CONFIG_KEY_PATTERN | Rejected before CLI call |
| Workspace trust | Separate mechanism | `arc workspace trust` → `trusted-workspaces.json` |

### Safe-save gaps

| Gap | Severity | Detail |
|---|---|---|
| `saveConfig` uses `execFileSync` | **Medium** | Blocks Node backend for 10s |
| `getProviderCatalog/setProviderKeyRef/unsetProviderKeyRef` no try/catch | **Medium** | Unhandled exceptions propagate through RPC |
| Profile schema v1 loaded without migration | **Medium** | `load_custom_profiles()` reads without version check |
| `~/arc/providers.json` no advisory lock | **Medium** | Concurrent writes can corrupt the file |
| `allowPaidCalls=true` in config does NOT bypass EnforcementContext | **Note** | Config field must be explicitly passed to enforce; not auto-applied |

---

## 4. UI Gap Analysis

### ConfigTab (IDE)

| Feature | Status | Notes |
|---|---|---|
| Runtime radio group | ✅ | Shows detected runtimes with capability-driven disabled state |
| Mode radio group | ✅ | With mode descriptions |
| Trust status display | ✅ | Shows trust level + reason |
| Save config button | ✅ | Maps to saveConfig(SafeConfigUpdate) |
| Provider key ref save | ✅ | Env-var reference only, no raw key capture |
| Provider dropdown | ✅ | Catalog-backed, pre-filled env var name |
| Source badges | ✅ | Shows env/keyring/file/unset |
| Provider diagnostics | ✅ | Offline/degraded copy |
| Quota rows | ✅ | Local counters only |
| Cost policy summary | ✅ | dry-run/paid-call gating label |
| Live provider gate | ✅ | providerCall always false; gated states clear |
| Routing section | ⚠️ Read-only | Mode/dry-run/isolation shown but not editable in routing section |
| Profile selector | ✅ | `listProfiles()` backed |
| Active model selection | ❌ | Model list display-only; no "select as default" |
| Base_url per-provider config | ❌ | Exists in `ProviderAccountUpdate`, not wired |
| OAuth / device-flow | ❌ | `auth_kind` in catalog, no UI |
| ProviderAccountInfo rendering | ❌ | masked_key, fingerprint, enabled toggle not surfaced |
| Remove/unset provider | ❌ | `unsetProviderKeyRef` exists in service, not wired to UI |
| Docs_url links from catalog | ❌ | Not rendered |
| ProviderCatalogStatus (research_only, not_recommended) | ❌ | Not shown to user |
| Background refresh | ❌ | Manual only |

### TUI SettingsView

| Feature | Status | Notes |
|---|---|---|
| Isolation backend selector | ✅ | RadioSet, persists to config.yaml |
| Theme selector | ⚠️ | Only dark/light shown (4 themes missing) |
| Mode selector | ⚠️ | Not persisted on Apply (only isolation is saved) |
| Theme not persisted | ❌ | Theme RadioSet has no on_button_pressed handler |

### Status bar (TUI / IDE)

| Item | TUI StatusBar | IDE Status Rail |
|---|---|---|
| Execution mode (fake/real) | ✅ | ❌ (bottom strip only, not persistent rail) |
| Paid-call indicator | ✅ | ❌ |
| Provider/model | ✅ | ❌ |
| Isolation backend | ❌ | ❌ |
| Profile name | ❌ | ❌ |
| Trust level | ❌ | ❌ (not in status items, only in ConfigTab) |

### Parity matrix (CLI / TUI / IDE)

| Operation | CLI | TUI | IDE |
|---|---|---|---|
| Set runtime | ✅ `arc config` | ✅ `/runtime use` | ✅ ConfigTab radio |
| Set isolation | ✅ `arc isolation use` | ✅ SettingsView RadioSet | ✅ ConfigTab (via saveConfig) |
| Set mode | ✅ `arc config` | ✅ `/plan /build /auto` | ✅ ConfigTab radio |
| Set profile | ✅ `arc profiles create` | ❌ no /profile cmd | ✅ ConfigTab selector |
| View trust status | ✅ `arc workspace trust-status` | ✅ `/workspace trust-status` | ✅ ConfigTab workspace section |
| Set workspace trust | ✅ `arc workspace trust` | ❌ no write cmd | ❌ absent |
| Set provider key ref | ✅ `arc providers key set` | ✅ `/providers add --api-key-env` | ✅ Provider Key Reference section |
| View provider status | ✅ `arc providers status` | ✅ `/providers` | ✅ ConfigTab source badges |
| Reset quota | ✅ `arc providers quota reset` | ❌ | ✅ ConfigTab button |
| Set routing | ✅ `arc providers routing set` | ❌ | ❌ Read-only |

---

## 5. Test Gap Analysis

### Confirmed test coverage

| Test | Covers |
|---|---|
| `tests/web/test_phase55_provider_trust.py` | 4 provider mutation routes trust-gated |
| `tests/web/test_phase50_trust_surface_audit.py` | 14 HTTP routes trust-checked before data read |
| `tests/security/test_enforcement_context.py` | EnforcementContext immutability, dry_run bypass |
| `tests/test_cli_profiles_workspace.py` | Profile list, show, workspace config |
| `tests/web/test_cli_budget.py` | Budget CLI commands |
| `packages/arc-extension/src/browser/__tests__/config-tab-provider-parsing.contract.test.ts` | ConfigTab provider parsing, snake_case/camelCase aliasing |
| `packages/arc-extension/src/browser/__tests__/config-tab-remediation.contract.test.ts` | ConfigTab remediation copy |
| `packages/arc-extension/src/browser/__tests__/chat-tab-runtime-setup.contract.test.ts` | ChatTab runtime setup |
| `node/__tests__/services.unit.test.ts` | ConfigService validation (SAFE_CONFIG_KEYS, UNSAFE_CONFIG_KEY_PATTERN) |
| `tests/tui/test_settings_isolation.py` | SettingsView isolation RadioSet + persist |

### Critical gaps

| Gap | Severity | Detail |
|---|---|---|
| Profile schema v1 loads without migration | **Medium** | No test for v1 profile file being silently loaded; no migration test |
| `load_custom_profiles()` no version check | **Medium** | `PROFILE_SCHEMA_VERSION=2` in source; `raw.get("version", 1)` not checked |
| `saveConfig` execFileSync blocking | **Medium** | No test verifying async behavior or that other RPCs don't block |
| `getProviderCatalog/setProviderKeyRef` no try/catch | **Medium** | No test for what happens when CLI fails on these methods |
| `~/arc/providers.json` concurrent write | **Medium** | No test for race condition |
| TUI SettingsView theme not persisted | **Low** | No test asserting theme save on Apply |
| TUI SettingsView mode not persisted | **Low** | No test asserting mode save on Apply |
| `arc workspace trust` unavailable in TUI | **Low** | No slash command; no test |
| `arc workspace trust` unavailable in IDE | **Low** | No UI button; no test |
| Profile `allow_secrets` not in enforcement | **Low** | Field exists in RunProfile but no `enforce_secrets_gate()` exists |

---

## 6. Improved Implementation Prompt

**Target:** Three focused fixes that improve config reliability and TUI settings consistency.

```
# Config/Settings Next Slice: Profile Version Check + SettingsView Persist + ConfigService Async

## Context

ARC Studio v0.8-r-ux2. Three config gaps:

1. load_custom_profiles() in security/profiles.py reads ~/.arc/profiles.json
   without checking the version field. PROFILE_SCHEMA_VERSION=2 is declared
   but the code does `raw.get("version", 1)` without any comparison or
   migration. A v1 profile file is silently loaded with potentially wrong
   fields, or a v3+ file from a future version is loaded without error.

2. TUI SettingsView RadioSet for theme and mode are not persisted on Apply.
   Only isolation backend is actually saved. Theme and mode changes are lost
   when the panel is dismissed. Users cannot tell which changes were applied.

3. ConfigService.saveConfig() uses execFileSync with a 10s timeout.
   This blocks the Node.js backend during config save, freezing all other
   IDE JSON-RPC calls.

## Scope

### 1. Profile schema version guard

File: python/src/agent_runtime_cockpit/security/profiles.py

```python
def load_custom_profiles(path: Path | None = None) -> dict[str, RunProfile]:
    store_path = path or profile_store_path()
    if not store_path.exists():
        return {}
    raw = json.loads(store_path.read_text())
    
    stored_version = raw.get("version", 1)
    if stored_version > PROFILE_SCHEMA_VERSION:
        raise ValueError(
            f"Profile store version {stored_version} > supported {PROFILE_SCHEMA_VERSION}. "
            "Upgrade ARC Studio to read these profiles."
        )
    if stored_version < PROFILE_SCHEMA_VERSION:
        # v1 → v2 migration: ensure 'extra' field exists on each profile
        for item in raw.get("profiles", []):
            item.setdefault("extra", {})
    
    # ... rest of loading unchanged ...
```

Tests: python/tests/security/test_profiles.py (add):
```python
def test_load_custom_profiles_rejects_future_version(tmp_path):
    store = tmp_path / "profiles.json"
    store.write_text(json.dumps({"version": 999, "profiles": []}))
    with pytest.raises(ValueError, match="version 999 > supported"):
        load_custom_profiles(store)

def test_load_custom_profiles_v1_migrates_silently(tmp_path):
    store = tmp_path / "profiles.json"
    store.write_text(json.dumps({
        "version": 1,
        "profiles": [{"id": "my-profile", "name": "My Profile"}]
    }))
    profiles = load_custom_profiles(store)
    assert "my-profile" in profiles
    assert profiles["my-profile"].extra == {}  # migrated

def test_load_custom_profiles_v2_loads_correctly(tmp_path):
    store = tmp_path / "profiles.json"
    store.write_text(json.dumps({
        "version": 2,
        "profiles": [{"id": "my-profile", "name": "My Profile", "extra": {"k": "v"}}]
    }))
    profiles = load_custom_profiles(store)
    assert profiles["my-profile"].extra == {"k": "v"}
```

### 2. Fix TUI SettingsView: persist theme and mode

File: python/src/agent_runtime_cockpit/tui/views/settings_view.py

In `on_button_pressed("#apply-btn")`:
```python
async def on_button_pressed(self, event: Button.Pressed) -> None:
    if event.button.id == "apply-btn":
        # Existing: persist isolation
        isolation = self._persist_isolation()
        
        # ADD: persist theme
        theme_buttons = self.query(RadioButton).filter("#theme-dark, #theme-light, #theme-mocha, #theme-latte, #theme-hc, #theme-mono")
        for btn in theme_buttons:
            if btn.value:
                theme_name = btn.id.replace("theme-", "").replace("hc", "high-contrast")
                self.app.theme_manager.select(theme_name)
                break
        
        # ADD: persist mode
        mode_buttons = self.query(RadioButton).filter("#mode-build, #mode-plan, #mode-auto")
        for btn in mode_buttons:
            if btn.value:
                self.app.data.mode = btn.id.replace("mode-", "")
                break
        
        self.dismiss()
```

Also add missing theme options to the RadioSet:
```python
with RadioSet(id="theme-radio"):
    yield RadioButton("dark", id="theme-dark", value=current_theme == "dark")
    yield RadioButton("light", id="theme-light", value=current_theme == "light")
    yield RadioButton("mocha", id="theme-mocha", value=current_theme == "mocha")
    yield RadioButton("latte", id="theme-latte", value=current_theme == "latte")
    yield RadioButton("high-contrast", id="theme-hc", value=current_theme == "high-contrast")
    yield RadioButton("mono", id="theme-mono", value=current_theme == "mono")
```

Tests: python/tests/tui/test_settings_isolation.py (add):
```python
async def test_settings_theme_persists_on_apply(app_pilot):
    # Mount SettingsView, select "mocha", press Apply
    # Assert app.theme_manager.current.name == "mocha"

async def test_settings_mode_persists_on_apply(app_pilot):
    # Mount SettingsView, select "plan", press Apply
    # Assert app.data.mode == "plan"
```

### 3. Convert ConfigService.saveConfig to async

File: packages/arc-extension/src/node/services/config-service.ts

```typescript
import { execFile } from 'child_process';
import { promisify } from 'util';
const execFileAsync = promisify(execFile);

async saveConfig(update: SafeConfigUpdate): Promise<{ success: boolean; message: string }> {
    // ... validation unchanged ...
    
    try {
        // Replace execFileSync with async:
        await execFileAsync('arc', args, {
            timeout: 10000,
            encoding: 'utf-8',
            windowsHide: true,
            env: buildArcCliEnv(),
        });
        return { success: true, message: 'Configuration saved.' };
    } catch (error) {
        return {
            success: false,
            message: `Failed to save config: ${error instanceof Error ? error.message : 'Unknown error'}`,
        };
    }
}
```

Apply same async conversion to:
- `listProfiles()` — `execFileSync` → `execFileAsync`
- `getIsolationStatus()` — `execFileSync` → `execFileAsync`
- `getConfigStatus()` — two `execFileSync` calls → `await Promise.all([execFileAsync(...), execFileAsync(...)])`

The `getConfigStatus()` parallelization makes it fetch providers and config simultaneously, halving the round-trip time.

### 4. Add try/catch to ConfigService provider methods

File: packages/arc-extension/src/node/services/config-service.ts

```typescript
async getProviderCatalog(): Promise<ProviderCatalogEntry[]> {
    try {
        const output = execFileSync('arc', ['providers', 'list', '--json'], {
            timeout: 10000, encoding: 'utf-8',
            windowsHide: true, env: buildArcCliEnv(),
        });
        const parsed = JSON.parse(output);
        return Array.isArray(parsed?.data) ? parsed.data : [];
    } catch (error) {
        // Graceful degradation — return empty catalog
        return [];
    }
}

// Same pattern for setProviderKeyRef and unsetProviderKeyRef:
async setProviderKeyRef(request: ProviderKeyRefRequest): Promise<void> {
    try {
        // ... existing logic ...
    } catch (error) {
        throw new ArcError(
            ArcErrorCode.RUN_FAILED,
            `Failed to set provider key ref: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
    }
}
```

## Do NOT do in this slice

- Profile diff/apply UI (separate profiles UI slice)
- Enterprise settings page
- Workspace trust banner in IDE
- OAuth/device-flow provider setup
- ConfigService full async migration (only saveConfig/listProfiles/getConfigStatus)

## Verification

```bash
cd python && uv run pytest tests/security/test_profiles.py tests/tui/test_settings_isolation.py -q
pnpm typecheck && pnpm build
pnpm --filter arc-extension test
```
```

---

## Appendix: Config fields mapped across surfaces

| Config field | config.yaml key | CLI command | ConfigTab field | TUI setting | Default |
|---|---|---|---|---|---|
| Runtime | `runtime.default` | `arc config set runtime.default=X` | Runtime radio | `/runtime use <id>` | `swarmgraph` |
| Isolation | `execution.isolation` | `arc isolation use <backend>` | ConfigTab (via saveConfig) | SettingsView RadioSet ✅ | `none` |
| Mode | `execution.mode` | `arc config set execution.mode=X` | Mode radio | `/plan /build /auto /mode X` | `build` |
| Allow paid | `execution.allow_paid_calls` | `arc run --allow-paid-calls` | Checkbox ✅ | (session.allow_paid from DataStore) | `false` |
| Dry run | `providers.dry_run` | n/a (CLI enforced) | ConfigTab checkbox ✅ | (session flag) | `true` |
| Routing mode | `providers.routing_mode` | `arc providers routing set --mode X` | Read-only display | ❌ | `manual` |
| Profile | `profiles.selected_profile` | `arc profiles create / show` | Profile selector ✅ | ❌ no TUI cmd | `local-safe` |
| Trust | `trusted-workspaces.json` | `arc workspace trust/untrust` | Read-only display | `/workspace trust-status` (read) | untrusted |
| Provider key ref | `providers.json` | `arc providers key set` | Provider Key Reference ✅ | `/providers add --api-key-env` | none |
