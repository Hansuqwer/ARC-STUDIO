import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command } from '@theia/core/lib/common/command';
import { ArcMobileWidget } from './arc-mobile-widget';

export const OpenMobileCommand: Command = {
    id: 'arc:open-mobile-runtime',
    label: 'ARC: Open Mobile Runtime',
    category: 'ARC',
};

@injectable()
export class ArcMobileContribution extends AbstractViewContribution<ArcMobileWidget> {
    constructor() {
        super({
            widgetId: ArcMobileWidget.ID,
            widgetName: ArcMobileWidget.LABEL,
            defaultWidgetOptions: { area: 'main' },
            toggleCommandId: OpenMobileCommand.id,
        });
    }
}
