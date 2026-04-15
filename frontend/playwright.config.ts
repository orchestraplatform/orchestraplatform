import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E configuration for Orchestra frontend.
 *
 * Tests require the full stack (kind + helm install + mock OIDC).
 * See frontend/tests/e2e/auth.spec.ts and docs/contributing/testing.md.
 *
 * Run: npm run test:e2e
 */
export default defineConfig({
  testDir: './tests/e2e',
  // All e2e specs are skipped by default; unskip them when the stack is up.
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [['html', { outputFolder: 'tests/e2e/report' }], ['list']],

  use: {
    // Base URL of the frontend — override with PLAYWRIGHT_BASE_URL in CI.
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'https://app.orchestra.localhost',
    trace: 'on-first-retry',
    // Accept self-signed certs for local kind + cert-manager setups.
    ignoreHTTPSErrors: true,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
