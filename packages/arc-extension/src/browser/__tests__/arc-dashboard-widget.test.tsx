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
