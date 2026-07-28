import { test, expect } from '@playwright/test'

test('app shell loads with all navigation links', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('link', { name: 'SlotFit' })).toBeVisible()
  for (const label of [
    'Routine Designer',
    'Start Workout',
    'Exercise Browser',
    'History',
    'Analytics',
    'Records',
    'Settings',
  ]) {
    await expect(page.getByRole('link', { name: label })).toBeVisible()
  }
})

test('device id is generated in localStorage', async ({ page }) => {
  await page.goto('/')
  await expect
    .poll(async () => page.evaluate(() => localStorage.getItem('slotfit_device_id')))
    .toBeTruthy()
})
