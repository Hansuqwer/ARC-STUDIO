import { defineConfig, devices } from '@playwright/test';
import { existsSync } from 'fs';

const localSwarmGraphCli = '/Users/hansvilund/HansuQWER/WorkSpace/ARC/SwarmGraph/swarmgraph';
const localSwarmGraphWorkspace = '/Users/hansvilund/HansuQWER/WorkSpace/ARC/SwarmGraph';

export default defineConfig({
  testDir: '.',
  timeout: 60_000,
  retries: 1,
  reporter: [['list'], ['html', { open: 'never', outputFolder: '../../test-results/e2e-html' }]],
  use: {
    baseURL: process.env.ARC_E2E_URL || 'http://localhost:3000',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    headless: true,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'pnpm --filter @arc-studio/browser start',
    cwd: '../..',
    url: process.env.ARC_E2E_URL || 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 60_000,
    env: {
      ...process.env,
      ...(process.env.ARC_SWARMGRAPH_CLI || existsSync(localSwarmGraphCli) ? { ARC_SWARMGRAPH_CLI: process.env.ARC_SWARMGRAPH_CLI || localSwarmGraphCli } : {}),
      ...(process.env.ARC_WORKSPACE_PATH || existsSync(localSwarmGraphWorkspace) ? { ARC_WORKSPACE_PATH: process.env.ARC_WORKSPACE_PATH || localSwarmGraphWorkspace } : {}),
      ARC_SWARMGRAPH_RUN_BACKEND: process.env.ARC_SWARMGRAPH_RUN_BACKEND || 'stub',
    },
  },
});
