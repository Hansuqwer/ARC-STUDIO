# ARC Studio Roadmap Automation Prompt

## Mission
Implement the ARC Studio Roadmap systematically with AI assistance, maintaining test-green discipline and security-first principles.

## Core Constraints

### MUST Rules
1. **Tests must pass before any commit** - Run full test suite; fix all failures before proceeding
2. **Security gates enforced** - No live provider calls without dual gating; redact all secrets
3. **API verification first** - Verify exact Theia 1.71 APIs before implementing any Theia integration
4. **Protocol versions pinned** - Pin AG-UI schema, OTel semconv version, SDK versions before coding
5. **JSONL source of truth** - Preserve .arc/traces/*.jsonl format; index is derivative
6. **No custom protocols** - Use MCP for tools, AG-UI for events, OTel for telemetry
7. **Extend Theia AI** - Use Theia Chat Agents, not custom chat UI
8. **Provider gating** - Require both ARC_<RUNTIME>_RUN_BACKEND and ARC_<RUNTIME>_ALLOW_COSTS for live calls

### NEVER Rules
1. **Never commit failing tests**
2. **Never expose secrets** - No keys/tokens in traces, logs, UI, or telemetry
3. **Never fork protocols** - No custom event formats parallel to AG-UI
4. **Never skip verification** - No "assume API exists" implementations
5. **Never auto-execute untrusted code** - Workspace files, MCP servers, A2A agents require explicit user consent
6. **Never batch security fixes** - Address security issues immediately in separate commits

## Implementation Order

### Phase 0: Verification (May 2026, Week 1-2)
**Goal**: Resolve all [VERIFY] items before implementation begins

#### PR0.1: API Verification Spike
**Acceptance**: Document exists with exact import paths and version confirmations

Tasks:
- [ ] Confirm installed Theia version is exactly 1.71.x
- [ ] Locate and document Chat Agent contribution API (likely @theia/ai-chat)
- [ ] Locate and document AI Variable contribution API (likely @theia/ai-core)
- [ ] Locate and document PromptService / slash command APIs
- [ ] Verify StatusBar contribution import path (@theia/core/lib/browser/status-bar/status-bar)
- [ ] Investigate public Theia MCP host/client APIs; document findings
- [ ] Pin AG-UI schema version and package source
- [ ] Pin OTel GenAI semconv version (note: docs say "Development" status)
- [ ] Pin OpenAI Agents SDK version for adapter
- [ ] Pin LangGraph version for event mapping
- [ ] Pin A2A Agent Card schema version
- [ ] Document findings in docs/API_VERIFICATION.md
- [ ] Update ROADMAP.md with [VERIFY] resolutions

**Tests**: N/A (documentation PR)

**Security**: None

**Deliverable**: docs/API_VERIFICATION.md with exact import paths, versions, and any API gaps

---

#### PR0.2: Repo Architecture Audit
**Acceptance**: Confirmed file paths and existing patterns documented

Tasks:
- [ ] Open arc-theia-studio workspace locally (not SwarmGraph)
- [ ] Confirm Python daemon process/control endpoint names
- [ ] Confirm .arc/traces/ JSONL exact event format
- [ ] Confirm provider diagnostics route exists or needs creation
- [ ] Confirm current Run Timeline implementation location
- [ ] Confirm package naming conventions (avoid inventing packages/arc-runtime if absent)
- [ ] Document existing test patterns (Node + Python)
- [ ] Document findings in docs/ARCHITECTURE_AUDIT.md

**Tests**: Run existing test suite to establish baseline

**Security**: None

**Deliverable**: docs/ARCHITECTURE_AUDIT.md + passing test baseline

---

### Phase 1: AG-UI Foundation (May-Jun 2026)

#### PR1.1: AG-UI Schema & Fixtures
**Acceptance**: Canonical AG-UI event types defined with golden test fixtures

Tasks:
- [ ] Create packages/arc-ag-ui (or extend existing protocol package)
- [ ] Define TypeScript AG-UI event types matching pinned schema version
- [ ] Create tests/fixtures/ag-ui/ directory
- [ ] Add golden JSONL fixtures for: agent_start, agent_end, tool_call, tool_result, text_delta, error, state_snapshot
- [ ] Create docs/AG_UI_MAPPING.md with mapping table
- [ ] Add schema validation utility
- [ ] Add redaction utility for secrets in events

**Tests**:
- [ ] Schema validation tests for each event type
- [ ] Redaction tests (API keys, env vars, marked secrets)
- [ ] Golden fixture parsing tests

**Security**: Implement redaction rules for provider keys, env vars, tool args marked secret

**Deliverable**: AG-UI type system + fixtures + mapping docs

---

#### PR1.2: SwarmGraph → AG-UI Mapping
**Acceptance**: SwarmGraph runs produce valid AG-UI events

Tasks:
- [ ] Locate SwarmGraph trace emitter in Python codebase
- [ ] Implement mapping from SwarmGraph events to AG-UI
- [ ] Map: run_start → agent_start, queen/worker → agent roles, handoff → tool_call, state → state_snapshot
- [ ] Handle unknown events as RAW/CUSTOM type
- [ ] Apply redaction to mapped events
- [ ] Update existing SwarmGraph fixtures to include AG-UI output

**Tests**:
- [ ] Unit tests for each SwarmGraph event type mapping
- [ ] Golden test: SwarmGraph fixture → expected AG-UI JSONL
- [ ] Redaction preserved in mapping

**Security**: Verify no secrets leak through mapping layer

**Deliverable**: SwarmGraph adapter emits AG-UI events

---

#### PR1.3: LangGraph → AG-UI Mapping
**Acceptance**: LangGraph runs produce valid AG-UI events

Tasks:
- [ ] Locate LangGraph event capture in Python codebase
- [ ] Implement mapping from LangGraph astream_events v2 to AG-UI
- [ ] Map: on_chain_start → agent_start, on_tool_start → tool_call, state snapshots → state_snapshot
- [ ] Handle conditional edges as dynamic routing metadata
- [ ] Apply redaction to mapped events
- [ ] Update existing LangGraph fixtures to include AG-UI output

**Tests**:
- [ ] Unit tests for each LangGraph event type mapping
- [ ] Golden test: LangGraph fixture → expected AG-UI JSONL
- [ ] Conditional edge metadata preserved

**Security**: Verify no secrets leak through mapping layer

**Deliverable**: LangGraph adapter emits AG-UI events

---

### Phase 2: Event Stream & OpenAI Adapter (Jun-Jul 2026)

#### PR2.1: OpenAI Agents SDK Adapter Skeleton
**Acceptance**: Adapter registered, stub execution works, no live calls

Tasks:
- [ ] Create python/**/adapters/openai_agents.py
- [ ] Register adapter in adapter registry
- [ ] Implement stub execution path (no real SDK calls)
- [ ] Add conformance test with fake SDK events
- [ ] Implement dual gating check (ARC_OPENAI_RUN_BACKEND + ARC_OPENAI_ALLOW_COSTS)
- [ ] Add arc adapter test openai-agents command

**Tests**:
- [ ] Adapter registration test
- [ ] Stub execution produces expected AG-UI events
- [ ] Gating test: live call blocked unless both gates enabled
- [ ] No-live-provider regression test

**Security**: Dual gating enforced; no keys in trace

**Deliverable**: OpenAI adapter skeleton with gating

---

#### PR2.2: OpenAI Agents SDK Integration
**Acceptance**: Real OpenAI SDK sample runs when gated

Tasks:
- [ ] Integrate OpenAI Agents SDK execution (framework-native, not custom client)
- [ ] Capture SDK tracing/events
- [ ] Map SDK events to AG-UI via mapping layer
- [ ] Handle tool calls, handoffs, guardrails
- [ ] Add example OpenAI agent in examples/

**Tests**:
- [ ] Integration test with SDK installed (skipped if SDK missing)
- [ ] Tool/handoff/guardrail event mapping tests
- [ ] No-live default test

**Security**: No provider upload by default; keys external

**Deliverable**: OpenAI adapter functional with gating

---

#### PR2.3: AG-UI Event Stream View Shell
**Acceptance**: View opens, renders fixture events

Tasks:
- [ ] Create theia-extensions/arc-event-stream/ (or package-local)
- [ ] Implement ReactWidget for event stream
- [ ] Implement AbstractViewContribution
- [ ] Add CommandContribution for "ARC: Open Event Stream"
- [ ] Add MenuContribution
- [ ] Implement fixture-based renderer for all AG-UI event types
- [ ] Add event detail drawer

**Tests**:
- [ ] Widget unit tests (if infra exists)
- [ ] Fixture render snapshot tests
- [ ] Manual browser smoke test

**Security**: Render JSON safely, no HTML injection

**Deliverable**: Event Stream view renders fixtures

---

#### PR2.4: Event Stream Live Subscription
**Acceptance**: View shows live events from running adapter

Tasks:
- [ ] Implement run event subscription service
- [ ] Connect Event Stream widget to live events
- [ ] Add virtualized list for 1000+ events
- [ ] Add filtering by event type
- [ ] Add auto-scroll toggle

**Tests**:
- [ ] Subscription lifecycle tests
- [ ] Virtualization performance test
- [ ] Filter tests

**Security**: Cap event payload size in UI

**Deliverable**: Event Stream shows live runs

---

### Phase 3: Telemetry & Health (Jul-Aug 2026)

#### PR3.1: OTel Semconv Pin & Span Fixtures
**Acceptance**: OTel GenAI semconv version pinned, span fixtures defined

Tasks:
- [ ] Pin OTel GenAI semconv version in docs/TELEMETRY_SEMCONV.md
- [ ] Document opt-in env var if using experimental semconv
- [ ] Create span fixture tests for: gen_ai.agent.*, gen_ai.tool.*, gen_ai.request.*, gen_ai.response.*
- [ ] Add span attribute validation tests
- [ ] Document which attributes are stable vs experimental

**Tests**:
- [ ] Span attribute unit tests
- [ ] Fixture validation tests

**Security**: No prompt/tool secret attributes

**Deliverable**: OTel semconv pinned + span fixtures

---

#### PR3.2: Runtime Trace Exporter Service
**Acceptance**: OTLP export works to local collector

Tasks:
- [ ] Create exporter service in Python
- [ ] Convert run span JSON to OTLP format
- [ ] Add PreferenceContribution for OTLP endpoint
- [ ] Add CommandContribution for "ARC: Export Trace"
- [ ] Default disabled; require explicit endpoint config
- [ ] Add non-local endpoint warning

**Tests**:
- [ ] Local fake OTLP collector test
- [ ] No endpoint = no export test
- [ ] Endpoint validation test

**Security**: User opt-in; endpoint validation; no secrets in spans

**Deliverable**: Trace exporter functional

---

#### PR3.3: Python Daemon Health Monitor
**Acceptance**: Health view shows daemon status

Tasks:
- [ ] Confirm Python daemon health endpoint exists
- [ ] Create health client service in Theia
- [ ] Implement health view widget (AbstractViewContribution)
- [ ] Add CommandContribution for "ARC: Restart Daemon" with confirmation
- [ ] Poll health endpoint (loopback only)
- [ ] Show daemon reachable/degraded, active runs, version

**Tests**:
- [ ] Client unit tests with mocked HTTP
- [ ] UI smoke test

**Security**: Loopback only; restart confirmation; no env dump

**Deliverable**: Health monitor view

---

#### PR3.4: Health Monitor Status Bar (Optional)
**Acceptance**: Status bar shows daemon health if API verified

Tasks:
- [ ] Only if StatusBar API verified in PR0.1
- [ ] Add status bar entry for daemon health
- [ ] Click opens health view

**Tests**:
- [ ] Status bar update tests

**Security**: None

**Deliverable**: Optional status bar integration

---

#### PR3.5: Provider Diagnostics Endpoint
**Acceptance**: Redacted provider diagnostics endpoint exists

Tasks:
- [ ] Create /api/providers/diagnostics/redacted endpoint in Python
- [ ] Return provider configured/missing, mock/live, last check (no secrets)
- [ ] Add explicit diagnostic command (gated)

**Tests**:
- [ ] Redaction tests (no raw keys/tokens)
- [ ] Route tests

**Security**: Highest priority - never serialize raw keys/tokens

**Deliverable**: Diagnostics endpoint

---

#### PR3.6: Provider Diagnostics View
**Acceptance**: View shows provider health without secrets

Tasks:
- [ ] Create diagnostics view widget (AbstractViewContribution)
- [ ] Add CommandContribution for "ARC: Provider Diagnostics"
- [ ] Display provider status from redacted endpoint
- [ ] Add explicit diagnostic request button (gated)

**Tests**:
- [ ] Route mocked UI tests
- [ ] No secret display test

**Security**: No live call unless explicit and gated

**Deliverable**: Provider diagnostics view

---

### Phase 4: Run History & AI Variables (Aug-Sep 2026)

#### PR4.1: JSONL Run History Index
**Acceptance**: In-memory index of .arc/traces/*.jsonl runs

Tasks:
- [ ] Create run history service
- [ ] Implement JSONL parser for .arc/traces/
- [ ] Build in-memory index: run ID, runtime, status, start/end time, metadata
- [ ] Handle corrupt JSONL gracefully
- [ ] Preserve JSONL source of truth (index is derivative)

**Tests**:
- [ ] JSONL parser tests
- [ ] Corrupt JSONL handling tests
- [ ] Index rebuild tests

**Security**: Do not parse workspace JSON as code; redaction invariant

**Deliverable**: Run history index service

---

#### PR4.2: Run History View
**Acceptance**: View lists past runs with filters

Tasks:
- [ ] Create run history view widget (AbstractViewContribution)
- [ ] Add CommandContribution for "ARC: Run History"
- [ ] Display runs list with filters: runtime, status, date range
- [ ] Add search by run ID
- [ ] Link to Event Stream replay

**Tests**:
- [ ] Filter tests
- [ ] Search tests
- [ ] UI smoke test

**Security**: Redaction preserved in display

**Deliverable**: Run history view

---

#### PR4.3: Run Replay Controller
**Acceptance**: Replay JSONL run into Event Stream

Tasks:
- [ ] Create replay controller service
- [ ] Implement replay speed controls: 1x, 2x, 5x
- [ ] Stream JSONL events to Event Stream view
- [ ] Add replay progress indicator
- [ ] Add pause/resume/stop controls

**Tests**:
- [ ] Replay deterministic fixture test
- [ ] Speed control tests

**Security**: Source JSONL unchanged

**Deliverable**: Run replay functional

---

#### PR4.4: ARC AI Variables - Config & Capabilities
**Acceptance**: #arcConfig and #runtime:capabilities variables work in Theia chat

Tasks:
- [ ] Only after Theia AI variable API verified in PR0.1
- [ ] Implement Theia AI variable contribution
- [ ] Add #arcConfig variable (reads config schema)
- [ ] Add #runtime:capabilities variable (reads runtime registry)
- [ ] Apply redaction to variable output

**Tests**:
- [ ] Variable resolver unit tests
- [ ] Redaction tests

**Security**: Redact env/provider keys; cap output

**Deliverable**: Config/capabilities variables

---

#### PR4.5: ARC AI Variables - Run & Workflow
**Acceptance**: #run:<id> and #workflow:<id> variables work

Tasks:
- [ ] Add #run:<id> variable (reads run history)
- [ ] Add #workflow:<id> variable (reads workflow metadata)
- [ ] Handle invalid IDs with clear errors
- [ ] Apply redaction to variable output

**Tests**:
- [ ] Variable resolver unit tests
- [ ] Invalid ID error tests
- [ ] Redaction tests

**Security**: Redact secrets; cap output

**Deliverable**: Run/workflow variables

---

### Phase 5: Chat Agent & Workflow Inspector (Sep-Oct 2026)

#### PR5.1: Runtime Configuration Chat Agent Registration
**Acceptance**: ARC chat agent appears in Theia AI Chat View

Tasks:
- [ ] Only after Chat Agent API verified in PR0.1
- [ ] Implement Theia Chat Agent contribution
- [ ] Register "ARC Runtime Configuration" agent
- [ ] Add static responses for common questions
- [ ] Use ARC AI Variables for context

**Tests**:
- [ ] Agent registration test
- [ ] Static response tests

**Security**: No auto-edits; no hidden provider calls

**Deliverable**: Chat agent registered

---

#### PR5.2: Chat Agent Schema-Aware Suggestions
**Acceptance**: Agent suggests config fixes based on schema

Tasks:
- [ ] Integrate config schema validation
- [ ] Implement schema-grounded suggestions
- [ ] Add prompt injection warning for untrusted workspace input
- [ ] Use dual gating if Theia AI configured model requires provider

**Tests**:
- [ ] Prompt/context assembly tests
- [ ] Schema failure fixture tests

**Security**: No auto-edits initially; prompt injection warning

**Deliverable**: Schema-aware chat agent

---

#### PR5.3: Workflow Graph Model
**Acceptance**: Normalized workflow graph model for LangGraph + SwarmGraph

Tasks:
- [ ] Create workflow graph model: nodes, edges, metadata
- [ ] Implement LangGraph → graph model adapter
- [ ] Implement SwarmGraph → graph model adapter
- [ ] Add CrewAI sequential placeholder
- [ ] Normalize dynamic routing metadata

**Tests**:
- [ ] Model normalization tests
- [ ] Snapshot of graph nodes/edges

**Security**: Treat exported workflow metadata as untrusted; sanitize labels

**Deliverable**: Workflow graph model

---

#### PR5.4: Workflow Inspector Static View
**Acceptance**: View renders static workflow graph

Tasks:
- [ ] Create workflow inspector view widget (AbstractViewContribution)
- [ ] Add CommandContribution for "ARC: Workflow Inspector"
- [ ] Implement lightweight React SVG/HTML graph renderer
- [ ] Render nodes, edges, labels
- [ ] Add node detail panel

**Tests**:
- [ ] LangGraph fixture render test
- [ ] SwarmGraph fixture render test
- [ ] CrewAI sequential placeholder test

**Security**: Sanitize labels

**Deliverable**: Static workflow inspector

---

#### PR5.5: Workflow Inspector Live Badges & Drilldown
**Acceptance**: Live run overlays on workflow graph

Tasks:
- [ ] Subscribe to AG-UI events for active run
- [ ] Add live badges: active node, completed nodes, error nodes
- [ ] Add node drilldown: prompt, config, source location
- [ ] Add jump-to-definition for node source

**Tests**:
- [ ] Live badge update tests
- [ ] Drilldown tests

**Security**: Same as static view

**Deliverable**: Live workflow inspector

---

### Phase 6: MCP & SwarmGraph Specialization (Oct-Dec 2026)

#### PR6.1: Theia MCP API Spike
**Acceptance**: Document Theia MCP host/client APIs or lack thereof

Tasks:
- [ ] Investigate Theia 1.71 MCP integration points
- [ ] Document public MCP server lifecycle APIs
- [ ] Document MCP tool exposure APIs
- [ ] If no public API, document workaround or downgrade plan
- [ ] Update ROADMAP.md with MCP implementation scope

**Tests**: N/A (documentation PR)

**Security**: None

**Deliverable**: docs/MCP_API_SPIKE.md

---

#### PR6.2: MCP Server Registry Config/List UI
**Acceptance**: View shows configured MCP servers

Tasks:
- [ ] Only if Theia MCP API verified in PR6.1
- [ ] Create MCP registry view widget (AbstractViewContribution)
- [ ] Add CommandContribution for "ARC: MCP Servers"
- [ ] Display configured servers: name, transport, status
- [ ] Add PreferenceContribution for MCP server config

**Tests**:
- [ ] Config tests
- [ ] List UI tests

**Security**: Secrets external/redacted

**Deliverable**: MCP config/list view

---

#### PR6.3: MCP Server Lifecycle
**Acceptance**: Start/stop local MCP servers

Tasks:
- [ ] Implement MCP server lifecycle service
- [ ] Add start/stop commands (require explicit enable + workspace trust)
- [ ] Support stdio and SSE transports
- [ ] Add command allowlist for security

**Tests**:
- [ ] Mock MCP server lifecycle tests
- [ ] Workspace trust gate tests

**Security**: Executing MCP servers is code execution; require explicit enable, workspace trust, command allowlist

**Deliverable**: MCP lifecycle management

---

#### PR6.4: MCP Tool Exposure
**Acceptance**: MCP server tools available to runtimes

Tasks:
- [ ] Integrate MCP tools into runtime tool registry
- [ ] Map MCP tool schema to runtime tool format
- [ ] Add tool invocation path
- [ ] No custom tool protocol (MCP only)

**Tests**:
- [ ] Tool registration tests
- [ ] Tool invocation tests

**Security**: Tool args redacted in traces

**Deliverable**: MCP tools exposed to runtimes

---

#### PR6.5: MCP Security Hardening
**Acceptance**: MCP security review passed

Tasks:
- [ ] Review command allowlist
- [ ] Review workspace trust integration
- [ ] Review secret handling
- [ ] Add security documentation
- [ ] Add threat model to docs/SECURITY.md

**Tests**:
- [ ] Security regression tests
- [ ] Allowlist bypass tests

**Security**: Full security review

**Deliverable**: MCP security hardened

---

#### PR6.6: SwarmGraph Workflow Specialization
**Acceptance**: SwarmGraph semantics in Workflow Inspector

Tasks:
- [ ] Create SwarmGraph graph adapter plugin
- [ ] Add queen/worker/handoff terminology to labels
- [ ] Add handoff path highlighting
- [ ] Add state pane for SwarmGraph state
- [ ] Add jump-to-definition for SwarmGraph nodes

**Tests**:
- [ ] SwarmGraph fixture graph tests
- [ ] Label/detail adapter tests

**Security**: Same as Workflow Inspector

**Deliverable**: SwarmGraph specialization

---

#### PR6.7: Tier-1 Hardening & Documentation
**Acceptance**: All Tier-1 items production-ready

Tasks:
- [ ] Security pass: review all redaction, gating, trust boundaries
- [ ] Performance pass: profile Event Stream, Run History, Workflow Inspector
- [ ] Documentation pass: update all docs, add tutorials
- [ ] Add CHANGELOG.md entries
- [ ] Add migration guide if needed
- [ ] Run full test suite
- [ ] Manual smoke test of all features

**Tests**:
- [ ] Full regression suite
- [ ] Performance benchmarks

**Security**: Full security review

**Deliverable**: Tier-1 complete

---

## Automation Workflow

### Before Starting Any PR
1. Read PR acceptance criteria
2. Verify all preconditions met (API verified, dependencies complete)
3. Create feature branch: `feature/<tier>-<item>-<pr-number>`
4. Run existing tests to establish baseline

### During PR Development
1. Implement tasks in order
2. Run tests after each significant change
3. Fix test failures immediately (never commit failing tests)
4. Run security checks for security-sensitive PRs
5. Update documentation as you go
6. Add new tests for new functionality

### Before Committing
1. Run full test suite: `npm test && cd python && uv run pytest`
2. Verify all tests pass
3. Run linter: `npm run lint`
4. Review changes for secrets (no keys, tokens, credentials)
5. Review changes for security issues
6. Update CHANGELOG.md if user-facing change

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

Refs: #<issue>
PR: <tier>-<item>-<pr-number>
```

Types: feat, fix, docs, test, refactor, security, perf

### After Committing
1. Push to feature branch
2. Create PR with template:
   - Summary of changes
   - What was tested
   - Security considerations
   - Breaking changes (if any)
3. Link to roadmap item
4. Request review

### PR Review Checklist
- [ ] All tests pass
- [ ] No secrets in code/traces/logs
- [ ] Security considerations addressed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Acceptance criteria met
- [ ] No breaking changes (or documented)

---

## Test Commands

### Node Tests
```bash
npm test                          # Run all Node tests
npm test -- --grep "AG-UI"        # Run specific test suite
npm run test:watch                # Watch mode
```

### Python Tests
```bash
cd python
uv run pytest                     # Run all Python tests
uv run pytest tests/unit          # Run unit tests only
uv run pytest -k "ag_ui"          # Run specific tests
uv run pytest --cov               # With coverage
```

### Integration Tests
```bash
npm run test:integration          # Run integration tests
```

### Manual Smoke Tests
```bash
npm run start:browser             # Start Theia browser
# Then manually test:
# - Open Event Stream view
# - Run sample adapter
# - Verify events appear
# - Check Run History
# - Test Chat Agent
# - etc.
```

---

## Security Checklist

### Before Every Commit
- [ ] No API keys, tokens, or credentials in code
- [ ] No secrets in test fixtures (use fake/redacted values)
- [ ] No secrets in logs or traces
- [ ] Redaction applied to all user-facing output
- [ ] Provider gating enforced for live calls
- [ ] Workspace trust checked for code execution
- [ ] Input validation for untrusted data
- [ ] No HTML injection in UI
- [ ] No command injection in shell commands
- [ ] No path traversal in file operations

### Security-Sensitive PRs (Additional)
- [ ] Threat model documented
- [ ] Security review requested
- [ ] Penetration testing considered
- [ ] docs/SECURITY.md updated

---

## Troubleshooting

### Tests Failing
1. Read test output carefully
2. Run single failing test: `npm test -- --grep "test name"`
3. Check test fixtures are up to date
4. Check API changes broke tests
5. Fix root cause (not symptoms)
6. Re-run full suite

### API Not Found
1. Check docs/API_VERIFICATION.md
2. Verify installed package version
3. Check import path
4. Search Theia source code
5. Ask in PR0.1 if unresolved

### Security Issue Found
1. Stop work immediately
2. Create security issue (private if needed)
3. Fix in separate commit
4. Add regression test
5. Update docs/SECURITY.md

### Performance Issue
1. Profile with Chrome DevTools
2. Check virtualization for large lists
3. Check subscription cleanup
4. Check memory leaks
5. Add performance test

---

## Success Criteria

### PR Success
- All tests pass
- Acceptance criteria met
- Security checklist complete
- Documentation updated
- Code review approved

### Tier-1 Success
- All 12 Tier-1 items complete
- Full test suite passes
- Security review passed
- Performance benchmarks met
- Documentation complete
- Manual smoke test passed

### Roadmap Success
- Tier-1 complete by Q4 2026
- Tier-2 prioritized for 2027
- No security incidents
- Test coverage >80%
- User feedback positive

---

## Emergency Procedures

### Critical Bug Found
1. Create hotfix branch from main
2. Fix bug with minimal changes
3. Add regression test
4. Fast-track review
5. Deploy immediately

### Security Vulnerability Found
1. Create private security issue
2. Assess severity (CVSS score)
3. Develop fix in private branch
4. Coordinate disclosure
5. Release security advisory

### Timeline Slipping
1. Review critical path
2. Cut non-essential items (see timeline section)
3. Parallelize more work
4. Request additional resources
5. Communicate new timeline

---

## Contact & Escalation

### Questions
- Roadmap questions: See docs/ROADMAP.md
- API questions: See docs/API_VERIFICATION.md
- Security questions: See docs/SECURITY.md

### Escalation
- Test failures blocking progress: Escalate after 2 hours
- API verification blocked: Escalate after 1 day
- Security issue found: Escalate immediately
- Timeline risk: Escalate weekly

---

## Appendix: Quick Reference

### Key Files
- `docs/ROADMAP.md` - Full roadmap
- `docs/API_VERIFICATION.md` - API verification results
- `docs/ARCHITECTURE_AUDIT.md` - Repo structure
- `docs/AG_UI_MAPPING.md` - AG-UI mapping table
- `docs/TELEMETRY_SEMCONV.md` - OTel semconv version
- `docs/SECURITY.md` - Security policies
- `docs/MOCK_POLICY.md` - Mock/stub policies

### Key Commands
- `npm test` - Run Node tests
- `uv run pytest` - Run Python tests
- `npm run lint` - Run linter
- `npm run start:browser` - Start Theia
- `arc run <runtime> <workflow>` - Run workflow
- `arc runs` - List runs
- `arc runs trace <id>` - Show trace

### Key Principles
1. Tests green before commit
2. Security first
3. API verification before implementation
4. Protocol versions pinned
5. JSONL source of truth
6. No custom protocols
7. Extend Theia AI
8. Provider gating enforced

---

**Last Updated**: 2026-05-12
**Version**: 1.0
**Status**: Ready for Phase 0
