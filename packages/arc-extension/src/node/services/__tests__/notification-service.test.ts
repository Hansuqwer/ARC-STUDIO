/**
 * Tests for NotificationBackendService.
 */

import { NotificationBackendService } from '../notification-service';

describe('NotificationBackendService', () => {
    let service: NotificationBackendService;

    beforeEach(() => {
        service = new NotificationBackendService();
    });

    it('returns counts on error gracefully', async () => {
        const counts = await service.getCounts();
        expect(counts).toHaveProperty('hitl');
        expect(counts).toHaveProperty('runFailures');
        expect(counts).toHaveProperty('auditAlerts');
    });

    it('initializes with zero counts', () => {
        expect(service.hitl).toBe(0);
        expect(service.runFailures).toBe(0);
        expect(service.auditAlerts).toBe(0);
    });

    it('handles empty output gracefully', async () => {
        // Mock the internal exec to return empty arrays
        const originalExec = (service as any).execCli;
        (service as any).execCli = async () => '[]';
        const counts = await service.getCounts();
        expect(counts.hitl).toBe(0);
        expect(counts.runFailures).toBe(0);
        (service as any).execCli = originalExec;
    });
});
