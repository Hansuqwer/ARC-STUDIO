# Phase 34.2 — IDE Battle Tab Implementation Prompt

**Status:** Ready for implementation  
**Phase:** 34.2 — IDE Battle Tab  
**Depends on:** Phase 34 (ARC Battle Mode baseline), Phase 34.1 (Battle run/trace integration)  
**Current Date:** 2026-05-23

## Objective

Implement IDE Battle tab to display battle runs, candidates, votes, outcomes, and ELO leaderboard with honest empty/degraded/present states. No fabricated data - all data must come from the battle store.

## Required Reading (Do This First)

Before starting implementation, read these files to understand the current architecture:

1. **Battle Infrastructure:**
   - `docs/roadmap.md` — R26A section (lines 626-665)
   - `docs/phases.md` — Phase 34, 34.1, 34.2 (lines 1306-1550)
   - `python/src/agent_runtime_cockpit/battle/models.py` — Battle data models
   - `python/src/agent_runtime_cockpit/battle/store.py` — Battle store operations
   - `python/src/agent_runtime_cockpit/battle/runner.py` — Battle execution logic
   - `python/src/agent_runtime_cockpit/cli/battle.py` — CLI commands for data access patterns

2. **Existing Tab Implementations (Use as Reference):**
   - `packages/arc-extension/src/browser/tabs/RunsTab.tsx` — Runs tab implementation
   - `packages/arc-extension/src/browser/tabs/WorkflowsTab.tsx` — Workflows tab
   - `packages/arc-extension/src/browser/tabs/ConfigTab.tsx` — Config tab
   - `packages/arc-extension/src/browser/arc-studio-widget.tsx` — Tab registration

3. **Backend Service Patterns:**
   - `packages/arc-extension/src/node/services/workflow-executor.ts` — CLI bridge pattern
   - `packages/arc-extension/src/node/arc-backend-service.ts` — Service orchestration
   - `packages/arc-extension/src/node/arc-extension-backend-module.ts` — DI bindings

4. **Reusable Components:**
   - `packages/arc-extension/src/browser/components/` — All reusable UI components

## Research Tasks (Use Available Tools)

Use Grep, Glob, and Context7 to gather context before implementing:

### 1. Find Existing Tab Patterns
```bash
# Find all tab implementations
glob "packages/arc-extension/src/browser/tabs/*.tsx"

# Search for tab registration patterns
grep -r "registerTab\|addTab" packages/arc-extension/src/browser/

# Find tab icon usage
grep -r "codicon\|fa-icon" packages/arc-extension/src/browser/tabs/
```

### 2. Find Backend Service Patterns
```bash
# Find CLI bridge patterns
grep -r "executeCommand\|spawn\|exec" packages/arc-extension/src/node/services/

# Find service registration in DI
grep -r "bind.*toSelf\|bind.*to" packages/arc-extension/src/node/arc-extension-backend-module.ts

# Find protocol type definitions
glob "packages/arc-extension/src/common/*-protocol.ts"
```

### 3. Find Reusable Components
```bash
# Find table components
grep -r "Table\|DataGrid" packages/arc-extension/src/browser/components/

# Find status badge components
grep -r "Badge\|Status" packages/arc-extension/src/browser/components/

# Find empty state components
grep -r "EmptyState\|NoData" packages/arc-extension/src/browser/components/
```

### 4. Research React/Theia Patterns (If Needed)
If you need additional context on React patterns or Theia APIs, use Context7:

```typescript
// Example: Research Theia widget APIs
// Use context7_resolve-library-id to find Theia docs
// Use context7_query-docs to get specific API documentation
```

## Implementation Plan

### Step 1: Create Battle Protocol Types

**File:** `packages/arc-extension/src/common/battle-protocol.ts`

Create TypeScript interfaces that mirror the Python battle models:

```typescript
export interface BattleRun {
    id: string;
    prompt: string;
    workers: number;
    topology: 'flat';
    consensus_protocol: 'majority' | 'quorum';
    runtime_mode: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    created_at: string;
    started_at?: string;
    completed_at?: string;
    consensus_escrow: boolean;
    require_hitl: boolean;
    error_detail?: string;
}

export interface BattleCandidate {
    id: string;
    battle_id: string;
    worker_id: string;
    model_id: string;
    output: string;
    created_at: string;
}

export interface BattleVote {
    id: string;
    battle_id: string;
    candidate_id: string;
    voter: string;
    voter_type: 'human' | 'model';
    approved: boolean;
    reasoning?: string;
    created_at: string;
}

export interface BattleOutcome {
    id: string;
    battle_id: string;
    winner_candidate_id?: string;
    consensus_reached: boolean;
    consensus_result: any;
    completed_at: string;
}

export interface EloRating {
    model_id: string;
    rating: number;
    games_played: number;
    wins: number;
    losses: number;
    draws: number;
    last_updated: string;
}

export interface BattleDetails {
    battle: BattleRun;
    candidates: BattleCandidate[];
    votes: BattleVote[];
    outcome?: BattleOutcome;
}
```

### Step 2: Create Battle Backend Service

**File:** `packages/arc-extension/src/node/services/battle-service.ts`

Create a backend service that bridges to Python CLI commands:

```typescript
import { injectable } from '@theia/core/shared/inversify';
import { spawn } from 'child_process';

@injectable()
export class BattleService {
    
    async listBattles(options?: { status?: string; limit?: number }): Promise<BattleRun[]> {
        // Execute: arc battle list --json [--status <status>] [--limit <limit>]
        // Parse JSON output
        // Return battle runs
    }
    
    async getBattleDetails(battleId: string): Promise<BattleDetails> {
        // Execute: arc battle show <battleId> --json
        // Parse JSON output
        // Return battle details with candidates, votes, outcome
    }
    
    async getLeaderboard(limit?: number): Promise<EloRating[]> {
        // Execute: arc battle leaderboard --json [--limit <limit>]
        // Parse JSON output
        // Return ELO ratings
    }
    
    private async executeCommand(args: string[]): Promise<any> {
        // Use spawn pattern from workflow-executor.ts
        // Handle errors, timeouts, JSON parsing
        // Return parsed result
    }
}
```

**Important:** Follow the existing CLI bridge pattern from `workflow-executor.ts`. Use `spawn` with proper error handling, timeout, and JSON parsing.

### Step 3: Register Service in DI Container

**File:** `packages/arc-extension/src/node/arc-extension-backend-module.ts`

Add BattleService to the DI container:

```typescript
import { BattleService } from './services/battle-service';

// In the bind() method:
bind(BattleService).toSelf().inSingletonScope();
```

### Step 4: Create Battle Tab Component

**File:** `packages/arc-extension/src/browser/tabs/BattleTab.tsx`

Create the main Battle tab component with three sections:

1. **Battle List Section** - List of recent battles
2. **Battle Detail Section** - Selected battle details (candidates, votes, outcome)
3. **Leaderboard Section** - ELO rankings

```typescript
import * as React from 'react';
import { BattleService } from '../../node/services/battle-service';

interface BattleTabProps {
    battleService: BattleService;
}

export const BattleTab: React.FC<BattleTabProps> = ({ battleService }) => {
    const [battles, setBattles] = React.useState<BattleRun[]>([]);
    const [selectedBattle, setSelectedBattle] = React.useState<BattleDetails | null>(null);
    const [leaderboard, setLeaderboard] = React.useState<EloRating[]>([]);
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState<string | null>(null);

    // Load battles on mount
    React.useEffect(() => {
        loadBattles();
        loadLeaderboard();
    }, []);

    const loadBattles = async () => {
        // Call battleService.listBattles()
        // Handle loading, error states
        // Update battles state
    };

    const loadBattleDetails = async (battleId: string) => {
        // Call battleService.getBattleDetails(battleId)
        // Handle loading, error states
        // Update selectedBattle state
    };

    const loadLeaderboard = async () => {
        // Call battleService.getLeaderboard()
        // Handle loading, error states
        // Update leaderboard state
    };

    // Render empty state if no battles
    if (battles.length === 0 && !loading) {
        return <EmptyState message="No battles found. Run 'arc battle run' to create a battle." />;
    }

    return (
        <div className="battle-tab">
            <div className="battle-list">
                {/* Render battle list */}
            </div>
            <div className="battle-details">
                {selectedBattle ? (
                    <>
                        <CandidateList candidates={selectedBattle.candidates} />
                        <VoteTable votes={selectedBattle.votes} />
                        <OutcomePanel outcome={selectedBattle.outcome} />
                    </>
                ) : (
                    <div>Select a battle to view details</div>
                )}
            </div>
            <div className="leaderboard">
                <EloLeaderboard ratings={leaderboard} />
            </div>
        </div>
    );
};
```

**Important:** 
- Use honest empty states when no data exists
- Show degraded states when data is incomplete
- Never fabricate data
- Handle loading and error states properly

### Step 5: Create UI Components

Create reusable components for battle data display:

**File:** `packages/arc-extension/src/browser/components/BattleRunCard.tsx`
```typescript
export const BattleRunCard: React.FC<{ battle: BattleRun; onClick: () => void }> = ({ battle, onClick }) => {
    // Display battle summary: status, workers, consensus, created_at
    // Use status badge for battle status
    // Make clickable to select battle
};
```

**File:** `packages/arc-extension/src/browser/components/CandidateList.tsx`
```typescript
export const CandidateList: React.FC<{ candidates: BattleCandidate[] }> = ({ candidates }) => {
    // Display list of candidates with worker_id, model_id, output preview
    // Use expandable sections for full output
};
```

**File:** `packages/arc-extension/src/browser/components/VoteTable.tsx`
```typescript
export const VoteTable: React.FC<{ votes: BattleVote[] }> = ({ votes }) => {
    // Display table of votes: voter, candidate, approved/rejected, reasoning
    // Use color coding for approved (green) vs rejected (red)
};
```

**File:** `packages/arc-extension/src/browser/components/OutcomePanel.tsx`
```typescript
export const OutcomePanel: React.FC<{ outcome?: BattleOutcome }> = ({ outcome }) => {
    // Display consensus result and winner
    // Show "No consensus reached" if consensus_reached is false
    // Show degraded state if outcome is missing
};
```

**File:** `packages/arc-extension/src/browser/components/EloLeaderboard.tsx`
```typescript
export const EloLeaderboard: React.FC<{ ratings: EloRating[] }> = ({ ratings }) => {
    // Display table of model rankings: rank, model_id, rating, games, W-L-D
    // Sort by rating descending
};
```

### Step 6: Register Battle Tab in Widget

**File:** `packages/arc-extension/src/browser/arc-studio-widget.tsx`

Add Battle tab to the tab bar:

```typescript
import { BattleTab } from './tabs/BattleTab';

// In the render method, add a new tab:
<Tab label="Battle" icon="codicon codicon-symbol-event">
    <BattleTab battleService={this.battleService} />
</Tab>
```

**Important:** Choose an appropriate icon from Codicons or FontAwesome that represents battles/competition.

### Step 7: Add Styling

**File:** `packages/arc-extension/src/browser/style/battle-tab.css`

Add CSS for battle tab layout and components:

```css
.battle-tab {
    display: grid;
    grid-template-columns: 300px 1fr 300px;
    gap: 1rem;
    height: 100%;
    padding: 1rem;
}

.battle-list {
    overflow-y: auto;
}

.battle-details {
    overflow-y: auto;
}

.leaderboard {
    overflow-y: auto;
}

/* Add more specific styles for components */
```

### Step 8: Write Tests

**File:** `packages/arc-extension/src/browser/tabs/__tests__/BattleTab.test.tsx`

Write tests for BattleTab component:

```typescript
describe('BattleTab', () => {
    it('should render empty state when no battles exist', () => {
        // Test empty state rendering
    });

    it('should load and display battles', async () => {
        // Mock battleService.listBattles()
        // Test battle list rendering
    });

    it('should load battle details when battle is selected', async () => {
        // Mock battleService.getBattleDetails()
        // Test detail view rendering
    });

    it('should display leaderboard', async () => {
        // Mock battleService.getLeaderboard()
        // Test leaderboard rendering
    });

    it('should handle loading states', () => {
        // Test loading indicators
    });

    it('should handle error states', () => {
        // Test error messages
    });
});
```

**File:** `packages/arc-extension/src/node/services/__tests__/battle-service.test.ts`

Write tests for BattleService:

```typescript
describe('BattleService', () => {
    it('should list battles via CLI', async () => {
        // Mock spawn to return battle list JSON
        // Test listBattles() method
    });

    it('should get battle details via CLI', async () => {
        // Mock spawn to return battle details JSON
        // Test getBattleDetails() method
    });

    it('should get leaderboard via CLI', async () => {
        // Mock spawn to return leaderboard JSON
        // Test getLeaderboard() method
    });

    it('should handle CLI errors', async () => {
        // Mock spawn to return error
        // Test error handling
    });
});
```

## Verification Commands

After implementation, run these commands to verify everything works:

```bash
# 1. Run TypeScript build
pnpm --filter arc-extension build

# 2. Run tests
pnpm --filter arc-extension test

# 3. Build browser app
pnpm --filter @arc-studio/browser build

# 4. Run e2e tests (if applicable)
pnpm --filter @arc-studio/e2e-tests test

# 5. Run full PR check
bash scripts/check-pr.sh

# 6. Check for banned claims
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md
```

## Constraints and Requirements

### Must Do:
- ✅ Use honest empty states when no battles exist
- ✅ Show degraded states when data is incomplete
- ✅ Never fabricate data - all data from battle store
- ✅ Handle loading and error states properly
- ✅ Follow existing tab patterns (RunsTab, WorkflowsTab)
- ✅ Use existing CLI bridge pattern from workflow-executor
- ✅ Register service in DI container
- ✅ Write tests for components and services
- ✅ Add proper TypeScript types

### Must Not Do:
- ❌ Do not fabricate battle data
- ❌ Do not make provider-backed/live Arena claims
- ❌ Do not implement real-time updates (manual refresh only)
- ❌ Do not implement battle cancellation from IDE (CLI only)
- ❌ Do not add features beyond the phase scope

## Expected Outcome

After completing this phase:

1. **IDE Battle Tab Visible:** Users can see a "Battle" tab in the ARC Studio widget
2. **Battle List:** Tab displays list of recent battles from `.arc/battles.db`
3. **Battle Details:** Clicking a battle shows candidates, votes, and outcome
4. **ELO Leaderboard:** Tab displays model rankings
5. **Empty States:** Honest empty state shown when no battles exist
6. **Tests Pass:** All new tests pass, no regressions
7. **Documentation Updated:** Phase 34.2 status updated to "Baseline Complete"

## Troubleshooting

### If CLI bridge fails:
- Check that `arc battle` commands work from terminal
- Verify spawn arguments match CLI command format
- Check JSON parsing of CLI output
- Add debug logging to see raw CLI output

### If DI injection fails:
- Verify service is bound in `arc-extension-backend-module.ts`
- Check that service is injected in widget constructor
- Ensure service is marked with `@injectable()` decorator

### If tab doesn't appear:
- Check tab registration in `arc-studio-widget.tsx`
- Verify tab icon is valid (codicon or fa-icon)
- Check browser console for React errors

### If data doesn't load:
- Verify battle store has data (run `arc battle list` in terminal)
- Check network/CLI calls in browser dev tools
- Add console.log to service methods to debug
- Verify JSON parsing matches Python CLI output format

## Next Steps After Completion

After Phase 34.2 is complete and verified:

1. Update `docs/phases.md` Phase 34.2 status to "Baseline Complete"
2. Update `docs/roadmap.md` R26A follow-up phases status
3. Commit changes with message: "Implement Phase 34.2: IDE Battle Tab"
4. Move to Phase 34.3 (Battle Replay Determinism) or Phase 34.4 (Persistent HITL Prompt Wiring)

## Questions to Ask Before Starting

If anything is unclear, ask:

1. Which existing tab should I use as the primary reference? (Recommended: RunsTab)
2. Should the battle tab auto-refresh, or require manual refresh? (Manual refresh for baseline)
3. What icon should I use for the battle tab? (Suggest: codicon-symbol-event or codicon-organization)
4. Should I implement filtering/sorting in the battle list? (Defer to polish phase)
5. How should I handle very long candidate outputs? (Truncate with expand/collapse)

---

**Ready to implement?** Start with Step 1 (Create Battle Protocol Types) and work through each step sequentially. Use the research tasks to gather context before implementing each component. Test frequently and verify at each step.
