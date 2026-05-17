/**
 * ARC Arena Contribution — commands, keybindings, menus, and view registration.
 */
import { injectable, inject } from '@theia/core/shared/inversify';
import { AbstractViewContribution } from '@theia/core/lib/browser';
import { Command, CommandRegistry } from '@theia/core/lib/common/command';
import { MenuModelRegistry, MenuPath } from '@theia/core/lib/common/menu';
import { KeybindingRegistry } from '@theia/core/lib/common/keybinding';
import { ArcArenaWidget } from './arc-arena-widget';

// ─── Commands ───────────────────────────────────────────────────────────

export const OpenArenaCommand: Command = {
  id: 'arc:open-arena',
  label: 'ARC: Open Arena',
  category: 'ARC',
};

export const ArenaBattleCommand: Command = {
  id: 'arc:arena-battle',
  label: 'ARC Arena: Battle Models',
  category: 'ARC Arena',
};

export const ArenaDirectCommand: Command = {
  id: 'arc:arena-direct',
  label: 'ARC Arena: Direct Chat',
  category: 'ARC Arena',
};

export const ArenaCodeCommand: Command = {
  id: 'arc:arena-code',
  label: 'ARC Arena: Generate Code',
  category: 'ARC Arena',
};

export const ArenaAgentPreviewCommand: Command = {
  id: 'arc:arena-agent-preview',
  label: 'ARC Arena: Agent Preview',
  category: 'ARC Arena',
};

export const ArenaAdoptCandidateCommand: Command = {
  id: 'arc:arena-adopt',
  label: 'ARC Arena: Adopt Selected Candidate',
  category: 'ARC Arena',
};

export const ArenaRejectCandidatesCommand: Command = {
  id: 'arc:arena-reject',
  label: 'ARC Arena: Reject All Candidates',
  category: 'ARC Arena',
};

export const ArenaVoteACommand: Command = {
  id: 'arc:arena-vote-a',
  label: 'ARC Arena: Vote A (Top)',
  category: 'ARC Arena',
};

export const ArenaVoteBCommand: Command = {
  id: 'arc:arena-vote-b',
  label: 'ARC Arena: Vote B (Bottom)',
  category: 'ARC Arena',
};

const ARENA_MENU: MenuPath = ['arc-arena-menu'];

@injectable()
export class ArcArenaContribution extends AbstractViewContribution<ArcArenaWidget> {

  constructor() {
    super({
      widgetId: ArcArenaWidget.ID,
      widgetName: ArcArenaWidget.LABEL,
      defaultWidgetOptions: { area: 'main' },
      toggleCommandId: OpenArenaCommand.id,
    });
  }

  override registerCommands(registry: CommandRegistry): void {
    super.registerCommands(registry);
    registry.registerCommand(OpenArenaCommand, {
      execute: () => this.openView({ activate: true }),
    });
    registry.registerCommand(ArenaBattleCommand, {
      execute: () => this.openView({ activate: true }),
    });
    registry.registerCommand(ArenaDirectCommand, {
      execute: () => this.openView({ activate: true }),
    });
    registry.registerCommand(ArenaCodeCommand, {
      execute: () => this.openView({ activate: true }),
    });
    registry.registerCommand(ArenaAgentPreviewCommand, {
      execute: () => this.openView({ activate: true }),
    });
    registry.registerCommand(ArenaAdoptCandidateCommand, {
      execute: () => {
        const widget = this.tryGetWidget();
        widget?.adoptSelected();
      },
    });
    registry.registerCommand(ArenaRejectCandidatesCommand, {
      execute: () => {
        const widget = this.tryGetWidget();
        widget?.rejectAll();
      },
    });
    registry.registerCommand(ArenaVoteACommand, {
      execute: () => {
        const widget = this.tryGetWidget();
        widget?.voteA();
      },
    });
    registry.registerCommand(ArenaVoteBCommand, {
      execute: () => {
        const widget = this.tryGetWidget();
        widget?.voteB();
      },
    });
  }

  override registerMenus(menus: MenuModelRegistry): void {
    super.registerMenus(menus);
    menus.registerSubmenu(ARENA_MENU, 'ARC Arena');
    menus.registerMenuAction(ARENA_MENU, { commandId: ArenaBattleCommand.id, label: 'Battle Models' });
    menus.registerMenuAction(ARENA_MENU, { commandId: ArenaDirectCommand.id, label: 'Direct Chat' });
    menus.registerMenuAction(ARENA_MENU, { commandId: ArenaCodeCommand.id, label: 'Generate Code' });
    menus.registerMenuAction(ARENA_MENU, { commandId: ArenaAgentPreviewCommand.id, label: 'Agent Preview' });
    menus.registerMenuAction(ARENA_MENU, { commandId: ArenaAdoptCandidateCommand.id, label: 'Adopt Selected' });
    menus.registerMenuAction(ARENA_MENU, { commandId: ArenaRejectCandidatesCommand.id, label: 'Reject All' });
  }

  override registerKeybindings(keybindings: KeybindingRegistry): void {
    super.registerKeybindings(keybindings);
    keybindings.registerKeybinding({
      command: ArenaAdoptCandidateCommand.id,
      keybinding: 'ctrl+1',
      when: 'widget:arc:arena focused',
    });
    keybindings.registerKeybinding({
      command: ArenaRejectCandidatesCommand.id,
      keybinding: 'ctrl+3',
      when: 'widget:arc:arena focused',
    });
    keybindings.registerKeybinding({
      command: ArenaVoteACommand.id,
      keybinding: 'ctrl+shift+1',
      when: 'widget:arc:arena focused && arc:arena:battle',
    });
    keybindings.registerKeybinding({
      command: ArenaVoteBCommand.id,
      keybinding: 'ctrl+shift+2',
      when: 'widget:arc:arena focused && arc:arena:battle',
    });
  }
}
