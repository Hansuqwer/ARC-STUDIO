/** ARC Runs Contribution — registers the trace-backed run timeline view. */
import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command } from '@theia/core/lib/common/command';
import { ArcRunTimelineWidget } from './arc-run-timeline-widget';

export const OpenRunTimelineCommand: Command = {
    id: 'arc:open-run-timeline',
    label: 'ARC: Open Run Timeline (Advanced Trace)',
    category: 'ARC',
};

@injectable()
export class ArcRunsContribution extends AbstractViewContribution<ArcRunTimelineWidget> {
    constructor() {
        super({
            widgetId: ArcRunTimelineWidget.ID,
            widgetName: ArcRunTimelineWidget.LABEL,
            defaultWidgetOptions: { area: 'main' },
            toggleCommandId: OpenRunTimelineCommand.id,
        });
    }

    async initializeLayout(): Promise<void> {
        const params = new URLSearchParams(window.location.search);
        if (params.get('arc-view') === 'run-timeline') {
            await this.openView({ activate: true });
        }
    }
}
