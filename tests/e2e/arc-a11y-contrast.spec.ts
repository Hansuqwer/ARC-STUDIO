/**
 * ARC Studio A11y — layout-capable color-contrast scan (Tier-2 L-G1)
 *
 * jsdom (jest-axe) cannot evaluate WCAG 1.4.3 color-contrast (no layout/paint). This spec renders the
 * real browser IDE in Chromium, opens the ARC Studio tabbed view (`?arc-view=arc-studio`), activates
 * each contrast-bearing tab, and runs axe-core's `color-contrast` rule scoped to ARC content
 * (`#arc-studio-widget`). Closes the rendered-contrast gap for B2P-03 (tabs), R-AUDIT23 (SwarmGraph
 * Insight cards) and R-AUDIT26 (MCP risk badges); surfaces any real violation to fix.
 */

import { test, expect } from '@playwright/test';
import { join } from 'path';

const APP_URL = process.env.ARC_E2E_URL || `http://127.0.0.1:${process.env.ARC_E2E_PORT || '3010'}`;
const AXE_PATH = join(__dirname, '..', '..', 'node_modules', 'axe-core', 'axe.min.js');
const TIMEOUT = 60_000;

type AxeNode = { target: string[]; html: string };
type AxeViolation = { id: string; impact?: string; nodes: AxeNode[] };

// Contrast-bearing ARC Studio tabs → their tab/panel element-id slugs.
const TABS: Array<{ name: string; slug: string }> = [
  { name: 'SwarmGraph Insight', slug: 'swarmgraph-insight' }, // R-AUDIT23 insight cards
  { name: 'MCP Workbench', slug: 'mcp-workbench' }, // R-AUDIT26 risk badges
  { name: 'Assurance', slug: 'assurance' },
  { name: 'Runs', slug: 'runs' },
  { name: 'Config', slug: 'config' },
];

async function acceptTrust(page: import('@playwright/test').Page): Promise<void> {
  const btn = page.getByRole('button', { name: /^yes,? i trust the authors$/i });
  if (await btn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await btn.click();
  }
}

/** Run axe color-contrast scoped to the ARC Studio widget; return violations. */
async function arcContrastViolations(page: import('@playwright/test').Page): Promise<AxeViolation[]> {
  await page.addScriptTag({ path: AXE_PATH });
  const result = await page.evaluate(async () => {
    const root = document.getElementById('arc-studio-widget') || document.body;
    // @ts-expect-error axe injected at runtime
    return await axe.run(root, {
      runOnly: { type: 'rule', values: ['color-contrast'] },
      resultTypes: ['violations'],
    });
  });
  return (result as { violations: AxeViolation[] }).violations || [];
}

test.describe('ARC Studio — layout-capable a11y color-contrast (L-G1)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${APP_URL}/?arc-view=arc-studio`, { waitUntil: 'domcontentloaded', timeout: TIMEOUT });
    await acceptTrust(page);
    // The tabbed view renders after the IDE boots; wait for it explicitly (boot ~6s).
    await page.locator('#arc-studio-widget').first().waitFor({ state: 'visible', timeout: 30_000 });
  });

  for (const { name, slug } of TABS) {
    test(`no ARC color-contrast violations on the ${name} tab`, async ({ page }) => {
      const tab = page.locator(`#arc-studio-tab-${slug}`).first();
      if (!(await tab.isVisible({ timeout: 10_000 }).catch(() => false))) {
        test.skip(true, `${name} tab not present in this app mode`);
      }
      await tab.click();
      await page.locator(`#arc-studio-panel-${slug}`).first().waitFor({ state: 'visible', timeout: TIMEOUT });
      await page.waitForTimeout(750); // let the panel paint
      const violations = await arcContrastViolations(page);
      if (violations.length > 0) {
        const summary = violations.flatMap((v) =>
          v.nodes.map((n) => ({ target: n.target?.join(' '), ...(n as unknown as { any?: Array<{ data?: unknown }> }).any?.[0]?.data as object }))
        );
        console.log(`AXE_CONTRAST ${name}:`, JSON.stringify(summary));
      }
      expect(violations, `ARC color-contrast violations on ${name}`).toEqual([]);
    });
  }
});

test.describe('ARC Adapters widget — a11y color-contrast (R-AUDIT21)', () => {
  test('no ARC color-contrast violations on the Adapters Status widget', async ({ page }) => {
    await page.goto(`${APP_URL}/?arc-view=adapters`, { waitUntil: 'domcontentloaded', timeout: TIMEOUT });
    await acceptTrust(page);
    // The adapters view opens in the 'main' area; in the headless harness 'main'-area widgets attach
    // but never become visible (only the 'left'-area arc-studio view renders via deep-link). axe
    // skips non-laid-out elements, so this scan can only run where the view is actually revealed
    // (e.g. a future harness that activates main-area widgets). Skip gracefully until then.
    const widget = page.locator('[id="arc:adapters-status"]').first();
    if (!(await widget.isVisible({ timeout: 15_000 }).catch(() => false))) {
      test.skip(true, 'Adapters (main-area) widget not visible in this app mode — see R-AUDIT21');
    }
    await page.waitForTimeout(750);
    const result = await (async () => {
      await page.addScriptTag({ path: AXE_PATH });
      return await page.evaluate(async () => {
        const root = document.getElementById('arc:adapters-status') || document.body;
        // @ts-expect-error axe injected at runtime
        return await axe.run(root, { runOnly: { type: 'rule', values: ['color-contrast'] }, resultTypes: ['violations'] });
      });
    })();
    const violations = (result as { violations: AxeViolation[] }).violations || [];
    if (violations.length > 0) {
      const summary = violations.flatMap((v) =>
        v.nodes.map((n) => ({ target: n.target?.join(' '), ...(n as unknown as { any?: Array<{ data?: unknown }> }).any?.[0]?.data as object }))
      );
      console.log('AXE_CONTRAST Adapters:', JSON.stringify(summary));
    }
    expect(violations, 'ARC color-contrast violations on Adapters widget').toEqual([]);
  });
});
