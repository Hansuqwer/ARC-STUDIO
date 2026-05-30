# ARC Studio packaging, distribution, and onboarding research

## Executive verdict

The highest-confidence path for ARC Studio is **not** to collapse everything into a single package immediately. Because ARC’s **canonical target is the browser Theia app**, and Theia is explicitly designed to support both browser and desktop deployments from a shared frontend/backend architecture, the best production path is a **hybrid distribution model**: keep the hosted/browser experience as the default surface, add a **locally installable companion daemon** as the main production install target, and treat a polished **Electron desktop app** as the premium convenience layer for users who want native shell behaviour, bundled local services, and seamless upgrades. Theia’s own platform and IDE emphasise cloud and desktop delivery from the same codebase, while Cursor, Codex, Claude Code, Continue, and OpenHands all show that multi-surface distribution beats single-channel distribution for developer tools. citeturn17search4turn17search0turn21view3turn45view0turn15search0turn26view0

For ARC specifically, that means the next production claim should be: **“supported browser app + supported local daemon install on macOS/Linux + signed macOS desktop shell”**, not “one universal desktop package”. The supporting evidence is strong. Cursor ships broad desktop artefacts plus a single-command CLI and enterprise controls; VS Code extensions rely on a marketplace, walkthroughs, and workspace trust rather than native bundling alone; Continue and OpenHands separate “install the UI” from “configure providers and runtime”; LangSmith and Phoenix both use a progressive journey from fastest-start surface to more advanced self-hosted/local setups. citeturn22view0turn23view0turn8search0turn8search12turn24view0turn26view1turn27view0turn28view1

The most practical architecture is therefore:

- **Primary**: browser Theia app + locally installed daemon.
- **Secondary**: Electron desktop app with a **bundled frozen daemon**.
- **Developer/CI**: Docker/devcontainer and headless CLI.
- **Convenience channels**: Homebrew, pipx, and optionally npm as a wrapper/bootstrap surface. citeturn17search4turn38view0turn36view0turn18search13

## Recommended distribution channels

The recommended channel mix for ARC Studio is shown below.

| Channel | Audience | Recommendation | Rationale |
|---|---|---|---|
| Browser Theia app | Most users | **Primary** | Aligns with ARC’s canonical target and Theia’s browser-first/cloud-supported architecture. citeturn17search4turn17search0 |
| Local daemon via **uv-based installer** | Most users who need local execution | **Primary** | `uv` can install tools in isolated environments and can also install/manage Python automatically, which removes one of the biggest onboarding problems for Python-backed tools. citeturn39view1turn39view2turn38view0 |
| Electron desktop app | Users who want all-in-one native UX | **Primary for macOS, secondary overall** | Electron has the most mature packaging, signing, auto-update, and Linux artefact tooling in this space; Cursor is the closest market analogue. citeturn5search5turn5search9turn21view3 |
| Homebrew **formula** | CLI/daemon users on macOS/Linux | **Primary convenience channel** | Homebrew treats Python apps as applications, not libraries, and expects bundled Python deps in a virtualenv; this maps well to a daemon/CLI package. citeturn35view0turn35view1 |
| Homebrew **cask** | Desktop app users on macOS | **Primary convenience channel** | Casks are designed for `.app` bundles and can also expose binaries from within the app bundle. citeturn34view0turn35view3 |
| Linux `.deb` / `.rpm` | Linux end users and managed desktops | **Primary Linux artefacts** | Package-manager installs integrate better with enterprise rollout and upgrades than portable binaries alone; Cursor now ships `.deb`, `.rpm`, and AppImage. citeturn21view3turn5search2turn5search19 |
| Linux AppImage | Portable Linux users | **Fallback artefact** | AppImage is portable and rootless, but desktop integration is not automatic by default; it is best as a portable fallback, not the default Linux story. citeturn33view0turn33view2turn20search11 |
| `pipx install` | Python-native users | **Secondary convenience channel** | pipx is excellent for isolated Python apps, but it assumes a Python/pipx-capable environment and is less universal than `uv` for first-run bootstrap. citeturn36view0turn36view1turn37view1 |
| npm package | Node-centric developers, CI, shell-first users | **Optional wrapper only** | Claude Code proves npm can be an effective agent install surface, but for a Python-backed daemon ARC should keep npm as a wrapper/bootstrap layer, not the source of truth. citeturn15search0turn15search3turn4search19 |
| Docker / devcontainer | Contributors, demos, support, air-gapped workflows | **Primary developer channel, not end-user default** | Matches OpenHands and Phoenix self-host patterns and aligns with the devcontainer spec and Compose support. citeturn26view0turn26view1turn28view1turn18search13turn18search0 |

### Recommended channel strategy

For the next production phase, I recommend shipping these channels in this order:

**First**, a browser experience plus **one-command local daemon bootstrap**. This is the lowest-risk path because it respects ARC’s current architecture, avoids premature desktop lock-in, and gives users local execution when they need it. A good user-facing command would be a branded bootstrap such as `curl … | sh`, but internally it should install `uv` if needed and then run `uv tool install arc-daemon --python 3.12`, because `uv` can manage the interpreter and tool environment in one flow. Cursor and Codex both show that single-command install materially reduces adoption friction. citeturn39view1turn39view2turn22view0turn45view0

**Second**, a signed **Electron desktop app for macOS** with the daemon bundled inside it. The Electron ecosystem has production-grade tooling for code signing, Linux artefacts, and auto-updates, and Electron-based coding tools like Cursor have standardised the “desktop app + CLI” pairing. Theia also already has a desktop path, so this is strategically aligned. citeturn5search5turn32view0turn17search4turn21view3

**Third**, Linux managed artefacts: `.deb` and `.rpm` first, AppImage second. Cursor’s public Linux download matrix is a useful benchmark here. Electron Builder and Electron Forge both support these formats; AppImage remains useful but should not carry the full Linux support burden because of its weaker install/update/integration story. citeturn21view3turn5search2turn5search19turn33view0turn33view2

### Benchmark comparison

The market patterns are consistent:

| Product / ecosystem | Distribution pattern | ARC implication |
|---|---|---|
| Cursor | Desktop app for macOS/Windows/Linux, Linux `.deb`/`.rpm`/AppImage, one-command CLI install, enterprise policies for trust and updates. citeturn21view3turn22view0turn23view0 | ARC should mirror the **desktop + CLI/daemon** split, especially for managed environments. |
| VS Code extensions | Marketplace / VSIX distribution, walkthroughs, workspace trust, telemetry controls. citeturn8search0turn8search12turn8search2turn8search3 | ARC should borrow **walkthrough**, **trust**, and **enterprise policy** patterns even outside extension distribution. |
| Theia apps | Same framework supports cloud and desktop; runtime VS Code extension support via Open VSX-compatible flows. citeturn17search4turn17search8turn17search15 | ARC should keep the browser target canonical and add desktop as an additional shell, not a fork. |
| Claude Code | npm for CLI; one-click bundled desktop extensions for local MCP servers, including Node/Python/binary servers. citeturn15search0turn15search3 | ARC can justify an **npm wrapper** later, but more importantly should copy the **bundled local extension/server** idea. |
| Codex CLI | Standalone installer, first-run sign-in, multi-surface quickstart. citeturn45view0turn45view2turn45view3 | ARC should copy the **first-run auth/setup flow** and **single-command install**. |
| Continue | IDE extension install, sign-in, interactive quickstart, explicit local-model and telemetry docs. citeturn24view0turn24view1turn25search0turn25search7 | ARC should copy the **interactive learning path** and **local provider setup guidance**. |
| OpenHands | Cloud, CLI, and local Docker GUI as separate entry points; uv-based launcher recommended; initial LLM settings popup. citeturn26view0turn26view1 | ARC should copy the **surface chooser** and the **provider-setup wizard**. |
| LangSmith / Phoenix | Cloud-first start, self-host later; simple API-key/env-var quickstarts; Phoenix also supports Docker/K8s/air-gapped paths. citeturn27view0turn27view1turn28view1 | ARC should present **fastest start first**, then reveal advanced local/self-host options rather than front-loading complexity. |

## Packaging architecture

### Recommended architecture

ARC should package around a **stable daemon contract**, not around a monolithic app bundle. Theia’s split between frontend and backend processes is already a good conceptual foundation: the UI should remain a thin client against a versioned local/remote service boundary, and packaging should vary by channel without changing that boundary. citeturn17search4turn17search9

I recommend producing **four first-class artefacts from the same release commit**:

1. **`arc-web`**: the hosted/browser Theia deployment.
2. **`arc-daemon`**: a Python daemon distributed as a wheel plus `uv`/pipx/Homebrew install target.
3. **`arc-desktop`**: an Electron shell that embeds the web UI and ships a frozen daemon inside the app resources.
4. **`arc-dev`**: Docker images and a devcontainer for contributors, CI, and support reproduction. citeturn18search0turn18search13turn26view1

That lets ARC meet three different user expectations cleanly: **browser-first**, **CLI/local-service-first**, and **desktop-all-in-one**. It also creates a durable support model: if the desktop shell ever lags, the browser app plus daemon remains viable; if self-hosted/air-gapped users reject desktop packaging, the daemon and container channels still work. This is the same kind of multi-surface resilience seen in Cursor, Codex, OpenHands, LangSmith, and Phoenix. citeturn21view3turn45view3turn26view0turn27view0turn28view1

### Best packaging approach for Python and Theia/Electron

For a **standalone daemon install**, the best approach is **`uv`-managed Python tooling**, with pipx support as an additional convenience channel. `uv` can install tools in isolated environments, keep those environments persistent, and automatically install missing Python versions. That is a better fit than asking users to manage Python themselves, and it is materially better than making pipx the only first-run path on Linux distributions that now treat system Python as externally managed. citeturn39view1turn39view2turn37view1

For a **desktop-bundled daemon**, the best approach is **Electron + frozen daemon bundle**. Electron Builder / Forge already cover the desktop shell packaging problem across macOS and Linux, while PyInstaller solves the “don’t require a separately installed Python” problem for the embedded daemon. PyInstaller explicitly bundles a Python application and its dependencies so it can run without a preinstalled interpreter, but it must be built per target platform. citeturn5search5turn5search9turn41view0turn42view3

That leads to a clean rule:

- **Use `uv` for independent daemon installs.**
- **Use PyInstaller only for the daemon embedded inside desktop artefacts.**
- **Do not use PyInstaller as the main public daemon distribution channel.** PyInstaller is excellent for “ship me a working runtime inside a desktop bundle,” but weaker as the only public upgrade and support surface because it ties everything to platform-specific frozen bundles. This last point is an architectural inference from the tooling characteristics, not an explicit vendor claim. citeturn41view0turn42view3turn39view2

### PyInstaller vs uv standalone vs embedded Python

| Option | Best fit | Strengths | Weaknesses | Recommendation |
|---|---|---|---|---|
| **PyInstaller** | Bundled desktop daemon | No separate Python install; mature frozen-app workflow; supports macOS/Linux/Windows builds on native hosts. citeturn41view0turn42view3 | Native per-platform build requirement; larger/fatter artefacts; less elegant as a standalone upgrade channel. | **Use inside Electron bundles only**. |
| **uv standalone + uv tool install** | Public daemon / CLI install | Isolated tool envs, persistent installs on PATH, automatic Python downloads/management, strong one-command story. citeturn39view1turn39view2turn38view0 | Still exposes a Python-tool mental model; not an all-in-one GUI story. | **Make this the default daemon install path**. |
| **Embedded Python via python-build-standalone / custom embed** | Future custom launcher / native wrapper | Self-contained highly portable Python distributions; designed for downstream repackaging and embedding. citeturn40view0turn43view0 | Highest engineering cost; you own much more of the runtime assembly and update logic. | **Reserve for a later optimisation phase**. |

The right sequencing is therefore: **`uv` now, PyInstaller for desktop bundles now, embedded Python later only if you outgrow both**. citeturn39view2turn41view0turn40view0

### Electron and Python daemon bundling

The recommended Electron packaging shape is:

- `app.asar` for the Electron/Theia shell.
- `resources/daemon/<platform>-<arch>/` for a **frozen daemon** and any helper files.
- A small manifest containing the daemon version, supported protocol version, and migration requirements.
- Desktop startup logic that launches the daemon, performs a health/version handshake, and only then opens the ARC workspace. This is an implementation recommendation grounded in Electron packaging maturity and Theia’s multi-process model. citeturn17search4turn5search5turn32view0

That architecture also supports mixed channels cleanly: the browser app can talk to an independently installed daemon, while the Electron app can talk to its own bundled daemon. The user sees the same product surface; ARC gets two packaging strategies without two backends. This is exactly the sort of separation that keeps future Tauri or native-shell experiments possible without rewriting the daemon. citeturn17search4turn17search8

### Tauri alternatives

Tauri’s documented advantages are real: it uses the system webview, aims for smaller binaries, and emphasises a more security-focused foundation. That makes it an attractive future option if ARC later decides bundle size or attack-surface perception matters more than ecosystem maturity. citeturn6search2turn6search10turn6search14

However, **Tauri is not the best first production path for ARC Studio**. ARC already has a Theia/browser core and an Electron packaging spike. Electron has better-aligned operational tooling for shipping an IDE-like desktop app with installers, auto-updates, signing, Linux packages, and a known market pattern among coding tools. Theia itself already positions cloud and desktop as twin targets, and the Theia IDE ships downloadable desktop artefacts. citeturn17search4turn17search1turn5search5turn5search9

If ARC wants alternatives beyond Tauri, **Wails** and **Neutralinojs** exist, but they are a worse fit for a Theia-based IDE product. Wails is Go-centred; Neutralino is intentionally minimal. Neither has the same level of alignment with Theia/VS Code-style extension ecosystems and desktop IDE expectations. They are useful references, but not the recommended packaging baseline. citeturn6search0turn6search8turn6search1turn6search9

## First-run onboarding

### First-run onboarding plan

ARC’s first-run onboarding should copy the best parts of **VS Code walkthroughs**, **Continue’s interactive tutorial**, **OpenHands’ provider settings popup**, and **Codex/Cursor’s short install-to-first-task path**. The key lesson from these products is that the first run should move the user through a **small number of irreversible checkpoints** with visible progress, not dump them into a settings screen. VS Code explicitly recommends walkthrough-based onboarding; Continue shows a step-by-step tutorial with concrete tasks; OpenHands opens with provider/model/API-key setup; Codex and Cursor reduce install friction by getting the user to a working session quickly. citeturn8search12turn24view1turn26view1turn45view0turn7search13

I recommend a **six-stage onboarding flow**:

1. **Choose mode**: “Browser only”, “Connect local agent”, or “Use desktop app”.
2. **Run ARC Doctor**: detect daemon, shell PATH, Docker, supported providers, and local model servers.
3. **Set up provider**: choose OpenAI, Anthropic, OpenAI-compatible, Ollama/LM Studio/local, or managed enterprise endpoint.
4. **Trust this workspace?**: restricted vs trusted mode, with explicit explanation of what changes.
5. **Telemetry and crash reports**: separate choices, both clearly explained.
6. **Do one useful task**: guided first action on the current repo, or a sample repo if no workspace is open. citeturn8search2turn8search12turn24view1turn25search0turn26view1

### Local provider setup UX

This is one of the most important UX areas. Continue’s model docs and Ollama guide, and OpenHands’ setup guide, both show that users need help with **more than just entering an API key**: they need model choice, base URLs, local server health checks, and clear defaults. citeturn25search7turn25search9turn26view1

ARC should therefore offer a provider picker with **prebuilt provider types**:

- **Managed cloud**: OpenAI, Anthropic, Gemini, ARC-managed endpoint.
- **OpenAI-compatible**: custom base URL, API key, model ID.
- **Local**: autodetect Ollama, LM Studio, llama.cpp, and any OpenAI-compatible localhost server.
- **Offline preset**: disables telemetry prompts, hides cloud providers, and prioritises local models. citeturn25search7turn25search1turn26view1turn28view1

Each provider flow should have:
- a **Test connection** action,
- a **recommended default model**,
- a **cost/privacy note**,
- and a **save to OS keychain / secret vault** option rather than plaintext config by default. The keychain pattern is strongly reinforced by Anthropic’s desktop extension architecture, which stores sensitive configuration in the OS secret store. citeturn15search3turn27view0

### Trust workspace UX

ARC should copy the **VS Code workspace trust** model almost directly. VS Code’s trust system exists because opening a repository can trigger code execution by the editor or extensions; that maps closely to ARC’s daemon, local tools, shell commands, model providers, and future agent behaviours. citeturn8search2turn8search9turn8search16

So ARC should have two modes:

- **Restricted mode**: read-only browsing, code search, explanations, no shell execution, no agent writes, no local-provider auto-run, no workspace hooks.
- **Trusted mode**: full daemon, tools, extensions, commands, provider access, and autonomous actions.

This should be per-folder, persisted, and reversible. Cursor’s enterprise policy surface also confirms that workspace trust is a policy-worthy control, not just a UX nicety. citeturn23view0

### Telemetry opt-in UX

Continue and VS Code both surface telemetry configuration explicitly, and VS Code distinguishes enterprise-managed telemetry controls from user settings. That is the right benchmark. ARC should use **explicit opt-in**, not silent collection plus a buried settings toggle, especially because ARC will touch code, providers, and local environments. citeturn25search0turn8search3turn8search7

The best pattern is a **split consent screen**:
- **Crash diagnostics**: off-by-default or soft-opt-in depending on product posture.
- **Product usage metrics**: explicit opt-in.
- **Never collect code, prompts, or keys without separate affirmative consent**.

Enterprise-managed installs should be able to lock these settings, just as Cursor and VS Code allow managed policy overrides. citeturn23view0turn8search3

## Signing, security, upgrades, and migrations

### Signing and security plan

For **macOS direct distribution**, the requirements are straightforward and non-optional: sign with a **Developer ID Application** certificate, enable the **Hardened Runtime**, notarize the app, and staple the notary ticket. Electron Builder’s docs are explicit that unsigned apps trigger warnings or blocks and that notarization is additionally required on macOS 10.15+ for direct distribution. Apple’s docs are explicit that Hardened Runtime is required for notarization and that only the entitlements actually needed by the app should be enabled. citeturn32view0turn29view1turn5search3

That means ARC should automate the following in CI for macOS desktop releases:

- sign the outer `.app`,
- sign all nested executables/frameworks,
- sign the **bundled daemon binary** separately inside the app bundle,
- notarize the final artefact,
- staple the ticket,
- fail the build if signing credentials are missing. Electron Builder’s `forceCodeSigning` option is specifically useful here. citeturn32view0

For **Linux**, the security plan should be channel-specific:

- **`.deb` / `.rpm`**: sign repository metadata / package repositories and publish checksums.
- **AppImage**: publish SHA-256 checksums and use AppImage’s signature/update capabilities where feasible. AppImage supports digital signatures and embedded update information, but it does not self-integrate with the desktop by default. citeturn20search2turn20search1turn33view2

For secrets, ARC should default to the **OS keychain / secret store** for provider credentials, not project files. Anthropic’s desktop extension model is a strong benchmark: sensitive configuration is stored in the operating system’s secret vault, while the manifest provides typed configuration fields. citeturn15search3

### Upgrade and migration plan

ARC should support **three release channels** from day one: **stable**, **preview**, and **nightly**. Cursor’s public release downloads and changelog cadence, plus its enterprise update policies and minimum-version posture, show how important disciplined channels and version windows are once a developer tool is installed on many machines. citeturn21view3turn23view0

The upgrade model should be different by channel:

- **Electron desktop**: background update checks, apply-on-quit for self-managed users, and MDM/package-manager updates for managed users.
- **uv-installed daemon**: `arc upgrade` should wrap `uv tool upgrade arc-daemon`.
- **pipx-installed daemon**: `arc upgrade` should wrap `pipx upgrade arc-daemon`.
- **Homebrew**: `brew upgrade` for formula/cask users.
- **Docker/devcontainer**: explicit image/tag updates, not silent mutation. citeturn23view0turn39view0turn36view0turn18search13

For user data, ARC needs a **versioned migration engine**. OpenHands provides a very simple but telling precedent by documenting a local-state path migration for older versions. ARC should formalise that idea: every stateful file should carry a schema version; app startup should run migrations before opening the workspace; major migrations should create an automatic backup and a rollback path. citeturn26view1

The ideal post-upgrade UX is:

- show **what changed**,
- show **what was migrated**,
- warn if a workspace/provider/permission changed materially,
- and provide a **one-click rollback or restore backup** for local state. This is especially important if ARC adds trust policies, local-provider presets, or extension install state later. The recommendation is an inference from the migration and update patterns above. citeturn23view0turn26view1

## Devcontainer and Docker

ARC should keep Docker and devcontainers, but frame them as **developer and support infrastructure**, not as the main onboarding path for ordinary users. The devcontainer specification is specifically designed to define deterministic development environments through `devcontainer.json`, and the reference CLI integrates with Docker Compose for multi-container setups. VS Code’s devcontainer tooling then provides a familiar entry point for contributors. citeturn18search0turn18search8turn18search13

The recommended plan is:

- ship a **root `.devcontainer/devcontainer.json`** for contributors,
- support **Compose-backed development** when ARC needs the Theia app, daemon, and optional provider sidecars,
- publish an **`arc-dev` image** for reproducible local debugging, CI, demo environments, and support reproduction,
- and add an **`arc doctor --container`** mode that validates Docker socket, images, ports, and mounted workspace permissions. citeturn18search5turn12search13turn26view1

OpenHands is a good cautionary example here. It successfully offers a local Docker GUI and a `uv`-based launcher, but its docs still have to walk users through Docker prerequisites, socket settings, and model configuration. That is manageable for contributors and advanced users; it is too heavy to be ARC’s default mainstream onboarding path. citeturn26view0turn26view1

So the Docker/devcontainer plan should be:

- **End users**: browser + daemon, or desktop app.
- **Contributors**: devcontainer first.
- **CI / support / demos**: Docker image and Compose.
- **Air-gapped or enterprise trials**: documented container deployment path with pinned versions. Phoenix’s self-hosting docs are a good benchmark for this “cloud first, self-host later, container-ready throughout” posture. citeturn28view1turn27view0

## Prioritised improvements and feature table

### Top onboarding improvements

The highest-leverage onboarding improvements for ARC are these:

1. **Welcome checklist / walkthrough panel** after first launch. Inspired by VS Code walkthroughs and Continue’s tutorial. citeturn8search12turn24view1  
2. **ARC Doctor** that checks daemon, PATH, Docker, local providers, permissions, and versions before the user hits a failure. Inspired by Wails’ `doctor`, Cursor CLI verification, and OpenHands’ setup guidance. citeturn6search4turn22view0turn26view1  
3. **One-click local daemon install** from the browser UI. Inspired by Cursor/Codex one-command installer patterns. citeturn22view0turn45view0  
4. **Provider picker with presets** for OpenAI, Anthropic, OpenAI-compatible, and local model servers. Inspired by OpenHands and Continue. citeturn26view1turn25search7  
5. **Local model autodiscovery** for Ollama / localhost-compatible servers. Inspired by Continue’s local-model guidance. citeturn25search7turn25search1  
6. **Test connection + save to keychain** on every provider screen. Inspired by Anthropic desktop extension config handling and LangSmith’s key-first setup. citeturn15search3turn27view0  
7. **Workspace trust gate** before shell, write, agent, or extension capabilities are enabled. Inspired by VS Code and Cursor. citeturn8search2turn23view0  
8. **Split telemetry consent** for crash reports vs product analytics. Inspired by VS Code and Continue. citeturn8search3turn25search0  
9. **Guided first task** against the current repo, with one safe example. Inspired by Continue quick start and Cursor quickstart. citeturn24view1turn7search13  
10. **Optional sample repo** when no workspace is open. Inspired by tutorial-led products like Continue and LangSmith quickstarts. citeturn24view1turn27view1  
11. **Permission preview** showing what ARC may run in restricted vs trusted mode. Inspired by Codex approval modes and Cursor allowlists. citeturn45view0turn23view0  
12. **Health dashboard** for daemon, provider, extensions, and agent capabilities. Inspired by observability-oriented onboarding in LangSmith/Phoenix. citeturn27view1turn28view1  
13. **Migration summary after upgrade** explaining changed settings, moved state, or required actions. Inspired by OpenHands’ explicit migration note. citeturn26view1  
14. **Offline / air-gapped preset** that hides cloud-first assumptions and disables telemetry by default. Inspired by Continue offline mode and Phoenix self-hosting. citeturn25search1turn28view1  
15. **Managed-environment awareness** that tells the user when policies are enforced by IT. Inspired by Cursor enterprise policies and VS Code enterprise controls. citeturn23view0turn8search3  

### Top packaging improvements

The most important packaging improvements are these:

1. **Adopt `uv` as the primary daemon installer**. citeturn39view1turn39view2  
2. **Ship a signed Electron desktop app with a bundled frozen daemon**. citeturn32view0turn41view0  
3. **Publish a Homebrew tap with both formula and cask**. citeturn34view0turn35view1  
4. **Make `.deb` and `.rpm` the primary Linux packages**. citeturn21view3turn5search2turn5search19  
5. **Keep AppImage as a portable fallback, not the only Linux package**. citeturn33view0turn33view2  
6. **Automate macOS signing, notarization, and stapling in CI**. citeturn32view0turn29view1turn5search3  
7. **Version the daemon/app protocol explicitly** so browser, daemon, and desktop packages can negotiate compatibility. This is an architectural recommendation supported by the multi-surface patterns above. citeturn17search4turn21view3turn45view3  
8. **Give every release a machine-readable artefact manifest** with hashes, channels, and minimum compatible versions. This is a recommendation grounded in the release/update patterns used by Cursor/Homebrew/package channels. citeturn23view0turn35view2  
9. **Add a branded `arc upgrade` command** that delegates to the right underlying channel. citeturn39view0turn36view0turn23view0  
10. **Offer an npm wrapper only after the core daemon and desktop channels are stable**. citeturn15search0turn4search19  

### Feature table

| Feature | Source | User value | Platform | Complexity | Priority |
|---|---|---|---|---|---|
| Onboarding: Welcome checklist | VS Code walkthroughs; Continue Quick Start citeturn8search12turn24view1 | Clear progress from install to first success | All | M | P0 |
| Onboarding: ARC Doctor | Wails doctor; Cursor CLI verification; OpenHands setup citeturn6search4turn22view0turn26view1 | Fewer setup failures and support tickets | All | M | P0 |
| Onboarding: One-click daemon install from UI | Cursor CLI installer; Codex standalone installer citeturn22view0turn45view0 | Turns browser users into productive local users quickly | macOS, Linux | M | P0 |
| Onboarding: Provider picker with presets | OpenHands setup; Continue model guidance citeturn26view1turn25search9 | Faster provider setup and fewer invalid configs | All | M | P0 |
| Onboarding: Local model autodiscovery | Continue Ollama guide; Continue offline mode citeturn25search7turn25search1 | Better privacy-focused and offline UX | macOS, Linux | M | P0 |
| Onboarding: Test connection and keychain save | Anthropic desktop extensions; LangSmith account/API-key flow citeturn15search3turn27view0 | Prevents broken provider setup and insecure key storage | All | M | P0 |
| Onboarding: Workspace trust gate | VS Code Workspace Trust; Cursor policy controls citeturn8search2turn23view0 | Safer repo opening and better enterprise confidence | All | M | P0 |
| Onboarding: Split telemetry consent | VS Code telemetry docs; Continue telemetry docs citeturn8search3turn25search0 | Clearer privacy posture and less surprise | All | S | P0 |
| Onboarding: Guided first task | Continue tutorial; Cursor quickstart citeturn24view1turn7search13 | Users reach value immediately | All | M | P0 |
| Onboarding: Sample repo fallback | Continue tutorial; LangSmith quickstart citeturn24view1turn27view1 | Useful even before opening a real workspace | All | S | P1 |
| Onboarding: Permission preview | Codex approval modes; Cursor allowlists citeturn45view0turn23view0 | Reduces fear around agent autonomy | All | M | P1 |
| Onboarding: Health dashboard | LangSmith tracing visibility; Phoenix workflow overview citeturn27view1turn28view0 | Easier troubleshooting and admin support | All | M | P1 |
| Onboarding: Post-upgrade migration summary | OpenHands state migration note citeturn26view1 | Fewer confusing “something changed” moments | All | M | P1 |
| Onboarding: Offline preset | Continue offline guide; Phoenix self-hosting/air-gapped stance citeturn25search1turn28view1 | Stronger offline and regulated-environment story | macOS, Linux | M | P1 |
| Onboarding: Managed-environment awareness | Cursor enterprise deployment; VS Code enterprise telemetry management citeturn23view0turn8search3 | Better enterprise UX and fewer support escalations | All | M | P1 |
| Packaging: uv-first daemon installer | uv tool install and managed Python citeturn39view1turn39view2 | One-command install without preinstalled Python | macOS, Linux | M | P0 |
| Packaging: Bundled frozen daemon inside Electron | Electron Builder packaging; PyInstaller app bundling citeturn5search5turn41view0 | All-in-one desktop UX | macOS, Linux | L | P0 |
| Packaging: Homebrew formula for daemon/CLI | Homebrew Python app guidance; bottle docs citeturn35view1turn35view2 | Familiar install/upgrade path for developers | macOS, Linux | M | P0 |
| Packaging: Homebrew cask for desktop app | Homebrew Cask Cookbook citeturn34view0turn35view3 | Native desktop install path on macOS | macOS | M | P0 |
| Packaging: Linux `.deb` and `.rpm` | Cursor Linux artefacts; Electron Forge makers citeturn21view3turn5search2turn5search19 | Better managed installs and updates | Linux | L | P0 |
| Packaging: AppImage fallback with signatures/update info | AppImage docs on updates/signatures; Electron Builder AppImage docs citeturn20search1turn20search2turn33view0 | Portable Linux install for unmanaged users | Linux | M | P1 |
| Packaging: CI signing/notarization pipeline | Apple notarization/hardened runtime; Electron Builder signing docs citeturn29view1turn5search3turn32view0 | Removes scary macOS warnings and enables production trust | macOS | L | P0 |
| Packaging: Release manifest with hashes/channels | Homebrew bottle metadata; Cursor update/version controls citeturn35view2turn23view0 | Safer upgrades and clearer support matrix | All | M | P1 |
| Packaging: Unified `arc upgrade` command | uv upgrades; pipx upgrades; Cursor update modes citeturn39view0turn36view0turn23view0 | Simpler cross-channel maintenance | All | M | P1 |
| Packaging: npm wrapper / bootstrap CLI | Anthropic npm install pattern; npm publish docs citeturn15search0turn4search19 | Better Node-centric adoption and CI fit | All | M | P2 |

## Open questions and limitations

A few product-shaping questions remain unresolved because they depend on ARC’s product stance rather than public packaging tooling.

The first is whether ARC wants to be **SaaS-first**, **desktop-first**, or **air-gapped-first** for its next commercial step. The recommended architecture above supports all three, but the correct default channel is different in each case. The public research strongly supports a browser-plus-daemon baseline, but the final weighting depends on ARC’s customer mix. citeturn17search4turn28view1turn23view0

The second is how much ARC intends to rely on **runtime extension install** versus shipping a more closed, curated bundle. Theia and VS Code patterns support both, but trust, support load, and packaging complexity all change materially depending on that choice. citeturn17search15turn8search4turn8search11

The third is whether ARC wants the **npm channel** to be a real product surface or only a convenience wrapper. Claude Code makes npm attractive, but ARC’s Python daemon means npm becomes most compelling only if it wraps a signed binary or a `uv`/Docker bootstrap, rather than owning the runtime itself. citeturn15search0turn15search3turn39view2

On the evidence collected here, the most defensible next move is still clear: **productionise the browser + daemon path first, add a signed Electron desktop shell second, and keep Docker/devcontainers as developer infrastructure rather than mainstream onboarding**. citeturn17search4turn39view2turn32view0turn18search0