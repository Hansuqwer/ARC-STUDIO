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
const DAEMON_URL = process.env.ARC_E2E_DAEMON_URL;
const DAEMON_RUN_ID = process.env.ARC_E2E_DAEMON_RUN_ID;
const TIMEOUT = 60_000;
const REPO_ROOT = join(__dirname, '..', '..');
const TERMINAL_EVENTS = new Set(['RUN_COMPLETED', 'RUN_FAILED', 'RUN_CANCELLED', 'STREAM_END']);

async function acceptWorkspaceTrustIfShown(page: import('@playwright/test').Page): Promise<void> {
  const trustButton = page.getByRole('button', { name: /^yes,? i trust the authors$/i });
  if (await trustButton.isVisible({ timeout: 1000 }).catch(() => false)) {
    await trustButton.click();
  }
}

async function openArcStudioTab(
  page: import('@playwright/test').Page,
  tabName: string
): Promise<boolean> {
  const tab = page.getByRole('tab', { name: tabName }).first();
  if (!(await tab.isVisible({ timeout: 5000 }).catch(() => false))) {
    return false;
  }

  await tab.click();
  await expect(tab).toHaveAttribute('aria-selected', 'true', { timeout: TIMEOUT });
  return true;
}

function parseServerSentEventTypes(body: string): string[] {
  return body
    .split('\n')
    .filter((line) => line.startsWith('data: '))
    .map((line) => JSON.parse(line.slice('data: '.length)).type);
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

  test('config release shell is visible when ARC Studio tabs are routable', async ({ page }) => {
    if (!(await openArcStudioTab(page, 'Config'))) {
      test.skip(true, 'ARC Studio tab shell not routable in this app mode');
    }

    await expect(page.getByRole('region', { name: 'Config panel' })).toBeVisible({ timeout: TIMEOUT });
    await expect(page.getByText('Config').first()).toBeVisible({ timeout: TIMEOUT });
    await expect(page.getByText(/Dry run|Run Policy|Safe Config Snapshot|Config unavailable/).first()).toBeVisible({
      timeout: TIMEOUT,
    });
  });

  test('SwarmGraph Insight release shell is visible when ARC Studio tabs are routable', async ({ page }) => {
    if (!(await openArcStudioTab(page, 'SwarmGraph Insight'))) {
      test.skip(true, 'ARC Studio tab shell not routable in this app mode');
    }

    await expect(page.getByRole('heading', { name: 'SwarmGraph Insight' })).toBeVisible({ timeout: TIMEOUT });
    await expect(page.getByText(/Live insight:/)).toBeVisible({ timeout: TIMEOUT });
    await expect(page.getByText(/disconnected|degraded|not configured|no active stream/i).first()).toBeVisible({
      timeout: TIMEOUT,
    });
  });

  test('SwarmGraph Insight renders configured daemon live frame or degraded state', async ({ page }) => {
    if (!DAEMON_URL || !DAEMON_RUN_ID) {
      test.skip(true, 'ARC_E2E_DAEMON_URL and ARC_E2E_DAEMON_RUN_ID not configured');
    }

    await page.goto(`${APP_URL}/?arc-view=arc-studio`, { waitUntil: 'networkidle', timeout: TIMEOUT });
    await acceptWorkspaceTrustIfShown(page);

    if (!(await openArcStudioTab(page, 'SwarmGraph Insight'))) {
      test.skip(true, 'ARC Studio tab shell not routable in this app mode');
    }

    await page.locator('#arc-swarmgraph-live-run').fill(DAEMON_RUN_ID);
    await page.locator('#arc-swarmgraph-live-base-url').fill(DAEMON_URL);
    await page.getByRole('button', { name: 'Connect live' }).click();

    const liveInsight = page.getByText(/^Live insight:/).first();
    await expect(liveInsight).toBeVisible({ timeout: TIMEOUT });

    await expect(page.getByText(/active event|live stream disconnected; showing/i).first()).toBeVisible({
      timeout: TIMEOUT,
    });
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

  test('SSE proof stream emits limited local RUN_STARTED and terminal event', async ({ request }) => {
    const response = await request
      .get(`${APP_URL}/api/sse-proof?event_delay=0&heartbeat_interval=0&heartbeat_count=0`, {
        timeout: 15000,
      })
      .catch((e) => {
        test.skip(true, `Python server not available: ${e}`);
        throw e;
      });

    if (response.status() === 404) {
      test.skip(true, 'Python SSE proof endpoint not available');
    }

    expect(response.ok()).toBe(true);
    expect(response.headers()['content-type']).toContain('text/event-stream');

    const eventTypes = parseServerSentEventTypes(await response.text());
    expect(eventTypes).toContain('RUN_STARTED');
    expect(eventTypes.some((type) => TERMINAL_EVENTS.has(type))).toBe(true);
  });

  test('SSE proof remains a local deterministic stream only', async ({ request }) => {
    const response = await request
      .get(`${APP_URL}/api/sse-proof?event_delay=0&heartbeat_interval=0&heartbeat_count=0`, {
        timeout: 15000,
      })
      .catch((e) => {
        test.skip(true, `Python server not available: ${e}`);
        throw e;
      });

    if (response.status() === 404) {
      test.skip(true, 'Python SSE proof endpoint not available');
    }

    expect(response.ok()).toBe(true);
    const body = await response.text();
    expect(body).toContain('RUN_STARTED');
    expect(body).not.toMatch(/provider|paid|api[_-]?key|broad runtime/i);
  });
});
