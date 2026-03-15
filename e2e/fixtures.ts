/**
 * Shared Playwright fixtures for E2E tests.
 *
 * Provides helpers to interact with the backend API directly (bypassing the
 * frontend) for test setup: seeding towers, authenticating, and resetting state.
 */

import { test as base, expect, type APIRequestContext } from '@playwright/test'

const BACKEND_URL = 'http://localhost:8080'
const ADMIN_PASSWORD = 'e2e-test-password'

/** Helper to authenticate against the backend and return a Bearer token. */
async function getAdminToken(request: APIRequestContext): Promise<string> {
  const response = await request.post(`${BACKEND_URL}/auth/login`, {
    data: { password: ADMIN_PASSWORD },
  })
  expect(response.ok()).toBe(true)
  const body = await response.json()
  return body.token as string
}

/** Wipe all towers (and cascaded tasks/paths) so each test starts clean. */
async function clearAllTowers(request: APIRequestContext, token: string): Promise<void> {
  const response = await request.get(`${BACKEND_URL}/towers`)
  const { towers } = await response.json()
  for (const tower of towers) {
    await request.delete(`${BACKEND_URL}/towers/${tower.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
  }
}

/** Extended test fixture that exposes admin helpers. */
export const test = base.extend<{
  adminToken: string
  backendUrl: string
  adminPassword: string
}>({
  adminToken: async ({ request }, use) => {
    const token = await getAdminToken(request)
    await clearAllTowers(request, token)
    await use(token)
  },
  backendUrl: BACKEND_URL,
  adminPassword: ADMIN_PASSWORD,
})

export { expect }
