# Theia Version-Skew Audit

**Date:** 2026-05-14
**Scope:** Compatibility between `packages/arc-extension` (declares `^1.45.0`) and `applications/browser` (declares `1.71.0` exact)

---

## 1. Version Declarations vs. Resolution

| Context | `@theia/core` version | Semver range |
|---|---|---|
| `packages/arc-extension/package.json` | `^1.45.0` | >=1.45.0, <2.0.0 |
| `applications/browser/package.json` | `1.71.0` (exact) | =1.71.0 |
| Lockfile resolution (installed) | **1.71.0** | — |

**Verdict:** Semver-compatible. `^1.45.0` permits 1.71.0. The lockfile resolves all
`@theia/*` packages to 1.71.0, matching the app shell.

---

## 2. Theia API Compatibility Matrix

| Theia API / Import path | Used in | First appeared | Breaking 1.45→1.71? | Risk |
|---|---|---|---|---|
| `@theia/core/shared/inversify` (ContainerModule) | Backend + frontend modules | pre-1.0 | None | ✅ Safe |
| `injectable` / `inject` / `postConstruct` | All services, widget | pre-1.0 | None | ✅ Safe |
| `ConnectionHandler` | Backend module | pre-1.0 | None | ✅ Safe |
| `JsonRpcConnectionHandler` | Backend module | pre-1.0 | None | ✅ Safe |
| `BackendApplicationContribution` | health-endpoint, metrics-endpoint | pre-1.0 | None | ✅ Safe |
| `WebSocketConnectionProvider` | Frontend module | pre-1.0 | None | ✅ Safe |
| `WidgetFactory` | Frontend module | pre-1.0 | None | ✅ Safe |
| `bindViewContribution` | Frontend module | pre-1.0 | None | ✅ Safe |
| `AbstractViewContribution` | arc-widget-contribution | pre-1.0 | None | ✅ Safe |
| `ReactWidget` | arc-widget | pre-1.0 | None | ✅ Safe |
| `MessageService` | arc-widget | pre-1.0 | None | ✅ Safe |
| `KeybindingContribution` | arc-keybinding-contribution | pre-1.0 | None | ✅ Safe |
| `KeybindingRegistry` | arc-keybinding-contribution | pre-1.0 | None | ✅ Safe |
| `CommandContribution` | arc-keybinding-contribution | pre-1.0 | None | ✅ Safe |
| `CommandRegistry` | arc-keybinding-contribution | pre-1.0 | None | ✅ Safe |
| `Command` | arc-keybinding-contribution | pre-1.0 | None | ✅ Safe |
| `MenuModelRegistry` | arc-widget-contribution | pre-1.0 | None | ✅ Safe |
| `@theia/core/shared/react` | All components | 1.31+ | Bundle version may differ; compatible | ✅ Safe |
| `@theia/core/lib/browser` (general) | Various | pre-1.0 | None | ✅ Safe |

**All 19 distinct Theia APIs are stable core abstractions. Zero breaking changes
expected between 1.45.x and 1.71.x.**

---

## 3. Dependency Declarations vs. Actual Usage

| Declared in `package.json` | Imported in source? | Note |
|---|---|---|
| `@theia/core` | ✅ Yes | Heavily used |
| `@theia/filesystem` | ❌ No | Unused — can be removed |
| `@theia/workspace` | ❌ No | Unused — can be removed |
| `@theia/navigator` | ❌ No | Unused — can be removed |
| `@theia/terminal` | ❌ No | Unused — can be removed |

These four unused dependencies may be left over from an earlier iteration or
needed as peer type providers. They do no harm but could be cleaned up.

---

## 4. Protocol Layer

`packages/arc-extension/src/common/arc-protocol.ts` has **zero Theia imports**.
It contains only pure TypeScript types, enums, interfaces, and a `Symbol` for
the ARC service path. It is fully portable across Theia versions.

---

## 5. Found Issues (Non-Version-Related)

### 5.1 Missing DI registration: `ArcKeybindingContribution`

`src/browser/arc-keybinding-contribution.ts` implements both
`KeybindingContribution` and `CommandContribution` but is **never bound** in
`arc-extension-frontend-module.ts`. This means four keyboard shortcuts
(`Ctrl+E`, `Ctrl+L`, `Ctrl+Shift+S`, `Ctrl+H`) and their commands are defined
but will not activate.

**Fix:** Add to frontend module:
```typescript
bind(KeybindingContribution).to(ArcKeybindingContribution).inSingletonScope();
bind(CommandContribution).to(ArcKeybindingContribution).inSingletonScope();
```

This is a functional gap, not a version-compatibility issue. It predates the
version skew and should be tracked separately.

---

## 6. Overall Assessment

| Category | Finding |
|---|---|
| **Version compatibility** | ✅ `^1.45.0` → 1.71.0 is semver-compatible |
| **API surface** | 19 APIs from `@theia/core` only |
| **Breaking changes expected** | ✅ None |
| **Unused deps** | 4 (`filesystem`, `workspace`, `navigator`, `terminal`) |
| **Missing bindings** | 1 (`ArcKeybindingContribution` — functional bug) |
| **Protocol portability** | ✅ Zero Theia imports in protocol layer |
| **Overall risk** | **Low** — no version-related risks identified |

**Recommendation:** `packages/arc-extension` may continue to declare
`"^1.45.0"` without risk. When wiring into `applications/browser` (PR 5),
the lockfile will resolve all packages to 1.71.0. No code changes are required
for version compatibility.
