# ARC Studio

**Agent Runtime Cockpit** — a local command center for running, inspecting, and debugging AI agent workflows.

ARC Studio is a Python CLI + Textual TUI + Eclipse Theia browser IDE. Everything runs on your machine. Your data stays with you.

```
arc          # launches the interactive Textual TUI
arc serve    # starts the HTTP daemon on 127.0.0.1:7777
```

**Current Release:** `v0.8-r-ux2` (internal track) · Published package: `v0.1.0a0`

> ⚠️ **Alpha software.** ARC Studio is a single-user local workstation tool. It is not production-grade, multi-tenant, or safe on shared hosts.

---

## What's in the box

| Layer | What you get |
|---|---|
| **Textual TUI** | Full-screen terminal interface — chat, slash commands, provider setup, model selection, 6 themes |
| **Python CLI** | 85+ `arc` subcommands — runs, traces, sandbox, audit, HITL, eval, providers, MCP, isolation |
| **HTTP Daemon** | Local loopback API at `127.0.0.1:7777` — single-user, no auth, no remote access |
| **Browser IDE** | Eclipse Theia app with workflow, trace, audit, HITL, SwarmGraph insight, and config views |
| **Provider Catalog** | 109 OpenAI-compatible providers bundled — see [Provider Catalog](#provider-catalog) below; live models.dev catalog opt-in |
| **Sandbox** | Policy-based command sandbox — deny-by-default, path confinement, env allowlist, audit chain |
| **Isolation Backend** | Selectable execution isolation: `auto` / `none` / `subprocess` / `docker` (gated) / `microvm` (gated, macOS arm64 only) |
| **Runtime Adapters** | SwarmGraph (native), LangGraph, CrewAI, OpenAI Agents SDK, AG2, LlamaIndex, LM Arena (stub) |
| **MCP Control Plane** | Local stdio MCP server — 11 tools, 3 resources, task registry, per-call risk gate |
| **Audit Chain** | HMAC-signed streaming audit verifier; `arc audit verify` CLI; 100 MB trace < 30s (tamper-evident for single-session local runs; does not protect against a local attacker with write access to ~/.arc/audit/) |
| **Token-Saving Suite** | Wallet, budget enforcement, compaction, model picker, Chinese-labs support, opt-in cloud features |
| **TUI Themes** | dark / light / mocha / latte / high-contrast / mono; live re-skin via `/theme`; `NO_COLOR` fallback |

---

## Quick Start

### Prerequisites

Pinned versions are in [`.tool-versions`](./.tool-versions):

- **Python** 3.11.10 · **uv** (latest) · **Node.js** 20.18.0 · **pnpm** 9.15.9

### 1. Install

```bash
git clone https://github.com/Hansuqwer/arc-theia-studio.git
cd arc-theia-studio/python
uv sync --all-extras --dev
```

### 2. Launch the TUI

```bash
uv run arc
```

Opens the full-screen Textual TUI. From there:

| Key / Command | Action |
|---|---|
| `/providers` or `/connect` | Browse all 13+ providers, enter API key, select a model |
| `/models` | Pick a model for the current provider |
| `/theme <name>\|list` | Switch themes live (dark/light/mocha/latte/high-contrast/mono) |
| `/wallet` | View token budget and usage |
| `/settings` | Configure isolation backend (subprocess/docker/microvm) |
| `/help` | Show all keybindings and slash commands |
| `/runs` | Browse stored run history |
| `/status` | Show workspace, daemon, cost |
| `!<cmd>` | Run a shell command inline (sandbox-gated) |
| `Ctrl+P` | Command palette |
| `Ctrl+C` twice | Exit |

### 3. (Optional) Launch the browser IDE

```bash
cd ..   # back to repo root
pnpm install --frozen-lockfile
pnpm start:browser:arc
```

Open `http://127.0.0.1:3000`.

---

## Provider Catalog

ARC bundles **109 OpenAI-compatible providers** from [models.dev](https://models.dev) — no network required to browse them. A live catalog opt-in fetches the latest snapshot at startup.

### Configure in the TUI

```
arc
/providers    →  select a provider  →  enter API key  →  pick a model
```

Or export environment variables directly:

```bash
export GITHUB_TOKEN=ghp_...
export OPENROUTER_API_KEY=sk-or-...
export DEEPSEEK_API_KEY=...
```

### Free / no-billing providers

| Provider | Env Key | Notes |
|---|---|---|
| **GitHub Models** | `GITHUB_TOKEN` | GPT-4.1 Mini, Llama 3.3 70B, DeepSeek V3 — free with GitHub account |
| **OpenRouter** | `OPENROUTER_API_KEY` | `*:free` model variants — DeepSeek R1, Llama 3.3 70B, Mistral 7B |
| **NVIDIA** | `NVIDIA_API_KEY` | Nemotron + community models — free tier available |
| **Hugging Face** | `HF_TOKEN` | Inference API free tier |
| **LM Studio** | `LMSTUDIO_API_KEY` | Local models via LM Studio server |
| **Ollama Cloud** | `OLLAMA_API_KEY` | Cloud-hosted Ollama endpoint |

### Major paid providers (bundled)

| Provider | Env Key | Notable Models |
|---|---|---|
| **OpenAI** | `OPENAI_API_KEY` | GPT-4.1, GPT-5, GPT-5.4, o-series |
| **Anthropic** | `ANTHROPIC_API_KEY` | Claude Opus 4.x, Claude Sonnet 4.x, Claude Haiku 4.x |
| **Google / DeepMind** | `GOOGLE_API_KEY` | Gemini 2.5 Flash/Pro, Gemini 3 Flash/Pro |
| **DeepSeek** | `DEEPSEEK_API_KEY` | DeepSeek V3.2, DeepSeek-R1, DeepSeek Reasoner |
| **xAI** | `XAI_API_KEY` | Grok 4.1, Grok 4.20, Grok 4-fast series |
| **Groq** | `GROQ_API_KEY` | Llama 3.3 70B, Mixtral, Gemma |
| **Fireworks AI** | `FIREWORKS_API_KEY` | Llama, Mixtral, CodeLlama |
| **Cerebras** | `CEREBRAS_API_KEY` | Ultra-fast inference |
| **Mistral** | `MISTRAL_API_KEY` | Mistral Large 2512, Ministral 14B |
| **Perplexity** | `PERPLEXITY_API_KEY` | Sonar models with web search |
| **Novita AI** | `NOVITA_API_KEY` | Large model zoo |
| **NVIDIA** | `NVIDIA_API_KEY` | Nemotron, community models |
| **Nebius** | `NEBIUS_API_KEY` | EU-based inference |
| **Databricks** | `DATABRICKS_HOST` + `DATABRICKS_TOKEN` | Enterprise model serving |
| **Snowflake Cortex** | `SNOWFLAKE_ACCOUNT` + `SNOWFLAKE_CORTEX_PAT` | Enterprise |
| **Upstage** | `UPSTAGE_API_KEY` | Solar models |
| **Sarvam** | `SARVAM_API_KEY` | Indic language models |

### Chinese-ecosystem providers (bundled)

| Provider | Env Key | Notable Models |
|---|---|---|
| **Alibaba (DashScope)** | `DASHSCOPE_API_KEY` | Qwen3-235B, Qwen-Flash, Qwen-Max |
| **ZhipuAI** | `ZHIPU_API_KEY` | GLM-4.5, GLM-4.6, GLM-4.7, GLM-5, GLM-5.1 |
| **Moonshot AI** | `MOONSHOT_API_KEY` | Kimi K2, Kimi K2 Thinking |
| **302.AI** | `302AI_API_KEY` | Aggregator — GPT, Claude, Gemini, GLM, DeepSeek |
| **SiliconFlow** | `SILICONFLOW_API_KEY` | Qwen3, DeepSeek, InternLM |
| **Stepfun** | `STEPFUN_API_KEY` | Step series models |
| **Baidu / Bailing** | `BAILING_API_TOKEN` | ERNIE / Bailing series |
| **ModelScope** | `MODELSCOPE_API_KEY` | Community models (Alibaba) |
| **Xiaomi** | `XIAOMI_API_KEY` | MiLM models |
| **Tencent** | `TENCENT_TOKENHUB_API_KEY` | Hunyuan models |
| **Drun** | `DRUN_API_KEY` | Chinese cloud inference |
| **iFlow** | `IFLOW_API_KEY` | Chinese inference platform |
| **Qiniu AI** | `QINIU_API_KEY` | Qiniu cloud models |

### Routing / aggregator providers (bundled)

| Provider | Env Key | Notes |
|---|---|---|
| **OpenRouter** | `OPENROUTER_API_KEY` | 300+ models via single API |
| **CrofAI** | `CROF_API_KEY` | Multi-model routing |
| **LLM Gateway** | `LLMGATEWAY_API_KEY` | Unified gateway |
| **Helicone** | `HELICONE_API_KEY` | Proxy + observability |
| **FastRouter** | `FASTROUTER_API_KEY` | Speed-optimized routing |
| **Requesty** | `REQUESTY_API_KEY` | Request routing |
| **Zenmux** | `ZENMUX_API_KEY` | Multi-provider mux |
| **NanoGPT** | `NANO_GPT_API_KEY` | Pay-per-token aggregator |
| **Wandb** | `WANDB_API_KEY` | Weave LLM proxy |

### Specialty / infrastructure providers (bundled)

| Provider | Env Key | Notes |
|---|---|---|
| **Cloudflare Workers AI** | `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_KEY` | Edge inference |
| **Digital Ocean** | `DIGITALOCEAN_ACCESS_TOKEN` | GPU Droplets |
| **Vultr** | `VULTR_API_KEY` | Cloud GPU inference |
| **OVHcloud** | `OVHCLOUD_API_KEY` | EU cloud |
| **Scaleway** | `SCALEWAY_API_KEY` | EU cloud |
| **STACKIT** | `STACKIT_API_KEY` | German cloud |
| **Evroc** | `EVROC_API_KEY` | EU sovereign cloud |
| **Berget** | `BERGET_API_KEY` | Nordic cloud |
| **Baseten** | `BASETEN_API_KEY` | ML model deployment |
| **Friendli** | `FRIENDLI_TOKEN` | High-throughput inference |
| **HPC-AI** | `HPC_AI_API_KEY` | HPC-optimised serving |
| **GMI Cloud** | `GMICLOUD_API_KEY` | GPU cloud |
| **io.net** | `IOINTELLIGENCE_API_KEY` | Decentralised GPU |
| **Near AI** | `NEARAI_API_KEY` | Web3-native inference |
| **Inception** | `INCEPTION_API_KEY` | Mercury Coder series |
| **Poolside** | `POOLSIDE_API_KEY` | Code-focused models |
| **Morph** | `MORPH_API_KEY` | Fast inference |
| **Clarifai** | `CLARIFAI_PAT` | Vision + LLM platform |
| **PrivateMode** | `PRIVATEMODE_API_KEY` + `PRIVATEMODE_ENDPOINT` | On-prem / private |
| **Wafer.ai** | `WAFER_API_KEY` | Inference as a service |
| **Chutes** | `CHUTES_API_KEY` | Inference platform |

### Live catalog (opt-in)

```bash
ARC_MODELS_DEV_LIVE=1 uv run arc
```

Fetches the latest models.dev snapshot at startup. Requires network access.

---

## Sandbox & Security

ARC runs a policy-based command sandbox on every tool execution:

- **Deny by default** — unknown, destructive, and privileged commands are blocked
- **Path confinement** — writes confined to workspace; symlink escapes rejected
- **Env allowlist** — only safe env vars pass to child processes; secrets stripped
- **Audit chain** — every sandbox decision appended to `~/.arc/audit/sandbox.audit.jsonl`
- **HMAC signing** — tamper-evident streaming audit verification for run traces (tamper-evident for single-session local runs; does not protect against a local attacker with write access to ~/.arc/audit/)
- **Landlock detection** — Linux Landlock LSM ABI probed at startup

```bash
uv run arc sandbox doctor --json            # health + isolation status
uv run arc policy explain -- curl ...       # explain what a command would do
uv run arc sandbox run --policy local-safe -- ls -la
uv run arc audit verify <run-id>            # verify audit chain for a run
```

### Isolation backends

| Backend | Status | Notes |
|---|---|---|
| `subprocess` | Default | Env-filtered, secret-stripped, path-confined |
| `docker` | Gated (`ARC_ENABLE_CONTAINER_SANDBOX=1`) | Container fallback; not default |
| `microvm` | Gated, default-off | macOS arm64 only; `pwd` proof reproducible via `tools/arc-vz-bringup.sh`; not production-grade |
| `none` | Direct | No filtering; for trusted-local use only |

```bash
uv run arc isolation status                 # show current backend
uv run arc isolation use subprocess         # switch backend
uv run arc isolation doctor                 # preflight checks
uv run arc workspace init                   # first-run isolation chooser
```

> MicroVM execution is gated and default-off. The macOS Apple VZ proof (`pwd`) is reproducible once on macOS arm64. Linux/Firecracker is preflight/baseline only (Linux/KVM required). Do not treat this as production-grade sandbox execution.

---

## Runtime Adapters

| Runtime | Support |
|---|---|
| **SwarmGraph** | Native in-process queen/worker/consensus lifecycle; CLI subprocess fallback |
| **LangGraph** | Detection, AST analysis, `.invoke()` / `.stream()` via `ARC_LANGGRAPH_EXPORT` |
| **CrewAI** | Detection, crew execution via `ARC_CREWAI_EXPORT` (paid-call gated) |
| **OpenAI Agents SDK** | Detection and SDK execution when `OPENAI_API_KEY` is set |
| **AG2** | Detection and run scaffolding |
| **LlamaIndex** | Detection and static workflow export |
| **LM Arena** | Stub/offline battle and direct modes (live productization deferred) |

```bash
uv run arc runtimes --capabilities --json
```

### Local-real execution (opt-in)

`langgraph+swarmgraph` local-real path requires both gates and installed deps:

```bash
ARC_REAL_RUNTIME_SMOKE=1 ARC_LANGGRAPH_SWARMGRAPH_REAL=1 uv run arc run <workflow-id>
```

Default and CI use fake/offline deterministic routing. No provider calls are made unless explicitly gated.

---

## MCP Control Plane

ARC exposes itself as a local MCP server over stdio:

```bash
uv run arc mcp serve --stdio               # start MCP server
uv run arc mcp workbench status --json     # inspect MCP server status
uv run arc mcp risk-scan                   # scan tool call risk
uv run arc mcp decisions                   # view per-call audit log
uv run arc mcp policy-explain              # explain risk policy
```

- 11 tools, 3 resources, task registry with state machine and retry
- Per-call deterministic risk scorer (critical/high/medium/low) — no LLM judgment
- Decisions logged to `~/.arc/audit/decisions.jsonl`
- Stdio-only; no HTTP listener; no external server auto-start

---

## Token Budget & Wallet

```bash
# Wallet + budget are interactive TUI commands — run `uv run arc`, then:
#   /wallet                                   # view token budget and usage
#   /budget                                   # show budget limits
uv run arc runs budget <run-id>             # post-hoc per-run budget report (CLI)
uv run arc providers quota reset --json     # reset local quota counters (local only, not provider)
```

- Real-time budget enforcement at effect boundaries
- `/wallet` and `/budget` TUI commands
- OTel-compatible alias
- Tier-1 provider pricing included

---

## CLI Reference

```bash
# Daemon
uv run arc serve                            # start daemon on 127.0.0.1:7777

# Workflows & runs
uv run arc workflows
uv run arc run <workflow-id>
uv run arc runs search
uv run arc runs replay <run-id>
uv run arc runs fork <run-id>               # fork run to new PENDING state
uv run arc runs budget <run-id>             # post-hoc budget report
uv run arc runs links <run-id>              # show run artifact links

# Sandbox & isolation
uv run arc sandbox doctor --json
uv run arc sandbox run --policy local-safe -- <cmd>
uv run arc policy explain -- <cmd>
uv run arc isolation status
uv run arc isolation use <backend>

# Providers & models
uv run arc providers list --json
uv run arc providers status
uv run arc providers action --help          # gated provider action (explicit opt-in required)

# Audit & HITL
uv run arc audit verify <run-id>
uv run arc hitl pending

# Evaluation & CI
uv run arc eval run --batch
uv run arc eval recommend-apply --profile <id> --dry-run
uv run arc ci check --json --private
uv run arc ci summary --format markdown

# MCP
uv run arc mcp serve --stdio
uv run arc mcp workbench status --json

# Workspace
uv run arc workspace init
uv run arc workspace inventory --json
uv run arc agents-md discover --json
uv run arc skills discover

# Runtime packs
uv run arc runtime-pack init --id org.my-runtime --name "My Runtime" ./my-pack/
uv run arc runtime-pack validate ./my-pack/ --json
uv run arc runtime-pack install ./my-pack/

# SwarmGraph
uv run arc swarmgraph plan --strategy dag --json
uv run arc swarmgraph eval --compare --json

# Doctor
uv run arc doctor all --json
uv run arc doctor storage
```

Full reference: `uv run arc --help`

---

## Development

### Python

```bash
cd python
uv run pytest -q                   # 5600+ tests
uv run ruff check src tests        # lint
uv run mypy src                    # type check
```

### TypeScript / Theia

```bash
pnpm build
pnpm test
pnpm lint
pnpm check:pr
```

### Environment

```bash
cp .env.example .env
# set ARC_SWARMGRAPH_CLI, ARC_LANGGRAPH_EXPORT, provider keys, etc.
```

---

## Architecture

```
arc-theia-studio/
├── python/src/agent_runtime_cockpit/
│   ├── tui/             # Textual TUI (app, screens, widgets, themes)
│   ├── cli/             # 85+ Typer subcommands (decomposed modules)
│   ├── security/        # Sandbox, trust, profiles, enforcement, HMAC audit
│   ├── isolation/       # subprocess, Docker (gated), microVM (gated)
│   ├── providers/       # models.dev catalog, OpenAI-compatible clients
│   ├── adapters/        # SwarmGraph, LangGraph, CrewAI, AG2, etc.
│   ├── audit/           # HMAC chain, HITL, streaming verifier
│   ├── storage/         # JSONL trace store, SQLite index
│   ├── swarmgraph/      # Native SwarmGraph runtime (queen/worker/consensus)
│   ├── mcp/             # MCP control plane (stdio, tools, resources, risk gate)
│   └── evals/           # Eval harness, policy apply, consensus eval
├── packages/arc-extension/        # Eclipse Theia extension (TypeScript)
├── applications/browser/          # Theia browser app (canonical release target)
└── docs/                          # ADRs, research, security, phases, roadmap
```

**Three interfaces, one backend:**
- **TUI** (`uv run arc`) — Textual full-screen terminal
- **Browser** (`pnpm start:browser:arc`) — Eclipse Theia at `localhost:3000`
- **CLI** (`uv run arc <cmd>`) — scriptable, JSON output, pipe-safe

---

## Security

ARC Studio is a **single-user local workstation tool**. The daemon binds to `127.0.0.1` and has no authentication.

- ✅ Safe for local development on personal workstations
- ❌ Not safe on multi-tenant hosts or shared containers
- ❌ Not production-grade
- ❌ No tenant isolation

See [docs/SECURITY.md](./docs/SECURITY.md) for the full threat model.

To report a vulnerability: open a private GitHub security advisory.

---

## License

**ARC Studio Proprietary License** — All rights reserved. See [LICENSE](./LICENSE).

This software is **not open source**. Viewing the source does not grant any right to copy, modify, distribute, sublicense, rebrand, or sell this software or any derivative work. See LICENSE for full terms.
