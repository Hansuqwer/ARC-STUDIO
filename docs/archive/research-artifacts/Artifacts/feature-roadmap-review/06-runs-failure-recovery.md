# Runs / Failure Recovery Review

## Current ARC Spec

ARC Studio v0.1 ships a **Runs panel with list + summary only**. There is no Trace UI, no event timeline, no event JSON viewer, no replay scrubber, and no `/trace` command in the default surface. This is an explicit scope decision documented in §0.5 of `ARC_STUDIO_UX_SPEC.md`.

### Runs Panel (§7.11, §8.5)

The Runs panel renders a table with these columns:

| Column | Source |
|---|---|
| Run ID | ULID, truncated |
| Runtime | SwarmGraph, LangGraph, etc. |
| Status | `running`, `completed`, `failed`, `cancelled` |
| Cost | USD or `unknown` |
| Duration | ms → human-readable |
| Failure node | Node name where failure occurred (failed runs only) |
| Summary | One-line status text |

Actions per row: `Open summary`, `Open advanced trace in editor`, `Delete`.

The IDE panel uses `RunList` and `RunSummaryCard` components. The CLI `/runs` command renders the same table in a terminal panel.

### RunSummary Schema (§9)

```ts
interface RunSummary {
  runId: string;
  sessionId: string;
  runtime: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  startedAt: string;
  durationMs?: number;
  costUsd?: number | 'unknown';
  failureNode?: string;
  failureReason?: string;
  advancedTraceAvailable: boolean;
}
```

### FailureCard (§9)

When a run fails, an inline chat card is rendered with:

- **Header:** `Run failed at {failureNode}: {failureReason}. Retry, run diagnostics, or open the advanced trace.`
- **Actions:** Retry, Open Diagnostic, Show Advanced Trace
- **Expandable section:** `Show me what happened` — shows only the **last five redacted events** before failure
- **Not Trace UI:** The spec explicitly states "This is bounded failure context, not Trace UI."

```ts
interface FailureCardProps {
  runSummary: RunSummary;
  lastEvents: Array<{ type: string; timestamp: string; summary: string }>;
  onRetry: () => void;
  onOpenDoctor: () => void;
  onOpenAdvancedTrace: () => void;
}
```

### Advanced Fallback

The only path to full trace detail in v0.1 is:
```bash
arc-studio advanced runs trace <run-id>
```

This is documented in §7.11, §8.5, and §15. The spec is consistent: no default Trace UI, advanced fallback available.

### CostCeilingBadge (§9)

Shows estimated min/max cost and approval state. Used on phase cards, status details, Runs rows, and paid-call confirmations. Unknown maximum renders `cost ?` with confirmation copy.

### Run Lifecycle (ADR-002)

States: `PENDING` → `RUNNING` → `COMPLETED`/`FAILED`/`CANCELLED`. Internal supervisor phases `cancelling`/`failing` exist in metadata only. `JobSupervisor` manages background runs, targeted cancellation, orphan recovery. `EventBroker` provides live SSE streaming with replay fallback.

### Storage (ADR-003)

JSONL is canonical source of truth. SQLite is a rebuildable index for fast listing/filtering/search. Dual-write on state transitions. `trace_path` and `audit_path` fields on `RunRecord` link to files.

### State Table (§15)

| Surface | Empty | Loading | Populated | Error | Offline |
|---|---|---|---|---|---|
| Runs | `No stored runs` | `Loading runs...` | run summaries | `Runs could not be loaded` | cached summaries |

### What v0.1 Explicitly Excludes

From §0.5:
- No `/trace` command
- No Timeline component
- No ReplayScrubber
- No event JSON viewer
- No graph scrubber or time-travel UI

From §15: "Runs has no detail view in v0.1; use `arc-studio advanced runs trace <id>` for event detail."

---

## Comparable Products / Research

### Trace Tree + Span Replay

| Product | Trace Tree | Span Detail | Span Replay | Error Diagnosis | Source |
|---|---|---|---|---|---|
| **LangSmith** | Full nested tree (trace → spans → child spans) | Per-span: inputs, outputs, metadata, tokens, latency, error | Re-run individual spans with modified inputs | Error stack traces per span, highlight failed span in red, linked to code | [needs verification] langsmith docs |
| **Langfuse** | Tree + flat list toggle | Per-span: input/output, model params, cost, tokens, scores | Re-evaluate spans via SDK, not UI replay | Error messages, exception types, linked to dataset items | [needs verification] langfuse docs |
| **Phoenix (Arize)** | Tree view with span timeline | Per-span: attributes, events, links, status code | No UI span replay; export/re-import via SDK | Error status codes, exception events per span | [needs verification] OpenTelemetry-based |
| **LangGraph Studio** | Graph view + checkpoint list | Per-checkpoint: state snapshot, next node, config | **Checkpoint replay**: resume from any checkpoint with modified state | Error shown on failed node, state inspectable at each checkpoint | [needs verification] LangGraph Studio docs |

### Run Status + Failure Recovery

| Product | Run List | Failure Card/Summary | Retry Mechanism | Diagnostics Integration | Source |
|---|---|---|---|---|---|
| **Temporal** | Workflow list with status, type, start time, duration | Failure shown as workflow status + error message in detail view | **Reset** (replay from specific event), **Retry** (re-run with same/different params), **Signal** (inject data into running workflow) | `tctl workflow show/stack/query`, stack traces from running workflows | [needs verification] Temporal docs |
| **Prefect** | Flow run list with status, duration, tags, deployment | Failed runs show error message + traceback in detail view | **Re-run** from start, **Resume** from failed task (with state hydration) | Task-level logs, error traceback, flow run timeline | [needs verification] Prefect docs |
| **Dagster** | Run list with status, duration, tags, job name | Failed runs show error + stack trace per op/asset | **Re-execute** from failure point (re-execution pipeline), retry specific ops | Op-level logs, asset lineage, run timeline/Gantt | [needs verification] Dagster docs |
| **GitHub Actions** | Workflow run list with status, trigger, duration, branch | Failed jobs show red X, error annotation in logs, failure summary at top | **Re-run failed jobs** (not full workflow), re-run all jobs | Log annotations, step-level failure markers, `@actions/core` error grouping | GitHub Actions UI |
| **LangGraph Studio** | Run list with status, thread ID, checkpoint count | Failed runs show error on graph node + state at failure | **Replay from checkpoint**: select prior checkpoint, modify state, continue | Node-level state inspection, error visible on graph | [needs verification] |

### Timeline / Gantt

| Product | Timeline View | Gantt Chart | Log Viewer | Run Detail Panel |
|---|---|---|---|---|
| **Prefect** | Yes — flow run timeline with task bars | Yes — nested task Gantt within flow run | Yes — per-task logs with filtering | Full detail: parameters, state history, task runs, artifacts |
| **Dagster** | Yes — run timeline | Yes — op-level Gantt | Yes — per-op logs with level filtering | Full detail: config, tags, op errors, asset materializations |
| **Temporal** | Yes — workflow event history timeline | No — event list, not Gantt | No — event payloads, not logs | Full detail: event history, stack trace, query results, signals |
| **LangSmith** | Yes — span timeline (waterfall) | Yes — span waterfall is effectively a Gantt | No — span inputs/outputs serve as logs | Full detail: trace tree, span metadata, feedback scores |
| **GitHub Actions** | Yes — job timeline with step durations | Partial — step bars within job | Yes — step-level log viewer | Full detail: job summary, annotations, artifacts, logs |

### Key Patterns From Competitors

1. **Every observability product has a trace/tree detail view.** LangSmith, Langfuse, Phoenix all show nested spans. ARC's decision to omit this in v0.1 is unusual for the category.
2. **Failure recovery is granular.** Temporal resets to specific events. Prefect/Dagster re-execute from failure points. GitHub Actions re-runs only failed jobs. ARC's "retry same input" is the least granular option.
3. **Error diagnosis is node/span-level.** All competitors show error context at the point of failure (span, node, task, step), not just "last 5 events."
4. **Checkpoint replay is LangGraph Studio's killer feature.** Resume from any checkpoint with modified state. This is the closest analog to ARC's SwarmGraph use case.
5. **Cost per run is standard.** LangSmith, Langfuse, and Phoenix all show per-run/per-span cost. ARC's cost tracking is competitive here.
6. **Status filtering is universal.** All products filter by status, date range, and runtime/type. ARC's planned filtering is adequate.

---

## Gaps

### Critical Gaps

1. **No failure node context in FailureCard.** The card shows `failureNode` and `failureReason` strings but no node-level state, no inputs to the failed node, no stack trace, and no node graph position. Users cannot answer "what was this node doing when it failed?" without dropping to advanced CLI.

2. **Last-five-events is arbitrary and non-configurable.** Five events may be too few for multi-phase failures (e.g., a cascade across 10 nodes) or too many for simple failures (e.g., a single tool error). The count is hardcoded in the spec with no setting.

3. **Retry is same-input-only.** The spec defines `onRetry: () => void` with no parameters. There is no mechanism to edit the prompt, modify node inputs, or change configuration before retry. Every competitor offers at least parameter modification on retry.

4. **No run detail panel.** §8.5 says "Runs panel shows run list and per-run summary only." There is no split-view detail, no click-to-expand, no per-run page. Selecting a run shows the same summary row. This makes the Runs panel read-only and shallow.

5. **No status filtering UI specified.** §8.5 mentions "filters" in the panel header but does not define which filters exist, their UI, or their defaults. The state table shows the panel but not filter controls.

6. **No run search.** ADR-003 defines SQLite indexes for status/runtime/workflow/date filtering, but the spec does not expose search or filter UI in v0.1. The CLI has `arc runs search` in P4 but not v0.1.

### Moderate Gaps

7. **Cost per run is not tied to failure.** The `RunSummary` includes `costUsd` but the `FailureCard` does not show cost. Users cannot answer "did this failed run cost money?" without cross-referencing the Runs table.

8. **No run comparison.** There is no mechanism to compare two runs (e.g., a failed run vs. a successful retry). No diff of inputs, outputs, duration, or cost.

9. **No run grouping by session or workflow.** Runs are listed flat. There is no grouping by session (despite `sessionId` on `RunSummary`) or by workflow. A session with 20 runs shows 20 flat rows.

10. **Diagnostics integration is a separate button, not inline.** `onOpenDoctor` opens a separate diagnostic flow. The FailureCard does not inline diagnostic results (e.g., "provider key expired" or "runtime unreachable") directly in the card.

11. **No run export format specified.** §7.11 shows an `Export` action but does not define the format (JSON? JSONL? ZIP with traces?). ADR-003 mentions `trace_path` but not export packaging.

12. **No run deletion confirmation specified.** §7.11 shows `Delete` but the spec does not define confirmation behavior, undo, or soft-delete. ADR-002 defines `CANCELLED` but not deletion semantics.

### Minor Gaps

13. **No run count or pagination.** The spec does not define how many runs are shown, whether there is pagination, virtual scrolling, or load-more. SQLite supports `LIMIT/OFFSET` but the UI spec is silent.

14. **No run duration percentiles.** The Runs table shows per-run duration but no aggregate stats (p50, p95, avg). ADR-003's SQLite index supports aggregation queries.

15. **No run status badge colors specified.** The `RunSummary` has `status` but the spec does not define which colors/badges map to which statuses in the table. The color system (§2.1) defines state tokens but the Runs section does not reference them.

16. **`advancedTraceAvailable` boolean has no defined false case.** The schema includes `advancedTraceAvailable: boolean` but the spec never defines when this is `false`. If JSONL traces always exist, this is always `true` and the field is dead.

17. **No offline run behavior.** §15 says "cached summaries if available" for offline state but does not define what "cached" means, how many runs are cached, or how stale they can be.

---

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **Add `failureContext` to FailureCard** — include node inputs (redacted), node graph position, and error stack trace (redacted) in the expandable section | Users cannot diagnose failures without knowing what the failed node was processing. Last 5 events are insufficient for multi-node cascades. | v0.1 | Low — data already exists in trace; just needs redaction and display | §9 `FailureCardProps`: add `failureContext: { nodeInputs: Record<string, string>; nodePosition: { x: number; y: number }; stackTrace?: string }` |
| **Make last-N-events configurable** — add `failureCard.eventCount` setting with default 5, range 3-20 | Five is arbitrary. Multi-phase workflows need more context. Simple failures need less. Let users tune it. | v0.1 | Low — setting is trivial; UI needs a label showing current count | §9 `FailureCardProps`: add `maxEvents: number`; §8.6 Config: add `failureCard.eventCount` under Advanced tab; §7.11: note configurable count |
| **Add retry-with-edit** — `onRetry` accepts optional modified prompt/config; add "Retry with changes" action to FailureCard | Same-input retry is the least useful option. Every competitor allows parameter modification. SwarmGraph workflows often need prompt tweaks after failure. | v0.2 | Medium — requires retry parameter protocol, UI for editing, and backend support for modified re-run | §9 `FailureCardProps`: change `onRetry: () => void` to `onRetry: (options?: { prompt?: string; config?: Partial<RunConfig> }) => void`; add "Retry with changes" action |
| **Add RunSummary detail panel** — split-view or expandable detail showing full summary, cost, failure context, and link to advanced trace | The current Runs panel is read-only and shallow. Users need at least one click of depth without leaving the panel. | v0.1 | Low — detail panel reuses existing `RunSummary` data; no new backend needed | §8.5: add split-view description (list left, detail right); §9: add `RunDetailPanel` component spec |
| **Define status filters** — add filter chips for status (All/Running/Completed/Failed/Cancelled), runtime, and date range (Today/7d/30d/All) | Filters are mentioned in §8.5 header but never defined. Without them, users with >50 runs cannot find specific runs. | v0.1 | Low — SQLite index already supports these queries; UI is standard filter chips | §8.5: define filter controls and defaults; §9: add `RunFilterChips` component spec |
| **Show cost on FailureCard** — add `costUsd` to the failure card header | Users need to know if a failed run incurred provider costs. This is a trust signal. | v0.1 | Low — cost is already on `RunSummary`; just pass it to FailureCard | §9 `FailureCardProps`: add `costUsd` display; §10.1: add cost-in-failure microcopy |
| **Define run export format** — specify JSON export with trace, metadata, and audit refs; add `arc runs export --format json/jsonl` | Export action exists but format is undefined. Users and integrations need a stable contract. | v0.1 | Low — JSONL traces already exist; export is a packaging decision | §7.11: define export format; add `arc runs export` spec |
| **Add run deletion confirmation** — require confirmation dialog for delete; no undo needed for v0.1 | Delete is destructive. The spec shows the action but no confirmation. | v0.1 | Low — standard confirmation modal | §7.11: add "Delete requires confirmation" note; §9: reference `Modal` component for delete confirmation |
| **Define run pagination** — show 50 runs by default, load-more or infinite scroll; SQLite `LIMIT/OFFSET` | Without pagination, loading 1000+ runs blocks the UI. | v0.1 | Low — standard pagination pattern | §8.5: add pagination behavior; §9 `RunListProps`: add `onLoadMore?: () => void` |
| **Group runs by session** — collapsible session groups in the run list; default collapsed for sessions with >3 runs | Flat list loses session context. `sessionId` exists on `RunSummary` but is unused in the UI. | v0.2 | Medium — requires grouping logic in list rendering, session header component | §8.5: add session grouping; §9: add `RunSessionGroup` component |
| **Add run comparison** — select two runs, show side-by-side diff of inputs, outputs, duration, cost, status | Useful for debugging retry outcomes and comparing workflow variants. | v0.3 | Medium — requires selection UI, comparison component, diff rendering | New §9 component: `RunComparisonView` |
| **Inline diagnostic results in FailureCard** — when failure reason matches known diagnostic (e.g., key expired, runtime unreachable), show inline fix suggestion | Reduces context switching. User sees the fix without opening a separate Doctor flow. | v0.2 | Medium — requires mapping failure reasons to diagnostic suggestions | §9 `FailureCardProps`: add `inlineDiagnostic?: { message: string; fixAction: string; onFix: () => void }` |
| **Add run count and aggregate stats** — show total run count, success rate, avg duration in Runs panel header | Users need at-a-glance health metrics. SQLite supports aggregation. | v0.2 | Low — aggregation query + header display | §8.5: add stats header; §9: add `RunStatsHeader` component |
| **Remove or define `advancedTraceAvailable`** — if always true, remove the field. If sometimes false, define the condition. | Dead schema fields create confusion and maintenance burden. | v0.1 | Low — schema cleanup | §9 `RunSummary`: remove `advancedTraceAvailable` or define false condition |
| **Define offline cache behavior** — specify how many runs are cached locally, cache TTL, and refresh strategy | §15 mentions "cached summaries" but provides no implementation contract. | v0.1 | Low — define cache size and TTL | §15: add offline cache spec for Runs panel |

---

## Recommended Decisions

### Lock for v0.1

1. **No default Trace UI remains correct for v0.1.** The product's v0.1 positioning is chat-first with graph overlay. Adding Trace UI now would expand scope beyond what the backend supports (no span-level indexing, no replay infrastructure). The advanced fallback path (`arc-studio advanced runs trace <id>`) is sufficient for power users.

2. **FailureCard must include failure context beyond last-5-events.** At minimum: the failed node's inputs (redacted), the error message (redacted), and the node's position in the graph. Last-5-events should remain as supplementary context, not the primary diagnostic.

3. **Last-N-events count must be configurable.** Default 5 is fine, but it must be adjustable. Add `failureCard.eventCount` to config with range 3-20. Display the current count in the expandable section header.

4. **Retry in v0.1 is same-input only.** Retry-with-edit requires protocol changes and UI for editing run parameters. This is a v0.2 feature. v0.1 retry should be clearly labeled "Retry with same input" to set correct expectations.

5. **Status filters ship in v0.1.** The SQLite index supports them. The UI needs filter chips for status, runtime, and date range. This is low effort and high value.

6. **Run detail panel ships in v0.1 as a simple expand.** No split-view needed. Clicking a run row expands it inline to show the full `RunSummary` fields, failure context, and the "Open advanced trace" link. This provides one level of depth without a separate panel.

7. **Cost must appear on FailureCard.** If a failed run cost money, users need to see it immediately. This is a trust and transparency requirement.

8. **Run deletion requires confirmation.** Standard destructive action pattern. No undo for v0.1.

9. **Export format is JSON with trace + metadata.** Single JSON file containing the full `RunRecord` from JSONL, plus any audit refs. Matches existing data model.

10. **`advancedTraceAvailable` should be removed from `RunSummary`.** If JSONL traces always exist (which they should), this field is always `true` and adds nothing. If there is a legitimate case where it is `false`, define that case explicitly.

### Defer to v0.2

- Retry-with-edit (requires protocol + UI)
- Run grouping by session (requires list restructuring)
- Inline diagnostic suggestions (requires failure-reason taxonomy)
- Run comparison (requires selection UI + diff component)
- Run aggregate stats (requires aggregation endpoint + UI)

### Defer to v0.3

- Trace UI redesign (explicitly deferred in spec)
- Replay scrubber (explicitly deferred in spec)
- Event JSON viewer in default UI (explicitly deferred in spec)
- Span-level replay (requires runtime support)

---

## Specific Spec Edits

### §0.5 — Out Of Scope For v0.1

**Current:**
> Trace UI — No `/trace`, no Timeline component, no ReplayScrubber, no event JSON viewer.

**Edit to:**
> Trace UI — No `/trace`, no Timeline component, no ReplayScrubber, no event JSON viewer. **FailureCard provides bounded failure context with last-N redacted events (configurable, default 5) and failure node context. Full trace detail available via `arc-studio advanced runs trace <id>`.**

### §7.11 — `/runs` Summary

**Current:**
> No event timeline, event JSON detail, replay scrubber, or `/trace` command ships in default v0.1. Advanced fallback: `arc-studio advanced runs trace <run-id>`.

**Add after:**
> **Filters:** Status (All/Running/Completed/Failed/Cancelled), Runtime (all detected), Date range (Today/7d/30d/All). Default: All statuses, all runtimes, 30 days.
>
> **Pagination:** 50 runs per load, load-more button. SQLite `LIMIT/OFFSET` backed.
>
> **Row expand:** Clicking a run row expands inline to show full `RunSummary` fields, failure context (if failed), cost, and "Open advanced trace" link.
>
> **Delete:** Requires confirmation modal. No undo.
>
> **Export:** Single JSON file containing full `RunRecord` from JSONL trace plus audit refs. Filename: `run-{runId}-{timestamp}.json`.

### §8.5 — Runs Panel

**Current:**
> Runs panel shows run list and per-run summary only. It does not show event timeline, event JSON, trace replay, or replay scrubber in v0.1. Columns: Run ID, Runtime, Status, Cost, Duration, Failure node, Summary. Failure rows include `Open advanced trace in editor`, which runs or displays `arc-studio advanced runs trace <run-id>`.

**Edit to:**
> Runs panel shows run list with inline expandable detail. It does not show event timeline, event JSON, trace replay, or replay scrubber in v0.1.
>
> **Header:** Filter chips (Status, Runtime, Date range) + run count badge.
>
> **List columns:** Run ID, Runtime, Status, Cost, Duration, Failure node, Summary.
>
> **Row expand:** Clicking a row expands inline showing: full RunSummary fields, failure context (if failed: node name, redacted error, redacted node inputs, graph position), cost detail, and action buttons (Retry, Delete, Export, Open advanced trace).
>
> **Failure rows:** Render with `state.danger` tone. Include `Open advanced trace in editor` action which runs `arc-studio advanced runs trace <run-id>`.
>
> **Pagination:** 50 runs per page, load-more button at bottom.
>
> **State table:** empty `No stored runs`; loading `Loading run summaries...`; populated run table with filters; error `Runs could not be loaded` with retry; offline `Local daemon unavailable; showing cached summaries (N runs, cached at {time})`.
>
> **Components:** `RunList`, `RunFilterChips`, `RunSummaryCard`, `CostCeilingBadge`.

### §9 — RunSummary

**Current:**
```ts
interface RunSummary {
  runId: string;
  sessionId: string;
  runtime: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  startedAt: string;
  durationMs?: number;
  costUsd?: number | 'unknown';
  failureNode?: string;
  failureReason?: string;
  advancedTraceAvailable: boolean;
}
```

**Edit to:**
```ts
interface RunSummary {
  runId: string;
  sessionId: string;
  runtime: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  startedAt: string;
  durationMs?: number;
  costUsd?: number | 'unknown';
  failureNode?: string;
  failureReason?: string;
  // Removed: advancedTraceAvailable — always true when JSONL trace exists
  // If trace is missing, run is marked as corrupted in SQLite, not hidden
}
```

### §9 — FailureCard

**Current:**
```ts
interface FailureCardProps {
  runSummary: RunSummary;
  lastEvents: Array<{ type: string; timestamp: string; summary: string }>;
  onRetry: () => void;
  onOpenDoctor: () => void;
  onOpenAdvancedTrace: () => void;
}
```

**Edit to:**
```ts
interface FailureCardProps {
  runSummary: RunSummary;
  lastEvents: Array<{ type: string; timestamp: string; summary: string }>;
  maxEvents: number; // Configurable, default from failureCard.eventCount setting (range 3-20)
  failureContext?: {
    nodeName: string;
    nodeType: string;
    redactedError: string;
    redactedInputs?: Record<string, string>;
    graphPosition?: { x: number; y: number };
  };
  costUsd?: number | 'unknown'; // Shown in header for transparency
  onRetry: () => void; // v0.1: same-input only. Label: "Retry with same input"
  onOpenDoctor: () => void;
  onOpenAdvancedTrace: () => void;
}
```

**Copy update:**
> `Run failed at {failureNode}: {failureReason}. Cost: {costUsd}. Retry with same input, run diagnostics, or open the advanced trace.`

**Expandable section header:**
> `Show me what happened (last {maxEvents} events before failure)`

### §9 — RunList

**Current:**
```ts
interface RunListProps {
  runs: RunSummary[];
  selectedRunId?: string;
  onSelect: (runId: string) => void;
  onOpenAdvancedTrace: (runId: string) => void;
}
```

**Edit to:**
```ts
interface RunListProps {
  runs: RunSummary[];
  selectedRunId?: string;
  expandedRunId?: string; // For inline expand
  filters: RunFilters;
  totalRunCount: number; // For header badge
  onSelect: (runId: string) => void;
  onExpand: (runId: string) => void;
  onFiltersChange: (filters: RunFilters) => void;
  onOpenAdvancedTrace: (runId: string) => void;
  onLoadMore?: () => void; // Pagination
}

interface RunFilters {
  status: 'all' | 'running' | 'completed' | 'failed' | 'cancelled';
  runtime: 'all' | string;
  dateRange: 'today' | '7d' | '30d' | 'all';
}
```

### §8.6 — Config

**Add to Advanced tab:**
> **Failure Card**
> - Events shown: `failureCard.eventCount` (number, default 5, range 3-20)
> - Hint: `Number of events shown in the failure card's expandable section. Increase for multi-phase workflows, decrease for simple failures.`

### §10.1 — Errors

**Add failure card microcopy:**
> | State | FailureCard text |
> |---|---|
> | Run failed with cost | `Run failed at {node}: {reason}. Cost: ${cost}. Retry with same input, run diagnostics, or open the advanced trace.` |
> | Run failed, cost unknown | `Run failed at {node}: {reason}. Cost: unknown. Retry with same input, run diagnostics, or open the advanced trace.` |
> | Run failed, no cost | `Run failed at {node}: {reason}. No provider calls made. Retry with same input, run diagnostics, or open the advanced trace.` |

### §15 — States And Edge Cases

**Update Runs row:**
> **Offline:** `Local daemon unavailable; showing cached summaries ({N} runs, cached at {time}).` Cache stores last 50 run summaries in SQLite. Stale after 1 hour without daemon connection.

**Add note:**
> Runs has no full detail view in v0.1. Inline expand shows summary fields and failure context. Full event detail requires `arc-studio advanced runs trace <id>`.

---

## Acceptance Criteria

### v0.1 Must-Have

- [ ] Runs panel renders a table with columns: Run ID, Runtime, Status, Cost, Duration, Failure node, Summary
- [ ] Status filter chips render: All, Running, Completed, Failed, Cancelled
- [ ] Runtime filter chip renders with all detected runtimes
- [ ] Date range filter renders: Today, 7d, 30d, All
- [ ] Default filters: All statuses, all runtimes, 30 days
- [ ] Clicking a run row expands inline showing full RunSummary fields
- [ ] Expanded failed run shows: failure node name, redacted error, redacted node inputs (if available), cost, and action buttons
- [ ] FailureCard renders with `state.danger` tone for failed runs
- [ ] FailureCard shows cost in header (or "unknown" / "no cost")
- [ ] FailureCard expandable section shows last N redacted events (N from config, default 5)
- [ ] Expandable section header shows current event count: `(last {N} events before failure)`
- [ ] `failureCard.eventCount` setting exists in Config > Advanced tab with range 3-20, default 5
- [ ] Retry action is labeled "Retry with same input"
- [ ] Delete action triggers confirmation modal
- [ ] Export action produces a single JSON file with full RunRecord + audit refs
- [ ] Export filename format: `run-{runId}-{timestamp}.json`
- [ ] "Open advanced trace" action runs `arc-studio advanced runs trace <run-id>`
- [ ] 50 runs loaded per page with load-more button
- [ ] Empty state: `No stored runs`
- [ ] Loading state: `Loading run summaries...`
- [ ] Error state: `Runs could not be loaded` with retry action
- [ ] Offline state: `Local daemon unavailable; showing cached summaries ({N} runs, cached at {time})`
- [ ] `advancedTraceAvailable` field removed from `RunSummary` or false condition defined
- [ ] All failure context data is redacted using the §10.10 redaction contract
- [ ] Redaction removes API keys, bearer tokens, passwords, provider secrets, cloud credentials, and .env values from failure context and events
- [ ] Run status badges use correct state tokens: `state.success` (completed), `state.danger` (failed), `state.warning` (cancelled), `state.running` (running)

### v0.1 Nice-To-Have

- [ ] Run count badge in panel header
- [ ] Success rate percentage in panel header (completed / total)
- [ ] Keyboard shortcut to focus Runs panel: `Ctrl/Cmd+Shift+U`
- [ ] Arrow key navigation within run list
- [ ] Enter to expand selected run
- [ ] Delete keyboard shortcut when run is focused

### v0.2 Targets (not v0.1 blockers)

- [ ] Retry-with-edit: modify prompt/config before retry
- [ ] Run grouping by session (collapsible groups)
- [ ] Inline diagnostic suggestions in FailureCard
- [ ] Run aggregate stats (p50/p95 duration, success rate)
- [ ] Run comparison view (select two runs, side-by-side diff)

### v0.3 Targets (explicitly deferred)

- [ ] Trace UI redesign with nested span tree
- [ ] Replay scrubber with time-travel
- [ ] Event JSON viewer in default UI
- [ ] Span-level replay from failure point
- [ ] Full-text search across run events

---

## Reject / Do Not Build

### Rejected for v0.1

| Idea | Why rejected | Revisit when |
|---|---|---|
| **Default Trace UI with nested span tree** | Explicitly out of v0.1 scope. Requires span-level indexing, replay infrastructure, and significant UI work. The product's v0.1 positioning is chat-first with graph overlay, not observability-first. Advanced fallback exists. | v0.3 audit explorer, after adoption events and audit chains are stable |
| **Event timeline / Gantt chart in Runs panel** | Same reason as Trace UI. Requires event-level timestamp indexing and significant rendering work. Prefect/Dagster have this because they are pipeline tools; ARC v0.1 is a chat-first cockpit. | v0.3, if user demand validates it |
| **Event JSON viewer in default UI** | Explicitly out of v0.1 scope. Raw JSON is power-user territory. Advanced CLI provides it. | v0.3, or never if advanced CLI suffices |
| **Span-level replay from failure point** | Requires runtime support (SwarmGraph checkpoint semantics) and replay infrastructure. Not a UI-only feature. Temporal and LangGraph Studio have this because their runtimes support it natively. | v0.3+, after SwarmGraph checkpoint/replay protocol exists |
| **Run comparison view** | Requires selection UI, diff rendering, and comparison component. Useful but not v0.1 critical. Most v0.1 users will have few runs. | v0.2, after run volume validates the need |
| **Run grouping by workflow** | `workflow_id` exists but workflow-level grouping adds UI complexity. Session grouping is more useful (users think in sessions, not workflows). | v0.2, if session grouping proves insufficient |
| **Soft-delete with trash/recycle bin** | Adds storage complexity (need trash table, retention policy, purge schedule). v0.1 users have local JSONL files as backup. Confirmation modal is sufficient protection. | v0.2+, if multi-user or shared workspace requires it |
| **Real-time run count updates via WebSocket** | SSE event broker already exists for live runs. Adding a separate WebSocket for count updates is redundant. Poll the count on panel open or refresh. | Never — SSE covers live updates |
| **Run tagging/labeling** | Useful for organizing runs but requires tag storage, tag UI, and tag-based filtering. v0.1 users can use session grouping and date filters. | v0.2, after run volume validates the need |
| **Run bookmarking/favorites** | Same as tagging — useful but premature. v0.1 users have few enough runs that bookmarking is unnecessary. | v0.2+, if run volume justifies it |
| **Run annotations/comments** | Requires annotation storage, user identity, and comment UI. This is a collaboration feature; ARC v0.1 is single-user local. | Post-v0.1, if multi-user support is added |
| **Automated failure classification (ML-based)** | Requires ML infrastructure, training data, and classification model. Overkill for v0.1. Rule-based inline diagnostic suggestions are sufficient. | v0.3+, if failure volume and patterns justify it |
| **Run dependency graph (DAG of runs)** | Useful for pipeline workflows but ARC v0.1 targets single-workflow execution. Combo runs are sequential, not DAG-based. | v0.3+, if pipeline orchestration becomes a product direction |
| **Full-text search across event content** | SQLite FTS5 is possible but requires indexing event content (not just metadata). ADR-003 explicitly defers this. v0.1 users can use `arc runs search` (P4) or advanced trace CLI. | v0.2+, if search demand validates it |
| **Run SLA/alerting** | Requires alert rules, notification channels, and SLA definitions. This is a monitoring feature, not a cockpit feature. | Post-v0.1, if monitoring becomes a product direction |

### Do Not Build (Ever, Unless Product Direction Changes)

| Idea | Why never |
|---|---|
| **Multi-tenant run views** | ARC v0.1 is single-user local. Multi-tenant requires auth, storage isolation, and tenant model redesign. |
| **Cloud-hosted run dashboard** | ARC is local-first. Cloud deployment requires auth, multi-tenancy, and security redesign. |
| **Run marketplace (share runs publicly)** | Runs contain workspace-specific data, prompts, and potentially secrets (even redacted). Sharing runs is a security risk. |
| **Automated retry with ML-tuned parameters** | Violates the high-assurance principle. Users should control retry parameters. Automated retry with paid calls is a cost risk. |
| **Run replay with real provider calls** | Replaying a run that makes provider calls incurs real costs. Replay must be sandboxed or explicitly gated. Deterministic replay is scoped behind runtime support. |
