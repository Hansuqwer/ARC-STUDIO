import { inject, injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command, CommandRegistry } from '@theia/core/lib/common/command';
import { PreferenceService } from '@theia/core/lib/common/preferences/preference-service';
import { ArcWelcomeWidget } from './arc-welcome-widget';

export const OpenWelcomeCommand: Command = {
    id: 'arc:open-welcome',
    label: 'ARC: Open Welcome',
    iconClass: 'codicon codicon-star',
};

@injectable()
export class ArcWelcomeContribution extends AbstractViewContribution<ArcWelcomeWidget> {
    @inject(PreferenceService)
    protected readonly preferences!: PreferenceService;

    constructor() {
        super({
            widgetId: ArcWelcomeWidget.ID,
            widgetName: ArcWelcomeWidget.LABEL,
            defaultWidgetOptions: { area: 'main', rank: 100 },
            toggleCommandId: OpenWelcomeCommand.id,
        });
    }

    override registerCommands(registry: CommandRegistry): void {
        super.registerCommands(registry);
        registry.registerCommand(OpenWelcomeCommand, {
            execute: () => this.openView({ activate: true }),
        });
    }

    async initializeLayout(): Promise<void> {
        if (this.preferences.get<boolean>('arc.ui.showOnboarding', false)) {
            await this.openView({ activate: true });
            await this.preferences.set('arc.ui.showOnboarding', false);
        }
    }
}
