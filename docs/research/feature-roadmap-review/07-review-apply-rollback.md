# Review / Apply / Rollback Review

## Current ARC Spec

ARC Studio specifies Review/Apply/Rollback as a **modal diff review surface** with per-hunk approve/reject/edit-first workflow, gated behind Build mode and workspace trust.

### CLI Diff Review (§7.8)

- `/diff` command opens full-screen diff review panel
- Shows file list (rows 2-4 if >2 files), hunk body (rows 5-23), action bar (row 25)
- Per-hunk status: `✓ approved`, `! pending`, `✗ rejected`
- Line numbers: 4 chars (3 chars in 80-col mode)
- Actions: `[Approve hunk] [Reject hunk] [Edit first] [Apply approved] [Cancel]`
- 80-column fallback: actions wrap to two rows, line numbers shrink, long paths middle-elide

### IDE Review Flow (§8.4)

- Review/Apply opens over canvas at 70% width; Chat shrinks to 30%
- Left column lists files/hunks; right column uses Monaco diff editor
- Footer actions: Apply Approved, Reject Pending, Edit First, Close
- Keyboard: `J/K` next/previous hunk, `A` approve, `R` reject, `E` edit-first, `Ctrl/Cmd+Enter` apply approved, `Esc` close
- Error state preserves hunk decisions and shows retry

### DiffHunk Component (§9)

```ts
interface DiffHunkProps {
  filePath: string;
  hunkId: string;
  status: 'pending' | 'approved' | 'rejected' | 'applied';
  lines: Array<{ type: 'add' | 'remove' | 'context'; oldLine?: number; newLine?: number; text: string }>;
  onApprove: (hunkId: string) => void;
  onReject: (hunkId: string) => void;
  onEditFirst: (hunkId: string) => void;
}
```

- Added/removed lines use diff tokens (`diff.add`, `diff.remove`, `diff.add.gutter`, `diff.remove.gutter`)
- Keyboard shortcuts: `A` approve, `R` reject, `E` edit-first, `J/K` navigate hunks

### HITL/Approval Integration (§7.2, §8.1, §9 Card)

- HITL cards in chat transcript with Approve/Reject/Edit First buttons
- Paid-call cards with provider, model, estimated ceiling, approval buttons
- Single-use decision tokens (P4 hardening)
- Slides into transcript with 12px offset fade animation (§6.2)

### Destructive Write Policy (§7.13, §10.3)

- Plan mode: read-only, no writes or paid calls
- Build mode: can propose changes, asks before applying
- Auto mode: follows `.arc/policy.yaml` — `destructive_writes: ask` by default, `trust_changes: deny`, `shell_exec: deny`
- Confirmation copy: `Apply approved changes to the workspace?`
- Rollback confirmation: `Rollback last applied change? This edits files back to the previous snapshot.`

### Workspace Trust Gate (§7.18, §9 WorkspaceTrustBanner)

- Untrusted workspaces: read-only chat/context, blocks writes, shell execution, paid calls, runtime execution
- Trust binds to canonical path + machine ID + user ID
- Symlinked paths resolve before trust check
- Moving/cloning a workspace requires new trust decision

### States (§15)

| Surface | Empty | Loading | Populated | Error | Offline | Awaiting approval | Applied/Rolled back |
|---|---|---|---|---|---|---|---|
| Review | no changes | preparing diff | hunks | apply error | disabled apply | pending hunk | applied badge |

### Colour Tokens for Diffs (§2.1)

| Token | Dark | Light | Use |
|---|---:|---:|---|
| `diff.add` | `#1f3320` | `#e8f5e9` | Added line bg |
| `diff.add.gutter` | `#9ece6a` | `#2e7d32` | Added gutter |
| `diff.remove` | `#3b1f2a` | `#ffebee` | Removed line bg |
| `diff.remove.gutter` | `#f7768e` | `#c62828` | Removed gutter |
| `diff.context` | `#24283b` | `#ffffff` | Context line bg |

### What ARC Review/Apply/Rollback Does NOT Currently Specify

- **No snapshot/checkpoint mechanism**: The spec references "previous snapshot" in rollback copy but does not define how snapshots are created, stored, or referenced.
- **No git integration**: No mention of git commits, branches, staging, or git-backed undo. The spec implies an ARC-managed snapshot system.
- **No rollback granularity**: "Rollback last applied change" implies single-step undo. No file-level, hunk-level, or run-level rollback is specified.
- **No conflict detection**: No specification for how concurrent external edits (user editing while agent proposes) are detected or resolved.
- **No file conflict handling**: No specification for what happens when an approved hunk cannot be cleanly applied (base file changed).
- **No multi-file apply ordering**: No specification for apply order when multiple files have approved hunks, or what happens on partial apply failure.
- **No undo history**: No list of past applied changes, no redo capability.
- **No binary file handling**: Spec assumes text diffs. Binary files are not addressed.
- **No large-file handling**: No behavior specified for very large diffs (e.g., >1000 lines, >10 files).
- **No diff source**: The spec does not specify where diffs come from — agent-generated proposals, git diff, or runtime output.

---

## Comparable Products / Research

| Feature | Cursor | Windsurf | VS Code Copilot | GitHub Copilot Workspace | Aider | OpenCode | ARC Studio (spec) |
|---|---|---|---|---|---|---|---|
| **Diff display** | Inline side-by-side in editor | Inline side-by-side in editor | Inline side-by-side in editor | Unified diff in web UI | Inline in chat (unified) | Inline in chat | Monaco diff editor (side-by-side) |
| **Per-hunk actions** | Accept/Reject per change | Accept/Revert per change | Accept/Discard per change | Review then Apply all | Auto-applies (git commit) | `/undo`/`/redo` | Approve/Reject/Edit First per hunk |
| **Bulk actions** | Accept All / Reject All | Accept All / Revert All | Accept All / Discard All | Apply all changes | N/A (auto-commits) | N/A | Apply Approved (bulk) |
| **Edit before apply** | Edit directly in editor | Edit directly in editor | Edit directly in editor | Edit in web editor | Edit in chat (re-prompt) | N/A | Edit First (opens editor) |
| **Multi-file diffs** | Tab per file, Accept/Reject each | Tab per file, Accept/Revert each | Tab per file, Accept/Discard each | File list + diff per file | All files in one commit | N/A | File list (rows 2-4), hunk navigation |
| **Undo mechanism** | Reject (before accept), git revert after | Revert (before accept), git after | Discard (before accept), git after | N/A | `/undo` (git revert) | `/undo` (git revert) | "Rollback last applied change" (unspecified) |
| **Redo mechanism** | N/A | N/A | N/A | N/A | `/redo` (git revert of revert) | `/redo` (git revert) | Not specified |
| **Snapshot/checkpoint** | N/A | Checkpoint timeline (Cascade) | N/A | N/A | Git commits | N/A | Referenced but not specified |
| **Git integration** | Works alongside git | Works alongside git | Works alongside git | Creates PR branch | Auto-commits every change | N/A | Not specified |
| **Conflict handling** | Shows merge conflict markers | Shows merge conflict markers | Shows merge conflict markers | Shows conflict UI | Shows git conflict | N/A | Not specified |
| **Concurrent edits** | Last-write-wins (editor) | Last-write-wins (editor) | Last-write-wins (editor) | PR merge resolution | Git merge | N/A | Not specified |
| **Binary files** | N/A (editor handles) | N/A (editor handles) | N/A (editor handles) | N/A | Skips binary | N/A | Not specified |
| **Large diff handling** | Paginates in editor | Paginates in editor | Paginates in editor | Paginates in web | No limit (git) | N/A | Not specified |
| **Apply failure** | Shows error inline | Shows error inline | Shows error inline | Shows error | Git error message | N/A | "apply error" state (no detail) |
| **Destructive confirmation** | None (direct apply) | None (direct apply) | None (direct apply) | Apply button | None (auto-commit) | None | `Apply approved changes to the workspace?` |
| **Rollback granularity** | File-level (Reject) | File-level (Revert) | File-level (Discard) | N/A | Run-level (git revert) | Run-level (git revert) | "last applied change" (ambiguous) |

### What Competitors Do Better

**Cursor** is the benchmark for inline diff review:
- **Inline diffs in editor context**: Changes appear directly in the file editor with green/red highlighting, not in a separate panel. Users see changes in their actual code context with full editor features (syntax highlighting, go-to-definition, minimap).
- **Accept/Reject per change**: Each changed region has inline Accept/Reject buttons. No modal review panel needed.
- **Composer multi-file edits**: Composer mode shows all changed files in a list, with Accept/Reject per file and Accept All/Reject All. Changes are visible simultaneously in editor tabs.
- **Edit-first is natural**: Since diffs are inline, users just edit the file directly — no separate "Edit First" action needed.
- **No separate review mode**: Diff review happens in the normal editing flow, not a modal overlay.

**Windsurf**:
- **Checkpoint timeline**: Cascade maintains checkpoints that users can revert to. This is a proper snapshot system, not just per-hunk undo.
- **Accept/Revert per change**: Same inline pattern as Cursor, with the addition of a checkpoint timeline for broader rollback.

**VS Code Copilot**:
- **Inline diffs with Accept/Discard**: Same pattern as Cursor — changes appear inline in the editor.
- **Native editor integration**: Uses VS Code's built-in diff editor, which means all editor features work (folding, search, minimap, peek).

**GitHub Copilot Workspace**:
- **PR-based workflow**: Changes are proposed as a branch with a PR. Users review diffs in the GitHub web UI, edit files, then merge. This provides natural git-backed snapshots and rollback.
- **File-level review**: File list on left, diff on right — similar to ARC's spec but with full GitHub review tooling (comments, suggestions, batch actions).

**Aider**:
- **Git-backed everything**: Every change is auto-committed. `/undo` reverts the last commit, `/redo` reverts the revert. Simple, reliable, no custom snapshot system needed.
- **Run-level rollback**: `/undo` reverts all changes from the last agent turn, not individual hunks. This matches how users think about agent actions.
- **No review step**: Aider applies changes immediately (with `--yes-always` or interactive approval before each write). No separate diff review phase. Trade-off: faster but less control.

**OpenCode**:
- **`/undo` and `/redo`**: Simple slash commands for reverting AI changes. Git-backed.
- **No separate review panel**: Changes are applied and visible in the editor. Undo/redo handles rollback.

### Key Patterns from Competitors

1. **Inline diffs beat modal panels**: Cursor, Windsurf, and Copilot all show diffs inline in the editor, not in a separate review panel. This is the dominant pattern because it keeps users in context.
2. **Git is the snapshot system**: Aider, OpenCode, and Copilot Workspace all use git for undo/redo/snapshots. Building a custom snapshot system is reinventing git.
3. **Accept/Reject per change, not per hunk**: Cursor and Windsurf operate at the change level (which may span multiple hunks), not the strict hunk level. This is more intuitive.
4. **Edit-first is just editing**: In inline-diff tools, "edit first" means the user directly edits the file. No separate button or mode needed.
5. **Bulk actions are essential**: Accept All / Reject All is present in every inline-diff tool. ARC's "Apply Approved" is equivalent but requires per-hunk approval first.
6. **Checkpoint timelines are emerging**: Windsurf's checkpoint system and Copilot Workspace's PR-based snapshots show that run-level or session-level rollback is becoming expected.

---

## Gaps

1. **No snapshot/checkpoint mechanism defined**: The spec references "previous snapshot" in rollback confirmation copy (§10.3) but does not define how snapshots are created, stored, enumerated, or restored. This is the most critical gap — rollback cannot work without snapshots.

2. **No git integration for undo**: Every competitor that supports undo uses git (Aider, OpenCode). ARC's spec implies a custom snapshot system but does not specify it. Building a custom snapshot system when git exists is unnecessary complexity.

3. **Rollback granularity is ambiguous**: "Rollback last applied change" (§10.3) — does this mean last hunk? Last file? Last apply batch? Last run? The spec does not say. Competitors use either per-change (Cursor/Windsurf) or per-run (Aider) granularity.

4. **No conflict detection or resolution**: The spec has no behavior for when an approved hunk cannot be cleanly applied because the base file was modified externally. Cursor/Windsurf/Copilot show merge conflict markers. Aider uses git merge. ARC has nothing specified.

5. **No concurrent external edit handling**: If the user edits a file while the agent is proposing changes to the same file, the spec does not define what happens. Last-write-wins? Conflict detection? Rejection?

6. **No multi-file apply ordering or partial failure handling**: If 5 files have approved hunks and file 3 fails to apply, what happens to files 4 and 5? The spec says "apply error" state but no recovery flow.

7. **No binary file handling**: The spec assumes all diffs are text. Binary files (images, compiled files, etc.) are not addressed. Should they be skipped? Shown as "binary changed"? Applied without review?

8. **No large diff handling**: No behavior for very large diffs (>1000 lines, >10 files, >100 hunks). The CLI panel at 100×30 rows cannot display large diffs effectively.

9. **Diff source is unspecified**: Where do diffs come from? Agent-generated proposals? `git diff`? Runtime output? The spec shows diff hunks but does not define the data source or diff format (unified diff, git diff, custom JSON?).

10. **No undo history or redo**: The spec supports "rollback last applied change" but no history of past changes, no list of undoable actions, and no redo. OpenCode and Aider both have `/undo` and `/redo`.

11. **Edit First workflow is underspecified**: "Edit First" opens the editor (§8.4) but the spec does not define: does it open the file in Monaco? Does it show the proposed change as editable? How does the user confirm the edit? What happens to the original hunk?

12. **No inline diff mode**: ARC uses a modal review panel (70% width overlay). Cursor, Windsurf, and Copilot all use inline diffs in the editor. ARC's approach is less contextual and requires mode-switching.

13. **No Accept All / Reject All**: The spec has "Apply Approved" (bulk apply of pre-approved hunks) but no single-click "Approve All" or "Reject All". Every competitor has bulk actions.

14. **No diff preview in chat**: The HITL card in chat (§7.2) shows a small diff preview, but the spec does not define how many lines are shown, whether it's collapsible, or how it transitions to the full review panel.

15. **No review session persistence**: If the user closes the review panel mid-review, are hunk decisions preserved? The spec says "error state preserves hunk decisions" (§8.4) but not normal close/reopen behavior.

---

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **Use git for snapshots and undo** | Every competitor with undo uses git. Building a custom snapshot system is unnecessary, fragile, and duplicates git's core competency. Git provides: atomic commits, diff generation, conflict detection, revert, branch-based isolation, and universal tooling. | v0.1 | Low — git is universally available in developer workspaces. Fallback: warn if not a git repo. | New §7.8.1: Git-backed snapshots; §10.3: update rollback copy; §15: add git-dependent states |
| **Define rollback granularity as "per apply batch"** | "Rollback last applied change" is ambiguous. Define it as: one `Apply Approved` action = one batch = one git commit. Rollback reverts that commit. This matches Aider's run-level undo and is intuitive. | v0.1 | Low — decision only | §10.3: define "last applied change" as last apply batch; new §8.4.1: Apply and Rollback semantics |
| **Add git commit on apply** | When user clicks "Apply Approved", create a git commit with message `[ARC Studio] Applied changes from run {run_id}`. This provides automatic snapshots, undo via `git revert`, and audit trail. | v0.1 | Medium — needs git detection, commit creation, error handling | New §8.4.1: Apply creates git commit; §7.8: add git status to diff panel |
| **Add `/undo` and `/redo` commands** | OpenCode and Aider both have these. They are simple, discoverable, and match user expectations. `/undo` = `git revert` of last ARC commit. `/redo` = `git revert` of the revert. | v0.1 | Low — wraps git revert | §10.4: add `/undo` and `/redo` to Workflow commands |
| **Add conflict detection before apply** | When base file has been modified since diff was generated, apply may fail. Detect this before apply and show conflict UI. Use git's conflict detection (attempt apply, check for conflict markers). | v0.1 | Medium — needs conflict detection logic and UI | §8.4: add conflict state; §15: add "conflict" column to Review row |
| **Add "Approve All" and "Reject All" buttons** | Every competitor has bulk actions. ARC's "Apply Approved" requires per-hunk approval first. Add bulk approve/reject for speed. | v0.1 | Low — UI addition | §7.8: add bulk buttons; §8.4: add bulk actions to footer |
| **Define Edit First workflow** | "Edit First" is listed but underspecified. Define: opens file in Monaco with proposed change applied as unstaged edit, user edits, saves, then the hunk is marked approved with the edited content. | v0.1 | Medium — needs Monaco editor integration and state management | §8.4: expand Edit First description; §9 DiffHunk: add edit state |
| **Add review session persistence** | If user closes review panel mid-review, hunk decisions should persist. Store per-hunk status in session state. Reopening `/diff` restores previous decisions. | v0.1 | Low — session state already exists (§7.14.1) | §7.14.1: add `pending_diffs` to session state; §8.4: add close/reopen behavior |
| **Defer inline diffs to v0.2** | Inline diffs in editor (Cursor/Windsurf pattern) are superior to modal panels but require deep Monaco/Theia integration. For v0.1, the modal review panel is acceptable. Inline diffs should be a v0.2 improvement. | v0.2 | High — requires Theia editor decoration API, inline diff rendering, complex state management | §8.4: note inline diffs as v0.2 target |
| **Add diff source specification** | Define that diffs come from agent proposals in unified diff format, generated by the runtime or adapter. Specify the JSON envelope for diff proposals. | v0.1 | Low — decision only | New §8.4.2: Diff Proposal Format |
| **Add binary file handling** | Binary files should be shown as "Binary file changed: {filename}" with Approve/Reject but no diff preview. Apply copies the binary. | v0.1 | Low — simple detection and display | §9 DiffHunk: add `isBinary` prop; §7.8: add binary file display |
| **Add large diff handling** | For diffs >100 hunks, show summary ("127 hunks across 8 files") with expand/collapse per file. For CLI, paginate with `+`/`-` keys. | v0.1 | Low — pagination logic | §7.8: add large diff pagination; §8.4: add large diff summary |
| **Add partial apply failure handling** | If apply fails for some files, show which succeeded and which failed. Offer: retry failed, skip failed, or rollback all. Create partial commit for successful files. | v0.1 | Medium — needs transaction-like semantics | §8.4: add partial failure state; §15: add "partial apply" state |
| **Add concurrent edit detection** | Before showing diff, check if file has been modified since the agent read it. If so, warn: "File was modified since agent read it. Review carefully." Use file mtime or git status. | v0.1 | Low — mtime/git status check | §8.4: add concurrent edit warning; §9 DiffHunk: add `staleBase` prop |
| **Defer checkpoint timeline to v0.2** | Windsurf-style checkpoint timeline is useful but requires snapshot history UI. For v0.1, git commit history provides equivalent functionality via `git log`. | v0.2 | Medium — needs timeline UI component | §8.4: reserve checkpoint timeline for v0.2 |
| **Add diff preview in HITL cards** | HITL cards in chat should show first 5 lines of diff with "Review full diff" button that opens the Review panel. | v0.1 | Low — extends existing HITL card spec | §9 Card component: add diff preview to HITL card variant |

---

## Recommended Decisions

### 1. Use git for all snapshot and undo operations
**Decision**: Yes. This is non-negotiable for v0.1.

Rationale:
- Git is universally available in developer workspaces (ARC's target audience)
- Git provides atomic commits, conflict detection, revert, and branch management for free
- Aider and OpenCode both use git-backed undo successfully
- Building a custom snapshot system is fragile, duplicates git, and creates maintenance burden
- Git commits provide natural audit trail: `[ARC Studio] Applied changes from run {run_id}`

Implementation:
- Before first apply in a session, check if workspace is a git repo
- If not a git repo: warn user "Workspace is not a git repository. Undo will not be available." Offer to `git init`.
- On "Apply Approved": create git commit with message `[ARC Studio] Applied changes from run {run_id}`
- `/undo`: find last ARC Studio commit, `git revert --no-edit <sha>`
- `/redo`: find last revert of ARC Studio commit, `git revert --no-edit <sha>`
- Rollback confirmation: `Revert last ARC Studio commit ({sha_short})? This creates a revert commit.`

### 2. Define rollback granularity as "per apply batch" (one git commit per apply)
**Decision**: Yes.

Rationale:
- "Last applied change" is ambiguous — users think in terms of agent actions, not individual hunks
- One apply action = one batch of approved hunks = one git commit = one undoable unit
- Matches Aider's run-level undo and user mental model
- Per-hunk undo is already handled by Reject before apply

### 3. Add `/undo` and `/redo` slash commands
**Decision**: Yes.

Spec:
```
/undo    Revert last ARC Studio applied changes (git revert)
/redo    Re-apply last undone ARC Studio changes (git revert of revert)
```

Behavior:
- `/undo`: finds most recent commit with `[ARC Studio]` prefix, runs `git revert --no-edit`
- If no ARC Studio commits exist: `No ARC Studio changes to undo.`
- `/redo`: finds most recent revert of an ARC Studio commit, reverts it
- If no redo available: `Nothing to redo.`
- Both commands require workspace trust

### 4. Add "Approve All" and "Reject All" bulk actions
**Decision**: Yes.

Updated action bar:
```
[Approve hunk] [Reject hunk] [Edit first] | [Approve all] [Reject all] | [Apply approved] [Cancel]
```

Behavior:
- "Approve All": marks all pending hunks as approved
- "Reject All": marks all pending hunks as rejected (with confirmation: `Reject all {N} pending hunks?`)
- "Apply Approved": creates git commit with all approved hunks

### 5. Define Edit First workflow explicitly
**Decision**: Yes.

Flow:
1. User clicks "Edit First" on a hunk
2. File opens in Monaco editor (IDE) or system editor (CLI) with proposed change applied as unstaged edit
3. User edits the file freely
4. User saves and returns to review panel
5. Hunk is marked "approved (edited)" — the edited content is what gets applied
6. If user cancels the edit, hunk returns to "pending"

CLI flow:
1. "Edit First" opens `$EDITOR` with the file
2. On editor exit, diff is re-computed
3. Hunk marked "approved (edited)"

### 6. Add conflict detection and resolution UI
**Decision**: Yes.

Flow:
1. Before applying each hunk, attempt a dry-run patch
2. If patch fails (base changed), mark hunk as "conflict"
3. Show conflict state: `⚠ Cannot apply cleanly — file was modified`
4. Actions: `[Open for manual merge] [Skip this hunk] [Apply remaining]`
5. "Open for manual merge" opens file with conflict markers in Monaco

### 7. Defer inline diffs to v0.2
**Decision**: Yes.

Rationale:
- Inline diffs require deep Theia/Monaco integration (editor decorations, inline diff rendering, zone widgets)
- Modal review panel is functional for v0.1 and matches GitHub Copilot Workspace's web-based approach
- Inline diffs are a significant UX improvement but are v0.2 scope
- Document as explicit v0.2 target in spec

### 8. Add review session persistence
**Decision**: Yes.

Implementation:
- Store pending diff decisions in session state (`transcript.jsonl` or separate `review_state.json`)
- Key: `{run_id}:{file_path}:{hunk_id}` → `{status: 'approved'|'rejected'|'pending'}`
- On `/diff` reopen, restore previous decisions
- On apply, clear decisions for applied hunks
- On session close, persist decisions for 24 hours (then garbage collect)

### 9. Add concurrent edit warning
**Decision**: Yes.

Implementation:
- When diff is generated, record file mtime for each file
- Before showing hunk, check current mtime
- If mtime changed since diff generation: show warning banner on hunk
- Warning: `⚠ {filename} was modified after this diff was generated. Review carefully before approving.`
- Warning tone: `state.warning`, non-blocking

---

## Specific Spec Edits

### §7.8 `/diff` Review

**Add after the existing layout (after line 613):**

```text
Git status line (row 26):
  ✓ git repo | branch: main | 0 uncommitted changes
  or
  ⚠ not a git repo — undo will not be available. Run "git init" to enable.

Bulk actions (row 25, updated):
  [Approve hunk] [Reject hunk] [Edit first] | [Approve all] [Reject all] | [Apply approved] [Cancel]

Hunk states (updated):
  pending:  ! pending
  approved: ✓ approved
  rejected: ✗ rejected
  applied:  → applied (commit {sha_short})
  conflict: ⚠ conflict — file modified
  edited:   ✓ approved (edited)
```

**Add new subsection §7.8.1:**

```markdown
### 7.8.1 Git-Backed Snapshots And Undo

ARC Studio uses git for all snapshot and undo operations.

**Pre-apply check:**
- If workspace is a git repo: proceed normally
- If workspace is NOT a git repo: show warning `Workspace is not a git repository. Undo will not be available.` with actions `[git init] [Continue without undo] [Cancel]`

**Apply behavior:**
- "Apply Approved" creates a git commit
- Commit message: `[ARC Studio] Applied changes from run {run_id}`
- Commit includes only approved hunks
- If all hunks are rejected: `No approved changes to apply.`

**Undo behavior (`/undo`):**
- Finds most recent commit with `[ARC Studio]` prefix
- Runs `git revert --no-edit <sha>`
- Confirmation: `Revert last ARC Studio commit ({sha_short}, {N} files)?`
- If no ARC commits: `No ARC Studio changes to undo.`

**Redo behavior (`/redo`):**
- Finds most recent revert of an ARC Studio commit
- Runs `git revert --no-edit <sha>` (revert of revert)
- If no redo available: `Nothing to redo.`

**Conflict handling:**
- Before apply, attempt dry-run patch per hunk
- If patch fails: mark hunk as `conflict`
- Conflict actions: `[Open for manual merge] [Skip] [Apply remaining]`
- Manual merge opens file with conflict markers in editor

**Concurrent edit detection:**
- Record file mtime when diff is generated
- Before displaying hunk, check current mtime
- If changed: show warning `⚠ {file} was modified after diff generation`
```

### §8.4 Review Flow

**Replace the existing §8.4 with:**

```markdown
### 8.4 Review Flow

Review/Apply opens over canvas at 70% width. Chat shrinks to 30%. Left column lists files/hunks; right column uses Monaco diff editor.

**Header:** changed files list with counts (`3 files, 12 hunks, 8 approved, 2 pending, 2 rejected`)

**Body:** Monaco diff editor with syntax highlighting, line numbers, gutter markers. Per-hunk status badge.

**Footer actions:**
- Primary: `[Apply approved]` (creates git commit)
- Per-hunk: `[Approve hunk] [Reject hunk] [Edit first]`
- Bulk: `[Approve all] [Reject all]`
- Cancel: `[Cancel]`

**Keyboard:** `J/K` next/previous hunk, `A` approve, `R` reject, `E` edit-first, `Ctrl/Cmd+Enter` apply approved, `Esc` close if no pending destructive confirmation.

**Edit First flow:**
1. Click "Edit First" on hunk
2. File opens in Monaco with proposed change applied as unstaged edit
3. User edits and saves
4. Hunk marked "approved (edited)"
5. Cancel edit returns hunk to "pending"

**Conflict state:**
- Hunk shows `⚠ conflict` badge
- Banner: `Cannot apply cleanly — base file was modified.`
- Actions: `[Open for manual merge] [Skip this hunk] [Apply remaining]`

**Concurrent edit warning:**
- Warning banner on hunk: `⚠ {filename} was modified after this diff was generated. Review carefully.`
- Non-blocking, warning tone (`state.warning`)

**Partial apply failure:**
- If some hunks apply and some fail: show summary
- `Applied 8/12 hunks. 4 hunks had conflicts.`
- Actions: `[Review conflicts] [Commit applied] [Rollback all]`

**Review session persistence:**
- Hunk decisions persist across panel close/reopen
- Stored in session state, keyed by `{run_id}:{file}:{hunk_id}`
- Decisions expire after 24 hours

**Error state:** preserves hunk decisions and shows retry.

**Git status:** footer shows git repo status, branch, and uncommitted change count.

**v0.2 reservation:** Inline diffs in editor (Cursor/Windsurf pattern) reserved for v0.2. Checkpoint timeline reserved for v0.2.
```

### §9 DiffHunk Component

**Update DiffHunkProps:**

```ts
interface DiffHunkProps {
  filePath: string;
  hunkId: string;
  status: 'pending' | 'approved' | 'rejected' | 'applied' | 'conflict' | 'edited';
  lines: Array<{ type: 'add' | 'remove' | 'context'; oldLine?: number; newLine?: number; text: string }>;
  isBinary?: boolean;
  staleBase?: boolean;  // true if file was modified after diff generation
  commitSha?: string;   // set when status is 'applied'
  onApprove: (hunkId: string) => void;
  onReject: (hunkId: string) => void;
  onEditFirst: (hunkId: string) => void;
  onSkip?: (hunkId: string) => void;      // for conflict state
  onOpenMerge?: (hunkId: string) => void;  // for conflict state
}
```

### §10.3 Confirmations

**Update rollback confirmation:**

| Before | After |
|---|---|
| `Rollback last applied change? This edits files back to the previous snapshot.` | `Revert last ARC Studio commit ({sha_short}, {N} files)? This creates a git revert commit.` |

**Add new confirmations:**

| Action | Confirmation |
|---|---|
| Approve All | `Approve all {N} pending hunks?` |
| Reject All | `Reject all {N} pending hunks?` |
| Apply (no git) | `Workspace is not a git repository. Undo will not be available. Continue?` |
| Partial apply | `Applied {M}/{N} hunks. {R} hunks had conflicts. Commit applied hunks?` |

### §10.4 Help Text

**Add to Workflow section:**

```text
  /undo     Revert last ARC Studio applied changes (git revert)
  /redo     Re-apply last undone ARC Studio changes
```

### §15 States And Edge Cases

**Update Review row:**

| Surface | Empty | Loading | Populated | Error | Offline | Awaiting approval | Applied/Rolled back | Conflict |
|---|---|---|---|---|---|---|---|---|
| Review | no changes | preparing diff | hunks | apply error | disabled apply | pending hunk | applied badge + commit sha | conflict markers, merge actions |

**Add new states:**

| State | Trigger | Display | Recovery |
|---|---|---|---|
| `no-git-warning` | Workspace not a git repo | `⚠ not a git repo — undo unavailable` | `[git init] [Continue]` |
| `concurrent-edit` | File mtime changed after diff generation | `⚠ file modified after diff` | Review carefully |
| `conflict` | Patch dry-run failed | `⚠ conflict — cannot apply` | Manual merge / skip |
| `partial-apply` | Some hunks applied, some failed | `Applied M/N hunks` | Review conflicts / commit / rollback |
| `edited` | User edited hunk via Edit First | `✓ approved (edited)` | Apply normally |

### §9 Card Component

**Add diff preview to HITL card variant:**

```ts
interface CardProps {
  variant: 'workflow' | 'run' | 'hitl' | 'paid-call' | 'message' | 'empty';
  tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info';
  title?: string;
  actions?: React.ReactNode;
  children?: React.ReactNode;
  diffPreview?: {  // new: for HITL cards with file changes
    files: Array<{ path: string; addedLines: number; removedLines: number }>;
    sampleLines?: string[];  // first 5 lines of diff
    onReviewFull: () => void;
  };
}
```

---

## Acceptance Criteria

### v0.1 Must-Have

- [ ] `/diff` command opens review panel with file list, hunk display, and action bar
- [ ] Per-hunk approve/reject/edit-first actions work
- [ ] "Apply Approved" creates a git commit with message `[ARC Studio] Applied changes from run {run_id}`
- [ ] "Approve All" and "Reject All" bulk actions work
- [ ] `/undo` reverts last ARC Studio commit via `git revert`
- [ ] `/redo` reverts the last undo via `git revert`
- [ ] Git repo detection works; non-git workspaces show warning before apply
- [ ] Conflict detection works: hunks that cannot be cleanly applied show conflict state
- [ ] Concurrent edit detection works: files modified after diff generation show warning
- [ ] Edit First opens file in editor with proposed change, saves edited content as approved
- [ ] Review session persistence: hunk decisions survive panel close/reopen
- [ ] Partial apply failure: shows which hunks succeeded/failed, offers retry/skip/rollback
- [ ] Binary files are detected and shown as "binary changed" without diff preview
- [ ] Large diffs (>100 hunks) show summary with expand/collapse per file
- [ ] Keyboard shortcuts work: J/K, A, R, E, Ctrl/Cmd+Enter, Esc
- [ ] Diff colour tokens render correctly (dark/light themes)
- [ ] 80-column CLI mode degrades gracefully
- [ ] All confirmation dialogs use exact copy from §10.3
- [ ] HITL cards in chat show diff preview with "Review full diff" button

### v0.1 Should-Have

- [ ] Git status line in review footer (branch, uncommitted changes)
- [ ] Commit SHA shown on applied hunks
- [ ] Diff source format documented (unified diff JSON envelope)
- [ ] Review decisions expire after 24 hours (garbage collection)

### v0.2 Targets

- [ ] Inline diffs in editor (Cursor/Windsurf pattern)
- [ ] Checkpoint timeline UI
- [ ] Branch-based isolation (agent works on feature branch)
- [ ] PR-based workflow (GitHub Copilot Workspace pattern)
- [ ] Multi-hunk edit (edit multiple hunks in one editor session)

---

## Reject / Do Not Build

### Rejected: Custom snapshot system (not git)
**Considered**: Building an ARC-managed snapshot system that stores file copies before/after apply.
**Rejected because**: Git already does this perfectly. Every competitor with undo uses git. A custom system would be fragile, lack conflict detection, lack branch management, lack universal tooling, and require significant maintenance. Git commits provide natural audit trail and integrate with all existing developer workflows.

### Rejected: Per-hunk undo after apply
**Considered**: Allowing users to undo individual hunks after they've been applied and committed.
**Rejected because**: This requires complex partial revert logic and creates confusing git history. Per-hunk control is available before apply (approve/reject). After apply, the unit of undo is the commit (batch). If users need per-hunk undo after apply, they can use `git checkout -p` or `git reset -p` directly.

### Rejected: Auto-apply without review in Build mode
**Considered**: In Build mode, automatically applying changes without requiring review (like Aider).
**Rejected because**: ARC's positioning is high-assurance. Explicit review before write is a core design principle. Auto-apply is available in Auto mode with policy-driven approvals, but Build mode should always require explicit review.

### Rejected: Separate rollback panel
**Considered**: A dedicated rollback panel showing undo history and allowing selective reverts.
**Rejected because**: For v0.1, `/undo` and `/redo` commands are sufficient. Git log provides full history. A dedicated rollback panel is v0.2 scope (checkpoint timeline).

### Rejected: Three-way merge for conflicts
**Considered**: Full three-way merge UI for conflict resolution (like VS Code's merge editor).
**Rejected because**: Three-way merge UI is complex and out of scope for v0.1. For conflicts, opening the file with standard conflict markers in the editor is sufficient. Users are developers who understand git conflict resolution.

### Rejected: Non-git fallback snapshots
**Considered**: Storing file copies in `.arc/snapshots/` for non-git workspaces.
**Rejected because**: Adds significant complexity for an edge case. Non-git workspaces are rare in ARC's target audience (agent workflow developers). The warning + `git init` suggestion is sufficient. If a user chooses to continue without git, they accept the risk of no undo.

### Deferred to v0.2: Inline diffs in editor
**Deferred because**: Requires deep Theia/Monaco integration (editor decorations, zone widgets, inline diff rendering). Modal review panel is functional for v0.1. Inline diffs are a significant UX improvement but require dedicated implementation time.

### Deferred to v0.2: Checkpoint timeline
**Deferred because**: Requires snapshot history UI component. Git log provides equivalent functionality for v0.1. A visual checkpoint timeline (like Windsurf's Cascade) is a v0.2 UX enhancement.

### Deferred to v0.3: Branch-based isolation
**Deferred because**: Requires agent to create and work on feature branches, then merge after approval. Useful for high-assurance workflows but adds significant git management complexity. v0.1 applies to working tree directly (with git commit).
