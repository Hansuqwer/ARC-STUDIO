import { DaemonDiscoveryService } from '../daemon-discovery-service';

describe('DaemonDiscoveryService', () => {
    const originalEnv = process.env.ARC_PYTHON_DAEMON_URL;
    const mockFetch = jest.fn();

    beforeEach(() => {
        jest.clearAllMocks();
        delete process.env.ARC_PYTHON_DAEMON_URL;
        (global as unknown as Record<string, unknown>).fetch = mockFetch;
    });

    const healthyResponse = {
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue({
            status: 'healthy',
            version: '0.1.0-alpha',
            uptime_seconds: 1,
            arc: true,
        }),
    };

    afterAll(() => {
        if (originalEnv === undefined) {
            delete process.env.ARC_PYTHON_DAEMON_URL;
        } else {
            process.env.ARC_PYTHON_DAEMON_URL = originalEnv;
        }
    });

    it('returns configured daemon URL from environment', () => {
        process.env.ARC_PYTHON_DAEMON_URL = 'http://127.0.0.1:8888';
        const service = new DaemonDiscoveryService();

        expect(service.getConfiguredUrl()).toBe('http://127.0.0.1:8888');
    });

    it('ignores non-loopback configured daemon URLs', () => {
        process.env.ARC_PYTHON_DAEMON_URL = 'https://example.com:8888';
        const service = new DaemonDiscoveryService();

        expect(service.getConfiguredUrl()).toBeUndefined();
    });

    it('ignores configured daemon URLs with credentials', () => {
        process.env.ARC_PYTHON_DAEMON_URL = 'http://user:pass@127.0.0.1:8888';
        const service = new DaemonDiscoveryService();

        expect(service.getConfiguredUrl()).toBeUndefined();
    });

    it('trims trailing slash when resolving configured URL', async () => {
        process.env.ARC_PYTHON_DAEMON_URL = 'http://127.0.0.1:8888/';
        const service = new DaemonDiscoveryService();

        await expect(service.resolveDaemonBaseUrl()).resolves.toBe('http://127.0.0.1:8888');
        expect(mockFetch).not.toHaveBeenCalled();
    });

    it('probes only loopback health endpoint for default discovery', async () => {
        mockFetch.mockResolvedValue(healthyResponse);
        const service = new DaemonDiscoveryService();

        await expect(service.discoverDefaultUrl()).resolves.toBe('http://127.0.0.1:7777');
        expect(mockFetch).toHaveBeenCalledTimes(1);
        const url = mockFetch.mock.calls[0][0] as URL;
        expect(url.hostname).toBe('127.0.0.1');
        expect(url.port).toBe('7777');
        expect(url.pathname).toBe('/health');
    });

    it('returns undefined when default daemon is not healthy', async () => {
        mockFetch.mockResolvedValue({ ok: false, status: 502, json: jest.fn() });
        const service = new DaemonDiscoveryService();

        await expect(service.discoverDefaultUrl()).resolves.toBeUndefined();
    });

    it('rejects health responses that expose run inventory', async () => {
        mockFetch.mockResolvedValue({
            ok: true,
            status: 200,
            json: jest.fn().mockResolvedValue({
                status: 'healthy',
                version: '0.1.0-alpha',
                uptime_seconds: 1,
                active_runs: 2,
                arc: true,
            }),
        });
        const service = new DaemonDiscoveryService();

        await expect(service.discoverDefaultUrl()).resolves.toBeUndefined();
    });

    it('caches resolved default URL', async () => {
        mockFetch.mockResolvedValue(healthyResponse);
        const service = new DaemonDiscoveryService();

        await expect(service.resolveDaemonBaseUrl()).resolves.toBe('http://127.0.0.1:7777');
        await expect(service.resolveDaemonBaseUrl()).resolves.toBe('http://127.0.0.1:7777');
        expect(mockFetch).toHaveBeenCalledTimes(1);
    });
});
