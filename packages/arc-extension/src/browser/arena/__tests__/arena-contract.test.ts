import * as fs from 'fs-extra';
import * as path from 'path';

describe('Arena inline completion contracts', () => {
    const arenaDir = path.join(__dirname, '..');

    it('keeps inline completions preference-gated', async () => {
        const contribution = await fs.readFile(path.join(arenaDir, 'arena-contribution.ts'), 'utf-8');
        const preferences = await fs.readFile(path.join(arenaDir, '..', 'arc-preference-schema.ts'), 'utf-8');

        expect(contribution).toMatch(/arc\.arena\.inlineCompletion\.enabled/);
        expect(contribution).toMatch(/registerInlineCompletionsProvider/);
        expect(preferences).toMatch(/arc\.arena\.inlineCompletion\.enabled/);
        expect(preferences).toMatch(/default:\s*false/);
    });

    it('supports cycling a single visible arena candidate', async () => {
        const contribution = await fs.readFile(path.join(arenaDir, 'arena-contribution.ts'), 'utf-8');
        const provider = await fs.readFile(path.join(arenaDir, 'arena-inline-completion-provider.ts'), 'utf-8');

        expect(contribution).toMatch(/arc\.arena\.nextCompletion/);
        expect(contribution).toMatch(/alt\+\]/);
        expect(contribution).toMatch(/alt\+\[/);
        expect(provider).toMatch(/items:\s*\[\{/);
        expect(provider).not.toMatch(/items:\s*pair\.completionItems\.map/);
    });
});
