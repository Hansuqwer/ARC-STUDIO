import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command } from '@theia/core/lib/common/command';
import { ArcHealthWidget } from './arc-health-widget';

export const OpenHealthMonitorCommand: Command = {
    id: 'arc:open-health-monitor',
    label: 'ARC: Show Health Monitor',
    category: 'ARC',
};

@injectable()
export class ArcHealthContribution extends AbstractViewContribution<ArcHealthWidget> {
    constructor() {
        super({
            widgetId: ArcHealthWidget.ID,
            widgetName: ArcHealthWidget.LABEL,
            defaultWidgetOptions: { area: 'main' },
            toggleCommandId: OpenHealthMonitorCommand.id,
        });
    }

    async initializeLayout(): Promise<void> {
        const params = new URLSearchParams(window.location.search);
        if (params.get('arc-view') === 'health-monitor') {
            await this.openView({ activate: true });
        }
    }
}
