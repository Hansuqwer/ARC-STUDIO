import { ContainerModule } from '@theia/core/shared/inversify';
import { CommandContribution } from '@theia/core/lib/common';
import { FrontendApplicationContribution, KeybindingContribution } from '@theia/core/lib/browser';
import { ArenaContribution } from './arena-contribution';
import { ArenaInlineCompletionProvider } from './arena-inline-completion-provider';
import { ArenaService } from './arena-service';

export default new ContainerModule(bind => {
    bind(ArenaService).toSelf().inSingletonScope();
    bind(ArenaInlineCompletionProvider).toSelf().inSingletonScope();
    bind(ArenaContribution).toSelf().inSingletonScope();
    bind(FrontendApplicationContribution).toService(ArenaContribution);
    bind(CommandContribution).toService(ArenaContribution);
    bind(KeybindingContribution).toService(ArenaContribution);
});
