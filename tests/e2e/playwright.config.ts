import { defineConfig, devices } from '@playwright/test';
import { join } from 'path';

const e2eWorkspace = join(__dirname, '..', '..');
const e2eSwarmGraphCli = join(__dirname, 'fixtures', 'swarmgraph-stub.sh');
const reuseExistingServer = process.env.ARC_E2E_REUSE_SERVER === 'true';
const defaultPortOffset = process.env.CI ? 0 : Math.floor(Math.random() * 1000);
const e2ePort = process.env.ARC_E2E_PORT || String(3010 + defaultPortOffset);
const e2eUrl = process.env.ARC_E2E_URL || `http://127.0.0.1:${e2ePort}`;
const e2eDaemonPort = process.env.ARC_E2E_DAEMON_PORT || String(32173 + defaultPortOffset);
const e2eDaemonUrl = process.env.ARC_E2E_DAEMON_URL || `http://127.0.0.1:${e2eDaemonPort}`;
const e2eDaemonRunId = process.env.ARC_E2E_DAEMON_RUN_ID || 'run-e2e-live-daemon';

process.env.ARC_E2E_REQUIRE_RUNTIME = process.env.ARC_E2E_REQUIRE_RUNTIME || 'true';
process.env.ARC_E2E_PORT = e2ePort;
process.env.ARC_E2E_URL = e2eUrl;
process.env.ARC_E2E_DAEMON_PORT = e2eDaemonPort;
process.env.ARC_E2E_DAEMON_URL = e2eDaemonUrl;
process.env.ARC_E2E_DAEMON_RUN_ID = e2eDaemonRunId;

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
  webServer: [
    {
      command: `node fixtures/daemon-sse-fixture.cjs`,
      cwd: __dirname,
      url: e2eDaemonUrl,
      reuseExistingServer,
      timeout: 30_000,
      env: {
        PATH: process.env.PATH,
        NODE_ENV: process.env.NODE_ENV,
        ARC_E2E_DAEMON_PORT: e2eDaemonPort,
      },
    },
    {
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
        ARC_PYTHON_DAEMON_URL: process.env.ARC_PYTHON_DAEMON_URL || e2eDaemonUrl,
      },
    },
  ],
});
