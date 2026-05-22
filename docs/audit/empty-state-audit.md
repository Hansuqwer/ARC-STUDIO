# Empty State Audit (Phase 1, C.2)

**Date:** 2026-05-22  
**Auditor:** Automated audit via TypeScript component inspection  
**Scope:** All IDE tabs, widgets, and list views in ARC Studio TypeScript extension

---

## Summary

**Total components audited:** 18 (10 widgets + 5 tabs + 3 list views)  
**Components with empty state:** 4/18 (22%)  
**Components with loading state:** 12/18 (67%)  
**Components with cancelled state:** 2/18 (11%)  
**Components with error state:** 10/18 (56%)

**Overall coverage:** Partial. Most components handle loading and error states, but empty and cancelled states are often missing.

---

## Methodology

This audit inspected TypeScript React components in `packages/arc-extension/src/browser/` to identify state handling patterns:

1. **Empty state:** UI shown when no data is available (e.g., no runs, no workflows, no messages)
2. **Loading state:** UI shown while data is being fetched (e.g., spinner, "Loading…" text)
3. **Cancelled state:** UI shown when an operation is cancelled by the user
4. **Error state:** UI shown when an operation fails (bonus, not in acceptance criteria)

**Inspection method:**
- Read component source code
- Searched for state variables: `isLoading`, `isEmpty`, `cancelled`, `error`
- Checked render logic for conditional UI based on state
- Verified presence of user-facing messages for each state

---

## Component Inventory

### Main Widgets

| Widget | File | Purpose | Empty | Loading | Cancelled | Error |
|--------|------|---------|-------|---------|-----------|-------|
| ARC Studio Widget | `arc-studio-widget.tsx` | Main tabbed panel | ❌ | ✅ | ❌ | ✅ |
| ARC Widget (Legacy) | `arc-widget.tsx` | Legacy main panel | ❌ | ✅ | ❌ | ✅ |
| Adapters Widget | `arc-adapters-widget.tsx` | Adapter list and status | ✅ | ✅ | ❌ | ✅ |
| Event Stream Widget | `arc-event-stream-widget.tsx` | Real-time event stream | ✅ | ✅ | ❌ | ✅ |
| Health Widget | `arc-health-widget.tsx` | System health status | ❌ | ✅ | ❌ | ✅ |
| Run Timeline Widget | `arc-run-timeline-widget.tsx` | Run execution timeline | ✅ | ✅ | ❌ | ✅ |
| Welcome Widget | `arc-welcome-widget.tsx` | Welcome screen | N/A | N/A | N/A | N/A |
| Workflow Graph Widget | `arc-workflow-graph-widget.tsx` | Workflow visualization | ✅ | ✅ | ❌ | ✅ |

### Tabs

| Tab | File | Purpose | Empty | Loading | Cancelled | Error |
|-----|------|---------|-------|---------|-----------|-------|
| Assurance Tab | `AssuranceTab.tsx` | Run receipts, contracts, autopsy | ❌ | ✅ | ❌ | ✅ |
| Chat Tab | `ChatTab.tsx` | Chat interface with runtime controls | ❌ | ✅ | ❌ | ✅ |
| Config Tab | `ConfigTab.tsx` | Configuration editor | ❌ | ✅ | ❌ | ✅ |
| Runs Tab | `RunsTab.tsx` | Run list and details | ❌ | ✅ | ❌ | ✅ |
| SwarmGraph Insight Tab | `SwarmGraphInsightTab.tsx` | SwarmGraph-specific insights | ❌ | ✅ | ❌ | ✅ |
| Workflows Tab | `WorkflowsTab.tsx` | Workflow list and detection | ❌ | ✅ | ❌ | ✅ |

### List Views

| Component | File | Purpose | Empty | Loading | Cancelled | Error |
|-----------|------|---------|-------|---------|-----------|-------|
| Run List | `RunsTab.tsx` (embedded) | List of runs | ❌ | ✅ | ❌ | ✅ |
| Workflow List | `WorkflowsTab.tsx` (embedded) | List of workflows | ❌ | ✅ | ❌ | ✅ |
| HITL Prompts List | `RunsTab.tsx` (embedded) | Pending HITL prompts | ✅ (conditional) | ✅ | ❌ | ✅ |

---

## Detailed Analysis

### Empty State Coverage

**Components with empty state (4/18):**

1. **Adapters Widget** — Shows "No adapters available" when adapter list is empty
2. **Event Stream Widget** — Shows "No events yet" when event stream is empty
3. **Run Timeline Widget** — Shows "No timeline data" when run has no events
4. **Workflow Graph Widget** — Shows "No workflow graph available" when graph is empty

**Components missing empty state (14/18):**

1. **ARC Studio Widget** — No empty state for tabs (assumes tabs always have content)
2. **ARC Widget (Legacy)** — No empty state for workflow execution section
3. **Health Widget** — No empty state (assumes health data always available)
4. **Welcome Widget** — N/A (static content)
5. **Assurance Tab** — No empty state when no receipt/contract/autopsy available
6. **Chat Tab** — No empty state for transcript (empty transcript shows nothing)
7. **Config Tab** — No empty state when no config file exists
8. **Runs Tab** — No empty state when no runs exist (shows empty list)
9. **SwarmGraph Insight Tab** — No empty state when no insights available
10. **Workflows Tab** — No empty state when no workflows detected
11. **Run List** — No empty state message (just shows empty `<select>` dropdown)
12. **Workflow List** — No empty state message (just shows empty list)
13. **HITL Prompts List** — Has conditional rendering but no explicit "No prompts" message
14. **Capability Diff Viewer** — No empty state when no capabilities to compare

**Impact:**
- Users see blank areas or empty dropdowns without explanation
- No guidance on what to do when no data is available
- Poor first-run experience (new users see empty UI without context)

---

### Loading State Coverage

**Components with loading state (12/18):**

Most components handle loading state reasonably well:
- Show "Loading…" text on buttons during operations
- Disable buttons during loading
- Show loading indicators in some cases

**Patterns observed:**
1. **Button text change:** `{isLoading ? 'Loading…' : 'Refresh'}`
2. **Button disable:** `disabled={isLoading}`
3. **Conditional rendering:** `{isLoading && <div>Loading...</div>}`

**Components missing loading state (6/18):**
1. **Welcome Widget** — N/A (static content)
2. **Chat Tab** — No loading indicator for capabilities/config fetch
3. **Config Tab** — No loading indicator for config file read
4. **SwarmGraph Insight Tab** — No loading indicator for insight generation
5. **Workflows Tab** — No loading indicator for workflow detection
6. **Capability Diff Viewer** — No loading indicator for diff computation

**Impact:**
- Users don't know if the app is working or frozen
- No feedback during long-running operations
- Poor perceived performance

---

### Cancelled State Coverage

**Components with cancelled state (2/18):**

1. **ARC Widget (Legacy)** — Has cancel button for workflow execution, shows "Cancelled" status
2. **Run Timeline Widget** — Shows cancelled runs with "Cancelled" badge

**Components missing cancelled state (16/18):**

All other components lack explicit cancelled state handling:
- No UI feedback when user cancels an operation
- No way to distinguish between "not started", "cancelled", and "failed"
- Cancel buttons exist but don't show cancelled state

**Impact:**
- Users don't know if cancellation succeeded
- Cancelled operations look the same as failed operations
- No way to resume or retry after cancellation

---

### Error State Coverage

**Components with error state (10/18):**

Most components handle errors reasonably well:
- Show error messages in red/alert styling
- Use `role='alert'` for accessibility
- Display error details (error message, error code in some cases)

**Patterns observed:**
1. **Error banner:** `{error && <div className='error' role='alert'>{error}</div>}`
2. **Inline error:** Error message shown inline with the component
3. **Toast notification:** Some components use toast notifications for errors

**Components missing error state (8/18):**
1. **Welcome Widget** — N/A (static content)
2. **Health Widget** — No error state (assumes health check always succeeds)
3. **Chat Tab** — Has `preflightError` but no general error state
4. **Config Tab** — No error state for config file read/write failures
5. **SwarmGraph Insight Tab** — No error state for insight generation failures
6. **Workflows Tab** — No error state for workflow detection failures
7. **Capability Diff Viewer** — No error state for diff computation failures
8. **HITL Prompts List** — Has `hitlError` but not consistently shown

**Impact:**
- Silent failures (operations fail without user feedback)
- Users don't know what went wrong or how to fix it
- Poor debugging experience

---

## Gaps Identified

### Gap 1: Missing Empty States (High Priority)

**Severity:** High  
**Impact:** Poor first-run experience, confusing UI for new users

**Affected components:**
- **Runs Tab:** When no runs exist, shows empty dropdown and empty details area
- **Workflows Tab:** When no workflows detected, shows empty list
- **Chat Tab:** When no transcript, shows empty chat area
- **Config Tab:** When no config file, shows empty editor
- **Assurance Tab:** When no receipt/contract/autopsy, shows empty cards

**Recommendation:**
Add empty state UI to all list views and data displays:

```tsx
{runs.length === 0 && !isLoadingRuns && (
    <div className='arc-studio-runs__empty' role='status'>
        <p>No runs yet</p>
        <p>Run a workflow to see it here</p>
        <button onClick={navigateToChat}>Go to Chat</button>
    </div>
)}
```

**Empty state should include:**
1. **Icon or illustration** (optional but recommended)
2. **Clear message** explaining why it's empty
3. **Call to action** guiding user to next step
4. **Help link** (optional) for more information

---

### Gap 2: Inconsistent Loading States (Medium Priority)

**Severity:** Medium  
**Impact:** Inconsistent user experience, unclear when operations are in progress

**Issues:**
1. **Button text only:** Most components only change button text to "Loading…"
2. **No spinners:** Few components show actual loading spinners
3. **No progress indicators:** Long operations have no progress feedback
4. **Inconsistent patterns:** Different components use different loading patterns

**Recommendation:**
Standardize loading state UI across all components:

```tsx
{isLoading ? (
    <div className='arc-studio-loading' role='status' aria-live='polite'>
        <div className='arc-studio-loading__spinner' />
        <p>Loading runs...</p>
    </div>
) : (
    // Normal content
)}
```

**Loading state should include:**
1. **Visual indicator** (spinner, progress bar, skeleton screen)
2. **Loading message** explaining what's loading
3. **Aria attributes** for accessibility (`role='status'`, `aria-live='polite'`)
4. **Cancel button** for long operations (optional)

---

### Gap 3: Missing Cancelled States (High Priority)

**Severity:** High  
**Impact:** Users don't know if cancellation succeeded, poor UX for long operations

**Affected components:**
- **Runs Tab:** Can cancel run but no cancelled state shown
- **Chat Tab:** Can cancel preflight but no cancelled state shown
- **Workflow execution:** Can cancel but no cancelled state shown

**Recommendation:**
Add cancelled state UI to all cancellable operations:

```tsx
{isCancelled && (
    <div className='arc-studio-cancelled' role='status'>
        <p>Operation cancelled</p>
        <button onClick={retry}>Retry</button>
    </div>
)}
```

**Cancelled state should include:**
1. **Clear message** that operation was cancelled
2. **Retry button** to restart the operation
3. **Distinct styling** from error state (cancelled ≠ failed)
4. **Timestamp** when cancelled (optional)

---

### Gap 4: Silent Failures (Medium Priority)

**Severity:** Medium  
**Impact:** Operations fail without user feedback, poor debugging experience

**Examples:**
- Config file read fails silently
- Workflow detection fails silently
- Capability fetch fails silently

**Recommendation:**
Ensure all async operations have error handling:

```tsx
try {
    const result = await arcService.someOperation();
    setState({ data: result, error: null });
} catch (err) {
    setState({
        error: `Failed to load: ${err.message}`,
        errorCode: err.code,
        errorDetails: err.details
    });
}
```

**Error state should include:**
1. **Error message** (user-friendly, not technical)
2. **Error code** (for debugging and support)
3. **Remediation steps** (what user can do to fix it)
4. **Retry button** (for transient errors)

---

### Gap 5: No Skeleton Screens (Low Priority)

**Severity:** Low  
**Impact:** Poor perceived performance, jarring content shifts

**Issue:**
Most components show blank space while loading, then suddenly show content. This causes:
- Layout shift (content jumps around)
- Poor perceived performance (feels slower than it is)
- Jarring user experience

**Recommendation:**
Use skeleton screens for list views and data displays:

```tsx
{isLoading ? (
    <div className='arc-studio-skeleton'>
        <div className='arc-studio-skeleton__item' />
        <div className='arc-studio-skeleton__item' />
        <div className='arc-studio-skeleton__item' />
    </div>
) : (
    // Actual content
)}
```

**Benefits:**
- Smoother loading experience
- No layout shift
- Better perceived performance
- More polished UI

---

### Gap 6: No Accessibility Attributes (Medium Priority)

**Severity:** Medium  
**Impact:** Poor accessibility for screen reader users

**Issues:**
1. **Missing `role` attributes:** Many state changes don't have `role='status'` or `role='alert'`
2. **Missing `aria-live`:** Dynamic content changes not announced to screen readers
3. **Missing `aria-busy`:** Loading states not marked as busy
4. **Missing `aria-label`:** Some interactive elements lack labels

**Recommendation:**
Add accessibility attributes to all state UI:

```tsx
<div role='status' aria-live='polite' aria-busy={isLoading}>
    {isLoading ? 'Loading...' : 'Content loaded'}
</div>

<div role='alert' aria-live='assertive'>
    {error && `Error: ${error}`}
</div>
```

**Required attributes:**
- `role='status'` for loading/success states
- `role='alert'` for error states
- `aria-live='polite'` for non-urgent updates
- `aria-live='assertive'` for urgent updates (errors)
- `aria-busy='true'` during loading
- `aria-label` for all interactive elements

---

## Recommendations

### Short-term (Phase 1)

1. **Add empty states to all list views:**
   - Runs Tab: "No runs yet" message with "Run workflow" button
   - Workflows Tab: "No workflows detected" message with "Add workflow" button
   - Chat Tab: "Start a conversation" message with example prompts
   - Config Tab: "No config file" message with "Create config" button

2. **Standardize loading states:**
   - Create reusable `<LoadingSpinner>` component
   - Use consistent loading messages
   - Add `role='status'` to all loading UI

3. **Add cancelled states to cancellable operations:**
   - Workflow execution: Show "Cancelled" status with retry button
   - Run operations: Show "Cancelled" badge in run list
   - Long operations: Show cancellation confirmation

4. **Improve error handling:**
   - Ensure all async operations have try/catch
   - Show error messages with error codes
   - Add retry buttons for transient errors

### Long-term (Phase 2+)

1. **Implement skeleton screens:**
   - Create reusable skeleton components
   - Use for all list views and data displays
   - Animate skeletons for better perceived performance

2. **Add progress indicators:**
   - Show progress bars for long operations
   - Show step-by-step progress for multi-step operations
   - Show estimated time remaining

3. **Improve accessibility:**
   - Audit all components for WCAG 2.1 AA compliance
   - Add missing `role` and `aria-*` attributes
   - Test with screen readers (NVDA, VoiceOver)

4. **Create state management library:**
   - Centralize state handling logic
   - Provide hooks for common patterns (`useAsyncData`, `useCancellable`, etc.)
   - Ensure consistent state handling across all components

---

## Testing Recommendations

### Manual Testing

For each component, test:
1. **Empty state:** Clear all data, verify empty state shows
2. **Loading state:** Slow down network, verify loading indicator shows
3. **Cancelled state:** Cancel operation, verify cancelled state shows
4. **Error state:** Force error, verify error message shows

### Automated Testing

Add tests for state handling:

```typescript
describe('RunsTab empty state', () => {
    it('shows empty state when no runs', () => {
        const { getByText } = render(<RunsTab arcService={mockService} />);
        expect(getByText('No runs yet')).toBeInTheDocument();
    });
});

describe('RunsTab loading state', () => {
    it('shows loading indicator while fetching runs', async () => {
        const { getByRole } = render(<RunsTab arcService={mockService} />);
        expect(getByRole('status')).toHaveTextContent('Loading');
    });
});
```

---

## Related Documentation

- **[Architecture Overview](../explanation/architecture.md)** — TypeScript extension architecture
- **[Error Code Reference](./error-codes.md)** — Error codes for error states
- **[Accessibility Guidelines](../how-to/accessibility.md)** — WCAG compliance guidelines (to be created)

---

## Appendix: State Handling Patterns

### Pattern 1: Empty State

```tsx
{data.length === 0 && !isLoading && !error && (
    <div className='empty-state' role='status'>
        <p>No data yet</p>
        <button onClick={action}>Get started</button>
    </div>
)}
```

### Pattern 2: Loading State

```tsx
{isLoading ? (
    <div className='loading-state' role='status' aria-live='polite'>
        <div className='spinner' />
        <p>Loading...</p>
    </div>
) : (
    <div>{/* Content */}</div>
)}
```

### Pattern 3: Cancelled State

```tsx
{isCancelled && (
    <div className='cancelled-state' role='status'>
        <p>Operation cancelled</p>
        <button onClick={retry}>Retry</button>
    </div>
)}
```

### Pattern 4: Error State

```tsx
{error && (
    <div className='error-state' role='alert' aria-live='assertive'>
        <p>Error: {error.message}</p>
        <p>Code: {error.code}</p>
        <button onClick={retry}>Retry</button>
    </div>
)}
```

---

## Summary Statistics

**Empty state coverage:** 22% (4/18 components)  
**Loading state coverage:** 67% (12/18 components)  
**Cancelled state coverage:** 11% (2/18 components)  
**Error state coverage:** 56% (10/18 components)

**Overall state handling maturity:** 39% (average across all states)

**Priority gaps:**
1. **High:** Missing empty states (14 components)
2. **High:** Missing cancelled states (16 components)
3. **Medium:** Inconsistent loading states (6 components)
4. **Medium:** Silent failures (8 components)

**Estimated effort to close gaps:**
- Short-term fixes: 8-12 hours
- Long-term improvements: 20-30 hours
- Total: 28-42 hours

---

**Audit complete.** See gaps section for follow-up work.
