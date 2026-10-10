import fs from 'node:fs';
import { defineConfig } from '@playwright/test';

const chromePath = process.env.PLAYWRIGHT_CHROME_PATH
  || (fs.existsSync('/usr/bin/google-chrome') ? '/usr/bin/google-chrome' : undefined);

export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: 'line',
  use: {
    baseURL: process.env.DASHBOARD_URL || 'http://127.0.0.1:5173',
    headless: true,
    trace: 'retain-on-failure',
    launchOptions: chromePath ? { executablePath: chromePath } : {},
  },
});
