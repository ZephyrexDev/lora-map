import { test, expect } from './fixtures'

test.describe('Visitor flow', () => {
  test('app loads with navbar and map container', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('.navbar-brand')).toContainText('LoRa Coverage Planner')
    await expect(page.locator('#map')).toBeVisible()
  })

  test('shows visitor mode UI when not logged in', async ({ page }) => {
    await page.goto('/')
    // The lock icon button should indicate visitor mode
    const lockBtn = page.locator('[data-bs-target="#loginModal"]')
    await expect(lockBtn).toHaveClass(/btn-outline-secondary/)
    // Should show "Log in as admin" text
    await expect(page.locator('.offcanvas-body')).toContainText('Log in as admin')
  })

  test('towers endpoint returns empty list on clean DB', async ({ page, adminToken }) => {
    // adminToken fixture clears all towers
    await page.goto('/')
    // "No towers" message should be visible
    await expect(page.getByText('No towers')).toBeVisible()
  })

  test('GET /towers API returns valid JSON', async ({ request, backendUrl, adminToken }) => {
    // adminToken fixture clears all towers
    const response = await request.get(`${backendUrl}/towers`)
    expect(response.ok()).toBe(true)
    const body = await response.json()
    expect(body).toHaveProperty('towers')
    expect(Array.isArray(body.towers)).toBe(true)
  })

  test('GET /tower-paths API returns valid JSON', async ({ request, backendUrl }) => {
    const response = await request.get(`${backendUrl}/tower-paths`)
    expect(response.ok()).toBe(true)
    const body = await response.json()
    expect(body).toHaveProperty('paths')
    expect(Array.isArray(body.paths)).toBe(true)
  })

  test('GET /matrix/config API returns valid config', async ({ request, backendUrl }) => {
    const response = await request.get(`${backendUrl}/matrix/config`)
    expect(response.ok()).toBe(true)
    const body = await response.json()
    expect(body).toHaveProperty('hardware')
    expect(body).toHaveProperty('antennas')
    expect(body).toHaveProperty('terrain')
  })

  test('map initializes with Leaflet tiles', async ({ page }) => {
    await page.goto('/')
    // Wait for Leaflet to initialize and start loading tiles
    await expect(page.locator('.leaflet-container')).toBeVisible()
    await expect(page.locator('.leaflet-tile-pane')).toBeVisible()
  })
})
