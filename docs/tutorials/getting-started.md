# Getting Started with ARC Studio

**What you'll build:** Install ARC Studio, run your first agent workflow via CLI, then explore it in the browser IDE.
**Time:** Under 10 minutes.
**Prerequisites:** `node --version` ≥ 20, `pnpm --version` ≥ 9, `python --version` ≥ 3.11, `uv --version` ≥ 0.4, `git`.

---

## 1. Install

Clone and bootstrap the full environment:

```bash
git clone https://github.com/Hansuqwer/arc-theia-studio.git
cd arc-theia-studio
pnpm install --frozen-lockfile
bash scripts/bootstrap-dev.sh
```

This installs Node dependencies, Python dependencies, and builds all TypeScript packages.

**Manual install** (if `bootstrap-dev.sh` is unavailable):

```bash
pnpm install
cd python && uv sync --all-extras --dev && cd ..
pnpm build
```

**Verify your environment:**

```bash
node --version   # must be >= 20
pnpm --version   # must be >= 9
python --version # must be >= 3.11
uv --version     # must be >= 0.4
```

## 2. Run Your First Workflow (CLI)

ARC Studio ships with a built-in SwarmGraph test workflow. Run it from the `python/` directory:

```bash
cd python
uv run arc run wf-swarmgraph-fixture
```

You'll see output like:

```
Running workflow wf-swarmgraph-fixture.
Run ID: run-sg-abc123def456
Status: completed
Duration: 0.42s
Trace: .arc/traces/run-sg-abc123def456.jsonl
```

- **Run ID** — unique identifier for this execution. Use it to inspect, replay, or audit the run.
- **Status** — `completed` means the workflow finished successfully.
- **Duration** — wall-clock time in seconds.
- **Trace** — path to the JSONL trace file containing every event.

## 3. Explore with the CLI

List available runtimes and their capabilities:

```bash
cd python && uv run arc runtimes --capabilities --json
```

Check environment health:

```bash
cd python && uv run arc doctor all
```

View your run history:

```bash
cd python && uv run arc runs search
```

Inspect the run you just created (replace `<run-id>` with your Run ID):

```bash
cd python && uv run arc inspect <run-id>
```

Verify the run's audit trail:

```bash
cd python && uv run arc audit verify <run-id>
```

## 4. Open the Browser IDE

Open a **second terminal** from the repository root:

```bash
pnpm start:browser
```

Open **http://localhost:3000** in your browser.

The ARC Studio IDE loads with the Eclipse Theia shell. The left activity bar has a project-diagram icon for the ARC panel — click it to see tabs for Chat, Runs, Workflows, and Config.

## 5. View a Run in the IDE

1. Click the ARC Studio icon (project-diagram) in the left activity bar.
2. Go to the **Runs** tab.
3. Find the run from step 2 in the list. Click it to view its trace events.
4. Switch to the **Workflows** tab to see detected workflow definitions.
5. The **Config** tab shows runtime settings, provider key status, and workspace trust state.

## 6. Next Steps

- **Explore the CLI:** `cd python && uv run arc --help` lists all commands. Try `cd python && uv run arc runs replay <run-id>` to replay a run's events.
- **Configure a provider:** Copy `.env.example` to `.env`, set your API keys, and see `cd python && uv run arc providers --help`.
- **Inspect a trace:** `cd python && uv run arc runs export <run-id>` shows the full event stream.
- **Use the daemon:** `cd python && uv run arc serve` starts the daemon on `http://127.0.0.1:7777`.
- **Contribute:** Read `docs/DEVELOPMENT.md` for build and test commands, `CONTRIBUTING.md` for the PR checklist.

## Troubleshooting

| Symptom | Fix |
|---------|------|
| `pnpm install` fails | Use pnpm 9.15.9. Run `corepack enable && corepack prepare pnpm@9.15.9 --activate`. |
| `arc` not found | From `python/`, run `uv sync --all-extras --dev` then use `uv run arc ...`. |
| `arc runtimes` shows `can_run=false` | Expected on fresh install. The fixture workflow runs regardless. Configure a real runtime in `.env` for provider-backed runs. |
| Browser loads but ARC panel is empty | The workspace root may not match the repo root. Use **File > Open Workspace** to select the project directory. |
| `pnpm start:browser` fails | Run `pnpm build` first, then retry. |

## More Resources

- [README.md](../../README.md) — project overview, features, and architecture
- [docs/DEVELOPMENT.md](../DEVELOPMENT.md) — build commands, test suite, adding extensions
- [docs/CONTRIBUTING.md](../../CONTRIBUTING.md) — PR checklist and commit conventions
- [docs/roadmap.md](../roadmap.md) — current status and upcoming work
- [docs/adr/](../adr/) — architecture decision records
- [docs/tutorials/](../tutorials/) — additional tutorials
