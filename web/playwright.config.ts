import { defineConfig } from '@playwright/test'

if (!process.env.E2E_DATABASE_URL) {
  throw new Error(
    'E2E_DATABASE_URL is not set. Set it to the slotfit_e2e connection string ' +
      '(copy DATABASE_URL from backend/.env.e2e). Refusing to run against the dev database.'
  )
}

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      // Windows path to the backend venv interpreter; adjust if running elsewhere
      command: 'venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000',
      cwd: '../backend',
      url: 'http://localhost:8000/docs',
      reuseExistingServer: true,
      timeout: 60_000,
      env: {
        DATABASE_URL: process.env.E2E_DATABASE_URL,
        // Force the deterministic rule-based recommendation provider in e2e:
        // blank keys prevent Claude/Gemini calls (and quota usage) during tests
        ANTHROPIC_API_KEY: '',
        GEMINI_API_KEY: '',
      },
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
})
