# CLI Commands Reference

**Type:** Reference (Diátaxis)  
**Audience:** Developers, users, scripters  
**Purpose:** Complete reference for all `arc` CLI commands

---

## Overview

The `arc` CLI provides commands for:
- Running workflows
- Managing runs and traces
- Configuring providers and profiles
- Inspecting workspace and runtime status
- Responding to HITL prompts
- Verifying audit chains
- Managing storage and configuration

**Total commands:** 69 (across 15 command groups)

---

## Command Groups

| Group | Commands | Purpose |
|-------|----------|---------|
| [Core](#core-commands) | 10 | Version, health, status, run workflows |
| [Context](#context-commands) | 1 | Context pack generation |
| [Adapter](#adapter-commands) | 2 | Adapter management and testing |
| [Doctor](#doctor-commands) | 5 | Diagnostics and health checks |
| [Workspace](#workspace-commands) | 2 | Workspace info and trust |
| [Isolation](#isolation-commands) | 5 | Isolation provider management |
| [Config](#config-commands) | 2 | Configuration management |
| [HITL](#hitl-commands) | 4 | Human-in-the-loop responses |
| [Storage](#storage-commands) | 2 | Storage management |
| [Studio](#studio-commands) | 3 | Chat REPL and sessions |
| [Runs](#runs-commands) | 11 | Run management and inspection |
| [Audit](#audit-commands) | 7 | Audit chain verification |
| [Providers](#providers-commands) | 9+ | Provider configuration |
| [Profiles](#profiles-commands) | 3 | Security profile management |
| [Eval](#eval-commands) | 3 | Evaluation and testing |

---

## Core Commands

### arc version

Show ARC Studio version information.

**Syntax:**
```bash
arc version [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

**Example:**
```bash
arc version
# Output: ARC Studio v0.2.0
```

**Exit codes:**
- `0` — Success

---

### arc health

Check ARC daemon and environment health.

**Syntax:**
```bash
arc health [OPTIONS]
```

**Options:**
- `--json` — Output as JSON
- `--debug` — Enable debug logging

**Example:**
```bash
arc health
```

**Exit codes:**
- `0` — Healthy
- `1` — Unhealthy

---

### arc status

Show workspace, runtime, and session status overview.

**Syntax:**
```bash
arc status [OPTIONS]
```

**Options:**
- `--workspace PATH` — Workspace path (default: cwd)
- `--json` — Output as JSON

**Example:**
```bash
arc status
```

**Exit codes:**
- `0` — Success

---

### arc inspect

Inspect workspace and detect runtimes.

**Syntax:**
```bash
arc inspect [OPTIONS]
```

**Options:**
- `--workspace PATH` — Workspace path
- `--json` — Output as JSON

**Example:**
```bash
arc inspect
```

---

### arc runtimes

List detected runtimes.

**Syntax:**
```bash
arc runtimes [OPTIONS]
```

**Options:**
- `--capabilities` — Show runtime capabilities
- `--json` — Output as JSON

**Example:**
```bash
arc runtimes --capabilities
```

---

### arc workflows

List detected workflows.

**Syntax:**
```bash
arc workflows [OPTIONS]
```

**Options:**
- `--workspace PATH` — Workspace path
- `--json` — Output as JSON

**Example:**
```bash
arc workflows
```

---

### arc schemas

List detected schemas.

**Syntax:**
```bash
arc schemas [OPTIONS]
```

**Options:**
- `--workspace PATH` — Workspace path
- `--json` — Output as JSON

---

### arc serve

Start HTTP daemon.

**Syntax:**
```bash
arc serve [OPTIONS]
```

**Options:**
- `--host HOST` — Host to bind (default: localhost)
- `--port PORT` — Port to bind (default: 8000)
- `--workspace PATH` — Workspace path

**Example:**
```bash
arc serve --port 8080
```

---

### arc run

Execute a workflow.

**Syntax:**
```bash
arc run WORKFLOW_ID [OPTIONS]
```

**Arguments:**
- `WORKFLOW_ID` — Workflow to run (default: wf-swarmgraph-fixture)

**Options:**
- `--runtime RUNTIME` — Runtime to use (swarmgraph, langgraph, crewai)
- `--profile PROFILE` — Security profile (default: local-safe)
- `--runtime-mode MODE` — Execution mode (fake, gated_local, provider_backed)
- `--allow-paid-calls` — Allow paid provider calls
- `--isolation PROVIDER` — Isolation provider (subprocess, none, docker)
- `--dry-run` — Preflight check only, don't execute
- `--json` — Output as JSON

**Examples:**
```bash
# Run with defaults (fake mode, no cost)
arc run wf-swarmgraph-fixture

# Run with real provider (requires setup)
arc run my-workflow \
  --runtime swarmgraph \
  --profile local-paid \
  --allow-paid-calls \
  --runtime-mode gated_local
```

**Exit codes:**
- `0` — Run completed successfully
- `1` — Run failed
- `2` — Invalid input or configuration

**Error codes:**
- `INVALID_INPUT` — Invalid parameters
- `RUN_FAILED` — Execution failed
- `ADAPTER_NOT_SUPPORTED` — Runtime not available
- See [Error Codes](./error-codes.md) for full list

---

### arc bug-report

Generate a bug report with diagnostic information.

**Syntax:**
```bash
arc bug-report [OPTIONS]
```

**Options:**
- `--output FILE` — Output file path
- `--json` — Output as JSON

---

## Context Commands

### arc context pack

Generate a context pack for the workspace.

**Syntax:**
```bash
arc context pack [OPTIONS]
```

**Options:**
- `--workspace PATH` — Workspace path
- `--output FILE` — Output file path
- `--format FORMAT` — Output format (json, yaml)
- `--json` — Output as JSON

**Example:**
```bash
arc context pack --output context.json
```

---

## Adapter Commands

### arc adapter list

List available adapters.

**Syntax:**
```bash
arc adapter list [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

**Example:**
```bash
arc adapter list
```

---

### arc adapter test

Test adapter conformance.

**Syntax:**
```bash
arc adapter test ADAPTER_ID [OPTIONS]
```

**Arguments:**
- `ADAPTER_ID` — Adapter to test

**Options:**
- `--workspace PATH` — Workspace path
- `--json` — Output as JSON

**Example:**
```bash
arc adapter test swarmgraph
```

---

## Doctor Commands

### arc doctor all

Run all diagnostic checks.

**Syntax:**
```bash
arc doctor all [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

**Example:**
```bash
arc doctor all
```

---

### arc doctor swarmgraph

Check SwarmGraph installation and configuration.

**Syntax:**
```bash
arc doctor swarmgraph [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

---

### arc doctor env

Check environment variables and configuration.

**Syntax:**
```bash
arc doctor env [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

---

### arc doctor network

Check network connectivity.

**Syntax:**
```bash
arc doctor network [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

---

### arc doctor storage

Check storage status and health.

**Syntax:**
```bash
arc doctor storage [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

---

## Workspace Commands

### arc workspace info

Show workspace information.

**Syntax:**
```bash
arc workspace info [OPTIONS]
```

**Options:**
- `--workspace PATH` — Workspace path
- `--json` — Output as JSON

---

### arc workspace trust

Trust a workspace for code execution.

**Syntax:**
```bash
arc workspace trust [PATH] [OPTIONS]
```

**Arguments:**
- `PATH` — Workspace path (default: cwd)

**Options:**
- `--json` — Output as JSON

**Example:**
```bash
arc workspace trust /path/to/workspace
```

---

## Isolation Commands

### arc isolation list

List available isolation providers.

**Syntax:**
```bash
arc isolation list [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

---

### arc isolation status

Show isolation provider status.

**Syntax:**
```bash
arc isolation status [OPTIONS]
```

**Options:**
- `--provider PROVIDER` — Specific provider
- `--json` — Output as JSON

---

### arc isolation doctor

Check isolation provider health.

**Syntax:**
```bash
arc isolation doctor [OPTIONS]
```

**Options:**
- `--provider PROVIDER` — Specific provider
- `--json` — Output as JSON

---

### arc isolation setup

Set up an isolation provider.

**Syntax:**
```bash
arc isolation setup PROVIDER [OPTIONS]
```

**Arguments:**
- `PROVIDER` — Provider to set up (docker, firecracker)

**Options:**
- `--json` — Output as JSON

---

### arc isolation test

Test an isolation provider.

**Syntax:**
```bash
arc isolation test PROVIDER [OPTIONS]
```

**Arguments:**
- `PROVIDER` — Provider to test

**Options:**
- `--json` — Output as JSON

---

## Config Commands

### arc config init

Initialize workspace configuration.

**Syntax:**
```bash
arc config init [OPTIONS]
```

**Options:**
- `--workspace PATH` — Workspace path
- `--name NAME` — Workspace name
- `--json` — Output as JSON

**Example:**
```bash
arc config init --name "My Project"
```

---

### arc config show

Show workspace configuration.

**Syntax:**
```bash
arc config show [OPTIONS]
```

**Options:**
- `--workspace PATH` — Workspace path
- `--json` — Output as JSON

---

## HITL Commands

### arc hitl pending

List pending HITL prompts.

**Syntax:**
```bash
arc hitl pending [OPTIONS]
```

**Options:**
- `--run-id RUN_ID` — Filter by run ID
- `--prompt-id PROMPT_ID` — Show specific prompt
- `--json` — Output as JSON

**Example:**
```bash
arc hitl pending
arc hitl pending --run-id abc123
```

---

### arc hitl approve

Approve a HITL prompt (deprecated, use `respond`).

**Syntax:**
```bash
arc hitl approve PROMPT_ID [OPTIONS]
```

**Arguments:**
- `PROMPT_ID` — Prompt to approve

**Options:**
- `--notes TEXT` — Approval notes
- `--token TOKEN` — Security token
- `--json` — Output as JSON

---

### arc hitl reject

Reject a HITL prompt (deprecated, use `respond`).

**Syntax:**
```bash
arc hitl reject PROMPT_ID [OPTIONS]
```

**Arguments:**
- `PROMPT_ID` — Prompt to reject

**Options:**
- `--notes TEXT` — Rejection notes
- `--token TOKEN` — Security token
- `--json` — Output as JSON

---

### arc hitl respond

Respond to a HITL prompt.

**Syntax:**
```bash
arc hitl respond PROMPT_ID DECISION [OPTIONS]
```

**Arguments:**
- `PROMPT_ID` — Prompt to respond to
- `DECISION` — Decision (approve, reject)

**Options:**
- `--notes TEXT` — Response notes
- `--token TOKEN` — Security token
- `--json` — Output as JSON

**Example:**
```bash
arc hitl respond hitl_abc123 approve --notes "Reviewed and approved"
```

---

## Storage Commands

### arc storage vacuum

Vacuum SQLite database to reclaim space.

**Syntax:**
```bash
arc storage vacuum [OPTIONS]
```

**Options:**
- `--workspace PATH` — Workspace path
- `--json` — Output as JSON

**Example:**
```bash
arc storage vacuum
```

---

### arc storage status

Show storage status and statistics.

**Syntax:**
```bash
arc storage status [OPTIONS]
```

**Options:**
- `--workspace PATH` — Workspace path
- `--json` — Output as JSON

---

## Studio Commands

### arc studio chat

Launch interactive chat REPL.

**Syntax:**
```bash
arc studio chat [OPTIONS]
```

**Options:**
- `--session-id ID` — Resume session
- `--json` — Output as JSON

**Example:**
```bash
arc studio chat
```

---

### arc studio sessions

List saved chat sessions.

**Syntax:**
```bash
arc studio sessions [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

---

### arc studio sessions-migrate

Migrate chat sessions to new format.

**Syntax:**
```bash
arc studio sessions-migrate [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

---

## Runs Commands

### arc runs search

Search and list runs.

**Syntax:**
```bash
arc runs search [OPTIONS]
```

**Options:**
- `--status STATUS` — Filter by status (completed, failed, cancelled)
- `--runtime RUNTIME` — Filter by runtime
- `--limit N` — Max results (default: 20)
- `--offset N` — Skip N results
- `--json` — Output as JSON

**Example:**
```bash
arc runs search --status failed --limit 10
```

---

### arc runs export

Export run events.

**Syntax:**
```bash
arc runs export RUN_ID [OPTIONS]
```

**Arguments:**
- `RUN_ID` — Run to export

**Options:**
- `--format FORMAT` — Output format (json, jsonl)
- `--json` — Output as JSON

**Example:**
```bash
arc runs export abc123def456 > trace.json
```

---

### arc runs import

Import a run from file.

**Syntax:**
```bash
arc runs import FILE [OPTIONS]
```

**Arguments:**
- `FILE` — Run export file

**Options:**
- `--workspace PATH` — Workspace path
- `--json` — Output as JSON

---

### arc runs replay

Replay a run.

**Syntax:**
```bash
arc runs replay RUN_ID [OPTIONS]
```

**Arguments:**
- `RUN_ID` — Run to replay

**Options:**
- `--json` — Output as JSON

---

### arc runs delete

Delete a run.

**Syntax:**
```bash
arc runs delete RUN_ID [OPTIONS]
```

**Arguments:**
- `RUN_ID` — Run to delete

**Options:**
- `--json` — Output as JSON

**Example:**
```bash
arc runs delete abc123def456
```

---

### arc runs backfill

Backfill SQLite index from JSONL traces.

**Syntax:**
```bash
arc runs backfill [OPTIONS]
```

**Options:**
- `--workspace PATH` — Workspace path
- `--json` — Output as JSON

---

### arc runs prune

Prune old runs.

**Syntax:**
```bash
arc runs prune [OPTIONS]
```

**Options:**
- `--older-than DAYS` — Delete runs older than N days
- `--status STATUS` — Only prune runs with status
- `--dry-run` — Show what would be deleted
- `--json` — Output as JSON

**Example:**
```bash
arc runs prune --older-than 30 --status completed
```

---

### arc runs fork

Fork a run to create a new run.

**Syntax:**
```bash
arc runs fork RUN_ID [OPTIONS]
```

**Arguments:**
- `RUN_ID` — Run to fork

**Options:**
- `--new-id ID` — New run ID
- `--json` — Output as JSON

---

### arc runs links

Show linked event chains for a run.

**Syntax:**
```bash
arc runs links RUN_ID [OPTIONS]
```

**Arguments:**
- `RUN_ID` — Run to analyze

**Options:**
- `--filter FILTER` — Filter type (all_ids, tool_calls, etc.)
- `--limit N` — Max results
- `--offset N` — Skip N results
- `--json` — Output as JSON

---

### arc runs status

Show run status and metadata.

**Syntax:**
```bash
arc runs status RUN_ID [OPTIONS]
```

**Arguments:**
- `RUN_ID` — Run to inspect

**Options:**
- `--json` — Output as JSON

**Example:**
```bash
arc runs status abc123def456
```

---

### arc runs diff

Compare two runs.

**Syntax:**
```bash
arc runs diff RUN_A RUN_B [OPTIONS]
```

**Arguments:**
- `RUN_A` — First run ID
- `RUN_B` — Second run ID

**Options:**
- `--json` — Output as JSON

**Example:**
```bash
arc runs diff abc123 def456
```

---

## Audit Commands

### arc audit verify

Verify HMAC audit chain integrity.

**Syntax:**
```bash
arc audit verify RUN_ID [OPTIONS]
```

**Arguments:**
- `RUN_ID` — Run to verify

**Options:**
- `--chain PATH` — Audit chain file path
- `--json` — Output as JSON

**Example:**
```bash
arc audit verify abc123def456
```

**Exit codes:**
- `0` — Chain verified
- `1` — Verification failed

---

### arc audit export

Export audit chain records.

**Syntax:**
```bash
arc audit export RUN_ID [OPTIONS]
```

**Arguments:**
- `RUN_ID` — Run to export

**Options:**
- `--chain PATH` — Audit chain file path
- `--format FORMAT` — Output format (json, jsonl)
- `--json` — Output as JSON

**Example:**
```bash
arc audit export abc123def456 --format json > audit.json
```

---

### arc audit key init

Generate and store HMAC audit key.

**Syntax:**
```bash
arc audit key init [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

**Example:**
```bash
arc audit key init
```

---

### arc audit key show

Show audit key status (key is never printed).

**Syntax:**
```bash
arc audit key show [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

---

### arc audit key delete

Delete stored HMAC audit key.

**Syntax:**
```bash
arc audit key delete [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

---

## Providers Commands

### arc providers list

List built-in provider definitions.

**Syntax:**
```bash
arc providers list [OPTIONS]
```

**Options:**
- `--provider PROVIDER` — Show specific provider
- `--json` — Output as JSON

**Example:**
```bash
arc providers list
arc providers list --provider openai
```

---

### arc providers catalog

List provider auth catalog entries.

**Syntax:**
```bash
arc providers catalog [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

---

### arc providers status

Show provider status from environment.

**Syntax:**
```bash
arc providers status [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

---

### arc providers diagnostics

Show redacted provider diagnostics.

**Syntax:**
```bash
arc providers diagnostics [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

**Example:**
```bash
arc providers diagnostics
```

---

### arc providers proxy

Dry-run provider proxy (no network call).

**Syntax:**
```bash
arc providers proxy [OPTIONS]
```

**Options:**
- `--provider PROVIDER` — Provider to use
- `--model MODEL` — Model to use
- `--prompt TEXT` — Prompt text
- `--live` — Make real API call (gated)
- `--json` — Output as JSON

---

### arc providers action

Run narrow provider action contract.

**Syntax:**
```bash
arc providers action [OPTIONS]
```

**Options:**
- `--provider PROVIDER` — Provider to use
- `--action ACTION` — Action to run (chat, embed, etc.)
- `--prompt TEXT` — Prompt text
- `--json` — Output as JSON

---

### arc providers accounts add

Add a provider account.

**Syntax:**
```bash
arc providers accounts add [OPTIONS]
```

**Options:**
- `--provider PROVIDER` — Provider name
- `--label LABEL` — Account label
- `--env-var VAR` — Environment variable with API key
- `--model MODEL` — Default model
- `--json` — Output as JSON

**Example:**
```bash
arc providers accounts add \
  --provider openai \
  --label "OpenAI Production" \
  --env-var OPENAI_API_KEY \
  --model gpt-4
```

---

### arc providers accounts list

List provider accounts.

**Syntax:**
```bash
arc providers accounts list [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

---

### arc providers accounts delete

Delete a provider account.

**Syntax:**
```bash
arc providers accounts delete ACCOUNT_ID [OPTIONS]
```

**Arguments:**
- `ACCOUNT_ID` — Account to delete

**Options:**
- `--json` — Output as JSON

---

## Profiles Commands

### arc profiles list

List security profiles.

**Syntax:**
```bash
arc profiles list [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

**Example:**
```bash
arc profiles list
```

---

### arc profiles show

Show profile details.

**Syntax:**
```bash
arc profiles show PROFILE_ID [OPTIONS]
```

**Arguments:**
- `PROFILE_ID` — Profile to show

**Options:**
- `--json` — Output as JSON

**Example:**
```bash
arc profiles show local-paid
```

---

### arc profiles create

Create a new security profile.

**Syntax:**
```bash
arc profiles create [OPTIONS]
```

**Options:**
- `--name NAME` — Profile name
- `--allow-paid-calls` — Allow paid provider calls
- `--allow-network` — Allow network access
- `--allow-shell` — Allow shell commands
- `--allow-secrets` — Allow secret access
- `--json` — Output as JSON

**Example:**
```bash
arc profiles create \
  --name "custom-profile" \
  --allow-paid-calls \
  --allow-network
```

---

## Eval Commands

### arc eval run

Evaluate a run against a golden trace.

**Syntax:**
```bash
arc eval run RUN_ID [OPTIONS]
```

**Arguments:**
- `RUN_ID` — Run to evaluate

**Options:**
- `--golden-id ID` — Golden trace ID
- `--batch` — Evaluate against all golden traces
- `--json` — Output as JSON

**Example:**
```bash
arc eval run abc123 --golden-id golden_xyz
```

---

### arc eval save

Save a run as a golden trace.

**Syntax:**
```bash
arc eval save RUN_ID [OPTIONS]
```

**Arguments:**
- `RUN_ID` — Run to save

**Options:**
- `--golden-id ID` — Golden trace ID
- `--expected-status STATUS` — Expected status
- `--json` — Output as JSON

---

### arc eval list

List saved golden traces.

**Syntax:**
```bash
arc eval list [OPTIONS]
```

**Options:**
- `--json` — Output as JSON

---

## Global Options

These options work with most commands:

- `--json` — Output as JSON (machine-readable)
- `--debug` — Enable debug logging
- `--workspace PATH` — Workspace path (default: current directory)

---

## Exit Codes

Standard exit codes used across all commands:

- `0` — Success
- `1` — General error or operation failed
- `2` — Invalid input or configuration error

---

## Environment Variables

Commands respect these environment variables:

- `ARC_DEBUG` — Enable debug logging (same as `--debug`)
- `ARC_NO_TUI` — Disable TUI/REPL (show help instead)
- `ARC_ALLOW_RUN` — Allow `/run` in chat REPL
- `ARC_REAL_RUNTIME_SMOKE` — Enable gated_local runtime mode
- `ARC_LANGGRAPH_SWARMGRAPH_REAL` — Enable LangGraph+SwarmGraph real mode
- `ARC_ALLOW_LIVE_PROVIDER_TESTS` — Enable live provider tests
- `ARC_AUDIT_REDACT_MESSAGES` — Redact LLM messages in audit
- `ARC_AUDIT_REDACT_TOOL_ARGS` — Redact tool arguments in audit
- `ARC_AUDIT_REDACT_TOOL_RESULTS` — Redact tool results in audit

---

## Related Documentation

- **[How-To Guides](../how-to/)** — Task-oriented guides
- **[Error Codes](./error-codes.md)** — Error code reference
- **[Slash Commands](./slash-commands.md)** — REPL command reference
- **[Getting Started](../tutorials/getting-started.md)** — First steps tutorial
