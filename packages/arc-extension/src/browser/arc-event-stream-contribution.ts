/** ARC Event Stream Contribution — registers the event stream view. */
import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command } from '@theia/core/lib/common/command';
import { ArcEventStreamWidget } from './arc-event-stream-widget';

export const OpenEventStreamCommand: Command = {
    id: 'arc:open-event-stream',
    label: 'ARC: Open Event Stream',
    category: 'ARC',
};

@injectable()
export class ArcEventStreamContribution extends AbstractViewContribution<ArcEventStreamWidget> {
    constructor() {
        super({
            widgetId: ArcEventStreamWidget.ID,
            widgetName: ArcEventStreamWidget.LABEL,
            defaultWidgetOptions: { area: 'main' },
            toggleCommandId: OpenEventStreamCommand.id,
        });
    }

    async initializeLayout(): Promise<void> {
        const params = new URLSearchParams(window.location.search);
        if (params.get('arc-view') === 'event-stream') {
            await this.openView({ activate: true });
        }
    }
}
