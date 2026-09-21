import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  use: { baseURL: 'http://127.0.0.1:5173', trace: 'on-first-retry' },
  webServer: [
    { command: 'python -m uvicorn backend.main:app --port 8000', url: 'http://127.0.0.1:8000/api/health', reuseExistingServer: true },
    { command: 'npm run dev -- --host 127.0.0.1 --port 5174', url: 'http://127.0.0.1:5174', reuseExistingServer: false }
  ],
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], baseURL: 'http://127.0.0.1:5174' } }]
})