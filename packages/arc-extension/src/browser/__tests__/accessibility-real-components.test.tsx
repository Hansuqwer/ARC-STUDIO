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
});
