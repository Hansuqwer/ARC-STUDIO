import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command } from '@theia/core/lib/common/command';
import { ArcSimulationWidget } from './arc-simulation-widget';

export const OpenSimulationCommand: Command = {
    id: 'arc:open-simulation-panel',
    label: 'ARC: Show IR Simulation Panel',
    category: 'ARC',
};

@injectable()
export class ArcSimulationContribution extends AbstractViewContribution<ArcSimulationWidget> {
    constructor() {
        super({
            widgetId: ArcSimulationWidget.ID,
            widgetName: ArcSimulationWidget.LABEL,
            defaultWidgetOptions: { area: 'main' },
            toggleCommandId: OpenSimulationCommand.id,
        });
    }
}
