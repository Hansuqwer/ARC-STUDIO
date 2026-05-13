/**
 * ARC Widget Contribution
 * 
 * Registers the ARC widget with Theia and provides commands
 * to open and interact with it.
 * 
 * This contribution class follows Theia's extension pattern for registering
 * custom widgets, commands, and menu items. It extends AbstractViewContribution
 * which provides standard widget lifecycle management.
 * 
 * @class ArcWidgetContribution
 * @extends {AbstractViewContribution<ArcWidget>}
 * 
 * @remarks
 * - Registers the ARC widget in the left side panel
 * - Provides 'arc.open' command to open/toggle the widget
 * - Widget is closable and can be reopened via command
 * 
 * @see {@link ArcWidget} for the widget implementation
 */

import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { ArcWidget } from './arc-widget';
import { Command, CommandRegistry } from '@theia/core/lib/common/command';
import { MenuModelRegistry } from '@theia/core/lib/common/menu';

/**
 * Command to open the ARC Studio widget.
 * 
 * This command can be invoked via:
 * - Command palette (F1 or Cmd+Shift+P)
 * - Programmatically via CommandRegistry
 * - Menu items (if registered)
 * 
 * @constant
 */
export const ArcCommand: Command = {
    id: 'arc.open',
    label: 'Open ARC Studio'
};

@injectable()
export class ArcWidgetContribution extends AbstractViewContribution<ArcWidget> {

    /**
     * Initialize the widget contribution.
     * 
     * Configures the widget with:
     * - Widget ID and name for registration
     * - Default placement in left side panel
     * - Rank for ordering among other side panel widgets
     * - Toggle command for opening/closing
     */
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

    /**
     * Register commands for the ARC widget.
     * 
     * Registers the 'arc.open' command which opens the widget and brings it
     * into focus. The command activates and reveals the widget if it's hidden.
     * 
     * @param commands - Theia's command registry
     * 
     * @remarks
     * - Command is available in command palette
     * - Can be bound to keyboard shortcuts via keybindings
     * - Calling when widget is open will bring it to front
     */
    registerCommands(commands: CommandRegistry): void {
        commands.registerCommand(ArcCommand, {
            execute: () => this.openView({ activate: true, reveal: true })
        });
    }

    /**
     * Register menu items for the ARC widget.
     * 
     * Currently uses default menu registration from AbstractViewContribution.
     * Can be extended to add custom menu items in View menu or context menus.
     * 
     * @param menus - Theia's menu model registry
     * 
     * @remarks
     * - Default implementation adds item to View menu
     * - Can be extended to add custom menu locations
     * 
     * @todo Add custom menu items if needed
     */
    registerMenus(menus: MenuModelRegistry): void {
        super.registerMenus(menus);
    }

    async executeWorkflow(): Promise<void> {
        const widget = await this.openView({ activate: true, reveal: true });
        widget.handleExecuteWorkflow();
    }

    async loadTraces(): Promise<void> {
        const widget = await this.openView({ activate: true, reveal: true });
        widget.handleLoadTraces();
    }

    async scanWorkspace(): Promise<void> {
        const widget = await this.openView({ activate: true, reveal: true });
        widget.handleScanWorkspace();
    }

    async showShortcuts(): Promise<void> {
        const widget = await this.openView({ activate: true, reveal: true });
        widget.toggleShortcutsHelp();
    }
}
