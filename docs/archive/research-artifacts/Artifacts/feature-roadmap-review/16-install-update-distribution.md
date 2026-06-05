# Install / Update / Distribution Review

## Current ARC Spec

### What the spec says (ARC_STUDIO_UX_SPEC.md)

**§10.9 Version And Update Check:**
- `/version` shows CLI version, daemon version, protocol version, and runtime manifest version
- `/update --check` checks the current package channel and prints the package-manager command; it does **not** modify installed files
- npm example: `npm install -g arc-studio@latest`
- pipx example: `pipx upgrade arc-studio`

**§16 Assets:**
- Logo concepts (SVG/PNG/ICO/ICNS), Theia themes, ANSI palette, Cytoscape style, fonts, social card, docs screenshots
- No install script, no binary distribution artifacts listed

**§17 Open Questions:**
- Is `arc-studio` npm name available? (needs verification)
- Embed Python in npm package? Options: download wheel, require Python, bundle standalone
- Recommendation: "Start with Python requirement + clear doctor"

**CLI_IDE_REDESIGN_PLAN.md §2.1:**
- Target: `npm install -g arc-studio` (preferred), `pipx install agent-runtime-cockpit`, Homebrew (future), curl install script (future)
- Implementation: npm package wraps Python CLI, bundles or downloads Python wheel
- Entry point: `arc-studio` binary (Node.js shim that invokes Python CLI)
- Keep `arc` as backward-compat alias

**CLI_IDE_REDESIGN_PLAN.md §4.1:**
- npm package includes pre-built Python wheel OR downloads from PyPI on first run
- Uses embedded Python or system Python (detect)
- Alternative: `pipx install agent-runtime-cockpit` for Python-native path

**IMPLEMENTATION_PLAN.md P5:**
- v0.1 scope: browser app + Python CLI/wheel
- Electron packaging is post-v0.1
- "Fresh clone can install, build, run CLI, start browser shell, and run smoke tests"
- Browser app + Python CLI/wheel release path is documented and tested

**ADR-008 (Daemon Bundling):**
- Status: Proposed (not implemented)
- Three-phase approach: P1 packaging spike, P2 bundling implementation, P3 update/bootstrap refinement
- Options: PyInstaller, Embedded Python + pip, uv-based bootstrap
- No decision until measured on target platforms
- Explicitly post-v0.1 for Electron bundling

### What exists today

| Component | Current state |
|---|---|
| Python package | `agent-runtime-cockpit` v0.1.0a0, hatchling build, pip installable |
| Entry point | `arc` command via `agent_runtime_cockpit.cli:app` |
| npm wrapper | Does not exist yet |
| pipx path | Works in theory (`pipx install agent-runtime-cockpit`), not tested in CI |
| Homebrew formula | Does not exist |
| curl install script | Does not exist |
| Shell completions | Not implemented |
| Update check | Not implemented |
| Version command | Exists (`arc version` added in P0) |
| Doctor command | Exists (`arc doctor all` added in P0) |
| Daemon bundling | Not implemented (ADR-008 proposed) |
| SwarmGraph bundling | Vendored in `runtimes/swarmgraph/`, works as CLI subprocess |
| First-run setup | Spec has welcome screen (§7.1), not implemented |
| Uninstall | No documented uninstall flow |

## Comparable Products / Research

| Product | Install methods | Update mechanism | Binary type | Auto-update | Version check | Doctor | Shell completions | Uninstall |
|---|---|---|---|---|---|---|---|---|
| **Claude Code** | curl install (native), brew cask, WinGet, npm, apt/dnf/apk | Native: auto-update in background; brew/WinGet/npm: manual; `claude update` for manual | Native binary (Node-based, per-platform optional deps) | Yes (native installs), configurable release channel (latest/stable), `DISABLE_AUTOUPDATER` env var | `claude --version` | `claude doctor` | Not explicitly documented | `rm -f ~/.local/bin/claude && rm -rf ~/.local/share/claude` + per-package-manager uninstall |
| **OpenCode** (archived → Crush) | curl install script, brew tap, AUR, `go install` | No auto-update; manual re-install | Go binary (single static binary) | No | `opencode --version` (implied) | No | No | Manual binary removal |
| **Codex CLI** | `npm install -g @openai/codex`, `brew install --cask codex`, GitHub Release binaries | npm: `npm install -g @openai/codex@latest`; brew: `brew upgrade codex` | Rust binary (prebuilt per platform in npm via optional deps, or brew cask) | No | `codex --version` | No | No | `npm uninstall -g @openai/codex` or `brew uninstall --cask codex` |
| **Aider** | `pip install aider-chat`, pipx | `pip install --upgrade aider-chat` or `pipx upgrade aider-chat` | Python package (wheel/sdist) | No | `aider --version` | No | No | `pip uninstall aider-chat` |
| **GitHub CLI** | brew, apt, dnf, WinGet, npm, prebuilt binaries, source | Package manager updates (`brew upgrade gh`, `apt upgrade gh`); no auto-update | Go binary (static) | No | `gh --version` | No | Yes (`gh completion -s bash`) | Package manager uninstall |
| **VS Code** | Platform installers, brew cask, apt, Snap, winget, zip | Built-in auto-update (Electron Squirrel/ShipIt); manual via package manager | Electron app | Yes (default), configurable | Code → About | No | No | Platform-specific |

### Key patterns from competitors

1. **Claude Code is the gold standard for install/update**: Native curl install with auto-update, release channels (latest/stable), version pinning, binary integrity verification (GPG-signed manifests), platform code signing, `claude update`, `claude doctor`. This is production-grade.

2. **Codex CLI uses npm with per-platform optional deps**: `@openai/codex` pulls `@openai/codex-darwin-arm64` etc. as optional dependencies. Postinstall links the native binary. The installed binary does NOT invoke Node. This is the pattern ARC should copy for npm distribution.

3. **Aider is the simplest path**: `pip install` or `pipx install`. No auto-update, no binary, just Python. This is the baseline for ARC's pipx path.

4. **GitHub CLI is the most comprehensive for package managers**: brew, apt, dnf, apk, WinGet, npm, prebuilt binaries, build from source. Signed repos. Build provenance attestations via Sigstore. Shell completions built in.

5. **OpenCode had a curl install script**: `curl -fsSL https://raw.githubusercontent.com/opencode-ai/opencode/refs/heads/main/install | bash` — simple but works. Archived, so not a model to follow long-term.

6. **Nobody with a Python backend bundles Python in npm**: All Python tools (Aider, etc.) stay in pip/pipx land. The npm-wrapper-for-Python pattern is uncommon and adds complexity.

## Gaps

1. **No npm package exists**: `arc-studio` npm package is entirely unbuilt. No `packages/arc-studio-cli/` directory, no shim, no Python bridge.

2. **No pipx CI verification**: The wheel builds (hatchling), but pipx install is not tested in CI.

3. **No update mechanism**: `/update --check` is spec'd but not implemented. No version comparison logic, no channel awareness, no upgrade command printing.

4. **No install script**: No curl-based install for quick onboarding.

5. **No Homebrew formula**: Not even a tap.

6. **No shell completions**: Not spec'd, not implemented. Every competitor CLI has this.

7. **No first-run setup flow**: Spec §7.1 shows welcome screen, but no implementation exists. Users currently need to know `uv run arc serve` and manually configure.

8. **No uninstall documentation**: No documented uninstall flow for any install method.

9. **Version mismatch handling is spec'd but not implemented**: §7.14.2 defines `version-mismatch` daemon state, but no detection or resolution logic exists.

10. **Daemon auto-start is not implemented**: Spec says `arc-studio` may auto-start daemon from `stopped` state, but no daemon lifecycle management exists in CLI.

11. **SwarmGraph bundling works but is opaque**: Vendored SwarmGraph runs via CLI subprocess, but users have no visibility into what's bundled or its version.

12. **No `arc-studio doctor install`**: Spec has `/doctor` for environment checks, but no install-specific doctor (checking if npm/pipx install is correct, if Python is available, if wheel is installed, etc.).

13. **No PyPI publishing pipeline**: The wheel can be built, but publishing to PyPI is not set up or tested.

14. **No npm publishing pipeline**: No CI workflow for npm publish.

15. **No release channel concept**: Claude Code has latest/stable channels. ARC has nothing.

16. **No binary integrity verification**: Claude Code has GPG-signed manifests. GitHub CLI has Sigstore attestations. ARC has nothing.

17. **No arc alias**: Spec says keep `arc` as backward-compat alias, but no alias mechanism exists.

18. **Electron bundling is entirely post-v0.1**: ADR-008 is proposed, not implemented. No spike has been run. This is correctly deferred but means v0.1 has no desktop app story.

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **P1: Create `arc-studio` npm package with per-platform optional deps (Codex pattern)** | npm is the primary distribution channel for Node-first users. Codex proves the pattern: npm pulls platform-specific native optional deps, postinstall links binary. For ARC, the "native binary" is the Python wheel + shim. | v0.1 | Medium — npm optional deps for Python wheel require careful platform targeting; Python must be present on system | §17: resolve npm name question; add npm package structure to §16 assets |
| **P2: pipx install as first-class Python path** | pipx is Python best practice for CLI tools. Aider uses it. Lower maintenance than npm wrapper. Python-first users prefer it. | v0.1 | Low — wheel already builds, just needs CI verification and PyPI publishing | §17: confirm pipx path; add PyPI publishing to P5 checklist |
| **P3: npm package calls `pipx install` or `pip install` under the hood (NOT bundling Python)** | Bundling Python in npm is complex and uncommon. Instead, npm shim should detect Python, then run `pip install agent-runtime-cockpit` or `pipx install agent-runtime-cockpit` on first run. Keeps npm package thin (~50KB shim + install script). | v0.1 | Medium — pip/pipx must be available; need fallback error messages | §17: change recommendation from "download wheel" to "npm triggers pip install" |
| **P4: Implement `/update --check` and `arc-studio update`** | Spec §10.9 requires it. Claude Code and Codex both have update commands. Check npm/pipx registry, compare semver, print upgrade command. | v0.1 | Low — registry API calls are simple; no self-modification needed | No spec edits needed; implement as spec'd |
| **P5: Implement `arc-studio --version` with client/daemon/protocol/manifest versions** | Spec §10.9 requires it. `arc version` exists but needs to expand to show all four version components. | v0.1 | Low — version sources exist, just need aggregation | No spec edits needed |
| **P6: Add `arc-studio doctor install` subcommand** | Install-specific diagnostics: check Python version, check pip/pipx availability, check if wheel is installed, check npm package version, detect version mismatches, verify SwarmGraph bundled runtime. | v0.1 | Low — extends existing `arc doctor` | Add to §10.4 help text: `/doctor install` for install diagnostics |
| **P7: Add curl install script for quick onboarding** | Claude Code, OpenCode, and most CLI tools have one-liner installs. Reduces onboarding friction dramatically. | v0.1 | Low — shell script that detects platform, installs via pipx or npm | Add to §16 assets: `install.sh` |
| **P8: Add shell completions** | GitHub CLI, Claude Code, and most modern CLIs have completions. ARC has 60+ subcommands; completions are essential for discoverability. | v0.1 | Low — Typer/Click have built-in completion generation | Add to §10.4 help text; add to §16 assets |
| **P9: Document uninstall for all install methods** | Claude Code has explicit uninstall docs per method. ARC needs the same. | v0.1 | Low — documentation only | Add new section to spec: §10.11 Uninstall |
| **P10: Add first-run setup wizard** | Spec §7.1 shows welcome screen. Setup should be: detect Python, offer install method, verify SwarmGraph bundled, prompt for provider key, trust workspace. | v0.1 | Medium — requires CLI REPL infrastructure (Phase 3 of redesign plan) | No spec edits needed; implement §7.1 |
| **P11: Version mismatch auto-detection and resolution** | Spec §7.14.2 defines `version-mismatch` state. Implement detection on startup, show exact versions, suggest upgrade command. | v0.1 | Low — version comparison is trivial; resolution is just printing commands | No spec edits needed |
| **P12: Homebrew tap (not cask)** | Homebrew is the dominant macOS install path. Start with a tap (simpler), graduate to cask after adoption. | v0.2 | Low — Homebrew formula is straightforward for Python packages | Add to §16 assets: `homebrew-tap/` |
| **P13: Release channels (latest/stable)** | Claude Code's release channel pattern is excellent for alpha software. `latest` for bleeding edge, `stable` for regression-tested. | v0.2 | Medium — requires release infrastructure and channel tagging | Add to §10.9: release channel concept |
| **P14: Binary integrity verification** | GPG-signed manifests or Sigstore attestations. Important for enterprise adoption. | v0.3 | Medium — requires signing infrastructure | Add to §16 assets: signing key docs |
| **P15: Daemon auto-start and lifecycle management** | Spec §7.14.2 defines daemon states. CLI should auto-start daemon from `stopped`, detect stale/port-conflict, handle version mismatch. | v0.1 | Medium — daemon lifecycle is non-trivial; needs PID file, health check, cleanup | No spec edits needed; implement §7.14.2 |
| **P16: SwarmGraph bundled version visibility** | Users should see bundled SwarmGraph version in `/version` and `/doctor`. Currently opaque. | v0.1 | Low — read version from vendored package metadata | Add to §10.9: bundled runtime version in version output |

## Recommended Decisions

### Decision 1: npm package uses thin shim + pip install (NOT bundled Python)

**Recommendation:** The `arc-studio` npm package should be a thin Node.js shim (~50KB) that:
1. Detects system Python (>=3.11)
2. Runs `pip install agent-runtime-cockpit` or `pipx install agent-runtime-cockpit` on first run
3. Subsequent runs invoke the installed Python CLI via `child_process`
4. On update, re-runs `pip install --upgrade agent-runtime-cockpit`

**Why:**
- Bundling Python in npm is complex, uncommon, and error-prone (platform-specific builds, signing, size)
- No competitor does this for Python backends
- Aider, LangGraph CLI, and other Python tools stay in pip land
- The npm package becomes a convenience wrapper, not a distribution mechanism for Python
- Keeps npm tarball small (< 100KB vs 50-100MB with bundled Python)
- pipx/pip handle Python package updates independently

**Spec edit:** §17 "Embed Python in npm package?" → change recommendation from "Start with Python requirement + clear doctor" to "npm shim triggers pip/pipx install; Python >=3.11 required"

### Decision 2: pipx is the canonical Python install path

**Recommendation:** `pipx install agent-runtime-cockpit` is the primary Python install method. `pip install` is secondary (for venv users). pipx handles isolation, PATH, and updates cleanly.

**Why:**
- pipx is Python community best practice for CLI tools
- Aider recommends pipx
- Isolated environment prevents dependency conflicts
- `pipx upgrade` handles updates
- No PATH pollution

**Spec edit:** §10.9 pipx example is correct; make it the primary Python recommendation in install docs

### Decision 3: v0.1 ships npm + pipx only; Homebrew/curl are v0.2

**Recommendation:** Do not expand v0.1 scope to include Homebrew formula, curl install script, or apt/dnf repos. Ship npm and pipx paths first, verify they work, then add package managers.

**Why:**
- v0.1 scope is already tight (browser app + Python CLI/wheel)
- npm + pipx covers 90% of target users (Node developers, Python developers)
- Homebrew/curl/apt add maintenance burden (formula updates, repo signing, install script security)
- Claude Code added apt/dnf/apk well after npm/brew existed

**Spec edit:** §17: mark Homebrew and curl install as v0.2

### Decision 4: `/update --check` prints commands, never self-modifies

**Recommendation:** Implement exactly as spec'd in §10.9. `/update --check` queries npm registry or PyPI, compares versions, prints the upgrade command. Never modifies installed files. `arc-studio update` (without `--check`) may run the upgrade command interactively with confirmation.

**Why:**
- Self-modifying installs are risky and uncommon in CLI tools
- Claude Code's auto-update is the exception, not the rule (and only for native installs)
- Printing the command is transparent and lets the user control their system
- Matches spec lock criteria: "/update --check does not self-modify installed files"

**Spec edit:** No changes needed; spec is correct

### Decision 5: Version mismatch is detected on startup, resolved by printing upgrade command

**Recommendation:** On startup, compare `arc-studio` CLI version against daemon version (via `/health`). If mismatch:
- Show both versions explicitly
- If CLI > daemon: suggest `arc-studio update` or package manager upgrade
- If daemon > CLI: suggest npm/pipx upgrade
- Do NOT auto-upgrade or block execution (unless major version mismatch, which is v0.2)

**Why:**
- Auto-upgrading on mismatch is aggressive and can break workflows
- Printing the fix is transparent and matches Claude Code's version-mismatch behavior
- Major version mismatch blocking is a v0.2 concern (when API stability is expected)

**Spec edit:** §7.14.2 `version-mismatch` recovery: change "upgrade matching package" to "show upgrade command; allow continue with warning"

### Decision 6: `arc-studio doctor install` should exist

**Recommendation:** Add install-specific doctor checks:
- Python version (>=3.11)
- pip/pipx availability
- `agent-runtime-cockpit` wheel installed and importable
- npm package version (if npm-installed)
- CLI/daemon version match
- SwarmGraph bundled runtime available
- PATH correctness (arc-studio command resolves correctly)

**Why:**
- Install problems are the #1 source of user friction
- Claude Code has `claude doctor` for exactly this
- ARC has complex dependencies (Python, npm, pip/pipx, SwarmGraph vendored)
- Doctor output is actionable and specific

**Spec edit:** Add to §10.4 help text and §7.10 doctor output

### Decision 7: Shell completions are v0.1 scope

**Recommendation:** Add shell completions for bash, zsh, and fish. Typer has built-in completion support (`--install-completion`). This is low effort and high value.

**Why:**
- ARC has 60+ subcommands; completions are essential for discoverability
- Every competitor has completions
- Typer makes it trivial
- Zero maintenance cost after initial setup

**Spec edit:** Add to §16 assets: shell completion files

### Decision 8: SwarmGraph stays bundled, version visible

**Recommendation:** Keep SwarmGraph vendored in `runtimes/swarmgraph/`. Add version visibility in `/version` output and `/doctor`. Do NOT make SwarmGraph a separate install for v0.1.

**Why:**
- Spec says "SwarmGraph default and bundled" (§0.5)
- Bundled runtime is the zero-friction default
- Separate install adds failure modes and support burden
- Version visibility is sufficient for transparency

**Spec edit:** §10.9: add bundled runtime version to `/version` output

## Specific Spec Edits

### §10.9 Version And Update Check

**Current:**
> `/version` shows CLI version, daemon version, protocol version, and runtime manifest version. `/update --check` checks the current package channel and prints the package-manager command; it does not modify installed files. npm example: `npm install -g arc-studio@latest`. pipx example: `pipx upgrade arc-studio`.

**Edit:**
> `/version` shows CLI version, daemon version, protocol version, runtime manifest version, and **bundled SwarmGraph version**. `/update --check` checks the current package channel and prints the package-manager command; it does not modify installed files. npm example: `npm install -g arc-studio@latest`. pipx example: `pipx upgrade agent-runtime-cockpit`. **`arc-studio update` (without `--check`) interactively runs the upgrade command after confirmation. Auto-update is not implemented in v0.1.**

### §10.4 Help Text

**Add to Diagnostic section:**
```
  /doctor install  install-specific diagnostics (Python, pip, wheel, versions)
```

### §10.10 Redaction Contract

**No changes needed.**

### §16 Assets And Deliverables List

**Add:**
| Asset | Format | Sizes / notes | Name |
|---|---|---|---|
| Shell completions | Script | bash, zsh, fish | `completions/arc-studio.{bash,zsh,fish}` |
| npm package | npm tarball | < 100KB | `arc-studio` on npm |
| Python wheel | PyPI wheel | per release | `agent_runtime_cockpit-*.whl` |
| Install script | Shell | future v0.2 | `install.sh` |
| Homebrew tap | Formula | future v0.2 | `homebrew-arc-studio/Formula/arc-studio.rb` |

### §17 Open Questions

**Resolve:**

| Question | Resolution |
|---|---|
| Is `arc-studio` npm name available? | **[needs verification]** Check npm registry. If taken, use `@arc-studio/cli`. |
| Embed Python in npm package? | **Resolved: No.** npm shim triggers `pip install` or `pipx install`. Python >=3.11 is a prerequisite. |
| Ship CLI before IDE redesign? | **Resolved: Together.** v0.1 ships browser app + Python CLI/wheel simultaneously. |
| Min terminal width? | **Resolved: 80 supported, 100 preferred.** (Already spec'd in §7) |

**Add:**
| Question | Options | Recommendation |
|---|---|---|
| Should `arc-studio doctor install` exist? | Yes, No | **Yes** — install diagnostics are the #1 friction point |
| Should Homebrew be v0.1 scope? | v0.1, v0.2 | **v0.2** — npm + pipx first, Homebrew after stability |
| Should curl install script be v0.1 scope? | v0.1, v0.2 | **v0.2** — security review needed for piped-to-bash scripts |
| How should version mismatch be handled? | Block execution, Warn + continue, Auto-upgrade | **Warn + continue** for v0.1; block on major mismatch in v0.2 |

### §7.14.2 Daemon Lifecycle Contract

**Edit `version-mismatch` row:**

| State | CLI startup | IDE startup | `/status` | `/doctor` | Recovery |
|---|---|---|---|---|---|
| `version-mismatch` | show client/daemon versions, **warn, allow continue** | show banner, **allow continue** | mismatch | fail | **show upgrade command; user runs package manager upgrade** |

### Lock Criteria (§end)

**Add:**
| Criterion | Status |
|---|---|
| Install method documented for npm and pipx. | Required |
| `/update --check` prints commands without self-modifying. | Required |
| `/version` shows CLI, daemon, protocol, manifest, and bundled runtime versions. | Required |
| Shell completions exist for bash, zsh, fish. | Required |
| Uninstall documented for all v0.1 install methods. | Required |

## Acceptance Criteria

### Install

- [ ] `npm install -g arc-studio` succeeds on macOS (arm64, x64), Linux (x64, arm64)
- [ ] `arc-studio --version` prints version and exits 0 after npm install
- [ ] `pipx install agent-runtime-cockpit` succeeds on macOS, Linux
- [ ] `arc --version` prints version and exits 0 after pipx install
- [ ] `arc` alias works after npm install (backward compatibility)
- [ ] First run after npm install auto-installs Python wheel via pip
- [ ] First run after pipx install works without additional setup
- [ ] Python >=3.11 prerequisite is checked and error message is clear if missing
- [ ] SwarmGraph bundled runtime works without additional install

### Update

- [ ] `/update --check` prints current version, latest version, and upgrade command
- [ ] `/update --check` does not modify installed files
- [ ] `/update --check` works for both npm and pipx installs
- [ ] `arc-studio update` prompts for confirmation before running upgrade
- [ ] Version mismatch between CLI and daemon is detected on startup
- [ ] Version mismatch shows exact client and daemon versions
- [ ] Version mismatch suggests specific upgrade command
- [ ] Version mismatch does not block execution in v0.1

### Doctor

- [ ] `arc-studio doctor install` checks Python version
- [ ] `arc-studio doctor install` checks pip/pipx availability
- [ ] `arc-studio doctor install` checks wheel installation
- [ ] `arc-studio doctor install` checks CLI/daemon version match
- [ ] `arc-studio doctor install` checks SwarmGraph bundled runtime
- [ ] `arc-studio doctor install` exits 0 when all checks pass
- [ ] `arc-studio doctor install` exits 2 when a required check fails
- [ ] `arc-studio doctor install --json` returns structured check results

### Version

- [ ] `arc-studio --version` shows CLI version
- [ ] `arc-studio --version` shows daemon version (when daemon running)
- [ ] `arc-studio --version` shows protocol version
- [ ] `arc-studio --version` shows runtime manifest version
- [ ] `arc-studio --version` shows bundled SwarmGraph version
- [ ] `arc-studio --version --json` returns structured version info

### Shell Completions

- [ ] `arc-studio --install-completion bash` installs bash completions
- [ ] `arc-studio --install-completion zsh` installs zsh completions
- [ ] `arc-studio --install-completion fish` installs fish completions
- [ ] Completions cover all top-level subcommands
- [ ] Completions cover options/flags for each subcommand

### Uninstall

- [ ] `npm uninstall -g arc-studio` removes all ARC files
- [ ] `pipx uninstall agent-runtime-cockpit` removes all ARC files
- [ ] Uninstall documentation exists for npm and pipx paths
- [ ] Uninstall removes daemon PID files and session data (or documents how to)
- [ ] Residual files after uninstall are documented

### Distribution

- [ ] Python wheel builds on CI for all supported Python versions (3.11, 3.12, 3.13)
- [ ] Python wheel publishes to PyPI (or TestPyPI for alpha)
- [ ] npm package publishes to npm registry
- [ ] npm package tarball is < 100KB
- [ ] Install instructions in README match actual install commands
- [ ] CI verifies pipx install works
- [ ] CI verifies npm install works

## Reject / Do Not Build

### Rejected: Bundling Python in npm package

**Why rejected:**
- Complex platform-specific builds (macOS signing, Linux musl/glibc, Windows)
- Large tarball (50-100MB vs < 100KB)
- No competitor does this for Python backends
- Maintenance burden for version updates
- Security implications (bundled Python needs its own CVE tracking)
- ADR-008 explicitly defers bundling decisions until measured

**Alternative:** Thin npm shim that triggers `pip install` or `pipx install`.

### Rejected: Auto-update in v0.1

**Why rejected:**
- Claude Code's auto-update is for native binaries, not Python packages
- Auto-updating Python packages through npm is fragile and non-standard
- pipx/pip have their own update mechanisms
- v0.1 is alpha; users should control when they upgrade
- Adds complexity to an already tight v0.1 scope

**Alternative:** `/update --check` prints commands; user runs upgrade manually. Revisit auto-update in v0.2 when release channels exist.

### Rejected: Homebrew cask in v0.1

**Why rejected:**
- Homebrew cask requires stable releases and review process
- Alpha software is a poor fit for Homebrew's stability expectations
- Homebrew tap (not cask) is simpler but still adds maintenance
- npm + pipx covers the primary audience

**Alternative:** Homebrew tap in v0.2, cask in v0.3 when stable releases exist.

### Rejected: curl install script in v0.1

**Why rejected:**
- Piping curl to bash is a security concern that needs review
- Install scripts need platform detection, error handling, rollback
- Adds maintenance burden
- npm + pipx are sufficient for v0.1

**Alternative:** curl install script in v0.2 after security review. Follow Claude Code's pattern (signed script, platform detection, clear error messages).

### Rejected: Electron desktop app in v0.1

**Why rejected:**
- Explicitly out of v0.1 scope per IMPLEMENTATION_PLAN.md and ADR-008
- Daemon bundling spike not yet run
- macOS signing/notarization is complex
- Browser app + CLI is sufficient for alpha

**Alternative:** Electron packaging spike in v0.2, desktop app in v0.3.

### Rejected: Release channels in v0.1

**Why rejected:**
- Requires release infrastructure (channel tagging, stable branch management)
- Alpha software doesn't need latest/stable distinction yet
- Claude Code added channels after many releases

**Alternative:** Release channels in v0.2 when there's enough release history to matter.

### Rejected: Binary integrity verification in v0.1

**Why rejected:**
- GPG signing infrastructure requires key management and CI changes
- Sigstore attestations require build provenance setup
- v0.1 alpha users are early adopters who trust the source
- Adds significant release complexity

**Alternative:** Binary integrity in v0.3 when enterprise adoption is a goal. Follow GitHub CLI's Sigstore pattern.

### Rejected: apt/dnf/apk repositories in v0.1

**Why rejected:**
- Linux package repositories require signing keys, repo hosting, and maintenance
- Python CLI tools are rarely distributed via apt/dnf (Aider doesn't do it)
- npm + pipx cover Linux users adequately

**Alternative:** Revisit in v0.3 if Linux enterprise adoption requires it.

### Rejected: `arc-studio install` command

**Why rejected:**
- Self-install commands are uncommon in CLI tools
- npm/pipx already handle installation
- Adds a command that duplicates package manager functionality

**Alternative:** `arc-studio doctor install` for diagnostics; package managers for actual install.
