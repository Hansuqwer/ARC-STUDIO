import { useState, useCallback, useEffect, DependencyList } from 'react';

/**
 * State returned by {@link useAsyncState}.
 */
export interface AsyncState<T> {
    /** Latest successful result, or `null` before the first success. */
    data: T | null;
    /** True while a fetch is in flight. */
    loading: boolean;
    /** Error message from the most recent failed fetch, or `null`. */
    error: string | null;
    /** Re-run the fetcher (clears the previous error first). */
    reload: () => Promise<void>;
    /** Imperatively replace the data (e.g. after a local mutation). */
    setData: (value: T | null) => void;
}

export interface UseAsyncStateOptions {
    /** Run the fetcher on mount. Defaults to `true`. */
    immediate?: boolean;
    /** Fallback message when the thrown error has no `.message`. */
    errorMessage?: string;
}

/**
 * Standard data / loading / error async-fetch state for IDE tabs.
 *
 * Replaces the hand-rolled `useState` triple + `load` callback + `useEffect`
 * pattern duplicated across tabs with a single tested helper. Behavior matches
 * that pattern exactly: `loading` starts `true` when `immediate` is set, every
 * reload clears the error before fetching, and `loading` is always cleared in a
 * `finally` so the spinner never sticks on failure.
 *
 * @param fetcher async function producing the data
 * @param deps dependency list controlling when `reload` is recreated (mirrors
 *   the deps you would pass to `useCallback`)
 * @param options `immediate` (fetch on mount) and `errorMessage` (fallback)
 */
export function useAsyncState<T>(
    fetcher: () => Promise<T>,
    deps: DependencyList = [],
    options: UseAsyncStateOptions = {},
): AsyncState<T> {
    const { immediate = true, errorMessage = 'Operation failed' } = options;
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState<boolean>(immediate);
    const [error, setError] = useState<string | null>(null);

    const reload = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await fetcher();
            setData(result);
        } catch (err: any) {
            setError(err?.message || errorMessage);
        } finally {
            setLoading(false);
        }
        // fetcher identity is governed by the caller-supplied deps, mirroring useCallback.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, deps);

    useEffect(() => {
        if (immediate) {
            void reload();
        }
    }, [reload, immediate]);

    return { data, loading, error, reload, setData };
}
