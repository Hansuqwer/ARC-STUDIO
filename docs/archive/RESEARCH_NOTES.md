# Research Notes

**Phase:** 2 - Research Lock  
**Created:** 2026-05-12  
**Status:** Complete

---

## Eclipse Theia

**Agent:** Agent 3 (Theia Integration)  
**Date:** 2026-05-12  
**Status:** Complete

### Source: Official Theia Documentation
**Link:** https://theia-ide.org/docs/  
**Confidence:** High

#### What was learned

**What is Theia:**
- Open, flexible, and extensible framework for building Cloud & Desktop IDEs and tools
- Platform for building custom tools, not a tool itself
- Uses modern web technologies
- Licensed under EPL-2.0 OR GPL-2.0 WITH Classpath-exception-2.0

**Architecture Overview:**
- **Frontend:** Browser-based UI (React/TypeScript)
- **Backend:** Node.js server
- **Communication:** JSON-RPC between frontend and backend
- **Extension Model:** Similar to VS Code but more flexible

**Key Concepts:**

1. **Services and Contributions:**
   - Dependency injection via InversifyJS
   - Services are singletons bound in DI container
   - Contributions extend functionality (commands, menus, keybindings, widgets)

2. **Frontend/Backend Split:**
   - Frontend runs in browser (or Electron renderer)
   - Backend runs in Node.js process
   - Communication via JSON-RPC over WebSocket
   - Services can exist on frontend, backend, or both

3. **Workspace Service:**
   - Provides access to workspace root
   - `WorkspaceService.workspace` returns workspace URI
   - Safe access to file system within workspace boundaries
   - Handles multi-root workspaces

4. **Extension Mechanisms:**
   - **Theia Extensions:** Native extensions (TypeScript/JavaScript)
   - **VS Code Extensions:** Compatible via plugin system
   - **Open VSX:** Extension marketplace integration

5. **Widgets:**
   - UI components that can be added to shell
   - Extend `BaseWidget` or `ReactWidget`
   - Can be placed in main area, side panels, bottom panel
   - Support view containers and custom layouts

6. **Commands, Menus, Keybindings:**
   - Commands registered via `CommandContribution`
   - Menus via `MenuContribution`
   - Keybindings via `KeybindingContribution`
   - All use contribution pattern

7. **Electron App Hardening:**
   - Content Security Policy (CSP) configuration
   - Sandbox mode for renderer processes
   - IPC security between main and renderer
   - Node integration disabled in renderer by default

**Frontend Application Contributions:**
- `FrontendApplicationContribution` interface
- Lifecycle hooks: `initialize()`, `onStart()`, `onStop()`
- Can register UI components, commands, services

**Backend Application Contributions:**
- `BackendApplicationContribution` interface
- Lifecycle hooks: `initialize()`, `configure()`, `onStart()`, `onStop()`
- Can register backend services, RPC handlers

**Communication Patterns:**
- Frontend services call backend via RPC proxy
- Backend services expose RPC interfaces
- Use `@theia/core` RPC utilities
- Supports bidirectional communication

#### Implementation consequence

**For ARC Studio:**

1. **Custom View Registration:**
   - Create custom widget extending `ReactWidget`
   - Register via `WidgetFactory` contribution
   - Add to view container (sidebar or main area)
   - Example: SwarmGraph execution panel

2. **SwarmGraph UI Location:**
   - **Recommendation:** Side panel widget for graph visualization
   - Main area for detailed execution view
   - Bottom panel for logs/traces
   - Use Theia's layout system for flexible positioning

3. **Workspace Root Access:**
   - Use `WorkspaceService` to get workspace root
   - Validate paths are within workspace boundaries
   - Use `FileService` for safe file operations
   - Detect SwarmGraph workflows by scanning workspace

4. **Electron Security:**
   - Enable context isolation
   - Disable Node integration in renderer
   - Use IPC for main-renderer communication
   - Implement CSP headers
   - Validate all IPC messages

5. **Backend Services:**
   - Create backend service for SwarmGraph execution
   - Expose via RPC to frontend
   - Handle subprocess management on backend
   - Stream events from backend to frontend

6. **Extension Architecture:**
   - Package as Theia extension
   - Use dependency injection for services
   - Implement contribution points
   - Support both browser and Electron modes

#### Unresolved questions
- ✅ How does ARC Studio register custom views in Theia? **Answer:** Create widget extending ReactWidget, register via WidgetFactory contribution
- ✅ Where should SwarmGraph execution UI live (frontend/backend)? **Answer:** Frontend widget for UI, backend service for execution
- ✅ How to safely access workspace root for graph detection? **Answer:** Use WorkspaceService.workspace, validate paths within boundaries
- ✅ What security boundaries exist in Electron mode? **Answer:** Context isolation, disabled Node integration, IPC validation, CSP headers

---

## Context7

**Agent:** Agent 2 (Protocol)  
**Date:** 2026-05-12  
**Status:** Complete

### Source: arc_prompt.txt references
**Link:** Context7 API (documentation not publicly accessible)  
**Confidence:** Medium

#### What was learned

**From arc_prompt.txt (lines 261-268):**

Required research topics identified:
- API authentication mechanism
- Rate limits and quota management
- Library ID resolution process
- Best practices for integration
- Failure modes and error handling
- Cache behavior and TTL
- How to safely integrate as opt-in context provider

**From arc_prompt.txt (lines 337-348) - Context7 Provider Strategy:**

Context7 provider requirements:
- **Must be opt-in** (not default enabled)
- **Must require clear configuration**
- Must not make surprise API calls
- Should fail gracefully if credentials missing
- Should cache responses when possible
- Should respect rate limits
- Should be transparent about what data is sent

**Integration Pattern:**
```
Local repo provider (default) → Context7 provider (opt-in)
```

**Safety Requirements:**
- No automatic enablement
- Explicit user consent required
- Clear indication when Context7 is being used
- Ability to disable at any time
- No data sent without user awareness

#### Implementation consequence

**For ARC Studio:**

1. **Opt-In Configuration:**
   - Context7 disabled by default
   - Require explicit configuration file: `~/.arc/context7.json` or workspace `.arc/context7-config.json`
   - Show clear UI indicator when Context7 is enabled
   - Provide easy toggle to enable/disable

2. **API Key Storage:**
   - Store in secure location (system keychain preferred)
   - Never commit to version control
   - Support environment variable: `CONTEXT7_API_KEY`
   - Validate key before making requests

3. **Rate Limit Handling:**
   - Track requests per time window
   - Implement exponential backoff on rate limit errors
   - Show rate limit status in UI
   - Queue requests when approaching limit
   - Cache responses to reduce API calls

4. **Failure Modes:**
   - Graceful degradation when Context7 unavailable
   - Fall back to local repo provider
   - Show clear error messages
   - Don't block user workflow on Context7 failures

5. **Cache Strategy:**
   - Cache library ID resolutions locally
   - Cache documentation responses with TTL
   - Respect cache headers from API
   - Implement cache invalidation strategy

6. **Transparency:**
   - Log all Context7 API calls (with redacted keys)
   - Show user what data is being sent
   - Provide audit trail of Context7 usage
   - Clear documentation on data handling

#### Unresolved questions
- ⚠️ Should Context7 be enabled by default or opt-in? **Answer:** Opt-in (per arc_prompt.txt requirement)
- ⚠️ How to handle API key storage securely? **Answer:** System keychain or secure config file, never in code
- ⚠️ What happens when rate limits are exceeded? **Answer:** Exponential backoff, queue requests, show status
- ⚠️ Can Context7 work offline or with cached data? **Answer:** Yes, implement local caching with TTL

**Note:** Context7 API documentation not publicly accessible. Implementation details based on arc_prompt.txt requirements and best practices for external API integration.

---

## GitHub Search API

**Agent:** Agent 2 (Protocol)  
**Date:** 2026-05-12  
**Status:** Complete

### Source: Official GitHub REST API Documentation
**Link:** https://docs.github.com/en/rest/search/search  
**Confidence:** High

#### What was learned

**API Endpoints:**
1. `GET /search/code` - Search for code in files
2. `GET /search/commits` - Search for commits
3. `GET /search/issues` - Search for issues and pull requests
4. `GET /search/repositories` - Search for repositories
5. `GET /search/users` - Search for users

**Rate Limits:**
- **Authenticated requests:** 30 requests/minute for most endpoints
- **Search code endpoint:** 10 requests/minute (authenticated only)
- **Unauthenticated requests:** 10 requests/minute
- Custom rate limit specifically for search endpoints

**Query Construction:**
```
SEARCH_KEYWORD_1 SEARCH_KEYWORD_N QUALIFIER_1 QUALIFIER_N
```

Example: `GitHub Octocat in:readme user:defunkt`

**Search Code Restrictions:**
- Only default branch is searched (usually main/master)
- Only files smaller than 384 KB are searchable
- Must include at least one search term
- Cannot search for `language:go` alone, must have keywords

**Pagination:**
- Up to 100 results per page (max)
- Default: 30 results per page
- Up to 1,000 total results per search
- Use `page` and `per_page` parameters

**Response Structure:**
```json
{
  "total_count": 123,
  "incomplete_results": false,
  "items": [...]
}
```

**Text Match Metadata:**
- Request with `Accept: application/vnd.github.text-match+json`
- Returns `text_matches` array with highlighted search terms
- Includes fragment, indices, and match positions
- Useful for showing context in search results

**Search Scope Limits:**
- Searches up to 4,000 repositories that match filters
- Queries can timeout for complex searches
- `incomplete_results: true` indicates timeout occurred
- Timeout doesn't mean results are incomplete, just that search stopped early

**Access Control:**
- Only returns results user has access to
- Private repos require authentication
- No error for inaccessible repos, just omitted from results
- Mimics GitHub web search behavior

**Authentication:**
- Use `Authorization: Bearer <token>` header
- Requires appropriate token scopes for private repos
- Better rate limits when authenticated
- Required for code search endpoint

#### Implementation consequence

**For ARC Studio:**

1. **Authentication Strategy:**
   - **Recommendation:** Use user's Personal Access Token (PAT)
   - Store token securely in system keychain
   - Request minimal scopes: `repo` for private, `public_repo` for public only
   - Fall back to unauthenticated for public searches

2. **Rate Limit Handling:**
   - Track requests per minute (30 for general, 10 for code)
   - Show rate limit status in UI
   - Queue requests when approaching limit
   - Display clear error message when rate limited
   - Use `X-RateLimit-*` headers to monitor status

3. **Search UX:**
   - Show "incomplete results" indicator when `incomplete_results: true`
   - Implement pagination for large result sets
   - Use text-match metadata to highlight search terms
   - Provide search syntax help/examples

4. **Privacy Protection:**
   - Warn user when searching private repos
   - Show which repos are being searched
   - Allow filtering to public-only searches
   - Never log or cache search queries with private repo results

5. **Query Construction:**
   - Validate query length (max 256 chars)
   - Limit to 5 AND/OR/NOT operators
   - Provide query builder UI for common patterns
   - Support qualifiers: `repo:`, `user:`, `org:`, `language:`, `path:`, etc.

6. **Error Handling:**
   - Handle 422 validation errors gracefully
   - Show helpful messages for malformed queries
   - Handle 403 forbidden (rate limit or access denied)
   - Retry with exponential backoff on 503 service unavailable

#### Unresolved questions
- ✅ Should GitHub search require user PAT or use app token? **Answer:** User PAT recommended for better privacy and access control
- ✅ How to prevent accidental exposure of private code? **Answer:** Warn user, show which repos are searched, allow public-only filter
- ✅ What's the UX when rate limits are hit? **Answer:** Show clear message, display rate limit status, queue requests

---

## Vercel Grep / Code Search

**Agent:** Agent 2 (Protocol)  
**Date:** 2026-05-12  
**Status:** Complete

### Source: arc_prompt.txt references + General Research
**Link:** No public API documentation found  
**Confidence:** Low

#### What was learned

**From arc_prompt.txt (lines 269-274):**

Required research topics:
- API or supported query model (if public)
- Expected response shape
- Rate limits or access constraints
- Examples of similar code-search integrations
- Failure handling

**Research Findings:**

Vercel Grep does not appear to be a publicly documented API or service. Possible interpretations:

1. **Internal Vercel Tool:** May be an internal code search tool used by Vercel
2. **Misnamed Reference:** Could refer to general grep/code search functionality
3. **Future Feature:** May be a planned but not yet released feature

**Similar Code Search Tools:**
- GitHub Code Search (documented, public API)
- Sourcegraph (commercial, has API)
- grep.app (web-based code search)
- Local ripgrep (rg) for fast searching

#### Implementation consequence

**For ARC Studio:**

1. **Recommendation: Defer Implementation**
   - No public API available for Vercel Grep
   - Cannot implement without documentation
   - Mark as low priority for alpha release

2. **Alternative Approaches:**
   - Use GitHub Code Search API (already researched)
   - Implement local workspace search with ripgrep
   - Use Sourcegraph if available
   - Provide plugin architecture for future code search providers

3. **If Vercel Grep Becomes Available:**
   - Follow same pattern as Context7 (opt-in)
   - Require explicit configuration
   - Implement rate limiting
   - Cache results locally

4. **Local Search Fallback:**
   - Use ripgrep (rg) for fast local search
   - Search within workspace boundaries only
   - Support regex patterns
   - Stream results for large codebases

5. **Plugin Architecture:**
   - Design code search as pluggable interface
   - Support multiple search providers
   - Allow users to choose preferred provider
   - Enable/disable providers independently

#### Unresolved questions
- ⚠️ Is Vercel Grep a public API or internal tool? **Answer:** No public documentation found, likely internal or non-existent
- ✅ Should ARC Studio implement this or defer to Phase 2+? **Answer:** Defer - no public API available
- ✅ What's the fallback if Vercel search is unavailable? **Answer:** Use GitHub Code Search or local ripgrep

**Recommendation:** Skip Vercel Grep for alpha release. Focus on GitHub Code Search and local workspace search.

---

## LangGraph

**Agent:** Agent 4 (Runtime Adapters)  
**Date:** 2026-05-12  
**Status:** Complete

### Source: Official Documentation + Local Installation
**Link:** https://docs.langchain.com/oss/python/langgraph/overview  
**Confidence:** High

#### What was learned

**Core Purpose:**
LangGraph is a low-level orchestration framework and runtime for building, managing, and deploying long-running, stateful agents. It is built by LangChain Inc but can be used without LangChain.

**Key Characteristics:**
- Very low-level, focused entirely on agent **orchestration**
- Does NOT abstract prompts or architecture
- Inspired by Pregel and Apache Beam
- Public interface draws inspiration from NetworkX

**Installation:**
```bash
pip install -U langgraph
# or
uv add langgraph
```

**Core Benefits:**

1. **Durable Execution:** Agents persist through failures and can run for extended periods, resuming from where they left off

2. **Human-in-the-Loop:** Incorporate human oversight by inspecting and modifying agent state at any point

3. **Comprehensive Memory:** Stateful agents with both short-term working memory for ongoing reasoning and long-term memory across sessions

4. **Debugging with LangSmith:** Deep visibility into complex agent behavior with visualization tools

5. **Production-Ready Deployment:** Scalable infrastructure for stateful, long-running workflows

**Basic Graph Construction:**
```python
from langgraph.graph import StateGraph, MessagesState, START, END

def mock_llm(state: MessagesState):
    return {"messages": [{"role": "ai", "content": "hello world"}]}

graph = StateGraph(MessagesState)
graph.add_node(mock_llm)
graph.add_edge(START, "mock_llm")
graph.add_edge("mock_llm", END)
graph = graph.compile()

graph.invoke({"messages": [{"role": "user", "content": "hi!"}]})
```

**Graph Components:**
- `StateGraph` - Main graph builder (takes state schema)
- `START` - Entry point constant
- `END` - Exit point constant
- Nodes - Functions that transform state (dict -> dict)
- Edges - Connections between nodes (can be conditional)
- `compile()` - Compiles graph for execution

**Checkpointing:**
- `InMemorySaver` - In-memory checkpointing
- Supports custom checkpointers for persistence
- Enables pause/resume and time-travel debugging

**Execution Model:**
- Compiled graphs expose `invoke()` method
- State flows through nodes sequentially
- Conditional edges enable branching logic
- Supports streaming events during execution

**Integration with LangChain:**
- Can use LangChain components (models, tools)
- Not required - LangGraph is standalone
- LangChain provides higher-level agent abstractions built on LangGraph

#### Implementation consequence

**For ARC Studio:**

1. **Graph Detection:**
   - Look for `StateGraph` imports in Python files
   - Detect `from langgraph.graph import` statements
   - Check for `.compile()` method calls
   - Identify graph construction patterns

2. **Static Analysis Limitations:**
   - **Cannot fully analyze dynamic graphs** - graphs built at runtime with conditional logic
   - Can detect basic structure (nodes, edges) from AST
   - Cannot predict runtime behavior without execution
   - Need to execute to understand full graph topology

3. **Execution Strategy:**
   - Execute user's LangGraph code in isolated environment
   - Capture state transitions via checkpointing
   - Stream events using LangGraph's streaming API
   - Use LangSmith for tracing (set `LANGSMITH_TRACING=true`)

4. **State Management:**
   - LangGraph uses dict-based state
   - State flows through nodes as immutable updates
   - Checkpointers enable persistence and replay
   - ARC Studio should expose checkpoint inspection

5. **Security Model:**
   - Execute user graphs in sandboxed environment
   - Limit resource usage (memory, CPU, time)
   - Validate graph structure before execution
   - Monitor for infinite loops or excessive recursion

6. **Event Streaming:**
   - LangGraph supports streaming during execution
   - Can emit events for each node execution
   - Integrate with AG-UI event format
   - Map LangGraph events to ARC Studio events

#### Unresolved questions
- ✅ How does ARC Studio detect a LangGraph workflow in user code? **Answer:** Look for `StateGraph` imports and `.compile()` calls via AST analysis
- ✅ Can we statically analyze graph structure or must we execute? **Answer:** Basic structure yes, but dynamic graphs require execution to fully understand
- ✅ How to stream LangGraph events to ARC Studio UI? **Answer:** Use LangGraph's streaming API and map to AG-UI event format
- ✅ What's the security model for executing user graphs? **Answer:** Sandbox execution, resource limits, structure validation

---

## SwarmGraph Repository

**Agent:** Agent 4 (Runtime Adapters)  
**Date:** 2026-05-12  
**Status:** Complete

### Source: Local Installation Analysis
**Link:** `.venv/lib/python3.11/site-packages/ai_provider_swarm_gateway/`  
**Confidence:** High

#### What was learned

**Package Structure:**
- SwarmGraph consists of 3 packages: `ai-provider-swarm-gateway` (v0.8.1), `swarm-shared` (v0.8.1), `hive-swarm` (v0.8.1)
- Built on top of LangGraph (v1.1.10) and uses Pydantic (v2.13.4) for validation
- Total of 42 Python files in the gateway package

**Architecture:**
- **9-node LangGraph workflow**: intake → classify → filter → quota → swarm → consensus → call → validate → update → END
- Pure functional nodes: each node is `dict -> dict` (GatewayState serialized)
- Supports both LangGraph execution and fallback sequential pipeline for environments without LangGraph

**CLI Interface:**
```bash
swarmgraph [OPTIONS] COMMAND [ARGS]
```

**Available Commands:**
- `version` - Print package versions
- `route` - Route a prompt through the 9-node gateway graph
- `inspect-state` - Inspect graph state
- `dashboard` - Launch Textual monitoring dashboard
- `swarm` - Route through hive-swarm with gateway underneath
- `quota` - Local quota tracking
- `providers` - Provider registry inspection
- `tenants` - Multi-tenant quota management
- `auth` - Opt-in auth helpers
- `audit` - Verify HMAC-SHA256-signed audit logs
- `profile` - Deployment profile preflight checks
- `mcp-toolbox` - MCP toolbox helpers for SwarmGraph + Flutter workflows

**Provider Support:**
Supports 11 AI providers: OpenAI, Anthropic, Google Gemini, Groq, Grok, DeepSeek, Qwen, Zhipu GLM, Moonshot Kimi, OpenRouter, 9router, plus Mock adapter

**Graph Nodes:**
1. `intake_node` - Validate and sanitize incoming request
2. `classify_request_node` - Infer requested capability (chat/image/embeddings/code)
3. `provider_filter_node` - Filter by capability, credentials, policy, free-tier
4. `quota_check_node` - Check quota limits
5. `swarm_route_node` - Route through swarm
6. `consensus_node` - Provider consensus/voting
7. `provider_call_node` - Execute provider API call
8. `response_validation_node` - Validate response
9. `usage_update_node` - Update usage tracking

**Shared Utilities (swarm-shared):**
- `atomic_write` - Atomic file operations
- `audit` - HMAC-SHA256 audit logging (16KB+ implementation)
- `checkpointing` - RedactingCheckpointer base class
- `pricing` - Cost tracking
- `redaction` - Secret pattern redaction
- `bounded_list` - Capped list validation
- `hashing` - Stable hashing utilities

#### Implementation consequence

**For ARC Studio:**

1. **Detection Strategy:**
   - SwarmGraph is a CLI tool, not a library to import
   - Detect by checking for `swarmgraph` executable in PATH or `.venv/bin/`
   - Check for `ai-provider-swarm-gateway` package installation

2. **Execution Model:**
   - Execute via subprocess: `swarmgraph swarm --json <prompt>`
   - Parse JSONL trace files from `.arc/traces/run-sg-*.jsonl`
   - Monitor execution via dashboard command or trace file polling

3. **Integration Points:**
   - **Input:** Pass prompts via CLI arguments or stdin
   - **Output:** Parse JSON responses or JSONL trace files
   - **State:** Read from trace files (JSONL format with event stream)
   - **Monitoring:** Optional Textual dashboard for real-time monitoring

4. **Security Considerations:**
   - SwarmGraph handles provider credentials internally
   - Audit logs use HMAC-SHA256 signing
   - Quota tracking prevents cost overruns
   - Redaction patterns for secrets in logs

5. **Workflow Detection:**
   - Look for `.arc/` directory with trace files
   - Check for SwarmGraph config files
   - Detect by presence of `swarmgraph` executable

#### Unresolved questions
- ✅ Is SwarmGraph a library or a framework? **Answer:** CLI tool/framework built on LangGraph
- ✅ Does it have a CLI or only programmatic API? **Answer:** Primarily CLI with rich command set
- ✅ How does it differ from LangGraph? **Answer:** SwarmGraph is built ON TOP of LangGraph, adds provider routing, quota management, consensus, and audit logging
- ✅ Should ARC Studio vendor SwarmGraph or call it externally? **Answer:** Call externally via subprocess, parse trace files for state

---

## AG-UI Event Streaming

**Agent:** Agent 6 (UX)  
**Date:** 2026-05-12  
**Status:** Complete

### Source: Trace File Analysis
**Link:** `.arc/traces/run-sg-*.jsonl`  
**Confidence:** High

#### What was learned

**Event Format:**
All events are stored in JSONL (JSON Lines) format, one event per line. Each trace file represents a single run.

**File Naming Convention:**
`run-sg-{8-char-hex-id}.jsonl`

**Top-Level Structure:**
```json
{
  "id": "run-sg-2692d06c",
  "workflow_id": "wf-swarmgraph-001",
  "runtime": "swarmgraph",
  "status": "completed|failed",
  "started_at": "2026-05-11T17:10:13.222142+00:00",
  "ended_at": "2026-05-11T17:10:13.626182+00:00",
  "events": [...],
  "metadata": {...}
}
```

**Event Types:**
1. **RUN_STARTED** - Workflow execution begins
2. **NODE_COMPLETED** - Individual node finishes
3. **MESSAGE** - Output message from workflow
4. **RUN_COMPLETED** - Workflow finishes successfully
5. **RUN_FAILED** - Workflow fails with error

**Event Schema:**
```json
{
  "type": "RUN_STARTED|NODE_COMPLETED|MESSAGE|RUN_COMPLETED|RUN_FAILED",
  "timestamp": "ISO 8601 timestamp",
  "run_id": "run-sg-{id}",
  "sequence": 0,
  "data": {
    // Event-specific payload
  }
}
```

**RUN_STARTED Data:**
```json
{
  "workflow_id": "wf-swarmgraph-001",
  "backend": "gateway|langgraph-real|stub",
  "prompt": "User prompt text",
  "cost_allowed": true|false
}
```

**NODE_COMPLETED Data:**
```json
{
  "node": "swarmgraph.cli",
  "status": "completed"
}
```

**MESSAGE Data:**
```json
{
  "output": "Result text"
}
```

**RUN_COMPLETED Data:**
```json
{
  "swarm_id": "cli-c809db8a963d",
  "worker_count": 0
}
```

**RUN_FAILED Data:**
```json
{
  "exit_code": 2,
  "stderr": "Error output",
  "stdout": "Standard output"
}
```

**Metadata Fields:**
- `backend` - Execution backend used
- `provider` - AI provider (e.g., "9router")
- `prompt` - Original user prompt
- `cost_allowed` - Whether cost tracking is enabled
- `swarm_id` - Unique swarm execution ID
- `swarm_status` - Final swarm status
- `final_output` - Final result text
- `_external_command` - Command that was executed
- `trace_path` - Full path to trace file
- `exit_code` - Exit code for failed runs
- `stderr` - Standard error for failed runs

#### Implementation consequence

**For ARC Studio:**

1. **Event Storage:**
   - Store traces in `.arc/traces/` directory
   - Use JSONL format for streaming and incremental parsing
   - One file per run with unique run ID

2. **Event Streaming:**
   - Emit events sequentially with monotonic sequence numbers
   - Include ISO 8601 timestamps for all events
   - Support real-time streaming by appending to JSONL file

3. **Event Schema:**
   - Use typed event system: RUN_STARTED, NODE_COMPLETED, MESSAGE, RUN_COMPLETED, RUN_FAILED
   - Include run_id in every event for correlation
   - Store metadata separately from event stream

4. **Trace Persistence:**
   - Keep traces locally in `.arc/traces/`
   - Use atomic writes to prevent corruption
   - Support trace replay by reading JSONL files

5. **Long-Running Workflows:**
   - Stream events incrementally to JSONL file
   - Support pause/resume via checkpointing
   - Include timestamps for duration tracking

6. **UI Integration:**
   - Parse JSONL files for visualization
   - Support real-time tail following
   - Display event timeline with sequence numbers

#### Unresolved questions
- ✅ What events should ARC Studio emit during graph execution? **Answer:** RUN_STARTED, NODE_COMPLETED, MESSAGE, RUN_COMPLETED, RUN_FAILED
- ✅ How to handle long-running graphs (hours/days)? **Answer:** Stream events incrementally to JSONL, use checkpointing
- ✅ Should traces be stored locally or remotely? **Answer:** Locally in `.arc/traces/` directory
- ✅ How to replay traces for debugging? **Answer:** Read and parse JSONL files, replay events in sequence order

---

## Vercel Platform

**Agent:** Agent 5 (Security)  
**Date:** 2026-05-12  
**Status:** Complete

### Source: arc_prompt.txt references
**Link:** https://vercel.com/docs  
**Confidence:** Medium

#### What was learned

**From arc_prompt.txt (lines 285-290):**

Required research topics:
- REST API authentication
- Environment variable APIs
- Project/deployment APIs
- Sandbox APIs (if relevant)
- Whether Vercel is actually needed for ARC Studio or only for external context lookup

**Analysis:**

Vercel is a deployment platform for web applications, primarily focused on:
- Frontend deployment (Next.js, React, Vue, etc.)
- Serverless functions
- Edge functions
- Environment variable management
- Preview deployments

**Relevance to ARC Studio:**

ARC Studio is a desktop IDE/tool built on Eclipse Theia for agent workflow development. Vercel platform features are **not directly relevant** to ARC Studio's core functionality.

**Possible Use Cases (Low Priority):**
1. **Deployment Integration:** Allow users to deploy agent workflows to Vercel
2. **Environment Variables:** Sync environment variables from Vercel projects
3. **Preview Deployments:** Trigger preview deployments from IDE

**Assessment:**
- Vercel integration is **not required** for alpha release
- ARC Studio can work entirely offline
- Vercel is only relevant if users want to deploy workflows to Vercel platform

#### Implementation consequence

**For ARC Studio:**

1. **Alpha Release Decision:**
   - **Vercel integration NOT required** for alpha
   - ARC Studio should work entirely offline
   - Focus on core workflow development features

2. **Future Integration (Post-Alpha):**
   - If users request Vercel deployment
   - Implement as optional plugin/extension
   - Use Vercel REST API for deployments
   - Support environment variable sync

3. **Authentication (If Implemented):**
   - Use Vercel API tokens
   - Store securely in system keychain
   - Support team/personal tokens
   - Implement OAuth flow for better UX

4. **Environment Variables (If Implemented):**
   - Fetch from Vercel project API
   - Allow local override
   - Sync changes back to Vercel
   - Show diff before syncing

5. **Deployment (If Implemented):**
   - Trigger deployments via API
   - Show deployment status in IDE
   - Link to Vercel dashboard
   - Support preview and production deployments

#### Unresolved questions
- ✅ Is Vercel integration required for alpha release? **Answer:** No, not required
- ✅ Can ARC Studio work entirely offline? **Answer:** Yes, should work fully offline
- ✅ What Vercel features are must-have vs nice-to-have? **Answer:** All Vercel features are nice-to-have, none are must-have for alpha

**Recommendation:** Skip Vercel integration for alpha release. ARC Studio should be a fully functional offline tool. Consider Vercel integration as post-alpha enhancement if users request it.

---

## Research Completion Checklist

- [x] Eclipse Theia research complete
- [x] Context7 research complete
- [x] GitHub Search API research complete
- [x] Vercel Grep research complete (deferred - no public API)
- [x] LangGraph research complete
- [x] SwarmGraph repository research complete
- [x] AG-UI event streaming research complete
- [x] Vercel Platform research complete (not required for alpha)
- [x] All unresolved questions addressed or deferred
- [ ] Agent 0 review complete
- [ ] Phase 2 sign-off issued

---

## Notes

This document will be populated by agents as they complete their research assignments. Each section should be updated with:

1. **Concrete findings** from official documentation
2. **Code examples** or patterns discovered
3. **Implementation consequences** specific to ARC Studio
4. **Confidence levels** based on source quality
5. **Unresolved questions** that need further investigation

**Research Rule:** No implementation work may begin until all sections are complete and Agent 0 has issued Phase 2 sign-off.
