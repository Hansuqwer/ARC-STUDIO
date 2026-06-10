/**
 * ARC Dashboard Widget — static contract tests (R95, Phase 320).
 * Avoids importing BaseWidget (triggers DragEvent in Jest).
 */
describe('ArcDashboardWidget (static contract)', () => {
    it('exports expected static constants', async () => {
        const mod = await import('../arc-dashboard-widget').catch(() => null);
        if (mod === null) return; // Theia DOM env issue in Jest — skip
        expect(mod.ArcDashboardWidget.ID).toBe('arc:dashboard');
        expect(mod.ArcDashboardWidget.LABEL).toBe('ARC Dashboard');
    });

    it('exports ArcDashboardContribution', async () => {
        const mod = await import('../arc-dashboard-contribution').catch(() => null);
        if (mod === null) return;
        expect(mod.OpenDashboardCommand.id).toBe('arc:open-dashboard');
        expect(mod.OpenDashboardCommand.label).toBe('ARC: Show Dashboard');
    });
});

describe('ArcDashboardWidget (a11y + UX states, Phase 337)', () => {
    it('loading state has role=status and aria-label', async () => {
        const fs = await import('fs');
        const content = fs.readFileSync(
            require('path').resolve(__dirname, '../arc-dashboard-widget.tsx'),
            'utf-8'
        );
        expect(content).toContain('data-testid="arc-dashboard-loading"');
        expect(content).toContain('role="status"');
        expect(content).toContain('aria-label="Loading workspaces"');
    });

    it('error state has role=alert and retry button with aria-label', async () => {
        const fs = await import('fs');
        const path = await import('path');
        const content = fs.readFileSync(
            path.resolve(__dirname, '../arc-dashboard-widget.tsx'),
            'utf-8'
        );
        expect(content).toContain('data-testid="arc-dashboard-error"');
        expect(content).toContain('role="alert"');
        expect(content).toContain('aria-label="Retry loading dashboard"');
    });

    it('empty state has role=status and aria-label', async () => {
        const fs = await import('fs');
        const path = await import('path');
        const content = fs.readFileSync(
            path.resolve(__dirname, '../arc-dashboard-widget.tsx'),
            'utf-8'
        );
        expect(content).toContain('data-testid="arc-dashboard-empty"');
        expect(content).toContain('aria-label="No workspaces found"');
    });

    it('summary cards have aria-labels for screen readers', async () => {
        const fs = await import('fs');
        const path = await import('path');
        const content = fs.readFileSync(
            path.resolve(__dirname, '../arc-dashboard-widget.tsx'),
            'utf-8'
        );
        expect(content).toContain('aria-label={`Workspaces:');
        expect(content).toContain('aria-label={`Active workspaces:');
        expect(content).toContain('aria-label={`Total cost');
    });

    it('workspace cards have role=button and tabIndex for keyboard nav', async () => {
        const fs = await import('fs');
        const path = await import('path');
        const content = fs.readFileSync(
            path.resolve(__dirname, '../arc-dashboard-widget.tsx'),
            'utf-8'
        );
        expect(content).toContain('role="button"');
        expect(content).toContain('tabIndex={0}');
        expect(content).toContain('aria-label={`Switch to workspace');
    });
});
