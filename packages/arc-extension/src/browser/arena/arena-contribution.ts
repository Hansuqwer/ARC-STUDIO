import { Command, CommandContribution, CommandRegistry } from '@theia/core/lib/common';
import { PreferenceService } from '@theia/core/lib/common/preferences';
import { FrontendApplication, FrontendApplicationContribution, KeybindingContribution, KeybindingRegistry } from '@theia/core/lib/browser';
import { inject, injectable } from '@theia/core/shared/inversify';
import * as monaco from '@theia/monaco-editor-core';
import { ArenaInlineCompletionProvider } from './arena-inline-completion-provider';
import { ArenaService } from './arena-service';

export namespace ArenaCommands {
    export const NEXT: Command = { id: 'arc.arena.nextCompletion', label: 'ARC Arena: Next Completion' };
    export const PREVIOUS: Command = { id: 'arc.arena.previousCompletion', label: 'ARC Arena: Previous Completion' };
    export const ACCEPT: Command = { id: 'arc.arena.acceptInlineCompletion', label: 'ARC Arena: Record Inline Acceptance' };
}

@injectable()
export class ArenaContribution implements FrontendApplicationContribution, CommandContribution, KeybindingContribution {
    @inject(ArenaInlineCompletionProvider)
    protected readonly provider!: ArenaInlineCompletionProvider;

    @inject(ArenaService)
    protected readonly arena!: ArenaService;

    @inject(PreferenceService)
    protected readonly preferences!: PreferenceService;

    onStart(_app: FrontendApplication): void {
        const enabled = this.preferences.get<boolean>('arc.arena.inlineCompletion.enabled', false);
        if (!enabled) {
            return;
        }
        monaco.languages.registerInlineCompletionsProvider({ pattern: '**' }, this.provider as monaco.languages.InlineCompletionsProvider);
    }

    registerCommands(commands: CommandRegistry): void {
        commands.registerCommand(ArenaCommands.NEXT, {
            execute: () => this.arena.selectNext(),
        });
        commands.registerCommand(ArenaCommands.PREVIOUS, {
            execute: () => this.arena.selectPrevious(),
        });
        commands.registerCommand(ArenaCommands.ACCEPT, {
            execute: async () => {
                const serverUrl = this.preferences.get<string>('arc.arena.serverUrl', '');
                if (serverUrl) {
                    await this.arena.recordAccepted(serverUrl);
                }
            },
        });
    }

    registerKeybindings(registry: KeybindingRegistry): void {
        registry.registerKeybinding({ command: ArenaCommands.NEXT.id, keybinding: 'alt+]' });
        registry.registerKeybinding({ command: ArenaCommands.PREVIOUS.id, keybinding: 'alt+[' });
    }
}
