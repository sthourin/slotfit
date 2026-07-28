import { test, expect } from '@playwright/test'
import { useDevice } from './helpers/device'

test.beforeEach(async ({ page }) => {
  await useDevice(page)
})

// This spec runs BEFORE workout-critical-path.spec.ts (alphabetical order),
// so on a fresh database no completed workout exists yet. It asserts only
// that pages render without crashes; data presence is verified manually
// after the full ordered run.
for (const [path, heading] of [
  ['/history', 'Workout History'],
  ['/analytics', 'Analytics Dashboard'],
  ['/records', 'Personal Records'],
] as const) {
  test(`page ${path} renders without console errors`, async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', (e) => errors.push(e.message))
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text())
    })
    await page.goto(path)
    await expect(page.getByRole('heading', { name: heading }).first()).toBeVisible({
      timeout: 10_000,
    })
    // Allow network 404s for optional data but no crashes
    expect(errors.filter((e) => !/404|Failed to load resource/i.test(e))).toEqual([])
  })
}
