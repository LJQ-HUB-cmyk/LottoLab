import { defineConfig } from '@playwright/test'
import base from './playwright.config'

export default defineConfig({
  ...base,
  testMatch: 'cloud.spec.ts',
  outputDir: 'test-results/cloud',
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report/cloud' }]],
  use: { ...base.use, baseURL: 'http://127.0.0.1:8012' },
  webServer: {
    command: `${process.platform === 'win32' ? '"..\\.venv\\Scripts\\python.exe"' : 'python'} ../scripts/e2e_server.py --cloud`,
    url: 'http://127.0.0.1:8012/api/v1/health',
    timeout: 60000,
    reuseExistingServer: false,
    gracefulShutdown: { signal: 'SIGTERM', timeout: 10000 },
  },
})
