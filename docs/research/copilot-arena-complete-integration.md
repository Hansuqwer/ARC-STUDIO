# Copilot Arena Complete Integration Research

**Date:** 2026-06-01  
**Branch:** feat/sandbox-lima-execution-docker-hardening-fuzzing  
**Status:** Research complete, implementation in progress

## Executive Summary

This document captures research for the **complete** Copilot Arena integration into ARC Studio with zero deferrals:
- **P1**: SwarmGraph battle fan-out (queen spawns N workers → N arena battles → consensus picks winners)
- **P3**: Self-hosted arena server fork (strip Firebase/GCP/Amplitude, replace with SQLite)
- **P4**: Theia paired inline completion (Monaco provider showing 2 completions, user cycles with Alt+]/Alt+[)

## Research Notes

### 1. Upstream Server Architecture

**Source:** https://github.com/lmarena/copilot-arena/tree/main/server

#### Hard Dependencies (Blockers)

| Component | File | Purpose | Replacement Strategy |
|-----------|------|---------|---------------------|
| **Firebase** | `src/firebase_client.py` | All storage: completions, outcomes, votes, users | SQLite with equivalent schema |
| **GCP** | `src/gcp_client.py` | Fetch global outcomes CSV from GCS for ELO | Local CSV or SQLite aggregation |
| **Amplitude** | `app.py` (scattered) | Analytics on every request | Remove or stub with logging |

#### Config Structure

**Source:** `server/config/DEV_README.md`

```yaml
# app_config.yaml
models:
  gpt-4o-mini-2024-07-18:
    weight: 0.3
    tags: [fast, edit]
    input_cost: 0.15
    output_cost: 0.6
  # ... more models

firebase_collections:
  all_completions: completions
  completions: completions_shown
  single_outcomes: single_outcomes
  outcomes: outcomes
  edits: edits
  edit_outcomes: edit_outcomes

version_backend: 1.0.0
```

**Loading:** `src/utils.py:get_settings()` tries `config/app_config.yaml` first, falls back to base64-encoded `APP_CONFIG_YAML` env var.

#### API Endpoints

| Endpoint | Method | Purpose | Key Fields |
|----------|--------|---------|------------|
| `/create_pair` | POST | Autocomplete battle (2 completions) | `prefix`, `suffix`, `userId`, `privacy`, `modelTags` |
| `/create_edit_pair` | POST | Inline-edit battle (2 responses) | `prefix`, `codeToEdit`, `userInput`, `language`, `suffix` |
| `/add_completion` | PUT | Log shown completion | `completionId`, `pairCompletionId`, `pairIndex`, `userId`, `model` |
| `/add_completion_outcome` | PUT | **The vote** | `pairId`, `userId`, `acceptedIndex`, `completionItems[2]` |
| `/add_single_outcome` | PUT | Single-shown outcome | `completionId`, `userId`, `model` |

#### Model Selection

**Source:** `app.py:select_models()`

- Reads `models` from config with `weight` and `tags`
- Filters by requested `modelTags`
- Weighted random selection based on `weight` field
- Returns 2 models for battle mode

#### ELO Scoring

**Source:** `src/scores.py`

- **Bradley-Terry MLE** (logistic regression via `sklearn`)
- Blends global + user outcomes with tunable lambda
- Requires `pandas`, `numpy`, `sklearn`
- Fetches global outcomes from GCS via `gcp_client.py`

**Decision:** Replace with simple ELO (`R_new = R_old + K * (S - E)`) to avoid heavy dependencies.

### 2. Inline Completion API

**Source:** `/tmp/copilot-arena/vscode/src/inlineCompletionProvider.ts`

#### Key Finding: One-at-a-Time Display

Both VSCode and Monaco show **one ghost text at a time**. The "paired" aspect is:
1. Server returns 2 completions in `completionItems[]`
2. Client stores both in cache
3. User cycles with `Alt+]` / `Alt+[` (VSCode) or equivalent keybindings
4. On accept, client POSTs vote with `acceptedIndex` (0 or 1)

**No simultaneous dual ghost-text rendering** in standard Monaco/VSCode API.

#### VSCode Implementation Pattern

```typescript
class ArenaInlineCompletionProvider implements vscode.InlineCompletionItemProvider {
    async provideInlineCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        context: vscode.InlineCompletionContext,
        token: vscode.CancellationToken
    ): Promise<vscode.InlineCompletionItem[]> {
        // 1. Check cache for existing pair
        const cached = await this.cache.getCompletions(fullPrefix);
        if (cached?.completionItems.length >= 2) {
            // Return both as separate InlineCompletionItems
            return cached.completionItems.map(item => 
                this.getSingleCompletionItem(item, startPos)
            );
        }
        
        // 2. Fetch new pair from server
        const pair = await fetchCompletionPair(prefix, suffix, modelTags);
        
        // 3. Cache the pair
        await this.cache.storeCompletions(fullPrefix, pair);
        
        // 4. Return both completions
        return pair.completionItems.map(item => 
            this.getSingleCompletionItem(item, startPos)
        );
    }
}
```

#### Theia/Monaco Equivalent

Theia uses Monaco editor, which has `monaco.languages.registerInlineCompletionsProvider`:

```typescript
monaco.languages.registerInlineCompletionsProvider('python', {
    provideInlineCompletions: async (model, position, context, token) => {
        // Same pattern as VSCode
        return { items: [...] };
    },
    freeInlineCompletions: (completions) => { /* cleanup */ }
});
```

### 3. Docker + SQLite Patterns

**Decision:** Use `docker-compose.yml` with single FastAPI service, SQLite volume mount.

```yaml
version: "3.8"
services:
  arena-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./data:/app/data  # SQLite database
```

## Decision Table

| Decision | Chosen Approach | Alternatives | Reason | Confidence |
|----------|----------------|--------------|--------|------------|
| **Server hosting** | Fork upstream, strip Firebase/GCP/Amplitude, use SQLite | (a) Use upstream public server, (b) Self-host with Firebase | Upstream hard-depends on Firebase+GCP; no local mode. ARC owns data. | High |
| **ELO algorithm** | Simple ELO (`R_new = R_old + K * (S - E)`) | Bradley-Terry MLE (upstream) | Avoids pandas/sklearn/numpy dependencies; "good enough" for local use | Medium |
| **Inline completion UX** | One-at-a-time with Alt+]/Alt+[ cycling | Simultaneous dual ghost text | Monaco/VSCode API limitation; matches upstream Copilot Arena behavior | High |
| **SwarmGraph integration** | New `ArenaProvider(ProviderClient)` | New `ExecutionMode` | Drop-in to existing `worker_execute(provider=...)`; no SDK changes | High |
| **Vote storage** | SQLite `outcomes` table | Reuse `battle/store.py` | Separate concern; arena votes ≠ battle ELO | High |

## Feasibility Verdict

### Blockers Resolved

1. **Firebase hard-dependency** → Replace with SQLite client (`sqlite_client.py`)
2. **GCP hard-dependency** → Remove; use local SQLite aggregation for ELO
3. **Amplitude** → Remove or stub with logging
4. **Monaco dual ghost text** → Not possible; use one-at-a-time cycling (matches upstream)

### Implementation Path

1. **P3 (Foundation):** Fork server, implement SQLite client, local ELO, Docker setup
2. **P1 (SwarmGraph):** Wire `ArenaProvider` into workers, add `arena_battle_mode`, emit votes
3. **P4 (Theia):** Implement Monaco `InlineCompletionsProvider`, cache pairs, cycle with keybindings

## Implementation Scope

### P3 — Self-Hosted Arena Server Fork

**Files to create:**
- `vendor/copilot-arena-server/` (forked from upstream)
- `src/sqlite_client.py` — replaces `firebase_client.py`
- `src/local_scores.py` — replaces `scores.py` (simple ELO)
- `src/local_config.py` — replaces `gcp_client.py` (reads local config)
- `config/app_config.yaml` — static model config
- `Dockerfile` + `docker-compose.yml`

**Schema:**
```sql
CREATE TABLE completions (
    completion_id TEXT PRIMARY KEY,
    pair_id TEXT,
    user_id TEXT,
    model TEXT,
    completion TEXT,
    timestamp INTEGER
);

CREATE TABLE outcomes (
    pair_id TEXT PRIMARY KEY,
    user_id TEXT,
    accepted_index INTEGER,
    completion_items TEXT,  -- JSON
    timestamp INTEGER
);

CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT,
    created_at INTEGER
);
```

### P1 — SwarmGraph Battle Fan-Out

**Files to modify:**
- `swarmgraph/nodes/worker.py` — detect `ArenaProvider`, call `complete()`, stash loser in metadata
- `swarmgraph/config.py` — add `arena_battle_mode: bool`
- `swarmgraph/nodes/consensus.py` — group candidates by `arena_pair_id`, run consensus per battle
- `swarmgraph/events.py` — add `ArenaVoteEvent`
- `swarmgraph/runner.py` — emit votes after consensus via `vote_emitter.py`

**New file:**
- `arena/vote_emitter.py` — async function to POST votes to arena server

### P4 — Theia Paired Inline Completion

**Files to create:**
- `packages/arc-extension/src/browser/arena/arena-service.ts` — TS client for arena server
- `packages/arc-extension/src/browser/arena/arena-inline-completion-provider.ts` — Monaco provider
- `packages/arc-extension/src/browser/arena/arena-contribution.ts` — commands/keybindings
- `packages/arc-extension/src/browser/arena/arena-frontend-module.ts` — DI registration

**Keybindings:**
- `Alt+]` — next completion (cycle forward)
- `Alt+[` — previous completion (cycle backward)
- `Tab` — accept current completion
- `Esc` — reject all completions

## Truth Boundaries

- "Self-hosted arena server" **only** when `docker-compose up` boots, `/create_pair` returns real completions, `/add_completion_outcome` persists to SQLite
- "SwarmGraph battle fan-out" **only** when N workers produce N battles with recorded votes + tests prove it
- "Theia paired inline completion" **only** when Monaco provider is registered, 2 completions are cached, user can cycle and accept, vote is POSTed
- **No "simultaneous dual ghost text" claim** — Monaco shows one at a time, user cycles
- Apache-2.0 LICENSE retained in vendor fork
- No live arena server calls in CI; all tests use mocks or local Docker

## Next Steps

1. ✅ Research complete
2. ⏳ Write this doc
3. ⏳ Implement P3 (server fork)
4. ⏳ Implement P1 (SwarmGraph battle fan-out)
5. ⏳ Implement P4 (Theia inline completion)
6. ⏳ Verification (ruff, pytest, build, typecheck, banned-claims, Docker integration)
