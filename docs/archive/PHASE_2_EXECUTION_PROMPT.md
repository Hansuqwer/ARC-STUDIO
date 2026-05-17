# Phase 2 Execution Prompt

**Date:** 2026-05-12  
**Phase:** Research Lock  
**Status:** Ready for Execution  
**Blocking:** All implementation work (Phases 3-7)

## Objective

Complete mandatory research documentation before any feature implementation begins. This phase gates all subsequent development work and ensures informed architectural decisions.

## Critical Rule

**No agent may introduce:**
- New external integration
- API shape
- Theia pattern
- Runtime execution behavior
- SwarmGraph behavior
- Security boundary

**Without first adding a research note and implementation decision.**

## Deliverables

### 1. docs/RESEARCH_NOTES.md

Must document research findings for all required areas with:
- Source name
- Link or citation
- What was learned
- Implementation consequence
- Confidence level (High/Medium/Low)
- Unresolved questions

### 2. docs/IMPLEMENTATION_DECISIONS.md

Must track all architectural decisions using this table format:

```
| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|----------|----------------|-------------------------|---------|----------------|------------|
```

## Required Research Areas

### Area 1: Eclipse Theia (Agent 3 Primary)

**Official Docs:** https://theia-ide.org/docs/

Research topics:
- [ ] Theia application structure and lifecycle
- [ ] Frontend contribution pattern (views, commands, menus)
- [ ] Backend service pattern (dependency injection, RPC)
- [ ] Workspace service / active workspace root access
- [ ] Electron app hardening (CSP, sandbox, IPC security)
- [ ] Extension/plugin model vs built-in contributions
- [ ] Open VSX behavior and extension loading
- [ ] Frontend-backend communication patterns

**Key Questions:**
- How does ARC Studio register custom views in Theia?
- Where should SwarmGraph execution UI live (frontend/backend)?
- How to safely access workspace root for graph detection?
- What security boundaries exist in Electron mode?

---

### Area 2: Context7 (Agent 2 Primary)

**Official Docs:** https://context7.ai/docs (if available)

Research topics:
- [ ] API authentication mechanism
- [ ] Rate limits and quota management
- [ ] Library ID resolution process
- [ ] Best practices for integration
- [ ] Failure modes and error handling
- [ ] Cache behavior and TTL
- [ ] How to safely integrate as opt-in context provider

**Key Questions:**
- Should Context7 be enabled by default or opt-in?
- How to handle API key storage securely?
- What happens when rate limits are exceeded?
- Can Context7 work offline or with cached data?

---

### Area 3: Vercel Grep / Code Search (Agent 2 Secondary)

**Research Sources:**
- Vercel platform documentation
- Public code search API examples
- Similar integrations in other IDEs

Research topics:
- [ ] API or supported query model (if public)
- [ ] Expected response shape and pagination
- [ ] Rate limits or access constraints
- [ ] Examples of similar code-search integrations
- [ ] Failure handling and timeout behavior

**Key Questions:**
- Is Vercel Grep a public API or internal tool?
- Should ARC Studio implement this or defer to Phase 2+?
- What's the fallback if Vercel search is unavailable?

---

### Area 4: GitHub Search (Agent 2 Secondary)

**Official Docs:** https://docs.github.com/en/rest/search

Research topics:
- [ ] Code search API endpoints and query syntax
- [ ] Authentication requirements (token scopes)
- [ ] Rate limits (authenticated vs unauthenticated)
- [ ] Query limits and result caps
- [ ] Pagination patterns
- [ ] Incomplete results handling
- [ ] Result metadata structure
- [ ] Safe handling of private repo queries
- [ ] How to search the SwarmGraph repo safely

**Key Questions:**
- Should GitHub search require user PAT or use app token?
- How to prevent accidental exposure of private code?
- What's the UX when rate limits are hit?

---

### Area 5: LangGraph (Agent 4 Primary)

**Official Docs:** https://langchain-ai.github.io/langgraph/

Research topics:
- [ ] Graph construction patterns (StateGraph, MessageGraph)
- [ ] Compiled graph execution model
- [ ] Streaming events and callbacks
- [ ] Checkpointers (memory, sqlite, postgres)
- [ ] Interrupt/resume patterns
- [ ] Common dynamic graph patterns that static AST extraction may miss
- [ ] Error handling and retry strategies

**Key Questions:**
- How does ARC Studio detect a LangGraph workflow in user code?
- Can we statically analyze graph structure or must we execute?
- How to stream LangGraph events to ARC Studio UI?
- What's the security model for executing user graphs?

---

### Area 6: SwarmGraph Repository (Agent 4 Primary, Agent 0 Coordination)

**Repository:** https://github.com/Hansuqwer/SwarmGraph

Research topics:
- [ ] Actual package layout and entry points
- [ ] Graph construction model (declarative vs imperative)
- [ ] Runtime execution model (sync/async, streaming)
- [ ] Streaming/event capabilities
- [ ] Public APIs and extension points
- [ ] Examples and test patterns
- [ ] How ARC Studio should detect SwarmGraph workflows
- [ ] How ARC Studio should eventually execute SwarmGraph workflows safely

**Key Questions:**
- Is SwarmGraph a library or a framework?
- Does it have a CLI or only programmatic API?
- How does it differ from LangGraph?
- Should ARC Studio vendor SwarmGraph or call it externally?

---

### Area 7: AG-UI Event Streaming (Agent 6 Primary)

**Research Sources:**
- Internal AG-UI documentation
- Existing trace files in `.arc/traces/`
- Event streaming patterns in similar tools

Research topics:
- [ ] Event naming conventions
- [ ] Event payload shape and schema
- [ ] Run lifecycle events (start, step, end, error)
- [ ] Cancellation/disconnect semantics
- [ ] Trace persistence model (JSONL format)
- [ ] Real-time streaming vs batch updates

**Key Questions:**
- What events should ARC Studio emit during graph execution?
- How to handle long-running graphs (hours/days)?
- Should traces be stored locally or remotely?
- How to replay traces for debugging?

---

### Area 8: Vercel Platform (Agent 5 Secondary)

**Official Docs:** https://vercel.com/docs

Research topics:
- [ ] REST API authentication
- [ ] Environment variable APIs
- [ ] Project/deployment APIs
- [ ] Sandbox APIs (if relevant)
- [ ] Whether Vercel is actually needed for ARC Studio or only for external context lookup

**Key Questions:**
- Is Vercel integration required for alpha release?
- Can ARC Studio work entirely offline?
- What Vercel features are must-have vs nice-to-have?

---

## Agent Responsibilities

### Agent 0 (Orchestrator)
- Enforce research-first gate
- Coordinate research completion across all agents
- Ensure no implementation work begins before Phase 2 complete
- Review and approve RESEARCH_NOTES.md and IMPLEMENTATION_DECISIONS.md

### Agent 1 (Build/CI)
- Research CI/CD patterns for Theia apps
- Document build artifact requirements
- Research package.json hygiene for monorepos

### Agent 2 (Protocol)
- **PRIMARY:** Context7, GitHub Search, Vercel Grep research
- Document API contracts and error handling
- Research rate limiting strategies

### Agent 3 (Theia Integration)
- **PRIMARY:** Eclipse Theia research
- Document frontend/backend patterns
- Research Electron security hardening

### Agent 4 (Runtime Adapters)
- **PRIMARY:** LangGraph and SwarmGraph research
- Document graph detection and execution patterns
- Research streaming event models

### Agent 5 (Security)
- Research daemon/provider security boundaries
- Document credential storage patterns
- Research sandbox/isolation strategies

### Agent 6 (UX)
- **PRIMARY:** AG-UI event streaming research
- Document UI event patterns
- Research trace visualization

### Agent 7 (Documentation)
- Review all research notes for clarity
- Ensure implementation decisions are well-documented
- Create research summary for handover

---

## Execution Steps

### Step 1: Initialize Documentation Structure
```bash
mkdir -p docs
touch docs/RESEARCH_NOTES.md
touch docs/IMPLEMENTATION_DECISIONS.md
```

### Step 2: Populate Research Notes Template

Each agent adds their research findings to `docs/RESEARCH_NOTES.md` using this format:

```markdown
## [Research Area Name]

**Agent:** [Agent Number and Name]  
**Date:** [YYYY-MM-DD]  
**Status:** [In Progress / Complete]

### Source: [Source Name]
**Link:** [URL or citation]  
**Confidence:** [High / Medium / Low]

#### What was learned
[Detailed findings]

#### Implementation consequence
[How this affects ARC Studio architecture]

#### Unresolved questions
- [Question 1]
- [Question 2]

---
```

### Step 3: Document Implementation Decisions

Each agent adds decisions to `docs/IMPLEMENTATION_DECISIONS.md`:

```markdown
| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|----------|----------------|-------------------------|---------|----------------|------------|
| Context7 integration | Opt-in with explicit config | Default enabled, No integration | Alpha must be safe; avoid surprise API calls | `src/context-providers/context7.ts`, `config.schema.json` | High |
```

### Step 4: Agent 0 Review

Agent 0 reviews all research notes and implementation decisions for:
- Completeness (all required areas covered)
- Consistency (decisions align with research)
- Clarity (future agents can understand the reasoning)
- Safety (security implications documented)

### Step 5: Phase 2 Sign-off

Agent 0 creates `docs/PHASE_2_COMPLETE.md` with:
- Date of completion
- Summary of key findings
- List of unresolved questions (to be addressed in later phases)
- Approval to proceed to Phase 3

---

## Success Criteria

Phase 2 is complete when:

- [x] `docs/` directory exists
- [ ] `docs/RESEARCH_NOTES.md` contains research for all 8 areas
- [ ] `docs/IMPLEMENTATION_DECISIONS.md` contains decisions for all major architectural choices
- [ ] All agents have reviewed and approved the documentation
- [ ] Agent 0 has signed off with `docs/PHASE_2_COMPLETE.md`
- [ ] No unresolved questions that block Phase 3 discovery

---

## Timeline Estimate

- **Agent 2 (Protocol):** 2-3 hours (Context7, GitHub, Vercel research)
- **Agent 3 (Theia):** 2-3 hours (Theia docs deep dive)
- **Agent 4 (Runtime):** 3-4 hours (LangGraph + SwarmGraph analysis)
- **Agent 6 (UX):** 1-2 hours (AG-UI event patterns)
- **Other agents:** 1 hour each (supporting research)
- **Agent 0 review:** 1 hour

**Total estimated time:** 12-16 hours of research work

---

## Next Phase

Once Phase 2 is complete, proceed to:

**Phase 3 — Discovery lock**  
All agents inspect their owned files and write a short status note. No code changes except command verification and docs recording.

---

## References

- Main prompt: `arc_prompt.txt:240-325` (Research gate definition)
- Phase overview: `arc_prompt.txt:780-829` (7-phase workflow)
- Project context: `arc_prompt.txt:1-100` (ARC Studio mission)
