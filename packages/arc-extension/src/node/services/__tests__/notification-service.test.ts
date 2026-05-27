/**
 * Tests for NotificationBackendService.
 */

import { NotificationBackendService } from '../notification-service';
import { spawn } from 'child_process';

jest.mock('child_process', () => ({
    spawn: jest.fn(),
}));

describe('NotificationBackendService', () => {
    let service: NotificationBackendService;

    beforeEach(() => {
        jest.resetAllMocks();
        service = new NotificationBackendService();
    });

    it('returns counts on error gracefully', async () => {
        (spawn as unknown as jest.Mock).mockImplementation(() => ({
            stdout: { on: jest.fn() },
            on: (event: string, cb: Function) => event === 'error' && cb(new Error('missing arc')),
            kill: jest.fn(),
        }));
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

    it('uses argv-only spawn for event summary', async () => {
        (spawn as unknown as jest.Mock).mockImplementation(() => ({
            stdout: { on: (event: string, cb: Function) => event === 'data' && cb(Buffer.from('{"data":{"hitl":2,"runFailures":1,"auditAlerts":1,"source":"local_event_log_recent","protocol":"sse"}}')) },
            on: (event: string, cb: Function) => event === 'close' && cb(0),
            kill: jest.fn(),
        }));
        const counts = await service.getCounts();
        expect(spawn).toHaveBeenCalledWith('arc', ['events', 'summary', '--json'], { shell: false });
        expect(counts.hitl).toBe(2);
        expect(counts.runFailures).toBe(1);
        expect(counts.auditAlerts).toBe(1);
        expect(counts.protocol).toBe('sse');
    });
});
