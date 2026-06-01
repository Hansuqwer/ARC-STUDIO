import { inject, injectable } from '@theia/core/shared/inversify';
import * as monaco from '@theia/monaco-editor-core';
import { PreferenceService } from '@theia/core/lib/common/preferences';
import { ArenaService } from './arena-service';

const MAX_CONTEXT_CHARS = 16_000;

@injectable()
export class ArenaInlineCompletionProvider {
    @inject(ArenaService)
    protected readonly arena!: ArenaService;

    @inject(PreferenceService)
    protected readonly preferences!: PreferenceService;

    provideInlineCompletions(model: monaco.editor.ITextModel, position: monaco.Position): Promise<monaco.languages.InlineCompletions<any>> {
        return this.provide(model, position);
    }

    disposeInlineCompletions(): void {
        // Monaco calls this for cleanup; ARC keeps no disposable item state here.
    }

    protected async provide(model: monaco.editor.ITextModel, position: monaco.Position): Promise<monaco.languages.InlineCompletions<any>> {
        const enabled = this.preferences.get<boolean>('arc.arena.inlineCompletion.enabled', false);
        const serverUrl = this.preferences.get<string>('arc.arena.serverUrl', '');
        if (!enabled || !serverUrl) {
            return { items: [] };
        }

        const context = this.contextFor(model, position);
        const pair = await this.arena.createPair(serverUrl, {
            ...context,
            language: model.getLanguageId(),
        });
        const item = pair.completionItems[0];
        if (!item?.completion) {
            return { items: [] };
        }

        return {
            items: [{
                insertText: item.completion,
                range: new monaco.Range(position.lineNumber, position.column, position.lineNumber, position.column),
                command: {
                    id: 'arc.arena.acceptInlineCompletion',
                    title: 'ARC Arena: Record Inline Acceptance',
                },
            }],
        };
    }

    protected contextFor(model: monaco.editor.ITextModel, position: monaco.Position): { prefix: string; suffix: string } {
        const value = model.getValue();
        const offset = model.getOffsetAt(position);
        return {
            prefix: value.slice(Math.max(0, offset - MAX_CONTEXT_CHARS), offset),
            suffix: value.slice(offset, offset + MAX_CONTEXT_CHARS),
        };
    }
}
