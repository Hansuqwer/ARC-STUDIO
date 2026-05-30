# ARC Studio plugin and extension ecosystem recommendations

## Executive recommendation

Taking your stated ARC baseline as the starting point — internal adapters, tools, an MCP server, CLI commands, Theia widgets, and a provider registry, but no stable third-party SDK yet — the strongest recommendation is **one manifest, several execution models, and explicit trust boundaries**. In practice, that means a single ARC plugin package format that can declare many component types, but each component runs in the safest viable runtime: declarative packs for prompts and workflows, out-of-process workers for tools and provider adapters, MCP bundles for protocol-native capabilities, and sandboxed webviews for IDE panels. That pattern borrows the best parts of VS Code’s contribution model, Theia’s host-process isolation, Claude Code’s directory-based plugin packaging and marketplaces, Continue’s repo-native prompt/check model, LangChain’s independent package ecosystem, LiteLLM’s provider adapters and callbacks, and MCP’s capability negotiation. It also avoids the weakest pattern in the market: giving third-party code the same privileges as the host application, which VS Code explicitly says its extension host has, and which Obsidian says it cannot reliably restrict with granular permissions. citeturn23view0turn23view1turn23view2turn23view4turn34view0turn27view2turn23view6turn23view7turn24view0turn35view0turn26view2

The practical outcome for ARC should be a **layered plugin system** rather than a single monolithic SDK. Third parties should be able to extend ARC through stable extension points for adapters, tools, slash commands, sandbox policies, MCP tools/resources/prompts, provider adapters, eval scorers, memory extractors, IDE panels/widgets, workflow templates, prompt templates, event sinks/webhooks, and context providers. But those extension points should not all share one privilege model or one runtime. kubectl/Krew, GitHub CLI, and MCP all show that executable plugins can be powerful and simple, yet both Kubernetes and GitHub warn users that third-party extensions are effectively arbitrary code and should be treated cautiously. ARC should therefore make “safe by default, powerful by request” a product principle rather than an afterthought. citeturn24view6turn30view2turn24view8turn30view3turn35view1

## Cross-ecosystem lessons

Across the systems you asked about, the most durable plugin ecosystems share three structural traits. First, they use **small declarative manifests** to advertise capabilities and compatibility: VS Code uses `package.json` with `contributes`, `activationEvents`, dependencies and engine compatibility; Obsidian uses `manifest.json` plus `minAppVersion` and optionally `versions.json`; Home Assistant uses `manifest.json` plus `config_flow`; Claude Code uses `.claude-plugin/plugin.json`; Continue uses `config.yaml` plus markdown frontmatter for prompts and checks; MCP uses capability declarations and standard message schemas for tools, resources and prompts. ARC should follow that pattern and keep the manifest human-readable, schema-validated, and stable. citeturn23view0turn26view0turn26view1turn24view3turn24view4turn27view2turn23view6turn35view1turn35view2turn36view1

Second, mature ecosystems separate **distribution metadata from execution artefacts**. Claude Code marketplaces are catalogues that list plugins and their sources; Krew is an index that points to plugin archives with version, URI and checksum; the MCP Registry is explicitly a standardised metadata layer that points to code in package registries and expects downstream marketplaces to add curation; LangChain now requires most integrations to live as independent packages outside the main repo; Theia can preinstall extensions from OpenVSX or URLs and can also let users install them at runtime. ARC should mirror that. It should have a registry that stores discovery metadata, permissions, review status, signatures and compatibility, while package bytes live in OCI, GitHub Releases, npm or another blob store. citeturn26view8turn41view1turn30view1turn30view2turn26view6turn23view7turn37view1turn40view1

Third, ecosystems split on security. Some systems rely heavily on **trust, review and user prompts** because they do not have meaningful runtime containment. VS Code now prompts users to trust third-party publishers, signs Marketplace extensions and secret-scans packages, but its extension host still inherits essentially all VS Code permissions. Obsidian defaults to Restricted Mode and warns that community plugins inherit Obsidian’s access because it cannot reliably impose fine-grained permission limits. GitHub CLI and kubectl both warn that third-party extensions are not certified or audited. By contrast, Theia puts plugins in a backend-spawned host process, Neovim remote plugins run in separate processes, Claude Code routes sensitive actions through explicit permission rules and PreToolUse hooks, and MCP’s own guidance says tools should remain human-controlled with explicit consent. ARC should take the latter route wherever possible. citeturn31view2turn31view1turn31view3turn26view2turn30view3turn24view6turn23view4turn28view4turn26view9turn34view2turn35view0turn35view1

A few ecosystem-specific lessons map especially well to ARC. Claude Code shows the value of a **namespaced, self-contained plugin directory** with bundled skills, hooks, MCP servers and versioned marketplaces; Continue shows how much adoption you get when prompts, checks and agents are just **markdown plus frontmatter** stored in the repo; LiteLLM shows that provider integration succeeds when the extension point is just an **adapter normalising to a standard output** with callbacks and logging around it; Home Assistant shows the value of **quality tiers, config flows, diagnostics and explicit manifest metadata**; LangChain shows that a central platform scales better when third parties ship **independent integration packages** that satisfy interface tests rather than landing everything in core. ARC should borrow all of those. citeturn34view0turn27view3turn25view0turn25view1turn25view3turn24view0turn24view1turn24view2turn24view3turn24view4turn24view5turn33view0turn23view7turn37view0turn37view1

## Recommended ARC plugin architecture

**Recommended plugin architecture.** ARC should ship a **capability-oriented plugin host** with four runtime classes.

The first class should be **declarative packs**: prompt templates, workflow templates, slash commands, checks/eval recipes, context recipes, and light-weight UI configuration. These should be YAML/JSON/Markdown assets only, similar to Continue checks and prompts or MCP prompt definitions. They are the easiest to review, safest to distribute, and should not require code execution permissions. citeturn25view0turn25view1turn25view3turn36view1

The second class should be **sandboxed workers** for local logic: memory extractors, eval scorers, context providers that read local state, and policy modules that make recommendations. These should run either in WASI or in tightly constrained subprocess containers with explicit file, network and CPU limits. The Theia host-process pattern, Neovim remote-plugin pattern and Claude’s tool-hook control flow all point in the same direction: isolate extension logic from the main product process and communicate over a narrow RPC surface. citeturn23view4turn28view4turn34view2

The third class should be **service adapters** for anything inherently processful or network-facing: provider adapters, tool adapters, external system adapters, event sinks, and bundled MCP servers. LiteLLM’s provider adapter model is directly relevant here: a provider plugin should normalise external request/response formats into ARC’s provider contract, while callbacks and logging remain host-managed. MCP also gives ARC a ready-made shape for exporting third-party tools, resources and prompts through a standard protocol. citeturn24view0turn38view2turn24view1turn24view2turn35view0turn35view1turn35view2turn36view1

The fourth class should be **UI extensions**: Theia widgets, panels, inspectors and task views. These should be rendered as webviews or iframes with strict content-security policy and a postMessage bridge, not with arbitrary code running inside ARC’s frontend shell. VS Code’s webview-style contribution model and Theia’s distinction between native extensions and VS Code-compatible plugins are the right inspirations here. citeturn23view0turn40view0turn40view1

Operationally, ARC should split the system into five host services: a **plugin manager** that installs, validates and updates plugins; a **permission broker** that resolves deny/ask/allow decisions; a **runtime supervisor** that starts workers, containers and UI bridges; an **audit/event service** that records installs, grants and invocations; and a **registry client** that fetches catalogue metadata and signatures. That shape maps well to Claude’s marketplace management, VS Code’s enterprise extension control, Krew’s index model, and the MCP Registry’s metadata-first design. citeturn26view8turn41view3turn32view0turn30view2turn26view6

One architecture decision matters more than the rest: **do not expose unstable internal ARC objects directly to third parties**. VS Code treats API compatibility as a first-order concern and uses “proposed APIs” for unstable features; LangChain now keeps most integrations outside core behind stable interfaces; Claude ignores unknown manifest fields to preserve forward compatibility. ARC should therefore expose only versioned, generated contracts per extension point, never raw internal classes, internal registry handles, or private adapter types. citeturn19search3turn37view1turn27view1

## Manifest and permissions

**Plugin manifest schema.** ARC should use a single top-level manifest with typed component sections and capability-scoped permissions. The schema below is a recommended starting point.

```yaml
manifestVersion: "1.0"

id: "acme.security-toolkit"
displayName: "Security Toolkit"
version: "1.2.0"
description: "Security-oriented tools, prompts, and evals for ARC"
author:
  name: "Acme Ltd"
  email: "plugins@acme.example"
publisher:
  id: "acme"
license: "Apache-2.0"
homepage: "https://example.com/arc/security-toolkit"
repository: "https://github.com/acme/arc-security-toolkit"
keywords: ["security", "evals", "prompts"]
categories: ["tools", "evals", "prompts"]

compatibility:
  arcVersion: "^2.4.0"
  sdkVersion: "^1.0.0"
  hosts: ["cli", "ide", "mcp-server"]
  runtimes: ["declarative", "process", "webview"]
  featureFlags: []
  experimental: []

activation:
  onStartup: false
  commands: ["security.scan"]
  events: ["session.open", "eval.run"]
  fileGlobs: ["**/*.py", "**/*.ts"]

components:
  adapters:
    - id: "jira-adapter"
      entrypoint: "./dist/adapters/jira.js"
      runtime: "process"

  tools:
    - id: "dependency-audit"
      title: "Dependency Audit"
      entrypoint: "./dist/tools/dependency-audit.js"
      runtime: "process"
      inputSchemaRef: "./schemas/dependency-audit.input.json"
      outputSchemaRef: "./schemas/dependency-audit.output.json"

  slashCommands:
    - id: "secure-review"
      file: "./commands/secure-review.md"

  promptTemplates:
    - id: "threat-model"
      file: "./prompts/threat-model.md"

  workflowTemplates:
    - id: "security-pr-gate"
      file: "./workflows/security-pr-gate.yaml"

  evalScorers:
    - id: "owasp-scorer"
      entrypoint: "./dist/evals/owasp-scorer.js"
      runtime: "process"

  memoryExtractors:
    - id: "decision-log"
      entrypoint: "./dist/memory/decision-log.js"
      runtime: "process"

  contextProviders:
    - id: "repo-issues"
      entrypoint: "./dist/context/repo-issues.js"
      runtime: "process"

  providerAdapters:
    - id: "custom-provider"
      entrypoint: "./dist/providers/custom-provider.js"
      runtime: "process"

  mcp:
    servers:
      - id: "security-mcp"
        file: "./mcp/server.json"
    exports:
      tools: true
      resources: true
      prompts: true

  panels:
    - id: "security-panel"
      title: "Security"
      entrypoint: "./webviews/security-panel/index.html"
      runtime: "webview"

  eventSinks:
    - id: "audit-webhook"
      entrypoint: "./dist/sinks/audit-webhook.js"
      runtime: "process"

  sandboxPolicies:
    - id: "deny-prod-writes"
      file: "./policies/deny-prod-writes.yaml"

configuration:
  schemaRef: "./schemas/config.schema.json"
  defaultsRef: "./schemas/config.defaults.json"

permissions:
  workspace:
    read: ["**/*"]
    write: ["reports/**", ".arc/**"]
  exec:
    allow: ["npm audit", "pip-audit"]
  network:
    allowHosts: ["api.github.com", "registry.npmjs.org"]
  secrets:
    read: ["github.token"]
  models:
    invoke: true
  ui:
    panels: ["security-panel"]
  mcp:
    exposeTools: true
    exposeResources: true
    exposePrompts: true
  webhooks:
    emitTo: ["https://hooks.example.com"]

distribution:
  channel: "stable"
  source: "oci"
  integrity:
    sha256: "..."
  updatePolicy: "minor-auto"

signing:
  publisherCert: "..."
  signature: "..."
  provenance: "slsa3"

observability:
  auditEvents: ["install", "enable", "invoke", "permission-grant", "network-egress"]
  redact:
    - "secrets.*"
    - "configuration.apiKey"
```

This schema deliberately combines ideas that have already succeeded elsewhere: VS Code’s `engines`, `contributes`, activation events and extension dependencies; Obsidian’s small manifest plus app-version gating; Claude’s optional manifest, namespaced component layout and version sources; Continue’s repo-native YAML and markdown assets; Home Assistant’s manifest-plus-config-flow-plus-diagnostics posture; and MCP’s capability declarations for tools, resources and prompts. citeturn23view0turn26view0turn26view1turn27view2turn23view6turn24view3turn24view4turn24view5turn35view1turn35view2turn36view1

**Permission model.** ARC should not copy ecosystems that either have no permission model or only offer coarse trust switches. Instead it should combine four layers.

At install time, every plugin should declare required permissions in the manifest and be assigned a **trust tier**: local-dev, unlisted, community, verified publisher, or curated. VS Code’s publisher-trust flow and verified-publisher badge show the value of identity signals; Claude’s marketplaces show the value of managed catalogues and commit pinning; the MCP Registry shows the value of DNS-based namespace verification for names. ARC should use all three. citeturn31view2turn26view8turn41view1turn26view6

At first use, ARC should use **deny > ask > allow** precedence with human-readable prompts. Claude Code already documents that deny rules win over ask rules and hooks do not bypass managed policy. MCP independently recommends a human in the loop for tool invocation, clear indicators when tools run, and explicit consent before data access or tool use. ARC should adopt that precedence globally, including for plugin-provided tools, provider adapters and MCP exports. citeturn26view9turn35view0turn35view1

At runtime, permissions should be **capability-scoped rather than plugin-scoped**. A plugin may be trusted enough to install but still require a prompt for writing outside `.arc/`, spawning shell commands, reading secrets, or calling a new network domain. Continue’s slash-command and check model, LiteLLM’s hook-based request interception, and Home Assistant’s diagnostics redaction all point to this more granular posture: the host should own the permission broker, the redaction layer and the audit pipeline, not the plugin. citeturn25view1turn25view0turn38view1turn24view5turn33view2

At the organisation layer, ARC needs **managed allow/deny policy**. VS Code now supports organisation-level allowlists by publisher, extension, version and platform, and can disable installed extensions that become disallowed. Claude lets admins restrict marketplaces. ARC should add the same concept for plugin IDs, publishers, permission classes, runtime classes and update channels. citeturn32view0turn41view3

## Sandbox, trust and audit model

**Sandbox model.** ARC should define four security grades.

Grade A is **declarative-only**. These plugins may contribute prompts, workflows, slash-command definitions, schemas or static UI metadata. No code execution, no network, no shell, no secret access. Continue checks, Continue prompts and MCP prompt definitions show how much can be done at this level. citeturn25view0turn25view1turn36view1

Grade B is **WASI or equivalent constrained compute**. This is for eval scorers, small memory extractors, transform steps and non-privileged policy suggestions. No host shell, no ambient network, no direct secret reads, and only mounted paths explicitly granted by ARC. This is the safest place for “code-like” plugins that do not need to talk to the outside world. This is a recommendation rather than something directly taken from one ecosystem, but it is motivated by the clear security limits in VS Code and Obsidian and by the benefits of process isolation shown in Theia and Neovim. citeturn23view2turn26view2turn23view4turn28view4

Grade C is **supervised subprocess/container**. This is where provider adapters, tool adapters, event sinks, memory services and bundled MCP servers should live. These runtimes should receive only the environment variables, filesystem mounts, network egress rules and secrets that the permission broker grants. kubectl plugins, GitHub CLI extensions and MCP servers all demonstrate the power of executable plug-ins, but their documentation also makes clear that executable code should be treated as privileged. ARC should therefore run them outside its main process and make their ambient authority explicit. citeturn24view6turn30view3turn35view0turn35view1

Grade D is **UI sandbox**. Panels and widgets should run in an iframe or webview with a strict CSP, an allowlisted RPC bridge and no direct Node.js or host-process access. This matches the direction of VS Code webview-style extension surfaces and keeps Theia panel contributions usable without letting panel code become a hidden privileged bridge. citeturn23view0turn40view1

On trust and marketplace review, ARC should combine **signing, review and runtime warnings**. VS Code Marketplace signs published extensions, malware-scans and secret-scans them, and can block-list and auto-uninstall malicious extensions. Obsidian reviews community plugins before publication and keeps Restricted Mode on by default. Claude’s community marketplace uses automated validation and safety screening and pins entries to specific commit SHAs. ARC should at minimum require package signatures for marketplace distribution, automated linting and malware/secret scanning, and manual review for plugins requesting elevated permissions such as shell execution, broad workspace write, unrestricted network egress or secret access. citeturn31view1turn31view3turn6search2turn26view2turn41view1

ARC also needs **first-class audit logging**. LiteLLM’s proxy logging is a good model here: every request gets a unique call identifier, callbacks can forward logs to many observability backends, and guardrail results are recorded for compliance and auditing. Home Assistant’s diagnostics guidance is equally important: troubleshooting data is valuable, but sensitive values must be redacted before export. ARC should therefore log installation, enable/disable, permission grants, tool calls, shell spawns, network egress, config changes and plugin crashes, while redacting secrets and user content by policy. citeturn24view2turn24view1turn38view0turn24view5turn33view2

## Distribution, SDK and compatibility

**Distribution and marketplace strategy.** ARC should launch in three phases. First, support **local path, git repository and signed private registry** installation for teams. That is the fastest route to utility and closely matches Claude’s local/Git marketplace sources, Theia’s OpenVSX-or-URL installation model, and Krew’s support for custom indexes and private plugin serving. citeturn26view8turn40view1turn30view0

Second, add an **organisation registry** that stores only metadata plus policy. The MCP Registry is a very strong precedent: a standardised metadata layer with namespace verification and downstream curation. ARC’s org registry should hold plugin IDs, publishers, permissions, review status, signatures, digests, compatibility, changelog pointers and support links, while artefacts live in OCI or another package store. That keeps catalogue operations fast and makes private and public marketplaces use the same protocol. citeturn26view6

Third, add a **public curated marketplace** only after signing, review tooling and audit telemetry are ready. ARC should distinguish at least four listing classes: unlisted, community, verified publisher and curated. Home Assistant’s quality scale is a useful inspiration for visible quality badges; VS Code’s verified publisher is a useful trust badge; Claude’s official versus community marketplace is a useful curation split. citeturn33view0turn31view2turn41view1

**Developer SDK design.** ARC should ship an SDK that is mostly **schema-first and transport-first**, not inheritance-first. That means versioned JSON Schema or protobuf contracts for each extension point and small host libraries that implement the transport, auth, logging and validation boilerplate. LangChain’s integration system and LiteLLM’s provider adapters both show why this works: third parties write packages that satisfy stable interfaces rather than importing internal host objects. citeturn37view0turn37view1turn24view0

The initial SDK should prioritise **TypeScript and Python**. TypeScript covers Theia/VS Code-style UI and tooling integrations; Python covers data, evaluation, provider and ML-heavy integrations, and aligns well with LangChain, LiteLLM and Home Assistant ecosystems. ARC can add other languages later through JSON-RPC if the manifest and transport stay language-agnostic. citeturn40view1turn37view0turn24view0turn24view4

The SDK should include an `arc` CLI with at least: `arc plugin init`, `arc plugin validate`, `arc plugin test`, `arc plugin sign`, `arc plugin pack`, `arc plugin publish`, and `arc plugin doctor`. Claude’s plugin tooling, GitHub CLI’s extension scaffolding, and VS Code’s `vsce` packaging all show the value of a first-party scaffolder and validator. citeturn34view0turn27view1turn24view9turn19search1

**Compatibility and versioning strategy.** ARC should version four distinct things: the manifest format, the stable SDK contract, the host compatibility range, and experimental capability flags. VS Code’s `engines.vscode`, Obsidian’s `minAppVersion` plus `versions.json`, Claude’s plugin version resolution, and Krew’s versioned manifest updates all show that compatibility needs to be machine-readable and update-safe. ARC should therefore require `manifestVersion`, `sdkVersion`, and `arcVersion`, while allowing per-component compatibility overrides if needed. citeturn23view0turn26view1turn27view1turn30view1

For experimental features, ARC should follow a **proposed-API model** rather than pretending new extension points are stable before they are. VS Code’s proposed APIs exist precisely because public extension APIs are otherwise hard to change. ARC should add an `experimental` namespace in the manifest, gate experimental capabilities behind feature flags, and refuse marketplace publication of plugins that depend on experimental APIs unless the entire plugin is marked preview. citeturn19search3

For updates, ARC should prefer **digest or commit pinning in catalogues** and semantic versioning in released packages. Claude’s community marketplace pins plugins to specific commit SHAs; VS Code supports stable versus pre-release channels; Obsidian uses `versions.json` to serve older compatible builds when the latest build requires a newer app. ARC should replicate that by pinning registry installs to immutable digests, allowing auto-update only within approved ranges, and supporting compatibility fallbacks when a plugin’s latest release targets a newer ARC host version. citeturn41view1turn39view1turn26view1

## Top plugin-enabled features

The feature ranking below is synthesised from official documentation across VS Code, Theia, Claude Code, Continue, LangChain, LiteLLM, Home Assistant, kubectl/Krew, GitHub CLI, Obsidian, Neovim and MCP. The priorities are recommendations for ARC, not claims about those ecosystems. citeturn23view0turn23view4turn34view0turn23view6turn37view0turn24view0turn33view0turn24view6turn24view8turn26view0turn28view4turn35view0

| Plugin feature | Inspiration | ARC extension point | Security gate | Complexity | Priority |
|---|---|---|---|---|---|
| Third-party tool packs | MCP tools, Claude plugins, LiteLLM hooks | `tools` | Tool permission prompt, network/exec scopes, audit log | Medium | P0 |
| Slash command packs | Continue prompts, Claude skills, MCP prompts | `slashCommands` | Declarative-only by default; prompt on privileged expansion | Low | P0 |
| Prompt template packs | Continue prompts, MCP prompts | `promptTemplates` | Declarative-only; content scanning | Low | P0 |
| Workflow template packs | Continue agents/checks, Claude skills | `workflowTemplates` | Declarative-only; schema validation | Low | P0 |
| Provider adapters | LiteLLM provider modules, LangChain provider packages | `providerAdapters` | Signed process runtime, secret scopes, egress allowlist | High | P0 |
| MCP server bundles | Claude external integrations, MCP Registry | `mcp.servers` | Process/container sandbox, host approval, digest pinning | High | P0 |
| Context providers | Continue context plugins, MCP resources | `contextProviders` | Read-scope grants, redaction, provenance marking | Medium | P0 |
| Eval scorers | Continue checks, Home Assistant quality rules | `evalScorers` | Read-only/VFS sandbox, no ambient network by default | Medium | P0 |
| IDE panels and widgets | VS Code UI contributions, Theia widgets | `panels` | Webview sandbox, CSP, bridge allowlist | High | P1 |
| Event sinks and webhooks | LiteLLM callbacks, Continue event agents | `eventSinks` | Explicit destination allowlist, secret scoping, retry policy | Medium | P1 |
| Memory extractors | Continue agents, LangChain long-term memory patterns | `memoryExtractors` | Data-classification rules, redact-before-store, audit trail | Medium | P1 |
| Adapter bundles for SaaS systems | Home Assistant integrations, Claude MCP bundles | `adapters` | Capability-scoped auth, review for elevated permissions | High | P1 |
| Native MCP exports | MCP tools/resources/prompts | `mcp.exports` | Consent UI, per-export visibility controls | Medium | P1 |
| Sandbox policy modules | Claude PreToolUse hooks, Workspace Trust | `sandboxPolicies` | Admin approval, deny-first merge semantics | High | P1 |
| CLI subcommands | kubectl plugins, GitHub CLI extensions | `cliCommands` | Process sandbox, signed binaries, shell policy | Medium | P1 |
| Quality badges and diagnostics | Home Assistant quality scale, diagnostics | `qualityMetadata` | Marketplace policy checks, sensitive-data redaction | Medium | P1 |
| Versioned extension packs | VS Code extension packs, Obsidian compatibility fallback | `packs` | Dependency resolution, compatibility solver | Medium | P2 |
| Team marketplace packs | Claude marketplaces, Krew custom indexes, MCP Registry | `distribution` | Org allowlist, signature verification, review status | Medium | P2 |
| Review and remediation plugins | Claude security-guidance, Continue checks | `tools` + `evalScorers` | Restricted runtime, repo trust, result provenance | Medium | P2 |
| Optional remote plugin hosts | Neovim remote plugins, Theia plugin host | `runtimeProviders` | Separate process contract, health checks, resource limits | High | P2 |

## Open questions and limitations

This recommendation assumes the ARC internals you supplied are accurate and current, but it is **not** grounded in private ARC source code or internal architectural documents. If ARC already has hidden constraints around process supervision, cross-platform packaging, or Theia frontend embedding, those could change the SDK surface and runtime split.

Public documentation is also uneven across ecosystems. The broad patterns are very clear, but some systems document architecture more explicitly than others. The strongest evidence is from official docs for VS Code, Theia, Claude Code, Continue, LangChain, LiteLLM, Home Assistant, Kubernetes/Krew, GitHub CLI, Obsidian, Neovim and MCP, while details like precise review workflows are sometimes only partially public. Where that happened, the recommendations above favour conservative, high-confidence design choices rather than trying to infer undocumented behaviour. citeturn31view1turn23view4turn41view1turn33view0turn30view3turn26view2turn26view6

If ARC wants the smallest viable starting point, the best initial slice is: **declarative prompt/workflow/slash-command packs, process-based tool/provider adapters, MCP bundles, and webview panels**, all behind one manifest and one permission broker. That yields immediate ecosystem value without forcing ARC to stabilise every internal abstraction at once.