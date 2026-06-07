/**
 * Tests for the useAsyncState hook (CR-029).
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useAsyncState } from './useAsyncState';

describe('useAsyncState', () => {
    it('starts loading and resolves to data on success', async () => {
        const { result } = renderHook(() => useAsyncState(async () => 'ok', []));

        // immediate (default) => loading begins true
        expect(result.current.loading).toBe(true);
        expect(result.current.data).toBeNull();
        expect(result.current.error).toBeNull();

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.data).toBe('ok');
        expect(result.current.error).toBeNull();
    });

    it('captures the error message and clears loading on failure', async () => {
        const { result } = renderHook(() =>
            useAsyncState(async () => {
                throw new Error('boom');
            }, []),
        );

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.error).toBe('boom');
        expect(result.current.data).toBeNull();
    });

    it('uses the fallback errorMessage when the thrown value has no message', async () => {
        const { result } = renderHook(() =>
            useAsyncState(
                async () => {
                    // eslint-disable-next-line no-throw-literal
                    throw 'no-message';
                },
                [],
                { errorMessage: 'Failed to load' },
            ),
        );

        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.error).toBe('Failed to load');
    });

    it('does not fetch on mount when immediate is false', async () => {
        const fetcher = jest.fn(async () => 'lazy');
        const { result } = renderHook(() => useAsyncState(fetcher, [], { immediate: false }));

        expect(result.current.loading).toBe(false);
        expect(fetcher).not.toHaveBeenCalled();

        await act(async () => {
            await result.current.reload();
        });
        expect(fetcher).toHaveBeenCalledTimes(1);
        expect(result.current.data).toBe('lazy');
    });

    it('reload clears a prior error before refetching', async () => {
        let shouldFail = true;
        const { result } = renderHook(() =>
            useAsyncState(async () => {
                if (shouldFail) {
                    throw new Error('first');
                }
                return 'recovered';
            }, []),
        );

        await waitFor(() => expect(result.current.error).toBe('first'));

        shouldFail = false;
        await act(async () => {
            await result.current.reload();
        });
        expect(result.current.error).toBeNull();
        expect(result.current.data).toBe('recovered');
    });

    it('setData imperatively replaces the value', async () => {
        const { result } = renderHook(() => useAsyncState(async () => 1, []));
        await waitFor(() => expect(result.current.data).toBe(1));

        act(() => result.current.setData(42));
        expect(result.current.data).toBe(42);
    });
});
