import { injectable } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command } from '@theia/core/lib/common/command';
import { ArcRunTimelineWidget } from './arc-run-timeline-widget';
import { ArcChatWidget } from './arc-chat-widget';
import { ArcRunDiffWidget } from './arc-run-diff-widget';

export const OpenRunTimelineCommand: Command = {
  id: 'arc:open-run-timeline',
  label: 'ARC: Open Run Timeline',
  category: 'ARC',
};

export const OpenArcChatCommand: Command = {
  id: 'arc:open-chat',
  label: 'ARC: Open Chat',
  category: 'ARC',
};

export const OpenRunDiffCommand: Command = {
  id: 'arc:open-run-diff',
  label: 'ARC: Open Run Diff',
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

@injectable()
export class ArcChatContribution extends AbstractViewContribution<ArcChatWidget> {
  constructor() {
    super({
      widgetId: ArcChatWidget.ID,
      widgetName: ArcChatWidget.LABEL,
      defaultWidgetOptions: { area: 'main' },
      toggleCommandId: OpenArcChatCommand.id,
    });
  }

  async initializeLayout(): Promise<void> {
    const params = new URLSearchParams(window.location.search);
    if (params.get('arc-view') === 'chat') {
      await this.openView({ activate: true });
    }
  }
}

@injectable()
export class ArcRunDiffContribution extends AbstractViewContribution<ArcRunDiffWidget> {
  constructor() {
    super({
      widgetId: ArcRunDiffWidget.ID,
      widgetName: ArcRunDiffWidget.LABEL,
      defaultWidgetOptions: { area: 'main' },
      toggleCommandId: OpenRunDiffCommand.id,
    });
  }
}
