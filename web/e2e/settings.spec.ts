import { test, expect } from '@playwright/test'
import { useDevice } from './helpers/device'

test.beforeEach(async ({ page }) => {
  await useDevice(page)
})

test('settings page loads profile for device user', async ({ page }) => {
  await page.goto('/settings')
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Profile', exact: true })).toBeVisible({
    timeout: 10_000,
  })
  // Edit Profile button confirms the profile section rendered with a user loaded
  await expect(page.getByRole('button', { name: 'Edit Profile' })).toBeVisible()
})

test('editing display name persists across reload', async ({ page }) => {
  await page.goto('/settings')
  await page.getByRole('button', { name: 'Edit Profile' }).click()
  const nameInput = page.getByPlaceholder('Enter your display name')
  await nameInput.fill('E2E Tester')
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  // Save exits edit mode and shows the name as text
  await expect(page.getByText('E2E Tester')).toBeVisible({ timeout: 10_000 })
  await page.reload()
  await expect(page.getByText('E2E Tester')).toBeVisible({ timeout: 10_000 })
})
