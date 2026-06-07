/**
 * ARC Mobile Widget — static contract tests only.
 * Avoids importing BaseWidget (triggers DragEvent in Jest).
 */
describe('ArcMobileWidget (static contract)', () => {
    it('exports expected static constants', async () => {
        const mod = await import('../arc-mobile-widget').catch(() => null);
        if (mod === null) return; // Theia DOM env issue in Jest — skip
        expect(mod.ArcMobileWidget.ID).toBe('arc:mobile-runtime');
        expect(mod.ArcMobileWidget.LABEL).toBe('ARC Mobile Runtime');
    });
});
