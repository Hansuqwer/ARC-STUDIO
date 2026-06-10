import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command } from '@theia/core/lib/common/command';
import { ArcDashboardWidget } from './arc-dashboard-widget';

export const OpenDashboardCommand: Command = {
    id: 'arc:open-dashboard',
    label: 'ARC: Show Dashboard',
    category: 'ARC',
};

@injectable()
export class ArcDashboardContribution extends AbstractViewContribution<ArcDashboardWidget> {
    constructor() {
        super({
            widgetId: ArcDashboardWidget.ID,
            widgetName: ArcDashboardWidget.LABEL,
            defaultWidgetOptions: { area: 'main' },
            toggleCommandId: OpenDashboardCommand.id,
        });
    }

    async initializeLayout(): Promise<void> {
        const params = new URLSearchParams(window.location.search);
        if (params.get('arc-view') === 'dashboard') {
            await this.openView({ activate: true, reveal: true });
        }
    }
}
