import { test, expect } from '@playwright/test'
import { useDevice } from './helpers/device'

test.beforeEach(async ({ page }) => {
  await useDevice(page)
})

// Depends on the 'E2E Push Day' routine created by routine-designer.spec.ts
// (workers: 1, alphabetical order guarantees it runs first)
test('start a workout from routine, log a set, complete it', async ({ page }) => {
  // Accept confirm() dialogs (Complete Workout confirmation)
  page.on('dialog', (dialog) => dialog.accept())

  await page.goto('/workout/start')

  // Step 1: select the routine
  await page.getByRole('button', { name: /E2E Push Day/ }).first().click()

  // Step 4 review appears, then start
  await expect(page.getByRole('heading', { name: '4. Review Exercises' })).toBeVisible({
    timeout: 10_000,
  })
  await page.getByRole('button', { name: 'Start Workout' }).click()

  // Active workout page
  await expect(page.getByRole('heading', { name: 'Active Workout' })).toBeVisible({
    timeout: 10_000,
  })

  // Slot has no exercise: open the selector and use the search tab
  await page.getByRole('button', { name: 'Select Exercise' }).click()
  await expect(page.getByRole('heading', { name: 'Select Exercise' })).toBeVisible()
  await page.getByRole('button', { name: 'Search All Exercises' }).click()
  await page.getByPlaceholder('Search exercises by name...').fill('push up')
  await page.getByRole('button', { name: 'Select', exact: true }).first().click()

  // Start the slot and log a set
  await page.getByRole('button', { name: 'Start Slot' }).click()
  await page.getByRole('button', { name: '+ Add Set' }).click()
  await expect(page.getByText('1 set logged')).toBeVisible()

  // Complete the slot, then the workout (confirms via dialog handler)
  await page.getByRole('button', { name: 'Complete Slot' }).click()
  const [response] = await Promise.all([
    page.waitForResponse(
      (r) => /\/workouts\/\d+\/complete/.test(r.url()) && r.request().method() === 'POST'
    ),
    page.getByRole('button', { name: 'Complete Workout' }).click(),
  ])
  expect(response.status()).toBeLessThan(300)

  // Summary modal
  await expect(page.getByRole('heading', { name: /Workout Complete/ })).toBeVisible({
    timeout: 10_000,
  })
})
