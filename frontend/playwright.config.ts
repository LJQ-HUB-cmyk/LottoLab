import { defineConfig } from '@playwright/test'
import { existsSync } from 'node:fs'

const edge = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
export default defineConfig({
  testDir: './e2e',
  testMatch: 'workbench.spec.ts',
  timeout: 90000,
  expect: { timeout: 15000 },
  workers: 1,
  fullyParallel: false,
  outputDir: 'test-results/local',
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report/local' }]],
  use: {
    baseURL: 'http://127.0.0.1:8011',
    viewport: { width: 1440, height: 1000 },
    actionTimeout: 15000,
    launchOptions: existsSync(edge) ? { executablePath: edge } : {},
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `${process.platform === 'win32' ? '"..\\.venv\\Scripts\\python.exe"' : 'python'} ../scripts/e2e_server.py`,
    url: 'http://127.0.0.1:8011/api/v1/health',
    timeout: 60000,
    reuseExistingServer: false,
    gracefulShutdown: { signal: 'SIGTERM', timeout: 10000 },
  },
})
