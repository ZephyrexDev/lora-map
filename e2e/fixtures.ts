/**
 * Shared Playwright fixtures for E2E tests.
 *
 * Provides helpers to interact with the backend API directly (bypassing the
 * frontend) for test setup: authenticating and seeding data.
 *
 * The DB is wiped at the start of each Playwright run (rm in webServer command),
 * so tests share a single clean database within a run.
 */

import { test as base, expect, type APIRequestContext } from '@playwright/test'

const BACKEND_URL = 'http://localhost:8080'
const ADMIN_PASSWORD = 'e2e-test-password'

/** Cached admin token — login only once per Playwright run to avoid rate limiting. */
let cachedToken: string | null = null

/** Helper to authenticate against the backend and return a Bearer token. */
async function getAdminToken(request: APIRequestContext): Promise<string> {
  if (cachedToken !== null) return cachedToken
  const response = await request.post(`${BACKEND_URL}/auth/login`, {
    data: { password: ADMIN_PASSWORD },
  })
  expect(response.ok()).toBe(true)
  const body = await response.json()
  cachedToken = body.token as string
  return cachedToken
}

/** Extended test fixture that exposes admin helpers. */
export const test = base.extend<{
  adminToken: string
  backendUrl: string
  adminPassword: string
}>({
  adminToken: async ({ request }, use) => {
    const token = await getAdminToken(request)
    await use(token)
  },
  backendUrl: BACKEND_URL,
  adminPassword: ADMIN_PASSWORD,
})

export { expect }
