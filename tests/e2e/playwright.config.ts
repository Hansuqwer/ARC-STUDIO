import { defineConfig, devices } from '@playwright/test';

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
  },
});
