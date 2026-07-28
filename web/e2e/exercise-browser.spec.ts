import { test, expect } from '@playwright/test'
import { useDevice } from './helpers/device'

test.beforeEach(async ({ page }) => {
  await useDevice(page)
})

test('exercise browser lists seeded exercises', async ({ page }) => {
  await page.goto('/exercises')
  await expect(page.getByRole('heading', { name: 'Exercise Browser' })).toBeVisible()
  // 3,240 exercises are seeded; the first page of cards must render
  await expect(page.locator('h3').first()).toBeVisible({ timeout: 15_000 })
  expect(await page.locator('h3').count()).toBeGreaterThan(5)
})

test('search narrows results', async ({ page }) => {
  await page.goto('/exercises')
  const search = page.getByPlaceholder('Search by name...')
  await search.fill('bench press')
  await expect(page.locator('h3').filter({ hasText: /bench press/i }).first()).toBeVisible({
    timeout: 10_000,
  })
})
