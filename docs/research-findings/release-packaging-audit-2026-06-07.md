# ARC Studio Release / Packaging / Install Story Audit — 2026-06-07

> **Scope:** Browser/Electron app readiness, packaging, signing preflight, npm/pipx/PyPI/Homebrew/curl install paths, artifacts, licenses, release checklist  
> **Source:** Synthesized from prior sessions + direct reads of browser/electron package.json, require-electron-signing.mjs, check-licenses.sh, bootstrap.sh, release notes

---

## 1. Release Architecture Map

```
┌─────────────────────────────────────────────────────────────────────┐
│              ARC STUDIO RELEASE ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────┤
│  CANONICAL RELEASE TARGET: applications/browser (NOT electron)      │
│                                                                      │
│  Browser app (applications/browser):                                │
│  ├── pnpm start:browser:arc → `node scripts/start-browser-arc.mjs`  │
│  ├── pnpm build:prod → `theia build --mode production`              │
│  ├── @theia 1.71.0 pinned across all packages                       │
│  ├── theiaPluginsDir: ../../plugins                                 │
│  ├── Default theme: "Dark+ (default dark)"                          │
│  ├── frontendConnectionTimeout: 30000ms                             │
│  └── reloadOnReconnect: true                                        │
│                                                                      │
│  Electron app (applications/electron):                               │
│  ├── electron 39.8.7, electron-builder ^24.13.3                    │
│  ├── package:smoke → CSC_IDENTITY_AUTO_DISCOVERY=false (no signing) │
│  ├── package:release → require-electron-signing.mjs THEN builder   │
│  ├── 4 exit codes on preflight fail: 10=env, 20=tools, 30=cert,    │
│  │   40=release-config                                              │
│  ├── require-electron-signing.mjs: full preflight (env, tooling,   │
│  │   certificate expiry, release config pattern checks)             │
│  └── Status: DEFERRED — browser is canonical release target         │
├─────────────────────────────────────────────────────────────────────┤
│  PYTHON PACKAGE                                                      │
│                                                                      │
│  python/pyproject.toml:                                             │
│  ├── name: agent-runtime-cockpit                                    │
│  ├── version: 0.1.0a0 (alpha)                                       │
│  ├── entrypoints: arc, arc-studio, arch-studio-cli (TYPO)          │
│  ├── requires-python: >=3.11                                        │
│  ├── swarmgraph-sdk: workspace:* (not on PyPI — BLOCKS pip install) │
│  ├── License: Apache-2.0 in pyproject.toml                         │
│  └── LICENSE file: Proprietary (MISMATCH)                          │
│                                                                      │
│  Install paths:                                                      │
│  ✅ `cd python && uv sync --all-extras --dev` (only working path)  │
│  ❌ `pip install arc-studio` (NOT on PyPI)                          │
│  ❌ `pipx install arc-studio` (swarmgraph-sdk blocks pip install)   │
│  ❌ `brew install arc-studio` (no Homebrew formula)                 │
│  ❌ `curl | sh` installer (not implemented)                         │
│  ❌ `npm install -g arc-studio` (no npm wrapper)                    │
├─────────────────────────────────────────────────────────────────────┤
│  LICENSE CHECK                                                       │
│                                                                      │
│  scripts/check-licenses.sh:                                         │
│  - Checks all package.json files via git ls-files                   │
│  - Pass if: package.private=true OR package.license present         │
│  - Used in release_check.sh                                         │
│                                                                      │
│  Findings:                                                           │
│  ✅ All @theia/* packages include license declarations               │
│  ✅ arc-extension: private:true (passes check)                      │
│  ⚠️ pyproject.toml: license="Apache-2.0" vs LICENSE file: Proprietary │
│  ⚠️ README footer: "ARC Studio Proprietary License"                 │
├─────────────────────────────────────────────────────────────────────┤
│  THEIA PLUGINS (deterministic download)                              │
│                                                                      │
│  theiaPluginsDir: ../../plugins (both browser and electron)         │
│  Plugins downloaded at build time via theia build                   │
│  No manual plugin download scripts found                            │
│  Reproducibility: @theia/cli 1.71.0 pinned → deterministic         │
├─────────────────────────────────────────────────────────────────────┤
│  SIGNING PREFLIGHT (require-electron-signing.mjs)                   │
│                                                                      │
│  Checks: env vars, release config YAML patterns, tooling, certs     │
│  4-level exit code system:                                           │
│  Exit 10: missing CSC_LINK/CSC_KEY_PASSWORD/APPLE_API_KEY_*        │
│  Exit 20: xcrun notarytool/stapler/codesign missing (macOS only)    │
│  Exit 30: no Developer ID Application certificate found             │
│  Exit 40: electron-builder.release.yml missing required fields      │
│  Exit 0: all checks pass                                            │
│  Smoke path: CSC_IDENTITY_AUTO_DISCOVERY=false (no signing check)   │
│  Secret redaction: applied to error output                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Install Story Critique

### What actually works

```bash
# The ONLY working install path:
git clone https://github.com/Hansuqwer/arc-theia-studio.git
cd arc-theia-studio/python
uv sync --all-extras --dev

# To also start the browser IDE:
cd ..
pnpm install --frozen-lockfile
pnpm start:browser:arc
```

### What doesn't work / is deferred

| Install method | Status | Blocker |
|---|---|---|
| `pip install arc-studio` | ❌ Not on PyPI | `swarmgraph-sdk` workspace-only dep |
| `pipx install arc-studio` | ❌ | Same — pip can't resolve workspace dep |
| `brew install arc-studio` | ❌ | No Homebrew formula |
| `curl \| sh` installer | ❌ | Not implemented |
| `npm install -g arc-studio` | ❌ | No npm wrapper package |
| `uv tool install arc-studio` | ❌ | Not on PyPI |
| Electron `.dmg`/`.exe`/`.deb` | ❌ | Deferred to v0.2 |
| `pnpm install arc-studio` | ❌ | Not published to npm |

### bootstrap.sh assessment

- 5-step script: Node version check, pnpm install, uv install + sync, pnpm install, status output
- Node version check: warns if < 20 but does not block
- pnpm installation: tries multiple fallbacks (npm, corepack) — can fail silently
- `--frozen-lockfile` replaced with `pnpm install` in bootstrap (defeats reproducibility)
- Does NOT set up `.tool-versions` automatically
- Does NOT run `pnpm build` (browser IDE won't start without this)

### Critical install documentation gaps

| Gap | Detail |
|---|---|
| README says "uv run arc" but no `pip install` path exists | README implies simpler install than reality |
| `arch-studio-cli` entrypoint typo | `pyproject.toml` has `arch-studio-cli` instead of `arc-studio-cli` |
| No `.tool-versions` auto-setup | Python 3.11.10 + Node 20.18.0 + pnpm 9.15.9 required but not enforced by bootstrap |
| `pnpm build` not documented as required | Browser app won't start without `pnpm build` first |
| No version pinning for uv | `uv sync` works but uv version not pinned in bootstrap |

---

## 3. Packaging Gap Matrix

| Artifact | Status | What exists | What's missing |
|---|---|---|---|
| Python wheel (`.whl`) | ❌ | `pyproject.toml` configured for hatchling | `swarmgraph-sdk` workspace dep blocks distribution |
| Python sdist (`.tar.gz`) | ❌ | Same as above | Same |
| Browser app (static bundle) | ✅ | `pnpm build:prod` → production bundle | Not published/hosted anywhere |
| Browser app (Docker) | ❌ | Not implemented | — |
| Electron `.dmg` | ❌ | Infrastructure exists, signing required | Signing setup + ADR-008 Phase 1 done; actual packaging deferred |
| Electron `.exe` | ❌ | Same | Same |
| Electron `.deb`/`.AppImage` | ❌ | Same | Same |
| npm global wrapper | ❌ | Not implemented | Proof-of-concept only in deep-research docs |
| Homebrew formula | ❌ | Not implemented | — |
| GitHub Release artifacts | ❌ | No release workflow uploads artifacts | — |

### Production build status

| Check | Status | Notes |
|---|---|---|
| `pnpm build:prod` for browser app | ✅ Should work (dev build confirmed green) | No explicit prod build CI verification found |
| `pnpm build` extension | ✅ | In `release_check.sh` |
| `pnpm typecheck` | ✅ | In `release_check.sh` |
| Python `uv build` | ✅ | In `release_check.sh` (builds wheel locally) |
| Python pytest 0 failures | ✅ | 5537 passed on aa788f3 |
| `pnpm install --frozen-lockfile` | ✅ | Verified in release checklist |

---

## 4. Signing / Electron Truth Table

| Claim | Actual status |
|---|---|
| Electron packaging infrastructure exists | ✅ `electron-builder` configs, `require-electron-signing.mjs` |
| Electron smoke build works (unsigned) | ✅ `package:smoke` with `CSC_IDENTITY_AUTO_DISCOVERY=false` |
| Electron release build works | ❌ Requires code signing setup; not verified |
| macOS signing: hardenedRuntime required | ✅ Checked in `releaseConfigCheck()` |
| macOS notarization via API key (not Apple ID) | ✅ Only `APPLE_API_KEY_*` strategy supported |
| Windows signing: `verifyUpdateCodeSignature: true` | ✅ Checked |
| Certificate expiry check | ✅ `certificateExpiry()` → days_until_expiry; warns if < 30 days |
| Secret redaction in preflight output | ✅ `redact()` strips sk-*, p12 passwords, api keys |
| Linux: no signing requirement | ✅ Skips Darwin-only checks |
| Electron is canonical release target | ❌ Browser is canonical; Electron deferred to v0.2 |
| PyInstaller binary packaging | ❌ ADR-008 Phase 1 spike done (~20MB binary); not scripted for CI |

---

## 5. Release Test Plan

### Currently tested (in release_check.sh)

1. `pnpm install --frozen-lockfile` ✅
2. `pnpm build` (extension) ✅
3. `uv build` (Python wheel) ✅
4. `pnpm typecheck` ✅
5. `uv run pytest -q` (5537 tests) ✅
6. `pnpm --filter arc-extension test` ✅
7. `check-banned-claims.sh` on key docs ✅
8. `spec_verify.py` (spec citations) ✅
9. Import guard tests (no-LLM, no-telemetry) ✅
10. `arc --help` exits 0 ✅
11. `arc runtimes --capabilities --json` honest output ✅

### Missing from release test plan

| Test | Severity | How to add |
|---|---|---|
| `pnpm build:prod` (production mode, not dev) | **High** | Add to release_check.sh: `cd applications/browser && pnpm build:prod` |
| `pnpm start:browser:arc` smoke (page loads, no ERR_) | **High** | E2e Playwright smoke already exists but is conditional; make unconditional in CI |
| `pnpm start:browser:arc` with prod build | **High** | Test prod bundle is serveable |
| `arc-studio-cli` entrypoint typo check | **Medium** | `grep -r "arch-studio-cli" python/pyproject.toml` should return nothing |
| Electron smoke build (no signing) | **Medium** | `cd applications/electron && pnpm package:smoke` — add to optional CI job |
| License check passes | **Medium** | `bash scripts/check-licenses.sh` — add to release_check.sh |
| `swarmgraph-sdk` not on PyPI blocker documented | **Low** | Add explicit note to install docs |
| bootstrap.sh runs end-to-end | **Low** | `bash scripts/bootstrap.sh` in a clean container |

---

## 6. Improved Release Implementation Prompt

**Target:** Three focused, safe improvements to the install story and release gate.

```
# Release Next Slice: Install Docs + Prod Build Gate + Entrypoint Typo Fix

## Context

ARC Studio v0.8-r-ux2. Three release gaps:

1. pyproject.toml has a typo: "arch-studio-cli" instead of "arc-studio-cli"
   as an entrypoint. This silently registers a misspelled command that
   will never be discovered by users.

2. release_check.sh runs `pnpm build` (development mode) but never runs
   `pnpm build:prod` (production mode). A production build failure would
   not be caught before tagging.

3. The install story is misleading — README implies a simpler setup than
   actually exists. There is no pip install path, no Homebrew formula,
   and no npm wrapper. The README should honestly document the single
   working install path.

## Scope

### 1. Fix entrypoint typo

File: python/pyproject.toml

```toml
# BEFORE:
arch-studio-cli = "agent_runtime_cockpit.cli_studio:app"

# AFTER:
arc-studio-cli = "agent_runtime_cockpit.cli_studio:app"
```

Add to release_check.sh:
```bash
echo "=== Entrypoint typo check ==="
if grep -q "arch-studio-cli" python/pyproject.toml; then
    echo "FAIL: arch-studio-cli typo in pyproject.toml"
    exit 1
fi
echo "OK: entrypoints clean"
```

### 2. Add production build to release gate

File: scripts/release_check.sh

Add after the development build step:
```bash
echo "=== Production browser build ==="
if [[ "$SKIP_PNPM" != "1" ]]; then
    (cd applications/browser && pnpm build:prod)
    echo "OK: production build succeeded"
fi
```

Note: Production build takes significantly longer (~3-5x vs dev).
Add a `--skip-prod-build` flag for faster CI iteration:
```bash
if [[ "${SKIP_PROD_BUILD:-0}" == "1" ]]; then
    echo "Skipping production build (SKIP_PROD_BUILD=1)"
else
    (cd applications/browser && pnpm build:prod)
fi
```

### 3. Fix license mismatch

File: python/pyproject.toml

The license field says "Apache-2.0" but the LICENSE file is proprietary.

```toml
# BEFORE:
license = "Apache-2.0"

# AFTER:
license = { text = "Proprietary" }
# or remove the field entirely since it's a private package:
# (remove license = ... line)
```

Also add license check to release_check.sh:
```bash
echo "=== License check ==="
bash scripts/check-licenses.sh
```

### 4. Honest install documentation

File: README.md

Replace the install section to be unambiguous about the single working path:

```markdown
## Installation

ARC Studio is in alpha. The only supported install method is from source:

### Prerequisites
- Python 3.11.10 (`.tool-versions` pinned)
- Node.js 20.18.0 (`.tool-versions` pinned)
- pnpm 9.15.9
- uv (latest)

### From source (the only supported method)
\`\`\`bash
git clone https://github.com/Hansuqwer/arc-theia-studio.git
cd arc-theia-studio/python
uv sync --all-extras --dev
\`\`\`

Launch the TUI:
\`\`\`bash
uv run arc
\`\`\`

Launch the browser IDE (optional):
\`\`\`bash
cd ..
pnpm install --frozen-lockfile
pnpm build
pnpm start:browser:arc
# Open http://127.0.0.1:3000
\`\`\`

**Not yet available:** `pip install`, `pipx install`, `brew install arc-studio`.
These install paths are planned for a future release.
```

### 5. Fix bootstrap.sh --frozen-lockfile

File: scripts/bootstrap.sh

Replace the `pnpm install` fallback with the frozen version:
```bash
# BEFORE (defeats reproducibility):
pnpm install || pnpm install --no-frozen-lockfile

# AFTER:
pnpm install --frozen-lockfile
```

And add the missing `pnpm build` step:
```bash
echo -e "\n${BOLD}[5/5] Building IDE...${NC}"
pnpm build
echo -e "${GREEN}✓ IDE built successfully${NC}"
echo ""
echo -e "${GREEN}${BOLD}Bootstrap complete!${NC}"
echo "  Start TUI:        cd python && uv run arc"
echo "  Start browser IDE: pnpm start:browser:arc"
```

## Do NOT do in this slice

- npm wrapper implementation (separate packaging slice)
- Homebrew formula (separate distribution slice)
- Electron signing setup (deferred to v0.2, requires certificate)
- PyPI publication (blocked by swarmgraph-sdk workspace dep)
- Docker packaging

## Verification

```bash
# Typo fix
grep "arch-studio-cli" python/pyproject.toml && echo "FAIL" || echo "OK"

# License check
bash scripts/check-licenses.sh

# Production build
cd applications/browser && pnpm build:prod && echo "Prod build OK"
```
```

---

## Appendix: Quick release status reference

| Component | Status | Notes |
|---|---|---|
| Python CLI `uv run arc` | ✅ Working | Primary interface |
| Browser IDE `pnpm start:browser:arc` | ✅ Working | Secondary, optional |
| Python wheel distribution | ❌ Blocked | swarmgraph-sdk workspace-only dep |
| PyPI publication | ❌ Blocked | Same |
| Electron packaging | ❌ Deferred | v0.2; signing infrastructure exists |
| Homebrew formula | ❌ Not started | — |
| npm wrapper | ❌ Not started | Deep-research proposed; not implemented |
| `arch-studio-cli` typo | ❌ Bug | Fix: arc-studio-cli |
| license mismatch | ❌ Bug | pyproject=Apache-2.0, LICENSE=Proprietary |
| Production build CI gate | ❌ Missing | Only dev build is checked |
| `pnpm --frozen-lockfile` in bootstrap | ❌ Missing | bootstrap.sh uses unfrozen |
| Theia plugins deterministic | ✅ | @theia/cli 1.71.0 pinned |
| Signing preflight | ✅ | require-electron-signing.mjs fully implemented |
