/**
 * Feature Flags E2E Tests — Playwright
 *
 * Tests the feature flag system in the browser:
 * 1. Feature Config page loads and shows categories
 * 2. Tier comparison tab works
 * 3. Toggle override buttons work
 * 4. API returns correct structure
 * 5. Feature flags endpoint is public (no auth)
 *
 * Prerequisites:
 *   - Docker Compose running on feature/msp-dashboard
 *   - Admin user exists
 *
 * Run: npx playwright test feature-flags.spec.ts
 */
import { test, expect, Page } from '@playwright/test';

async function login(page: Page) {
  // Dismiss product tour by setting localStorage before navigating
  await page.goto('/login');
  await page.evaluate(() => localStorage.setItem('shieldio_tour_completed', 'true'));

  try {
    await page.waitForSelector('nav', { timeout: 2000 });
    return;
  } catch {
    // Not logged in
  }
  await page.fill('input[type="text"]', 'admin');
  await page.fill('input[type="password"]', 'Admin123');
  await page.click('button[type="submit"]');
  await page.waitForSelector('nav', { timeout: 15000 });
  // Dismiss tour if it appeared
  await page.evaluate(() => localStorage.setItem('shieldio_tour_completed', 'true'));
}

// ═══════════════════════════════════════════════════════
// 1. Feature Config Page
// ═══════════════════════════════════════════════════════

test.describe('Feature Config Page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('page loads with title', async ({ page }) => {
    await page.goto('/features');
    await expect(page.getByText('Feature Configuration')).toBeVisible({ timeout: 5000 });
  });

  test('shows current tier', async ({ page }) => {
    await page.goto('/features');
    await expect(page.getByText('Tier:')).toBeVisible({ timeout: 5000 });
  });

  test('shows all 6 categories', async ({ page }) => {
    await page.goto('/features');
    // Use headings to avoid matching sidebar nav items with same text
    await expect(page.getByRole('heading', { name: 'Workloads' })).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('heading', { name: 'Intelligence' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Recovery' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Compliance' })).toBeVisible();
    await expect(page.getByText('Operations (MSP)')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Platform' })).toBeVisible();
  });

  test('shows enabled/disabled counts per category', async ({ page }) => {
    await page.goto('/features');
    // Each category shows "X/Y enabled"
    await expect(page.getByText(/enabled/).first()).toBeVisible({ timeout: 5000 });
  });

  test('tier comparison tab switches view', async ({ page }) => {
    await page.goto('/features');
    await page.getByText('Tier Comparison').click();
    // Should show tier column headers
    await expect(page.getByText('Community')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Professional')).toBeVisible();
    await expect(page.getByText('Business')).toBeVisible();
    await expect(page.getByText('Enterprise')).toBeVisible();
  });

  test('sidebar has Feature Config link', async ({ page }) => {
    // Administration section may be collapsed — click to expand
    await page.getByText('Administration').click().catch(() => {});
    await expect(page.getByText('Feature Config')).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════════════
// 2. Feature Flags API
// ═══════════════════════════════════════════════════════

test.describe('Feature Flags API', () => {
  test('features endpoint is public (no auth needed)', async ({ request }) => {
    const resp = await request.get('http://localhost:8000/api/features');
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data).toHaveProperty('tier');
    expect(data).toHaveProperty('features');
    expect(data).toHaveProperty('limits');
  });

  test('features has expected feature names', async ({ request }) => {
    const resp = await request.get('http://localhost:8000/api/features');
    const features = (await resp.json()).features;
    expect(features).toHaveProperty('exchange');
    expect(features).toHaveProperty('anomaly_detection');
    expect(features).toHaveProperty('msp_dashboard');
    expect(features).toHaveProperty('worm');
  });

  test('check single feature works', async ({ request }) => {
    const resp = await request.get('http://localhost:8000/api/features/check/exchange');
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.feature).toBe('exchange');
    expect(typeof data.enabled).toBe('boolean');
  });

  test('tier comparison returns all tiers', async ({ request }) => {
    const loginResp = await request.post('http://localhost:8000/api/auth/login', {
      form: { username: 'admin', password: 'Admin123' },
    });
    const token = (await loginResp.json()).access_token;

    const resp = await request.get('http://localhost:8000/api/features/tiers', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data).toHaveProperty('current_tier');
    expect(data).toHaveProperty('comparison');
    // Enterprise should have everything
    const comparison = data.comparison;
    for (const [feature, tiers] of Object.entries(comparison)) {
      expect((tiers as any).enterprise).toBe(true);
    }
  });

  test('admin can set and remove override', async ({ request }) => {
    const loginResp = await request.post('http://localhost:8000/api/auth/login', {
      form: { username: 'admin', password: 'Admin123' },
    });
    const token = (await loginResp.json()).access_token;
    const headers = { Authorization: `Bearer ${token}` };

    // Set override
    const setResp = await request.put('http://localhost:8000/api/features/override', {
      headers, data: { feature: 'cleanroom', enabled: true },
    });
    expect(setResp.status()).toBe(200);

    // Verify enabled
    const checkResp = await request.get('http://localhost:8000/api/features/check/cleanroom');
    expect((await checkResp.json()).enabled).toBe(true);

    // Remove override
    const delResp = await request.delete('http://localhost:8000/api/features/override/cleanroom', { headers });
    expect(delResp.status()).toBe(200);
  });

  test('override requires auth', async ({ request }) => {
    const resp = await request.put('http://localhost:8000/api/features/override', {
      data: { feature: 'msp_dashboard', enabled: true },
    });
    expect(resp.status()).toBe(401);
  });
});
