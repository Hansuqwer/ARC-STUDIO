import { injectable, inject } from '@theia/core/shared/inversify';
import { ConfirmDialog } from '@theia/core/lib/browser';
import { MessageService } from '@theia/core';

interface CostWarningPayload {
    runtime: string;
    backend: string;
    estimated_provider: string;
    gated_at: string;
}

@injectable()
export class CostWarningService {
    private readonly acks = new Set<string>();

    @inject(MessageService) protected readonly messages!: MessageService;

    async maybePrompt(name: string, value: unknown): Promise<boolean> {
        if (name !== 'arc.cost_warning' || !value || typeof value !== 'object') {
            return true;
        }
        const v = value as CostWarningPayload;
        if (this.acks.has(v.runtime)) {
            return true;
        }
        const dialog = new ConfirmDialog({
            title: 'ARC: Real provider run',
            msg:
                `You are about to execute a real run on the "${v.runtime}" runtime ` +
                `using backend "${v.backend}" (provider: ${v.estimated_provider}). ` +
                `This may incur provider costs. Continue?`,
            ok: 'Run',
            cancel: 'Cancel',
        });
        const accepted = await dialog.open();
        if (accepted) {
            this.acks.add(v.runtime);
            return true;
        }
        this.messages.warn(`ARC: run cancelled before backend "${v.backend}" was called.`);
        return false;
    }
}
