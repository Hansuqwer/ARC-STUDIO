/**
 * Real-component accessibility tests (B2P-03a).
 *
 * Unlike accessibility.test.tsx (which renders mock markup), these render the ACTUAL tab
 * components with a stub ArcService and run jest-axe over the real output. Color-contrast is
 * disabled because jsdom does no layout/painting (verified in-browser instead) — every other
 * structural WCAG rule is enforced.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import '@testing-library/jest-dom';

import { TestBenchTab } from '../tabs/TestBenchTab';
import { McpWorkbenchTab } from '../tabs/McpWorkbenchTab';
import { AssuranceTab } from '../tabs/AssuranceTab';
import { BattleTab } from '../tabs/BattleTab';
import { CiGuardrailsTab } from '../tabs/CiGuardrailsTab';
import { CommandCentreTab } from '../tabs/CommandCentreTab';
import { EditPlansTab } from '../tabs/EditPlansTab';
import { RunsTab } from '../tabs/RunsTab';
import { SwarmGraphInsightTab } from '../tabs/SwarmGraphInsightTab';
import type { ArcService } from '../../common/arc-protocol';

const AXE_OPTS = { rules: { 'color-contrast': { enabled: false } } };

function stubService(): ArcService {
    return {
        detectTestbench: jest.fn().mockResolvedValue({
            workspace: '/ws',
            count: 1,
            detected: [{ command: 'pytest', source: 'pyproject', confidence: 'high', runner: 'pytest' }],
        }),
        runTestbench: jest.fn().mockResolvedValue({ command: 'pytest', allowed: true, exitCode: 0 }),
        getMcpWorkbenchStatus: jest.fn().mockResolvedValue({
            workspace: '/ws',
            serverCreatable: true,
            tools: ['echo'],
            resources: [],
            trust: { level: 'trusted' },
            diagnostic: 'ok',
        }),
        getMcpDecisions: jest.fn().mockResolvedValue({ decisions: [] }),
        listPendingHitlPrompts: jest.fn().mockResolvedValue([]),
        listBattles: jest.fn().mockResolvedValue([]),
        getCiCheckStatus: jest.fn().mockResolvedValue({ private: false, workspace: '/ws', checks: {}, overall: 'skip' }),
        listChatSessions: jest.fn().mockResolvedValue([]),
        listEditPlans: jest.fn().mockResolvedValue({ plans: [], count: 0 }),
        getTraces: jest.fn().mockResolvedValue([]),
    } as unknown as ArcService;
}

describe('Real-component a11y (B2P-03a)', () => {
    it('TestBenchTab (real) has no axe violations once detections load', async () => {
        const { container } = render(<TestBenchTab arcService={stubService()} />);
        await screen.findByText(/Detected/);
        expect(await axe(container, AXE_OPTS)).toHaveNoViolations();
    });

    it('McpWorkbenchTab (real) has no axe violations once status loads', async () => {
        const { container } = render(<McpWorkbenchTab arcService={stubService()} />);
        await waitFor(() => expect(screen.queryByText(/Detecting|Loading/i)).not.toBeInTheDocument());
        expect(await axe(container, AXE_OPTS)).toHaveNoViolations();
    });

    // Remaining tabs rendered as REAL components with an empty-but-valid stub; axe their settled
    // (empty/populated) state. Covers the rest of the tab surface for B2P-03b.
    const REMAINING: Array<[string, React.ComponentType<{ arcService: ArcService }>]> = [
        ['AssuranceTab', AssuranceTab as React.ComponentType<{ arcService: ArcService }>],
        ['BattleTab', BattleTab as React.ComponentType<{ arcService: ArcService }>],
        ['CiGuardrailsTab', CiGuardrailsTab as React.ComponentType<{ arcService: ArcService }>],
        ['CommandCentreTab', CommandCentreTab as React.ComponentType<{ arcService: ArcService }>],
        ['EditPlansTab', EditPlansTab as React.ComponentType<{ arcService: ArcService }>],
        ['RunsTab', RunsTab as React.ComponentType<{ arcService: ArcService }>],
        ['SwarmGraphInsightTab', SwarmGraphInsightTab as React.ComponentType<{ arcService: ArcService }>],
    ];

    it.each(REMAINING)('%s (real) has no axe violations once settled', async (_name, Component) => {
        const { container } = render(<Component arcService={stubService()} />);
        await waitFor(() => expect(screen.queryByText(/Loading|Detecting/i)).not.toBeInTheDocument());
        expect(await axe(container, AXE_OPTS)).toHaveNoViolations();
    });
});
