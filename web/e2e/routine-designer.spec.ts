import { test, expect } from '@playwright/test'
import { useDevice } from './helpers/device'

test.beforeEach(async ({ page }) => {
  await useDevice(page)
})

test('create a routine with one slot and save it', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Create New Routine' }).click()

  // Name the routine
  const nameInput = page.getByPlaceholder('Enter routine name')
  await expect(nameInput).toHaveValue('New Routine')
  await nameInput.fill('E2E Push Day')

  // Add a slot
  await page.getByRole('button', { name: '+ Add Slot' }).click()
  await expect(page.getByText('Slots (1)')).toBeVisible()

  // Save to backend and confirm the API call succeeds
  const [response] = await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes('/api/v1/routines') && r.request().method() === 'POST'
    ),
    page.getByRole('button', { name: 'Save Routine' }).click(),
  ])
  expect(response.status()).toBeLessThan(300)
  await expect(page.getByText('Routine saved successfully!')).toBeVisible({ timeout: 10_000 })
  await expect(page.getByText(/Routine ID: \d+/)).toBeVisible()
})
