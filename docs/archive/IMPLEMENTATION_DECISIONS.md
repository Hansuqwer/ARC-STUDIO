# Implementation Decisions

**Phase:** 2 - Research Lock  
**Created:** 2026-05-12  
**Status:** In Progress

---

## Decision Log

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|----------|----------------|-------------------------|---------|----------------|------------|
| Context7 integration | Opt-in with explicit config file in `~/.arc/context7.json`; disabled by default; require API key | 1) Default enabled with env var, 2) No Context7 support in alpha | Per arc_prompt.txt requirement: alpha must be safe, avoid surprise API calls, users must explicitly enable | `src/context-providers/context7.ts`, `src/config/context7-config.ts`, `docs/CONTEXT_PROVIDERS.md` | High |
| GitHub Search authentication | Use user's Personal Access Token (PAT) stored in system keychain; fall back to unauthenticated for public searches | 1) Use app token, 2) Always unauthenticated | Better privacy control, respects user's access permissions, better rate limits (30 req/min vs 10) | `src/search/github-search.ts`, `src/auth/keychain.ts` | High |
| SwarmGraph execution | Execute via subprocess calling `swarmgraph` CLI; parse JSONL trace files from `.arc/traces/` | 1) Import as library, 2) Reimplement graph logic | SwarmGraph is designed as CLI tool, trace files provide complete execution history, subprocess isolation for security | `src/runtime/swarmgraph-executor.ts`, `src/trace/trace-parser.ts` | High |
| LangGraph detection | Static AST analysis for `StateGraph` imports and `.compile()` calls; execute for full topology | 1) Only static analysis, 2) Only runtime execution | Dynamic graphs require execution to understand, static analysis provides quick detection, hybrid approach balances speed and accuracy | `src/detection/langgraph-detector.ts`, `src/ast/graph-analyzer.ts` | High |
| AG-UI event format | JSONL format with typed events (RUN_STARTED, NODE_COMPLETED, MESSAGE, RUN_COMPLETED, RUN_FAILED); store in `.arc/traces/` | 1) JSON array, 2) Binary format, 3) SQLite database | JSONL enables streaming, incremental parsing, human-readable, matches SwarmGraph format, easy replay | `src/events/event-emitter.ts`, `src/trace/trace-writer.ts` | High |
| Theia widget architecture | Side panel widget for graph visualization; backend service for execution; JSON-RPC communication | 1) Main area only, 2) Frontend-only execution | Follows Theia patterns, backend execution for security/isolation, side panel for persistent visibility | `src/browser/swarmgraph-widget.tsx`, `src/node/swarmgraph-service.ts` | High |
| Workspace root access | Use Theia's WorkspaceService; validate all paths within workspace boundaries; use FileService for operations | 1) Direct fs access, 2) No validation | Follows Theia security model, prevents path traversal, respects workspace boundaries | `src/common/workspace-utils.ts`, `src/detection/workflow-scanner.ts` | High |
| Electron security | Enable context isolation; disable Node integration in renderer; validate all IPC messages; implement CSP | 1) Enable Node integration, 2) No context isolation | Follows Electron security best practices, prevents XSS and code injection, isolates renderer from main process | `src/electron-main/main.ts`, `src/electron-main/preload.ts` | High |
| Rate limit handling | Track requests per minute; queue when approaching limit; show status in UI; exponential backoff on errors | 1) No tracking, 2) Hard fail on limit | Provides better UX, prevents API bans, transparent to user, follows API best practices | `src/search/rate-limiter.ts`, `src/ui/rate-limit-indicator.tsx` | High |
| Vercel Grep integration | Skip for alpha release; no public API available | 1) Implement anyway, 2) Use alternative | No public documentation found, cannot implement without API, focus on GitHub Search and local ripgrep | N/A (deferred) | High |
| Vercel Platform integration | Skip for alpha release; not required for core functionality | 1) Implement deployment features, 2) Environment variable sync | ARC Studio should work fully offline, Vercel is deployment platform not required for IDE functionality | N/A (deferred) | High |
| Credential storage | Use system keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service) | 1) Plain text config files, 2) Encrypted config files | Most secure option, OS-managed encryption, follows platform conventions, prevents accidental exposure | `src/auth/keychain.ts`, `src/auth/credential-manager.ts` | High |
| Graph execution sandbox | Execute user graphs in isolated subprocess with resource limits (memory, CPU, time) | 1) In-process execution, 2) Docker containers | Subprocess provides isolation without Docker overhead, resource limits prevent runaway processes, easier to implement | `src/runtime/sandbox-executor.ts`, `src/runtime/resource-limiter.ts` | Medium |
| Trace file persistence | Store locally in `.arc/traces/` directory; one JSONL file per run; atomic writes | 1) Remote storage, 2) In-memory only, 3) SQLite database | Local storage works offline, JSONL is simple and debuggable, atomic writes prevent corruption, matches SwarmGraph pattern | `src/trace/trace-writer.ts`, `src/trace/atomic-write.ts` | High |
| Code search fallback | Use local ripgrep (rg) when GitHub Search unavailable or rate limited | 1) No fallback, 2) Use grep | Ripgrep is fast and widely available, works offline, respects .gitignore, good UX when API unavailable | `src/search/local-search.ts`, `src/search/ripgrep-adapter.ts` | High |

---

## Decision Categories

### 1. External Integrations
- Context7 integration strategy
- GitHub Search integration
- Vercel platform dependencies

### 2. Runtime Architecture
- LangGraph execution model
- SwarmGraph detection and execution
- Event streaming patterns

### 3. Security Boundaries
- Credential storage
- Workspace isolation
- API key management
- Sandbox/daemon security

### 4. Theia Integration
- Frontend contribution patterns
- Backend service architecture
- Electron hardening
- Extension model

### 5. UX/Event Model
- AG-UI event schema
- Trace persistence
- Real-time streaming vs batch updates

---

## Decision Template

When adding a new decision, use this format:

```markdown
| [Short decision name] | [Chosen approach with key details] | [Alternative 1, Alternative 2] | [Primary reason for choice] | [List of files that implement this decision] | [High/Medium/Low] |
```

### Example Entry

```markdown
| Context7 integration | Opt-in with explicit config file; require API key in `~/.arc/context7.json` | 1) Default enabled with env var, 2) No Context7 support in alpha | Alpha must be safe; avoid surprise external API calls; users must explicitly enable | `src/context-providers/context7.ts`, `config.schema.json`, `docs/CONTEXT_PROVIDERS.md` | High |
```

---

## Guidelines

1. **Be specific:** Include enough detail that future developers understand the choice
2. **Document alternatives:** Show what was considered and why it was rejected
3. **Link to research:** Reference the relevant section in RESEARCH_NOTES.md
4. **Update files affected:** Keep this list current as implementation progresses
5. **Assess confidence:** High = well-researched, Medium = some uncertainty, Low = needs validation

---

## Review Status

- [x] Agent 0 review pending
- [x] All major architectural decisions documented
- [x] All decisions have corresponding research notes
- [x] Files affected are accurate and complete
- [x] Confidence levels are realistic

---

## Notes

This document serves as the architectural decision record (ADR) for Phase 2. Every significant technical choice must be documented here before implementation begins.

**Implementation Rule:** No agent may introduce a new external integration, API shape, Theia pattern, runtime execution behavior, SwarmGraph behavior, or security boundary without first adding an entry to this table.
