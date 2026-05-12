import { defineConfig, devices } from '@playwright/test';
import { join } from 'path';

const e2eWorkspace = join(__dirname, '..', '..');
const e2eSwarmGraphCli = join(__dirname, 'fixtures', 'swarmgraph-stub.sh');
const reuseExistingServer = process.env.ARC_E2E_REUSE_SERVER === 'true';
const e2ePort = process.env.ARC_E2E_PORT || '3010';
const e2eUrl = process.env.ARC_E2E_URL || `http://localhost:${e2ePort}`;

process.env.ARC_E2E_REQUIRE_RUNTIME = process.env.ARC_E2E_REQUIRE_RUNTIME || 'true';
process.env.ARC_E2E_PORT = e2ePort;
process.env.ARC_E2E_URL = e2eUrl;

export default defineConfig({
  testDir: '.',
  timeout: 90_000,
  retries: 1,
  reporter: [['list'], ['html', { open: 'never', outputFolder: '../../test-results/e2e-html' }]],
  use: {
    baseURL: e2eUrl,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    headless: true,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: `pnpm --filter @arc-studio/browser exec theia start --port ${e2ePort} --hostname 127.0.0.1 --root-dir "${e2eWorkspace}"`,
    cwd: '../..',
    url: e2eUrl,
    reuseExistingServer,
    timeout: 90_000,
    env: {
      PATH: process.env.PATH,
      HOME: process.env.HOME,
      TMPDIR: process.env.TMPDIR,
      NODE_ENV: process.env.NODE_ENV,
      ARC_SWARMGRAPH_CLI: process.env.ARC_SWARMGRAPH_CLI || e2eSwarmGraphCli,
      ARC_WORKSPACE_PATH: process.env.ARC_WORKSPACE_PATH || e2eWorkspace,
      ARC_SWARMGRAPH_RUN_BACKEND: process.env.ARC_SWARMGRAPH_RUN_BACKEND || 'stub',
      ARC_E2E_REQUIRE_RUNTIME: process.env.ARC_E2E_REQUIRE_RUNTIME || 'true',
    },
  },
});
