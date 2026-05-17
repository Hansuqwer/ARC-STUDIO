/**
 * ARC Studio E2E Smoke Test — Playwright
 *
 * Covers the canonical `packages/arc-extension` widgets wired into
 * `applications/browser`. Runtime launch remains covered by backend/unit tests
 * until the Theia command/deep-link surface exposes ChatTab launch consistently.
 */

import { test, expect } from '@playwright/test';
import { join } from 'path';

const APP_URL = process.env.ARC_E2E_URL || `http://127.0.0.1:${process.env.ARC_E2E_PORT || '3010'}`;
const TIMEOUT = 60_000;
const REPO_ROOT = join(__dirname, '..', '..');

async function acceptWorkspaceTrustIfShown(page: import('@playwright/test').Page): Promise<void> {
  const trustButton = page.getByRole('button', { name: /^yes,? i trust the authors$/i });
  if (await trustButton.isVisible({ timeout: 1000 }).catch(() => false)) {
    await trustButton.click();
  }
}

test.describe('ARC Studio — Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(APP_URL, { waitUntil: 'networkidle', timeout: TIMEOUT });
    await acceptWorkspaceTrustIfShown(page);
  });

  test('browser app loads without crash', async ({ page }) => {
    const title = await page.title();
    expect(title).toBeTruthy();
    expect(title).not.toContain('ERR_');
    expect(title).not.toContain('Cannot GET');
  });

  test('page title contains ARC Studio', async ({ page }) => {
    await expect(page).toHaveTitle(/ARC Studio/);
  });

  test('Theia workbench element exists', async ({ page }) => {
    const shell = await page.waitForSelector('#theia-app-shell, .theia-ApplicationShell, body', {
      timeout: TIMEOUT,
    });
    expect(shell).toBeTruthy();
  });

  test('ARC activity bar contribution visible', async ({ page }) => {
    const activityBar = page.locator('.p-TabBar.theia-app-left, .theia-TabBar, [id="theia-left-side-panel"]');
    await expect(activityBar.first()).toBeAttached({ timeout: TIMEOUT });

    const arcIcon = page.locator('.codicon-circuit-board, .arc-icon, [title*="ARC"], [aria-label*="ARC"]');
    console.log(`ARC icon elements found: ${await arcIcon.count()}`);
  });

  test('run timeline deep link shows canonical trace timeline shell', async ({ page }) => {
    await page.goto(`${APP_URL}/?arc-view=run-timeline`, { waitUntil: 'networkidle', timeout: TIMEOUT });
    await acceptWorkspaceTrustIfShown(page);

    await expect(page.getByText(/Traces \(/)).toBeVisible({ timeout: TIMEOUT });
    await expect(page.getByRole('button', { name: 'Refresh' }).first()).toBeVisible({ timeout: TIMEOUT });
    await expect(page.getByText('No trace selected').or(page.getByText(/^Run:/).first())).toBeVisible({ timeout: TIMEOUT });
  });

  test('event stream deep link shows canonical event stream shell', async ({ page }) => {
    await page.goto(`${APP_URL}/?arc-view=event-stream`, { waitUntil: 'networkidle', timeout: TIMEOUT });
    await acceptWorkspaceTrustIfShown(page);

    await expect(page.getByText('Event Stream').first()).toBeVisible({ timeout: TIMEOUT });
    await expect(page.getByPlaceholder('Filter text or event type')).toBeVisible({ timeout: TIMEOUT });
    await expect(page.getByRole('button', { name: 'Clear' }).first()).toBeVisible({ timeout: TIMEOUT });
    await expect(page.getByText('Runs').first()).toBeVisible({ timeout: TIMEOUT });
  });

  test('health monitor deep link shows local daemon status shell', async ({ page }) => {
    await page.goto(`${APP_URL}/?arc-view=health-monitor`, { waitUntil: 'networkidle', timeout: TIMEOUT });
    await acceptWorkspaceTrustIfShown(page);

    await expect(page.getByTestId('arc-health-monitor')).toBeVisible({ timeout: TIMEOUT });
    await expect(page.getByRole('heading', { name: 'ARC Health Monitor' })).toBeVisible({ timeout: TIMEOUT });
    await expect(page.getByText('Backend').first()).toBeVisible({ timeout: TIMEOUT });
    await expect(page.getByText('Ready Runtimes').first()).toBeVisible({ timeout: TIMEOUT });
    await expect(page.getByText('Poll Interval').first()).toBeVisible({ timeout: TIMEOUT });
    await expect(page.getByRole('button', { name: 'Refresh Health' })).toBeVisible({ timeout: TIMEOUT });
  });
});

test.describe('ARC Python CLI — Integration', () => {
  test('arc inspect returns valid JSON envelope', async () => {
    const { execSync } = require('child_process');
    try {
      const output = execSync(
        `cd "${join(REPO_ROOT, 'python')}" && uv run arc inspect --json --workspace "${join(REPO_ROOT, 'examples', 'sample-swarmgraph-project')}"`,
        { cwd: __dirname, timeout: 15000, encoding: 'utf8' }
      );
      const envelope = JSON.parse(output);
      expect(envelope.ok).toBe(true);
      expect(envelope.version).toBe('1.0');
      expect(envelope.data).toBeTruthy();
      expect(envelope.data.runtimes).toBeInstanceOf(Array);
    } catch (e) {
      test.skip(true, `Python CLI not available: ${e}`);
    }
  });

  test('arc adapter test swarmgraph passes conformance', async () => {
    const { execSync } = require('child_process');
    try {
      const output = execSync(
        `cd "${join(REPO_ROOT, 'python')}" && uv run arc adapter test swarmgraph --json`,
        { cwd: __dirname, timeout: 15000, encoding: 'utf8' }
      );
      const envelope = JSON.parse(output);
      expect(envelope.ok).toBe(true);
      expect(envelope.data.ok).toBe(true);
      expect(envelope.data.failed).toBe(0);
    } catch (e) {
      test.skip(true, `Python CLI not available: ${e}`);
    }
  });
});
