/**
 * E2E tests: authentication flows via oauth2-proxy.
 *
 * These tests require the full stack running:
 *   kind create cluster
 *   helm install orchestra-crds deploy/charts/orchestra-crds
 *   helm install orchestra deploy/charts/orchestra -f deploy/values-dev.yaml
 *
 * Run with: npm run test:e2e
 *
 * TODO: implement once the stack is running in CI with a mock OIDC provider.
 * The scenarios below are written as documentation of the intended behaviour.
 */

import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// Unauthenticated redirect
// ---------------------------------------------------------------------------

test.skip('unauthenticated user is redirected to oauth2 login', async ({ page }) => {
  // Navigate directly — should redirect to /oauth2/start
  await page.goto('/');
  await expect(page).toHaveURL(/oauth2\/start/);
});

// ---------------------------------------------------------------------------
// Authenticated user sees their workshops
// ---------------------------------------------------------------------------

test.skip('authenticated user can create and see their workshop', async ({ page }) => {
  // Use Playwright's storageState or a cookie-based login fixture here.
  // With a mock OIDC provider (Dex) you can POST credentials and get a session.

  await page.goto('/');
  await expect(page.locator('text=Dashboard')).toBeVisible();

  // Create a workshop
  await page.click('text=Create Workshop');
  await page.fill('[name=name]', 'e2e-test-ws');
  await page.click('button[type=submit]');

  // Should appear in the dashboard
  await page.goto('/');
  await expect(page.locator('text=e2e-test-ws')).toBeVisible();
});

// ---------------------------------------------------------------------------
// Ownership isolation
// ---------------------------------------------------------------------------

test.skip("alice's workshop is not visible to bob", async ({ browser }) => {
  // Open two contexts with different session cookies (alice and bob).
  const aliceCtx = await browser.newContext();
  const bobCtx = await browser.newContext();

  const alicePage = await aliceCtx.newPage();
  const bobPage = await bobCtx.newPage();

  // Alice creates a workshop
  await alicePage.goto('/');
  // ... create flow ...

  // Bob's dashboard should be empty
  await bobPage.goto('/');
  await expect(bobPage.locator('text=e2e-test-ws')).not.toBeVisible();

  await aliceCtx.close();
  await bobCtx.close();
});

// ---------------------------------------------------------------------------
// Logout
// ---------------------------------------------------------------------------

test.skip('sign out clears the session and redirects to login', async ({ page }) => {
  await page.goto('/');
  // Assumes user is logged in via fixture
  await page.click('text=Sign out');
  await expect(page).toHaveURL(/oauth2\/sign_out|oauth2\/start/);
  // Navigating back should require login again
  await page.goto('/');
  await expect(page).toHaveURL(/oauth2\/start/);
});
