import { test, expect } from './fixtures'

test.describe('API integration', () => {
  test('tower CRUD lifecycle via API', async ({ request, backendUrl, adminToken }) => {
    const headers = { Authorization: `Bearer ${adminToken}` }

    // Create a tower via /predict
    const predictResponse = await request.post(`${backendUrl}/predict`, {
      headers,
      data: { lat: 40.0, lon: -105.0, tx_power: 20.0 },
    })
    expect(predictResponse.status()).toBe(201)
    const { task_id, tower_id } = await predictResponse.json()
    expect(task_id).toBeTruthy()
    expect(tower_id).toBeTruthy()

    // Tower should appear in GET /towers
    const towersResponse = await request.get(`${backendUrl}/towers`)
    const { towers } = await towersResponse.json()
    expect(towers.some((t: { id: string }) => t.id === tower_id)).toBe(true)

    // Task status should be valid
    const statusResponse = await request.get(`${backendUrl}/status/${task_id}`)
    expect(statusResponse.ok()).toBe(true)
    const status = await statusResponse.json()
    expect(['processing', 'completed', 'failed']).toContain(status.status)

    // Delete the tower
    const deleteResponse = await request.delete(`${backendUrl}/towers/${tower_id}`, { headers })
    expect(deleteResponse.ok()).toBe(true)

    // Tower should no longer appear
    const towersAfter = await request.get(`${backendUrl}/towers`)
    const { towers: remaining } = await towersAfter.json()
    expect(remaining.some((t: { id: string }) => t.id === tower_id)).toBe(false)
  })

  test('matrix config round-trip', async ({ request, backendUrl, adminToken }) => {
    const headers = { Authorization: `Bearer ${adminToken}` }

    // Read current config
    const getResponse = await request.get(`${backendUrl}/matrix/config`)
    expect(getResponse.ok()).toBe(true)
    const original = await getResponse.json()

    // Update with same values (idempotent)
    const putResponse = await request.put(`${backendUrl}/matrix/config`, {
      headers,
      data: original,
    })
    expect(putResponse.ok()).toBe(true)
    const updated = await putResponse.json()
    expect(updated.hardware).toEqual(original.hardware)
    expect(updated.antennas).toEqual(original.antennas)
    expect(updated.terrain).toEqual(original.terrain)
  })

  test('tower-paths requires at least 2 towers', async ({ request, backendUrl, adminToken }) => {
    const headers = { Authorization: `Bearer ${adminToken}` }

    // With 0 towers, should fail
    const response = await request.post(`${backendUrl}/tower-paths`, { headers })
    expect(response.status()).toBe(400)
    const body = await response.json()
    expect(body.detail).toContain('at least 2 towers')
  })

  test('tower-paths computed for multiple towers', async ({ request, backendUrl, adminToken }) => {
    const headers = { Authorization: `Bearer ${adminToken}` }

    // Create two towers
    const tower1 = await request.post(`${backendUrl}/predict`, {
      headers,
      data: { lat: 40.0, lon: -105.0, tx_power: 20.0 },
    })
    expect(tower1.status()).toBe(201)

    const tower2 = await request.post(`${backendUrl}/predict`, {
      headers,
      data: { lat: 40.1, lon: -105.1, tx_power: 20.0 },
    })
    expect(tower2.status()).toBe(201)

    // Compute paths
    const pathsResponse = await request.post(`${backendUrl}/tower-paths`, { headers })
    expect(pathsResponse.status()).toBe(202)
    const { paths, count } = await pathsResponse.json()
    expect(count).toBeGreaterThanOrEqual(1)
    expect(paths.length).toBe(count)

    // Verify paths appear in GET /tower-paths
    const listResponse = await request.get(`${backendUrl}/tower-paths`)
    expect(listResponse.ok()).toBe(true)
    const { paths: listedPaths } = await listResponse.json()
    expect(listedPaths.length).toBeGreaterThanOrEqual(1)
  })

  test('deadzones requires at least 2 completed simulations', async ({ request, backendUrl }) => {
    const response = await request.get(`${backendUrl}/deadzones`)
    expect(response.status()).toBe(400)
    const body = await response.json()
    expect(body.detail).toContain('at least 2')
  })

  test('admin login enables map and simulation UI', async ({ page, adminPassword }) => {
    await page.goto('/')

    // Close the offcanvas sidebar so it doesn't intercept clicks on login button
    await page.locator('[data-bs-dismiss="offcanvas"]').click()
    await expect(page.locator('#offcanvasDarkNavbar')).toBeHidden({ timeout: 5_000 })

    // Open login modal via navbar button
    await page.locator('[data-bs-target="#loginModal"]').click()
    await expect(page.locator('#loginModal')).toBeVisible()
    await page.locator('#passwordInput').fill(adminPassword)
    await page.locator('#loginModal button[type="submit"]').click()

    // Wait for login to complete — button class changes to success
    await expect(page.locator('[data-bs-target="#loginModal"]')).toHaveClass(/btn-outline-success/, {
      timeout: 10_000,
    })

    // Wait for modal and backdrop to fully close
    await expect(page.locator('#loginModal')).toBeHidden({ timeout: 5_000 })
    await expect(page.locator('.modal-backdrop')).toBeHidden({ timeout: 5_000 })

    // After login, Transmitter component mounts and initializes the map
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 10_000 })

    // Re-open the offcanvas to verify admin controls
    await page.locator('[data-bs-target="#offcanvasDarkNavbar"]').click()
    await expect(page.locator('#runSimulation')).toBeVisible({ timeout: 5_000 })
  })
})
