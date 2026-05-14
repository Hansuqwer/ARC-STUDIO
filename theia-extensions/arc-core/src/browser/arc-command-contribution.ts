/**
 * ARC Command Contribution
 *
 * Registers all ARC commands in the command palette and menus.
 * Commands are consolidated per the UX redesign plan:
 * 8 primary commands, grouped with separators.
 * Source: https://theia-ide.org/docs/extensions/#contributing-commands
 */

import { injectable, inject } from '@theia/core/shared/inversify';
import { CommandContribution, CommandRegistry, CommandService, MenuContribution, MenuModelRegistry } from '@theia/core/lib/common';
import { CommonMenus } from '@theia/core/lib/browser/common-frontend-contribution';
import { MessageService } from '@theia/core/lib/common/message-service';
import { PreferenceService } from '@theia/core/lib/common/preferences/preference-service';
import { ArcFrontendService } from './arc-frontend-service';

export const ARC_MENU_MAIN = [...CommonMenus.VIEW, 'arc'];
const OPEN_RUN_TIMELINE_COMMAND = 'arc:open-run-timeline';
const OPEN_RUN_DIFF_COMMAND = 'arc:open-run-diff';

/**
 * Consolidated ARC commands (8 primary commands, down from 20+).
 */
export const ArcCommands = {
  RUN_AGENT: {
    id: 'arc:run-agent',
    label: 'ARC: Run Agent',
    category: 'ARC',
  },
  COMPARE_MODELS: {
    id: 'arc:compare-models',
    label: 'ARC: Compare Models',
    category: 'ARC',
  },
  OPEN_TIMELINE: {
    id: 'arc:open-timeline',
    label: 'ARC: Open Timeline',
    category: 'ARC',
  },
  COMPARE_RUNS: {
    id: 'arc:compare-runs',
    label: 'ARC: Compare Runs',
    category: 'ARC',
  },
  EVALUATE_RUN: {
    id: 'arc:evaluate-run',
    label: 'ARC: Evaluate Run',
    category: 'ARC',
  },
  RUNTIME_DOCTOR: {
    id: 'arc:runtime-doctor',
    label: 'ARC: Runtime Doctor',
    category: 'ARC',
  },
  INSPECT_WORKSPACE: {
    id: 'arc:inspect-workspace',
    label: 'ARC: Inspect Workspace',
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
    // Run Agent → opens chat widget
    registry.registerCommand(ArcCommands.RUN_AGENT, {
      execute: async () => {
        await this.commandService.executeCommand('arc:open-chat');
      },
    });

    // Compare Models → opens arena widget
    registry.registerCommand(ArcCommands.COMPARE_MODELS, {
      execute: async () => {
        await this.commandService.executeCommand('arc:open-arena');
      },
    });

    // Open Timeline → delegates to arc-runs command
    registry.registerCommand(ArcCommands.OPEN_TIMELINE, {
      execute: async () => {
        await this.commandService.executeCommand(OPEN_RUN_TIMELINE_COMMAND);
      },
    });

    // Compare Runs → delegates to arc-runs diff command
    registry.registerCommand(ArcCommands.COMPARE_RUNS, {
      execute: async () => {
        await this.commandService.executeCommand(OPEN_RUN_DIFF_COMMAND);
      },
    });

    // Evaluate Run → opens timeline (eval available from there)
    registry.registerCommand(ArcCommands.EVALUATE_RUN, {
      execute: async () => {
        await this.commandService.executeCommand(OPEN_RUN_TIMELINE_COMMAND);
      },
    });

    // Runtime Doctor → opens adapters widget
    registry.registerCommand(ArcCommands.RUNTIME_DOCTOR, {
      execute: async () => {
        await this.commandService.executeCommand('arc:open-adapters');
      },
    });

    // Inspect Workspace → refresh sidebar data
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

    // Export Trace to OTLP
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

    // Group 1: Run
    menus.registerMenuAction(ARC_MENU_MAIN, {
      commandId: ArcCommands.RUN_AGENT.id,
      label: 'Run Agent',
    });
    menus.registerMenuAction(ARC_MENU_MAIN, {
      commandId: ArcCommands.COMPARE_MODELS.id,
      label: 'Compare Models',
    });

    // Group 2: Views
    menus.registerMenuAction(ARC_MENU_MAIN, {
      commandId: ArcCommands.OPEN_TIMELINE.id,
      label: 'Open Timeline',
    });
    menus.registerMenuAction(ARC_MENU_MAIN, {
      commandId: ArcCommands.COMPARE_RUNS.id,
      label: 'Compare Runs',
    });
    menus.registerMenuAction(ARC_MENU_MAIN, {
      commandId: ArcCommands.EVALUATE_RUN.id,
      label: 'Evaluate Run',
    });

    // Group 3: Tools
    menus.registerMenuAction(ARC_MENU_MAIN, {
      commandId: ArcCommands.RUNTIME_DOCTOR.id,
      label: 'Runtime Doctor',
    });
    menus.registerMenuAction(ARC_MENU_MAIN, {
      commandId: ArcCommands.INSPECT_WORKSPACE.id,
      label: 'Inspect Workspace',
    });

    // Group 4: Export
    menus.registerMenuAction(ARC_MENU_MAIN, {
      commandId: ArcCommands.EXPORT_TRACE_TO_OTLP.id,
      label: 'Export Trace to OTLP',
    });
  }
}
