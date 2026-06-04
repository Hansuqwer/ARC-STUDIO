## 📋 PROMPT — copy from here ⤵

You are a senior staff engineer doing pre-implementation research for ARC Studio.
Repo: https://github.com/Hansuqwer/arc-theia-studio (HEAD: main, post v0.2.1-alpha)

**Goal:** produce a ranked, evidence-based plan for reducing LLM token consumption
in ARC Studio's agent loop — without breaking security gates, audit integrity, or
the typed-event contract.

**Non-negotiable constraints (same as AGENTS.md):**
- No LLM in security decisions (CoSAI rule)
- EnforcementContext is frozen; no new fields
- Additive protocol only — never remove or rename typed events
- Local-first single-user; no cloud calls introduced

---

## What to research (6 tracks)

### Track 1 — Context-window management
Current state: `DataStore.total_tokens` is tracked, `DataStore.context_limit` exists (defaults 0),
`ContextMeter` widget renders `ctx N%`. No `/compact`, no history truncation, no summarization.

Research:
1. How does Claude Code's `/compact` work? (web search + Context7 Anthropic docs)
2. How does Codex CLI handle context overflow? (web search)
3. What truncation strategies exist: sliding window, semantic chunking, summarization, FIFO?
4. What is the token cost of ARC's typical system prompt + tool schema injection?
   (grep `python/src/agent_runtime_cockpit/adapters/swarmgraph.py` for where messages are assembled)

Deliverable: table of strategies × (token savings %, implementation complexity, audit risk)

### Track 2 — Prompt caching
Current state: no caching layer.

Research:
1. Anthropic prompt caching API — cache_control breakpoints, minimum cacheable tokens, TTL
   (Context7: /anthropic/anthropic-sdk-python query "prompt caching")
2. OpenAI cached prefix — automatic vs explicit, savings model
3. Which ARC prompt surfaces are stable enough to cache?
   (system prompt, tool schemas, capability card summaries, AGENTS.md content)
4. What providers in ARC's catalog (models.dev) support caching?

Deliverable: list of cacheable surfaces with estimated savings per provider

### Track 3 — Tool schema compression
Current state: MCP tool schemas are forwarded verbatim from `mcp/server.py`.

Research:
1. How much of a typical MCP tool schema is redundant? (estimate from `mcp/manifests.py`)
2. What is the token cost of ARC's 11 built-in MCP tools?
   (count tokens in `mcp/server.py` tool descriptions)
3. Strategies: schema deduplication, description shortening, lazy-load vs eager-load

Deliverable: estimated token savings from schema compression

### Track 4 — Streaming and early stopping
Current state: `DataStore.is_streaming` flag exists; screen.py has interrupt via `handle_escape`.
No token budget enforcement during streaming.

Research:
1. Can `BudgetEnforcer` (already in `budget.py`) be wired to interrupt streaming at a token threshold?
2. What is the interaction with audit integrity if a stream is cut mid-run?
3. Does Textual's streaming pattern (append_to_last) support mid-stream budget gates?

Deliverable: yes/no + implementation sketch

### Track 5 — `/fork` and `/rewind` for cost recovery
Current state: neither `/fork` nor `/rewind` exists (listed as P0 gap in UX_AUDIT.md § H03).
Sessions accumulate full history with no branch-off escape.

Research:
1. How does Claude Code's `/fork` work? (creates a new session branching from current point)
2. What state does ARC need to snapshot for a fork: DataStore entries, session_id, workspace trust?
3. What is the storage cost? (JSONL trace already exists via `storage/jsonl.py`)

Deliverable: fork spec + token savings from being able to start fresh mid-session

### Track 6 — Eval-driven prompt optimization
Current state: `evals/policy_recommend.py` exists (R1-R4 rules); `evals/apply.py` maps
recommendations to profile mutations. No eval that measures prompt token efficiency.

Research:
1. What eval metrics are needed: tokens/turn, tokens/task-completion, cost/quality ratio?
2. Can `evals/golden.py` be extended with a token-efficiency golden baseline?
3. What existing eval frameworks measure prompt compression fidelity?

Deliverable: eval design for token efficiency baseline

---

## Research method

For each track:
1. `web_search` for competitive behaviour (Claude Code, Codex CLI, Gemini CLI)
2. `context7` for SDK/API docs where relevant
3. `grep` the repo to verify what exists vs what is absent
4. Record findings with: source, link, what was learned, implementation consequence, confidence

---

## Deliverable

Commit `docs/research/TOKEN_SAVING_PLAN.md` to branch `research/token-saving-plan`.

Document must include:
1. **Executive summary** — top 3 wins by ROI (savings ÷ implementation effort)
2. **Per-track findings** with the source/link/consequence/confidence table
3. **Decision table** — same format as EXECUTION_PROMPT.md:
   | Decision | Chosen approach | Alternatives | Reason | Files affected | Confidence |
4. **P0 quick wins** (≤ 1 day each, no new deps, no security-surface changes)
5. **P1 wins** (2-5 days each)
6. **What NOT to do** — approaches that look attractive but have audit/security traps

Target length: 800-1500 lines.

Do NOT implement anything. Research and document only.

Commit:
```bash
git checkout -b research/token-saving-plan
git add docs/research/TOKEN_SAVING_PLAN.md
git commit -m "research(tokens): token-saving analysis for v0.3.0-alpha sprint"
```

---

## Failure protocol
- If a source is unavailable, note it and continue with what you have.
- If a proposed optimization conflicts with a security constraint, mark it RED in the decision table and skip it.
- Do not invent token counts — grep the actual files and estimate from character counts (÷ 4 ≈ tokens).

## 📋 END PROMPT ⤴

---

## How to use this prompt

```bash
# Feed only the prompt body (between the markers):
sed -n '/^## 📋 PROMPT — copy from here ⤵$/,/^## 📋 END PROMPT ⤴$/p' \
    TOKEN_SAVING_RESEARCH_PROMPT.md | claude

# Or run via next-sprint.sh:
./next-sprint.sh research
```

After the research doc is committed, read `docs/research/TOKEN_SAVING_PLAN.md`,
then run the continuation prompt below to generate the execution spec.

---

## Continuation prompt (run AFTER reading the research doc)

```
The token-saving research is committed at research/token-saving-plan.
Read docs/research/TOKEN_SAVING_PLAN.md.

Extract the P0 quick wins into an EXECUTION_PROMPT-style spec at
TOKEN_SAVING_EXECUTION_PROMPT.md following the same format as
/EXECUTION_PROMPT.md (ROLE, NON-NEGOTIABLE CONSTRAINTS, REPO REALITY,
OUTPUT FORMAT, THE PLAN with work items, verification commands, CHANGELOG).

Scope: P0 quick wins only — changes that take ≤ 1 day each, require no new
dependencies, and do not touch security surfaces.

Do NOT implement anything yet. Just produce the spec.

Commit:
  git checkout -b spec/token-saving-p0
  git add TOKEN_SAVING_EXECUTION_PROMPT.md
  git commit -m "spec(tokens): P0 quick-win execution prompt"
```
