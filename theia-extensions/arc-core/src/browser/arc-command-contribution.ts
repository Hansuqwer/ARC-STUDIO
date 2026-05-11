/**
 * ARC Command Contribution
 *
 * Registers all ARC commands in the command palette and menus.
 * Source: https://theia-ide.org/docs/extensions/#contributing-commands
 */

import { injectable, inject } from '@theia/core/shared/inversify';
import { CommandContribution, CommandRegistry, MenuContribution, MenuModelRegistry } from '@theia/core/lib/common';
import { CommonMenus } from '@theia/core/lib/browser/common-frontend-contribution';
import { MessageService } from '@theia/core/lib/common/message-service';
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
};

@injectable()
export class ArcCommandContribution implements CommandContribution, MenuContribution {

  @inject(MessageService)
  protected readonly messageService: MessageService;

  @inject(ArcFrontendService)
  protected readonly arcService: ArcFrontendService;

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
        this.messageService.info('ARC: Run launcher coming in next iteration. Open the Runs tab.');
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
