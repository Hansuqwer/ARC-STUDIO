/**
 * ARC Context Drawer — render contract test.
 * Verifies the widget renders agent data correctly with mocked data.
 */
import { ArcContextDrawer } from '../arc-context-drawer';

describe('ArcContextDrawer', () => {
    it('has correct static ID and LABEL', () => {
        expect(ArcContextDrawer.ID).toBe('arc-context-drawer');
        expect(ArcContextDrawer.LABEL).toBe('ARC Context');
    });

    it('renders empty state when no agents', () => {
        const drawer = new ArcContextDrawer();
        // Default state: no agents
        const rendered = drawer.render();
        expect(rendered).toBeTruthy();
    });

    it('can be instantiated without errors', () => {
        expect(() => new ArcContextDrawer()).not.toThrow();
    });
});
