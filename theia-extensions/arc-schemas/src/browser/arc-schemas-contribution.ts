import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command } from '@theia/core/lib/common/command';
import { ArcSchemaInspectorWidget } from './arc-schema-inspector-widget';

export const OpenSchemaInspectorCommand: Command = {
  id: 'arc:open-schema-inspector',
  label: 'ARC: Open Schema Inspector',
  category: 'ARC',
};

@injectable()
export class ArcSchemasContribution extends AbstractViewContribution<ArcSchemaInspectorWidget> {
  constructor() {
    super({
      widgetId: ArcSchemaInspectorWidget.ID,
      widgetName: ArcSchemaInspectorWidget.LABEL,
      defaultWidgetOptions: { area: 'main' },
      toggleCommandId: OpenSchemaInspectorCommand.id,
    });
  }

}
