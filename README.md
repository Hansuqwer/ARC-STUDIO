# ARC Studio

**Agent Runtime Cockpit** — a local command center for running, inspecting, and debugging AI agent workflows.

ARC Studio is a Python CLI + Textual TUI + Eclipse Theia browser interface. Everything runs on your machine. Your data stays with you.

```
arc          # launches the interactive Textual TUI
arc serve    # starts the HTTP daemon on 127.0.0.1:7777
```

**Current Release:** `v0.1.0-alpha`

---

## What's in the box

| Layer | What you get |
|---|---|
| **Textual TUI** | Full-screen terminal interface — chat, slash commands, provider setup, model selection |
| **Python CLI** | 85+ `arc` subcommands — runs, traces, sandbox, audit, HITL, eval, providers, battle |
| **HTTP Daemon** | Local loopback API at `127.0.0.1:7777` for daemon-backed features |
| **Browser IDE** | Eclipse Theia app with workflow, trace, and audit views |
| **Provider Catalog** | 13+ providers bundled (OpenAI, Groq, Cerebras, OpenRouter, GitHub Models, DeepSeek, and more) via models.dev |
| **Sandbox** | Policy-based command sandbox — deny-by-default, path confinement, audit chain |
| **Runtime Adapters** | SwarmGraph, LangGraph, CrewAI, OpenAI Agents SDK, AG2, LlamaIndex, LM Arena |

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

This opens the full-screen Textual TUI in your terminal. From there:

| Key / Command | Action |
|---|---|
| `/providers` or `/connect` | Browse all 13+ providers, enter API key, select a model |
| `/models` | Pick a model for the current provider |
| `/help` | Show all keybindings and slash commands |
| `/runs` | Browse stored run history |
| `/status` | Show workspace, daemon, cost |
| `!<cmd>` | Run a shell command inline |
| `Ctrl+P` | Command palette |
| `Ctrl+C` twice | Exit |

### 3. (Optional) Launch the browser app

```bash
cd ..   # back to repo root
pnpm install --frozen-lockfile
pnpm start:browser:arc
```

Open `http://127.0.0.1:3000`.

---

## Provider Setup

ARC bundles a catalog of 13+ OpenAI-compatible providers from [models.dev](https://models.dev). Free-tier providers require no billing setup.

### Free-tier providers (no payment needed)

| Provider | Key | Free models |
|---|---|---|
| **GitHub Models** | `GITHUB_TOKEN` | GPT-4.1 Mini, Llama 3.3 70B, DeepSeek V3 |
| **OpenRouter** | `OPENROUTER_API_KEY` | `*:free` variants (DeepSeek R1, Llama 3.3 70B, Mistral 7B) |
| **Cerebras** | `CEREBRAS_API_KEY` | GPT-OSS 120B |
| **Z.AI** | `ZHIPU_API_KEY` | GLM-4.5 Flash |
| **NVIDIA** | `NVIDIA_API_KEY` | Nemotron models |

### Configure in the TUI

```
arc
/providers    →  select a provider  →  enter API key  →  pick a model
```

Or set environment variables directly:

```bash
export OPENROUTER_API_KEY=sk-or-...
export GROQ_API_KEY=gsk_...
export GITHUB_TOKEN=ghp_...
```

### Live catalog

Enable the full models.dev live catalog (75+ providers) at startup:

```bash
ARC_MODELS_DEV_LIVE=1 uv run arc
```

---

## Sandbox & Security

ARC runs a policy-based command sandbox on every tool execution:

- **Deny by default** — unknown, destructive, and privileged commands are blocked
- **Path confinement** — writes are confined to the workspace; symlink escapes rejected
- **Env allowlist** — only safe env vars pass to child processes; secrets stripped
- **Audit chain** — every sandbox decision is appended to `~/.arc/audit/sandbox.audit.jsonl`
- **Landlock detection** — Linux Landlock LSM ABI probed at startup; enforcement coming in a follow-up

```bash
uv run arc sandbox doctor --json       # provider health + Landlock status
uv run arc policy explain -- curl ...  # explain what a command would do
uv run arc sandbox run --policy local-safe -- ls -la
```

---

## Runtime Adapters

| Runtime | Support |
|---|---|
| **SwarmGraph** | Subprocess execution via `ARC_SWARMGRAPH_CLI`; workflow export |
| **LangGraph** | Detection, AST analysis, `.invoke()` / `.stream()` via `ARC_LANGGRAPH_EXPORT` |
| **CrewAI** | Detection, crew execution via `ARC_CREWAI_EXPORT` (paid-call gated) |
| **OpenAI Agents SDK** | Detection and SDK execution when `OPENAI_API_KEY` is set |
| **AG2** | Detection and run scaffolding |
| **LlamaIndex** | Detection and static workflow export |
| **LM Arena** | Stub/offline battle and direct modes |

Check status:

```bash
uv run arc runtimes --capabilities --json
```

---

## CLI Reference

```bash
# Daemon
uv run arc serve                        # start daemon on 127.0.0.1:7777

# Workflows & runs
uv run arc workflows
uv run arc run <workflow-id>
uv run arc runs search
uv run arc runs replay <run-id>

# Sandbox
uv run arc sandbox doctor --json
uv run arc sandbox run --policy local-safe -- <cmd>
uv run arc policy explain -- <cmd>

# Providers & models
uv run arc providers list --json
uv run arc providers status

# Audit & HITL
uv run arc audit verify <run-id>
uv run arc hitl pending

# Evaluation
uv run arc eval run --batch
```

Full reference: `uv run arc --help`

---

## Development

### Python

```bash
cd python
uv run pytest -q                  # 3800+ tests
uv run ruff check src tests       # lint
uv run mypy src                   # type check
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
│   ├── tui/           # Textual TUI (app, screen, widgets, views)
│   ├── cli/           # 85+ Typer subcommands
│   ├── security/      # Sandbox, trust, profiles, enforcement
│   ├── isolation/     # subprocess, Docker, microVM providers
│   ├── providers/     # models.dev catalog, OpenAI-compatible clients
│   ├── adapters/      # SwarmGraph, LangGraph, CrewAI, AG2, etc.
│   ├── audit/         # HMAC chain, HITL, streaming verifier
│   └── storage/       # JSONL trace store, SQLite index
├── packages/arc-extension/   # Eclipse Theia extension (TypeScript)
├── applications/browser/     # Theia browser app
└── docs/                     # ADRs, research, security, phases
```

**Three interfaces, one backend:**
- **TUI** (`uv run arc`) — Textual full-screen terminal app
- **Browser** (`pnpm start:browser:arc`) — Eclipse Theia at `localhost:3000`  
- **CLI** (`uv run arc <cmd>`) — scriptable, JSON output, pipe-safe

---

## Security

ARC Studio is a **single-user local workstation tool**. The daemon binds to `127.0.0.1` and has no authentication.

- ✅ Safe for local development on personal workstations
- ❌ Not safe on multi-tenant hosts or shared containers

See [docs/SECURITY.md](./docs/SECURITY.md) for the full threat model.

To report a vulnerability: open a private GitHub security advisory.

---

## Contributing

1. Branch from `main`
2. Run tests: `cd python && uv run pytest -q` and `pnpm check:pr`
3. Include tests for new behavior
4. Open a PR — describe what you changed and why

See [CONTRIBUTING.md](./CONTRIBUTING.md) for conventions and the PR checklist.

---

## License

Apache-2.0. See [LICENSE](./LICENSE).
