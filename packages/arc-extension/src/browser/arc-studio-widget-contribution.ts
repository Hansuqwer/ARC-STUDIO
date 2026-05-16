/**
 * ARC Studio Widget Contribution
 *
 * Registers the ArcStudioWidget as the primary/default ARC widget.
 * Keeps old widget contributions available for backward compatibility.
 */

import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { ArcStudioWidget } from './arc-studio-widget';
import { Command, CommandRegistry } from '@theia/core/lib/common/command';
import { MenuModelRegistry } from '@theia/core/lib/common/menu';

export const ArcStudioCommand: Command = {
    id: 'arc-studio:open',
    label: 'Open ARC Studio'
};

@injectable()
export class ArcStudioWidgetContribution extends AbstractViewContribution<ArcStudioWidget> {

    constructor() {
        super({
            widgetId: ArcStudioWidget.ID,
            widgetName: ArcStudioWidget.LABEL,
            defaultWidgetOptions: {
                area: 'left',
                rank: 90
            },
            toggleCommandId: ArcStudioCommand.id
        });
    }

    registerCommands(commands: CommandRegistry): void {
        commands.registerCommand(ArcStudioCommand, {
            execute: () => this.openView({ activate: true, reveal: true })
        });
    }

    registerMenus(menus: MenuModelRegistry): void {
        super.registerMenus(menus);
    }
}
