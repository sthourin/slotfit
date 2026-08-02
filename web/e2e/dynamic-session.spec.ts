/**
 * End-to-end critical path for pattern-based dynamic sessions.
 *
 * The vignette: walk into the gym, create a day plan with pattern goals, pick
 * whatever compound station is free (the "anchor"), accept the app's partner
 * suggestion working the OPPOSITE movement pattern, log a set, watch coverage
 * update, and finish.
 *
 * Data assumptions (verified against the e2e database):
 *   - "Barbell Bent Over Row" is classified Horizontal Pull
 *   - "Barbell Bench Press" is classified Horizontal Push (its opposite)
 *   - "Suspension Archer Row" is classified Horizontal Pull (the distractor)
 * All three must be in the user's staple pool before they can be suggested,
 * which is what the Exercise Browser's "Add to Staples" action is for.
 *
 * Why a third staple: with only an opposite-pattern pair in the pool, asserting
 * that the partner picker offers the Horizontal Push exercise proves nothing --
 * it is the only other staple, so an engine that filtered to the opposite
 * pattern and one that simply listed every other staple would render the same
 * UI. The distractor is a SECOND Horizontal Pull, so the partner list at
 * position 2 must exclude it. That exclusion is the assertion that can fail,
 * and it is what actually tests antagonist pairing.
 */
import { test, expect, type Page, type APIRequestContext } from '@playwright/test'
import { useDevice, E2E_DEVICE_ID } from './helpers/device'

const API = 'http://localhost:8000/api/v1'
const apiHeaders = { 'X-Device-ID': E2E_DEVICE_ID }

const ANCHOR = 'Barbell Bent Over Row' // Horizontal Pull
const PARTNER = 'Barbell Bench Press' // Horizontal Push - the antagonist
// Same pattern as the anchor, so it must NOT be offered as a position-2 partner.
const DISTRACTOR = 'Suspension Archer Row' // Horizontal Pull

/**
 * A session left active by an earlier run makes `POST /sessions/` 409, so the
 * suite must start from a clean slate. Day plans are left alone: each run
 * creates a uniquely named one and addresses it by name.
 */
async function discardActiveSession(request: APIRequestContext): Promise<void> {
  const res = await request.get(`${API}/sessions/active`, { headers: apiHeaders })
  if (!res.ok()) return
  const body = (await res.text()).trim()
  if (!body || body === 'null') return
  const session = JSON.parse(body)
  if (session?.id) {
    await request.post(`${API}/sessions/${session.id}/discard`, { headers: apiHeaders })
  }
}

/**
 * Add one exercise to the staple pool via the Exercise Browser, scoping the
 * click to the card whose heading is an exact match so a substring collision
 * ("Barbell Close Grip Bench Press") cannot staple the wrong exercise.
 */
async function addStapleViaBrowser(page: Page, exerciseName: string): Promise<void> {
  await page.goto('/exercises')
  await page.getByPlaceholder('Search by name...').fill(exerciseName)
  const card = page
    .locator('div.bg-white.rounded-lg.shadow')
    .filter({ has: page.getByRole('heading', { name: exerciseName, exact: true }) })
    .first()
  await expect(card).toBeVisible({ timeout: 15_000 })
  await card.getByRole('button', { name: 'Add to Staples' }).click()
  // "Added" also appears on a 409 (already a staple), which keeps this idempotent
  // across repeated runs against the same database.
  await expect(card.getByText('Added')).toBeVisible({ timeout: 10_000 })
}

test.beforeEach(async ({ page, request }) => {
  await useDevice(page)
  await discardActiveSession(request)
})

test('create day plan, run a dynamic session with a superset round, finish', async ({ page }) => {
  page.on('dialog', (dialog) => dialog.accept())

  const planName = `E2E Dynamic Day ${Date.now()}`

  // --- Staples: anchor suggestions are drawn from the staple pool, which
  // starts empty for the e2e device. Both patterns must be represented or the
  // partner step at position 2 has no candidates. The distractor shares the
  // anchor's pattern and exists purely to be excluded from the partner list.
  await addStapleViaBrowser(page, ANCHOR)
  await addStapleViaBrowser(page, PARTNER)
  await addStapleViaBrowser(page, DISTRACTOR)

  // --- Create a day plan with opposing pattern goals. The goals are what make
  // the coverage chips render at all.
  await page.goto('/')
  await page.getByRole('button', { name: 'New Day Plan' }).click()
  await page.getByPlaceholder('e.g. Full Body A').fill(planName)
  await page.getByLabel('Horizontal Pull').check()
  await page.getByLabel('Horizontal Push').check()
  await page.getByRole('button', { name: 'Create Day Plan' }).click()

  const planRow = page
    .locator('div.bg-white.rounded-lg.shadow')
    .filter({ hasText: planName })
    .first()
  await expect(planRow).toBeVisible({ timeout: 10_000 })
  await expect(planRow).toContainText('Horizontal Pull')
  await expect(planRow).toContainText('Horizontal Push')

  // --- Start the session
  await planRow.getByRole('button', { name: 'Start Session' }).click()
  await expect(page.getByRole('heading', { name: 'Active Session' })).toBeVisible({
    timeout: 15_000,
  })

  // Coverage chips render because the plan carries pattern goals.
  const chips = page.getByTestId('coverage-chips')
  await expect(chips).toBeVisible()
  await expect(chips).toContainText('Horizontal Pull 0/3')
  await expect(chips).toContainText('Horizontal Push 0/3')

  // --- Round 1: pick the anchor from whatever station is free
  await page.getByRole('button', { name: /Start Round 1/ }).click()
  await expect(page.getByText(/Pick your anchor/)).toBeVisible({ timeout: 10_000 })

  const picker = page.getByTestId('picker')
  const anchorButton = picker.getByRole('button', { name: new RegExp(ANCHOR, 'i') })
  await expect(anchorButton).toHaveCount(1)
  // The distractor must be reachable HERE, in the anchor picker. If it were
  // missing from the staple pool, the "absent from the partner list" assertion
  // below would pass vacuously - this is what gives that assertion its teeth.
  await expect(picker.getByRole('button', { name: new RegExp(DISTRACTOR, 'i') })).toHaveCount(1)
  await anchorButton.click()

  // --- Partner suggestion: must offer the OPPOSITE pattern...
  await expect(page.getByText(/Partner suggestion/)).toBeVisible({ timeout: 10_000 })
  const partnerButton = picker.getByRole('button', { name: new RegExp(PARTNER, 'i') }).first()
  await expect(partnerButton).toBeVisible({ timeout: 10_000 })
  // ...and must NOT offer an exercise sharing the anchor's pattern. Checked only
  // after the candidates have rendered (line above), so an absence cannot be an
  // artifact of the list still loading. Scoped to the picker so the anchor's own
  // entry card, already on the page, cannot affect the count either way.
  await expect(picker.getByRole('button', { name: new RegExp(DISTRACTOR, 'i') })).toHaveCount(0)
  await partnerButton.click()

  // Both entries are now in the round; the picker closes.
  await expect(page.getByTestId('picker')).toHaveCount(0)
  const anchorCard = page
    .locator('div.bg-white.rounded-lg.border')
    .filter({ hasText: ANCHOR })
    .first()
  const partnerCard = page
    .locator('div.bg-white.rounded-lg.border')
    .filter({ hasText: PARTNER })
    .first()
  await expect(anchorCard).toBeVisible()
  await expect(partnerCard).toBeVisible()
  // The pattern label on each card proves the antagonist pairing, not just that
  // two exercises happened to be added.
  await expect(anchorCard).toContainText('horizontal pull')
  await expect(partnerCard).toContainText('horizontal push')

  // --- Log a set on each entry
  await anchorCard.getByPlaceholder('weight').fill('135')
  await anchorCard.getByPlaceholder('reps').fill('8')
  await anchorCard.getByRole('button', { name: 'Log Set' }).click()
  await expect(anchorCard).toContainText('1 sets', { timeout: 10_000 })

  await partnerCard.getByPlaceholder('weight').fill('185')
  await partnerCard.getByPlaceholder('reps').fill('5')
  await partnerCard.getByRole('button', { name: 'Log Set' }).click()
  await expect(partnerCard).toContainText('1 sets', { timeout: 10_000 })

  // --- Coverage reflects the logged work
  await expect(chips).toContainText('Horizontal Pull 1/3')
  await expect(chips).toContainText('Horizontal Push 1/3')

  // --- Finish and read the summary
  await page.getByRole('button', { name: 'Finish Session' }).click()
  await expect(page.getByRole('heading', { name: 'Session Complete' })).toBeVisible({
    timeout: 15_000,
  })
  const summary = page.getByText(/Round 1:/)
  await expect(summary).toBeVisible()
  await expect(page.getByText(`${ANCHOR} (1 sets)`)).toBeVisible()
  await expect(page.getByText(`${PARTNER} (1 sets)`)).toBeVisible()
})
