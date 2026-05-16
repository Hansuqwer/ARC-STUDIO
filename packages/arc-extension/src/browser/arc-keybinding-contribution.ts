/**
 * ARC Keybinding Contribution
 * 
 * Registers global keyboard shortcuts for ARC Studio commands.
 * These shortcuts work application-wide, not just when the widget has focus.
 */

import { injectable, inject } from '@theia/core/shared/inversify';
import { KeybindingContribution, KeybindingRegistry } from '@theia/core/lib/browser';
import { CommandContribution, CommandRegistry, Command } from '@theia/core/lib/common';
import { ArcWidgetContribution } from './arc-widget-contribution';

export namespace ArcCommands {
    export const EXECUTE: Command = { id: 'arc.execute', label: 'ARC: Execute Workflow' };
    export const SCAN_WORKSPACE: Command = { id: 'arc.scanWorkspace', label: 'ARC: Scan Workspace' };
    export const SHOW_SHORTCUTS: Command = { id: 'arc.showShortcuts', label: 'ARC: Show Shortcuts' };
}

@injectable()
export class ArcKeybindingContribution implements KeybindingContribution, CommandContribution {
    @inject(ArcWidgetContribution)
    protected readonly arcContribution!: ArcWidgetContribution;

    registerCommands(commands: CommandRegistry): void {
        commands.registerCommand(ArcCommands.EXECUTE, {
            execute: () => this.arcContribution.executeWorkflow()
        });
        commands.registerCommand(ArcCommands.SCAN_WORKSPACE, {
            execute: () => this.arcContribution.scanWorkspace()
        });
        commands.registerCommand(ArcCommands.SHOW_SHORTCUTS, {
            execute: () => this.arcContribution.showShortcuts()
        });
    }

    registerKeybindings(registry: KeybindingRegistry): void {
        registry.registerKeybinding({ command: ArcCommands.EXECUTE.id, keybinding: 'ctrlcmd+e' });
        registry.registerKeybinding({ command: ArcCommands.SCAN_WORKSPACE.id, keybinding: 'ctrlcmd+shift+s' });
        registry.registerKeybinding({ command: ArcCommands.SHOW_SHORTCUTS.id, keybinding: 'ctrlcmd+h' });
    }
}
