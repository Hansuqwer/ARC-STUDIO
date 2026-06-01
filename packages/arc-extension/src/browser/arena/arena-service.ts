import { injectable } from '@theia/core/shared/inversify';

export interface ArenaCompletionItem {
    completionId: string;
    prompt?: string;
    completion: string;
    model: string;
}

export interface ArenaPair {
    pairId: string;
    completionItems: ArenaCompletionItem[];
}

export interface ArenaRequestContext {
    prefix: string;
    suffix: string;
    language?: string;
}

const DEFAULT_USER_ID = 'arc-theia-inline';
const DEFAULT_PRIVACY = 'Private';
const CLIENT_VERSION = 'arc-theia-studio-p4';

@injectable()
export class ArenaService {
    protected activePair: ArenaPair | undefined;
    protected activeIndex = 0;

    async createPair(serverUrl: string, context: ArenaRequestContext): Promise<ArenaPair> {
        const response = await fetch(`${serverUrl.replace(/\/$/, '')}/create_pair`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prefix: context.prefix,
                suffix: context.suffix,
                userId: DEFAULT_USER_ID,
                privacy: DEFAULT_PRIVACY,
                max_lines: 8,
                modelTags: context.language ? [context.language] : [],
            }),
        });
        if (!response.ok) {
            throw new Error(`arena create_pair failed: ${response.status}`);
        }
        const pair = await response.json() as ArenaPair;
        if (!pair.pairId || !Array.isArray(pair.completionItems) || pair.completionItems.length === 0) {
            throw new Error('arena create_pair returned invalid payload');
        }
        this.activePair = pair;
        this.activeIndex = 0;
        return pair;
    }

    currentCompletion(): ArenaCompletionItem | undefined {
        return this.activePair?.completionItems[this.activeIndex];
    }

    currentPair(): ArenaPair | undefined {
        return this.activePair;
    }

    selectNext(): number {
        return this.selectDelta(1);
    }

    selectPrevious(): number {
        return this.selectDelta(-1);
    }

    async recordAccepted(serverUrl: string): Promise<void> {
        const pair = this.activePair;
        if (!pair || pair.completionItems.length < 2) {
            return;
        }
        await fetch(`${serverUrl.replace(/\/$/, '')}/add_completion_outcome`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pairId: pair.pairId,
                userId: DEFAULT_USER_ID,
                acceptedIndex: this.activeIndex,
                version: CLIENT_VERSION,
                privacy: DEFAULT_PRIVACY,
                completionItems: pair.completionItems.map(item => ({
                    completionId: item.completionId,
                    prompt: item.prompt ?? '',
                    completion: item.completion,
                    model: item.model,
                })),
            }),
        });
    }

    protected selectDelta(delta: number): number {
        const count = this.activePair?.completionItems.length ?? 0;
        if (count === 0) {
            this.activeIndex = 0;
            return this.activeIndex;
        }
        this.activeIndex = (this.activeIndex + delta + count) % count;
        return this.activeIndex;
    }
}
