/**
 * ARC Adapters Contribution — Registers the adapters status widget.
 *
 * Placed in area:'left' so the widget is rendered by the Theia sidebar
 * and visible in the layout-capable axe e2e colour-contrast scan
 * (R-AUDIT21 closure — main-area views have 0 size in headless harness).
 */
import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command } from '@theia/core/lib/common/command';
import { ArcAdaptersWidget } from './arc-adapters-widget';

export const OpenAdaptersCommand: Command = {
    id: 'arc:open-adapters',
    label: 'ARC: Open Adapters Status',
    category: 'ARC',
};

@injectable()
export class ArcAdaptersContribution extends AbstractViewContribution<ArcAdaptersWidget> {
    constructor() {
        super({
            widgetId: ArcAdaptersWidget.ID,
            widgetName: ArcAdaptersWidget.LABEL,
            // area:'left' — sidebar placement makes the widget visible in the
            // layout-capable axe e2e scan (area:'main' stays 0-size in headless harness).
            defaultWidgetOptions: { area: 'left', rank: 510 },
            toggleCommandId: OpenAdaptersCommand.id,
        });
    }

    async initializeLayout(): Promise<void> {
        // Deep-link parity with the other ARC views (e.g. ?arc-view=event-stream).
        const params = new URLSearchParams(window.location.search);
        if (params.get('arc-view') === 'adapters') {
            await this.openView({ activate: true, reveal: true });
        }
    }
}
