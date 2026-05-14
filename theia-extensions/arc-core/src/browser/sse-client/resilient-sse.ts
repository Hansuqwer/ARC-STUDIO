/**
 * Resilient SSE client with exponential backoff and message deduplication.
 */
export interface SSEOptions {
    url: string;
    onEvent: (event: { id?: string; data: unknown }) => void;
    onError?: (err: Error, attempt: number) => void;
    maxBackoffMs?: number;
}

export class ResilientSSEClient {
    private es?: EventSource;
    private lastEventId?: string;
    private attempt = 0;
    private stopped = false;

    constructor(private readonly opts: SSEOptions) {}

    start(): void {
        this.stopped = false;
        this.connect();
    }

    stop(): void {
        this.stopped = true;
        this.es?.close();
    }

    private connect(): void {
        const sep = this.opts.url.includes('?') ? '&' : '?';
        const url = this.lastEventId
            ? `${this.opts.url}${sep}lastEventId=${encodeURIComponent(this.lastEventId)}`
            : this.opts.url;

        const es = new EventSource(url, { withCredentials: false } as EventSourceInit);
        this.es = es;

        es.onmessage = ev => {
            if (ev.lastEventId) {
                this.lastEventId = ev.lastEventId;
            }
            try {
                const data = ev.data ? JSON.parse(ev.data) : null;
                this.opts.onEvent({ id: ev.lastEventId, data });
            } catch (err) {
                this.opts.onError?.(err as Error, this.attempt);
            }
            this.attempt = 0;
        };

        es.onerror = () => {
            es.close();
            if (this.stopped) {
                return;
            }
            this.attempt += 1;
            const backoff = Math.min(
                (this.opts.maxBackoffMs ?? 30_000),
                250 * 2 ** Math.min(this.attempt, 8),
            );
            this.opts.onError?.(new Error(`SSE disconnected (attempt ${this.attempt})`), this.attempt);
            setTimeout(() => this.connect(), backoff);
        };
    }
}
