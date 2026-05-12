/**
 * ARC Widget Contribution
 * 
 * Registers the ARC widget with Theia and provides commands
 * to open and interact with it.
 */

import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { ArcWidget } from './arc-widget';
import { Command, CommandRegistry } from '@theia/core/lib/common/command';
import { MenuModelRegistry } from '@theia/core/lib/common/menu';

export const ArcCommand: Command = {
    id: 'arc.open',
    label: 'Open ARC Studio'
};

@injectable()
export class ArcWidgetContribution extends AbstractViewContribution<ArcWidget> {

    constructor() {
        super({
            widgetId: ArcWidget.ID,
            widgetName: ArcWidget.LABEL,
            defaultWidgetOptions: {
                area: 'left',
                rank: 100
            },
            toggleCommandId: ArcCommand.id
        });
    }

    registerCommands(commands: CommandRegistry): void {
        commands.registerCommand(ArcCommand, {
            execute: () => this.openView({ activate: true, reveal: true })
        });
    }

    registerMenus(menus: MenuModelRegistry): void {
        super.registerMenus(menus);
    }
}
