/**
 * ARC Studio A11y — layout-capable color-contrast scan (Tier-2 L-G1)
 *
 * jsdom (jest-axe) cannot evaluate WCAG 1.4.3 color-contrast because it has no
 * layout/paint. This spec renders the real browser IDE in Chromium and runs
 * axe-core's `color-contrast` rule against the ARC-owned widget surfaces —
 * closing the contrast gaps left at Baseline for B2P-03, R-AUDIT21, R-AUDIT23,
 * and R-AUDIT26. Violations are filtered to ARC nodes (class contains `arc-`)
 * so this measures ARC's own colors, not Theia's chrome.
 */

import { test, expect } from '@playwright/test';
import { join } from 'path';

const APP_URL = process.env.ARC_E2E_URL || `http://127.0.0.1:${process.env.ARC_E2E_PORT || '3010'}`;
const AXE_PATH = join(__dirname, '..', '..', 'node_modules', 'axe-core', 'axe.min.js');
const TIMEOUT = 60_000;

type AxeNode = { target: string[]; html: string; any: Array<{ id: string; data?: unknown }> };
type AxeViolation = { id: string; impact?: string; nodes: AxeNode[] };

async function acceptTrust(page: import('@playwright/test').Page): Promise<void> {
  const btn = page.getByRole('button', { name: /^yes,? i trust the authors$/i });
  if (await btn.isVisible({ timeout: 1000 }).catch(() => false)) {
    await btn.click();
  }
}


/** Run axe color-contrast over the document, return only ARC-owned violation nodes. */
async function arcContrastViolations(page: import('@playwright/test').Page): Promise<AxeViolation[]> {
  await page.addScriptTag({ path: AXE_PATH });
  const result = await page.evaluate(async () => {
    // @ts-expect-error axe injected at runtime
    return await axe.run(document, {
      runOnly: { type: 'rule', values: ['color-contrast'] },
      resultTypes: ['violations'],
    });
  });
  const violations = (result as { violations: AxeViolation[] }).violations || [];
  // Keep only nodes whose target/html references an ARC-owned class.
  return violations
    .map((v) => ({
      ...v,
      nodes: v.nodes.filter(
        (n) => n.target.some((t) => /arc-/i.test(t)) || /class="[^"]*arc-/i.test(n.html),
      ),
    }))
    .filter((v) => v.nodes.length > 0);
}

test.describe('ARC Studio — layout-capable a11y color-contrast (L-G1)', () => {
  // Deep-linkable ARC widgets are routable in the e2e app mode (the tabbed ARC Studio view is
  // not — the smoke suite skips it likewise). These render ARC-owned colors (event badges,
  // health status, timeline), so they exercise the real layout-capable color-contrast path.
  for (const arcView of ['event-stream', 'health-monitor', 'run-timeline']) {
    test(`no ARC color-contrast violations on the ${arcView} widget`, async ({ page }) => {
      await page.goto(`${APP_URL}/?arc-view=${arcView}`, { waitUntil: 'networkidle', timeout: TIMEOUT });
      await acceptTrust(page);
      const widget = page.locator(`[id="arc:${arcView}"]`).first();
      if (!(await widget.isVisible({ timeout: 10_000 }).catch(() => false))) {
        test.skip(true, `${arcView} widget not routable in this app mode`);
      }
      await page.waitForTimeout(750); // let the widget paint
      const violations = await arcContrastViolations(page);
      if (violations.length > 0) {
        console.log(`ARC contrast violations on ${arcView}:`, JSON.stringify(violations, null, 2));
      }
      expect(violations, `ARC color-contrast violations on ${arcView}`).toEqual([]);
    });
  }
});
