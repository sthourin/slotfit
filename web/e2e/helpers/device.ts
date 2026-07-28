import type { Page } from '@playwright/test'

export const E2E_DEVICE_ID = 'e2e-0000-4000-8000-fixed-device-01'

export async function useDevice(page: Page): Promise<void> {
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    ['slotfit_device_id', E2E_DEVICE_ID]
  )
}
