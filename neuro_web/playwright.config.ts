import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60000,
  retries: 1,
  reporter: [['list'], ['json', { outputFile: '/tmp/pw-results.json' }]],
  use: {
    baseURL: 'http://localhost:3002',
    headless: false,
    screenshot: 'on',
    video: 'on',
    // Give extra time for LiveKit and API calls
    actionTimeout: 10000,
    navigationTimeout: 15000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // Don't start dev server — we run it separately
  webServer: undefined,
});
