import { test, expect } from './fixtures'

test.describe('Admin authentication', () => {
  test('login modal opens and accepts correct password', async ({ page, adminPassword }) => {
    await page.goto('/')

    // Open login modal
    await page.locator('[data-bs-target="#loginModal"]').click()
    await expect(page.locator('#loginModal')).toBeVisible()
    await expect(page.locator('#loginModalLabel')).toContainText('Admin Login')

    // Fill in password and submit
    await page.locator('#passwordInput').fill(adminPassword)
    await page.locator('#loginModal button[type="submit"]').click()

    // Wait for modal to close and UI to update
    await expect(page.locator('[data-bs-target="#loginModal"]')).toHaveClass(/btn-outline-success/, {
      timeout: 10_000,
    })

    // Admin-only elements should appear in the offcanvas
    await expect(page.locator('#runSimulation')).toBeVisible({ timeout: 5_000 })
  })

  test('login modal rejects incorrect password', async ({ page }) => {
    await page.goto('/')

    await page.locator('[data-bs-target="#loginModal"]').click()
    await expect(page.locator('#loginModal')).toBeVisible()

    await page.locator('#passwordInput').fill('wrong-password')
    await page.locator('#loginModal button[type="submit"]').click()

    // Error message should appear
    await expect(page.locator('#loginModal .alert-danger')).toContainText('Invalid password')

    // Should still be in visitor mode
    await expect(page.locator('[data-bs-target="#loginModal"]')).toHaveClass(/btn-outline-secondary/)
  })

  test('admin can logout', async ({ page, adminPassword }) => {
    await page.goto('/')

    // Login first
    await page.locator('[data-bs-target="#loginModal"]').click()
    await page.locator('#passwordInput').fill(adminPassword)
    await page.locator('#loginModal button[type="submit"]').click()
    await expect(page.locator('[data-bs-target="#loginModal"]')).toHaveClass(/btn-outline-success/, {
      timeout: 10_000,
    })

    // Wait for modal and backdrop to fully close
    await expect(page.locator('#loginModal')).toBeHidden({ timeout: 5_000 })
    await expect(page.locator('.modal-backdrop')).toBeHidden({ timeout: 5_000 })

    // Open modal again — should show "Logged In" with logout button
    await page.locator('[data-bs-target="#loginModal"]').click()
    await expect(page.locator('#loginModalLabel')).toContainText('Logged In')
    await page.locator('#loginModal button', { hasText: 'Logout' }).click()

    // Should be back in visitor mode
    await expect(page.locator('[data-bs-target="#loginModal"]')).toHaveClass(/btn-outline-secondary/, {
      timeout: 5_000,
    })
  })

  test('protected API endpoints reject unauthenticated requests', async ({ request, backendUrl }) => {
    const response = await request.post(`${backendUrl}/predict`, {
      data: { lat: 40.0, lon: -105.0, tx_power: 20.0 },
    })
    expect(response.status()).toBe(401)
  })

  test('protected API endpoints accept valid token', async ({ request, backendUrl, adminToken }) => {
    // GET /matrix/config is public, but PUT requires admin
    const response = await request.get(`${backendUrl}/matrix/config`)
    expect(response.ok()).toBe(true)
    const config = await response.json()

    const putResponse = await request.put(`${backendUrl}/matrix/config`, {
      headers: { Authorization: `Bearer ${adminToken}` },
      data: config,
    })
    expect(putResponse.ok()).toBe(true)
  })
})
