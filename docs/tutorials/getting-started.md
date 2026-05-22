# Getting Started with ARC Studio

**What you'll build:** Install ARC Studio, run your first agent workflow via CLI, then see the same workflow in the browser IDE.
**Time:** Under 5 minutes.
**Prerequisites:** `node --version` ≥ 20, `pnpm --version` ≥ 9, `python --version` ≥ 3.11, `git`.

---

## 1. Install

```bash
git clone https://github.com/Hansuqwer/arc-theia-studio.git
cd arc-theia-studio
pnpm install --frozen-lockfile
bash scripts/bootstrap-dev.sh
```

This installs Node dependencies, Python dependencies, and builds the TypeScript packages.

## 2. Run Your First Workflow (CLI)

ARC Studio ships with a built-in SwarmGraph test workflow. Run it with:

```bash
cd python
uv run arc run wf-swarmgraph-fixture
```

You'll see output like:

```
Running workflow wf-swarmgraph-fixture.
Run ID: abc123def456
Status: completed
Duration: 0.42s
Trace: /path/to/.arc/traces/abc123def456.jsonl
```

That's it. You've executed an agent workflow locally.

## 3. Explore with the CLI

List available runtimes:

```bash
uv run arc runtimes --capabilities --json
```

Check environment health:

```bash
uv run arc doctor all
```

View your run history:

```bash
uv run arc runs search
```

Verify the audit trail for your first run:

```bash
uv run arc audit verify abc123def456
```

## 4. Start the Browser IDE

Open a second terminal. From the repository root:

```bash
pnpm start:browser:arc
```

Open **http://localhost:3000** in your browser.

The ARC Studio IDE loads with the Theia shell. The left activity bar has a project-diagram icon for the ARC panel — click it to see your workflows, runs, traces, and configuration.

## 5. Run a Workflow from the IDE

1. Click the ARC Studio icon in the left activity bar.
2. Go to the **Runs** tab.
3. Click **Execute Workflow**.
4. Watch the progress bar update as the workflow runs.
5. After completion, the run appears in the runs list with its trace path.

## 6. Next Steps

Now that you've run your first workflow:

- **Explore the CLI:** `arc --help` lists all commands. Try `arc studio chat` for the interactive REPL.
- **Configure a provider:** Copy `.env.example` to `.env` and `arc provider` configuration.
- **Inspect a trace:** `arc runs export <run-id>` shows the full event stream.
- **Read the docs:** `docs/SECURITY.md` for the security model, `docs/release/checklist.md` for verification evidence.
- **Contribute:** Branch from `main`, run `pnpm check:pr` before opening a PR.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `pnpm install` fails | Use pnpm `9.15.9`. Run `corepack enable && corepack prepare pnpm@9.15.9 --activate`. |
| `arc` not found | From `python/`, run `uv sync --all-extras --dev` then `uv run arc --help`. |
| `arc runtimes` shows can_run=false | Expected on fresh install. Configure a runtime in `.env`. |
| Browser loads but ARC panel empty | The workspace root may not be the repo root. Use **File > Open Workspace** to select it. |
