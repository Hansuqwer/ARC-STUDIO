/**
 * ARC Command Contribution
 *
 * Registers all ARC commands in the command palette and menus.
 * Source: https://theia-ide.org/docs/extensions/#contributing-commands
 */

import { injectable, inject, postConstruct } from '@theia/core/shared/inversify';
import { CommandContribution, CommandRegistry, CommandService, MenuContribution, MenuModelRegistry } from '@theia/core/lib/common';
import { CommonMenus } from '@theia/core/lib/browser/common-frontend-contribution';
import { MessageService } from '@theia/core/lib/common/message-service';
import { PreferenceService } from '@theia/core/lib/common/preferences/preference-service';
import { ArcFrontendService } from './arc-frontend-service';

export const ARC_MENU_MAIN = [...CommonMenus.VIEW, 'arc'];

export const ArcCommands = {
  INSPECT_WORKSPACE: {
    id: 'arc:inspect-workspace',
    label: 'ARC: Inspect Workspace',
    category: 'ARC',
  },
  LIST_RUNTIMES: {
    id: 'arc:list-runtimes',
    label: 'ARC: List Runtimes',
    category: 'ARC',
  },
  LIST_WORKFLOWS: {
    id: 'arc:list-workflows',
    label: 'ARC: List Workflows',
    category: 'ARC',
  },
  LIST_SCHEMAS: {
    id: 'arc:list-schemas',
    label: 'ARC: List Schemas',
    category: 'ARC',
  },
  START_RUN: {
    id: 'arc:start-run',
    label: 'ARC: Start Run',
    category: 'ARC',
  },
  GENERATE_CONTEXT_PACK: {
    id: 'arc:generate-context-pack',
    label: 'ARC: Generate Context Pack',
    category: 'ARC',
  },
  SHOW_DAEMON_STATUS: {
    id: 'arc:daemon-status',
    label: 'ARC: Show Daemon Status',
    category: 'ARC',
  },
  EXPORT_TRACE_TO_OTLP: {
    id: 'arc:export-trace-otlp',
    label: 'ARC: Export Trace to OTLP',
    category: 'ARC',
  },
};

@injectable()
export class ArcCommandContribution implements CommandContribution, MenuContribution {

  @inject(MessageService)
  protected readonly messageService: MessageService;

  @inject(PreferenceService)
  protected readonly preferences: PreferenceService;

  @inject(ArcFrontendService)
  protected readonly arcService: ArcFrontendService;

  @inject(CommandService)
  protected readonly commandService: CommandService;

  registerCommands(registry: CommandRegistry): void {
    registry.registerCommand(ArcCommands.INSPECT_WORKSPACE, {
      execute: async () => {
        try {
          const result = await this.arcService.inspectWorkspace();
          if (result.ok && result.data) {
            const { runtimes, files_scanned } = result.data;
            this.messageService.info(
              `ARC: Found ${runtimes.length} runtime(s) in ${files_scanned} files`
            );
          } else {
            this.messageService.error(`ARC: ${result.error?.message ?? 'Unknown error'}`);
          }
        } catch (e) {
          this.messageService.error(`ARC inspect failed: ${e}`);
        }
      },
    });

    registry.registerCommand(ArcCommands.LIST_RUNTIMES, {
      execute: async () => {
        try {
          const result = await this.arcService.listRuntimes();
          if (result.ok && result.data) {
            const names = result.data.map(r => r.name).join(', ');
            this.messageService.info(`ARC Runtimes: ${names || 'none detected'}`);
          }
        } catch (e) {
          this.messageService.error(`ARC runtimes failed: ${e}`);
        }
      },
    });

    registry.registerCommand(ArcCommands.LIST_WORKFLOWS, {
      execute: async () => {
        try {
          const result = await this.arcService.listWorkflows();
          if (result.ok && result.data) {
            this.messageService.info(`ARC: Found ${result.data.length} workflow(s)`);
          }
        } catch (e) {
          this.messageService.error(`ARC workflows failed: ${e}`);
        }
      },
    });

    registry.registerCommand(ArcCommands.LIST_SCHEMAS, {
      execute: async () => {
        try {
          const result = await this.arcService.listSchemas();
          if (result.ok && result.data) {
            this.messageService.info(`ARC: Found ${result.data.length} schema(s)`);
          }
        } catch (e) {
          this.messageService.error(`ARC schemas failed: ${e}`);
        }
      },
    });

    registry.registerCommand(ArcCommands.START_RUN, {
      execute: async () => {
        await this.commandService.executeCommand('arc:open-chat');
      },
    });

    registry.registerCommand(ArcCommands.GENERATE_CONTEXT_PACK, {
      execute: async () => {
        const task = 'inspect agent runtime';
        try {
          const result = await this.arcService.generateContextPack(task);
          if (result.ok && result.data) {
            this.messageService.info(`ARC Context Pack: ${result.data.length} entries generated`);
          }
        } catch (e) {
          this.messageService.error(`Context pack failed: ${e}`);
        }
      },
    });

    registry.registerCommand(ArcCommands.SHOW_DAEMON_STATUS, {
      execute: async () => {
        try {
          const result = await this.arcService.getDaemonStatus();
          if (result.data) {
            const { running, version } = result.data;
            this.messageService.info(
              running
                ? `ARC Daemon: running (v${version})`
                : 'ARC Daemon: not running. Start with `uv run arc serve`'
            );
          }
        } catch (e) {
          this.messageService.error(`Daemon status check failed: ${e}`);
        }
      },
    });

    registry.registerCommand(ArcCommands.EXPORT_TRACE_TO_OTLP, {
      execute: async (runId?: string) => {
        const endpoint = this.preferences.get<string>('arc.telemetry.otlpEndpoint', '');
        
        if (!endpoint) {
          this.messageService.warn('OTLP endpoint not configured. Set arc.telemetry.otlpEndpoint in Preferences.');
          return;
        }

        if (!runId) {
          this.messageService.warn('No run selected. Open a run in the Run Timeline first.');
          return;
        }

        try {
          const result = await this.arcService.exportTraceToOTLP(runId, endpoint);
          if (result.ok && result.data) {
            let message = `Trace exported to ${endpoint}`;
            if (result.data.warning) {
              message = `${result.data.warning}\n\n${message}`;
            }
            this.messageService.info(message);
          } else {
            this.messageService.error(`Export failed: ${result.error?.message ?? 'Unknown error'}`);
          }
        } catch (e) {
          this.messageService.error(`Export failed: ${e}`);
        }
      },
    });
  }

  registerMenus(menus: MenuModelRegistry): void {
    menus.registerSubmenu(ARC_MENU_MAIN, 'ARC');

    Object.values(ArcCommands).forEach(cmd => {
      menus.registerMenuAction(ARC_MENU_MAIN, {
        commandId: cmd.id,
        label: cmd.label,
      });
    });
  }
}
