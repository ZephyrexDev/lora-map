import { defineConfig, devices } from '@playwright/test'

const BACKEND_PORT = 8080
const FRONTEND_PORT = 5173

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: `ADMIN_PASSWORD=e2e-test-password DB_PATH=/tmp/e2e-test.db uv run uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}`,
      port: BACKEND_PORT,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: `pnpm run dev --port ${FRONTEND_PORT}`,
      port: FRONTEND_PORT,
      reuseExistingServer: !process.env.CI,
      timeout: 15_000,
    },
  ],
})
