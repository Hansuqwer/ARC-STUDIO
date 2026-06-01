import { ArenaService } from '../arena-service';

describe('ArenaService', () => {
    const originalFetch = global.fetch;

    afterEach(() => {
        global.fetch = originalFetch;
        jest.restoreAllMocks();
    });

    it('creates a pair against the self-hosted arena endpoint', async () => {
        const fetchMock = jest.fn().mockResolvedValue({
            ok: true,
            json: async () => ({
                pairId: 'pair-1',
                completionItems: [
                    { completionId: 'c1', completion: 'alpha', model: 'm1' },
                    { completionId: 'c2', completion: 'beta', model: 'm2' },
                ],
            }),
        });
        global.fetch = fetchMock as any;

        const service = new ArenaService();
        const pair = await service.createPair('http://localhost:8080/', {
            prefix: 'const x = ',
            suffix: ';',
            language: 'typescript',
        });

        expect(pair.pairId).toBe('pair-1');
        expect(fetchMock).toHaveBeenCalledWith('http://localhost:8080/create_pair', expect.objectContaining({ method: 'POST' }));
        const body = JSON.parse(fetchMock.mock.calls[0][1].body);
        expect(body).toMatchObject({ prefix: 'const x = ', suffix: ';', userId: 'arc-theia-inline', privacy: 'Private' });
        expect(body.modelTags).toEqual(['typescript']);
    });

    it('cycles active completion without claiming simultaneous ghost text', async () => {
        global.fetch = jest.fn().mockResolvedValue({
            ok: true,
            json: async () => ({
                pairId: 'pair-1',
                completionItems: [
                    { completionId: 'c1', completion: 'alpha', model: 'm1' },
                    { completionId: 'c2', completion: 'beta', model: 'm2' },
                ],
            }),
        }) as any;

        const service = new ArenaService();
        await service.createPair('http://localhost:8080', { prefix: '', suffix: '' });

        expect(service.currentCompletion()?.completion).toBe('alpha');
        expect(service.selectNext()).toBe(1);
        expect(service.currentCompletion()?.completion).toBe('beta');
        expect(service.selectPrevious()).toBe(0);
        expect(service.currentCompletion()?.completion).toBe('alpha');
    });

    it('records accepted completion outcome', async () => {
        const fetchMock = jest.fn()
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    pairId: 'pair-1',
                    completionItems: [
                        { completionId: 'c1', prompt: 'p1', completion: 'alpha', model: 'm1' },
                        { completionId: 'c2', prompt: 'p2', completion: 'beta', model: 'm2' },
                    ],
                }),
            })
            .mockResolvedValueOnce({ ok: true });
        global.fetch = fetchMock as any;

        const service = new ArenaService();
        await service.createPair('http://localhost:8080', { prefix: '', suffix: '' });
        service.selectNext();
        await service.recordAccepted('http://localhost:8080');

        expect(fetchMock).toHaveBeenLastCalledWith('http://localhost:8080/add_completion_outcome', expect.objectContaining({ method: 'PUT' }));
        const body = JSON.parse(fetchMock.mock.calls[1][1].body);
        expect(body).toMatchObject({ pairId: 'pair-1', acceptedIndex: 1, privacy: 'Private' });
        expect(body.completionItems).toHaveLength(2);
    });
});
