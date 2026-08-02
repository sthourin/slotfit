/**
 * Playwright globalSetup: reset the e2e database once before the suite.
 *
 * Each run logs sets against a persistent database. WEEKLY_SET_LIMIT caps a
 * muscle group at 20 sets per ISO week, so without a reset the volume filter
 * legitimately starts rejecting the partner suggestion after roughly ten runs
 * and the suite fails for a correct reason. A state filter cannot rescue this:
 * the flow under test ends by COMPLETING the session, so its sets count.
 *
 * The truncation itself lives in `backend/scripts/reset_e2e_db.py` (the web
 * package has no Postgres driver, and the backend venv already has one). Both
 * sides refuse to run against a database whose name does not contain "e2e".
 */
import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const BACKEND_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../backend')
const PYTHON = path.join(BACKEND_DIR, 'venv', 'Scripts', 'python.exe')

export default function globalSetup(): void {
  const url = process.env.E2E_DATABASE_URL?.trim()
  if (!url) {
    throw new Error('E2E_DATABASE_URL is not set. Refusing to reset any database.')
  }
  // Everything after the last "/" (minus any ?query) is the database name.
  const dbName = url.split('?')[0].split('/').pop() ?? ''
  if (!dbName.toLowerCase().includes('e2e')) {
    throw new Error(
      `E2E_DATABASE_URL points at database "${dbName}", whose name does not contain ` +
        '"e2e". Refusing to truncate it.'
    )
  }

  const result = spawnSync(PYTHON, ['-m', 'scripts.reset_e2e_db'], {
    cwd: BACKEND_DIR,
    env: { ...process.env, E2E_DATABASE_URL: url },
    encoding: 'utf-8',
  })
  if (result.error) {
    throw new Error(`Could not run the e2e database reset (${PYTHON}): ${result.error.message}`)
  }
  if (result.status !== 0) {
    throw new Error(
      `e2e database reset failed (exit ${result.status}):\n${result.stdout ?? ''}${
        result.stderr ?? ''
      }`
    )
  }
  process.stdout.write(result.stdout)
}
