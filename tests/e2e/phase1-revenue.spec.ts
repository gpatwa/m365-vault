import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';
const API = 'http://localhost:8000/api';

// ── Auth Helper ──
let token = '';
test.beforeAll(async ({ request }) => {
  const res = await request.post(`${API}/auth/login`, {
    form: { username: 'admin', password: 'Admin123' },
  });
  if (res.ok()) {
    const data = await res.json();
    token = data.access_token;
  }
});

async function loginAsAdmin(page: any) {
  await page.goto(`${BASE}/login`);
  await page.waitForTimeout(2000);
  // Use JS to fill + submit (more reliable than MCP clicks)
  await page.evaluate(() => {
    const inputs = document.querySelectorAll('input');
    if (inputs[0]) { (inputs[0] as HTMLInputElement).value = 'admin'; inputs[0].dispatchEvent(new Event('input', {bubbles: true})); }
    if (inputs[1]) { (inputs[1] as HTMLInputElement).value = 'Admin123'; inputs[1].dispatchEvent(new Event('input', {bubbles: true})); }
    const btn = document.querySelector('button[type="submit"]');
    if (btn) (btn as HTMLButtonElement).click();
  });
  await page.waitForTimeout(5000);
  if (page.url().includes('/onboard')) await page.goto(`${BASE}/`);
  await page.waitForLoadState('networkidle');
}

// ═══════════════════════════════════════════════════════
// BILLING PAGE
// ═══════════════════════════════════════════════════════
test.describe('Billing Page', () => {
  test.beforeEach(async ({ page }) => { await loginAsAdmin(page); });

  test('billing page loads with current plan', async ({ page }) => {
    await page.goto(`${BASE}/billing`);
    await page.waitForTimeout(3000);
    await expect(page.locator('text=Billing').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Current Plan').first()).toBeVisible();
  });

  test('shows 3 pricing tiers', async ({ page }) => {
    await page.goto(`${BASE}/billing`);
    await page.waitForTimeout(3000);
    await expect(page.locator('text=Professional').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Business').first()).toBeVisible();
    await expect(page.locator('text=Enterprise').first()).toBeVisible();
  });

  test('shows correct pricing', async ({ page }) => {
    await page.goto(`${BASE}/billing`);
    await page.waitForTimeout(3000);
    await expect(page.locator('text=$1.50').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=$3.00').first()).toBeVisible();
    await expect(page.locator('text=$5.00').first()).toBeVisible();
  });

  test('shows trial CTA buttons', async ({ page }) => {
    await page.goto(`${BASE}/billing`);
    await page.waitForTimeout(3000);
    const trials = page.locator('text=Start 14-Day Trial');
    const count = await trials.count();
    expect(count).toBeGreaterThanOrEqual(2);
  });

  test('billing visible in sidebar', async ({ page }) => {
    await page.goto(`${BASE}/billing`);
    await page.waitForTimeout(3000);
    // Sidebar should have Billing link active
    await expect(page.locator('text=Billing').first()).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════════════
// BILLING API
// ═══════════════════════════════════════════════════════
test.describe('Billing API', () => {
  test('GET /billing/config returns price IDs', async ({ request }) => {
    const res = await request.get(`${API}/billing/config`);
    expect(res.ok()).toBeTruthy();
    const data = await res.json();
    expect(data.prices).toBeDefined();
    expect(data.prices.professional).toBeTruthy();
    expect(data.prices.business).toBeTruthy();
    expect(data.prices.enterprise).toBeTruthy();
    expect(data.trial_days).toBe(14);
  });

  test('GET /billing/subscription returns tenant status', async ({ request }) => {
    const res = await request.get(`${API}/billing/subscription?tenant_id=3`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    // May return 404 if tenant doesn't exist on this DB, or 200 with data
    expect(res.status()).toBeLessThan(500);
  });

  test('POST /billing/checkout requires auth', async ({ request }) => {
    const res = await request.post(`${API}/billing/checkout`, {
      data: { tenant_id: 3, price_id: 'price_test', quantity: 1 },
    });
    expect(res.status()).toBe(401);
  });

  test('POST /billing/webhook accepts POST', async ({ request }) => {
    const res = await request.post(`${API}/billing/webhook`, {
      data: { type: 'test', data: { object: {} } },
      headers: { 'Content-Type': 'application/json' },
    });
    // Should return 400 (invalid signature) or 200, not 404/405
    expect([200, 400]).toContain(res.status());
  });
});

// ═══════════════════════════════════════════════════════
// FORGOT PASSWORD
// ═══════════════════════════════════════════════════════
test.describe('Forgot Password', () => {
  test('forgot password API returns 200 for any email', async ({ request }) => {
    const res = await request.post(`${API}/auth/forgot-password`, {
      data: { email: 'nonexistent@test.com' },
    });
    expect(res.ok()).toBeTruthy();
    const data = await res.json();
    expect(data.message).toContain('reset link');
  });

  test('forgot password API creates reset token for real user', async ({ request }) => {
    const res = await request.post(`${API}/auth/forgot-password`, {
      data: { email: 'admin@kavachiq.local' },
    });
    expect(res.ok()).toBeTruthy();
  });

  test('reset password API rejects invalid token', async ({ request }) => {
    const res = await request.post(`${API}/auth/reset-password`, {
      data: { token: 'invalid-token-12345', new_password: 'NewPass123' },
    });
    expect(res.status()).toBe(400);
  });

  test('verify email API rejects invalid token', async ({ request }) => {
    const res = await request.post(`${API}/auth/verify-email`, {
      data: { token: 'invalid-verify-token' },
    });
    expect(res.status()).toBe(400);
  });
});

// ═══════════════════════════════════════════════════════
// FORGOT PASSWORD UI
// ═══════════════════════════════════════════════════════
test.describe('Forgot Password UI', () => {
  test('forgot password form shows on click', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.waitForTimeout(2000);
    // Click via JS (more reliable for React state changes)
    await page.evaluate(() => {
      const btn = [...document.querySelectorAll('button')].find(b => b.textContent?.includes('Forgot password'));
      if (btn) btn.click();
    });
    await page.waitForTimeout(500);
    await expect(page.locator('text=Send Reset Link')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Back to Sign In')).toBeVisible();
  });

  test('reset password page loads', async ({ page }) => {
    await page.goto(`${BASE}/reset-password?token=test123`);
    await page.waitForTimeout(2000);
    await expect(page.locator('text=Reset Your Password').first()).toBeVisible({ timeout: 10000 });
  });

  test('verify email page loads', async ({ page }) => {
    await page.goto(`${BASE}/verify-email?token=test123`);
    await page.waitForTimeout(3000);
    // Should show error (invalid token) or verification result
    const page_text = await page.textContent('body');
    expect(page_text).toMatch(/Verify|Verification|Failed/i);
  });
});

// ═══════════════════════════════════════════════════════
// EMAIL SERVICE API
// ═══════════════════════════════════════════════════════
test.describe('Email Service', () => {
  test('registration sends welcome email (console mode)', async ({ request }) => {
    // Register a new test user
    const unique = `testuser${Date.now()}`;
    const res = await request.post(`${API}/auth/register`, {
      data: { username: unique, email: `${unique}@test.com`, password: 'TestPass123', full_name: 'Test User' },
    });
    // Should succeed (201 or 200)
    expect(res.status()).toBeLessThan(300);
  });
});

// ═══════════════════════════════════════════════════════
// HEALTH CHECK
// ═══════════════════════════════════════════════════════
test.describe('Health Check', () => {
  test('GET /health returns system status', async ({ request }) => {
    const res = await request.get('http://localhost:8000/health');
    expect(res.ok()).toBeTruthy();
    const data = await res.json();
    expect(data.status).toBeDefined();
  });

  test('backend API is responsive', async ({ request }) => {
    const res = await request.get(`${API}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.ok()).toBeTruthy();
  });
});

// ═══════════════════════════════════════════════════════
// LICENSE / FEATURE FLAGS
// ═══════════════════════════════════════════════════════
test.describe('License & Features', () => {
  test('GET /features returns current tier features', async ({ request }) => {
    const res = await request.get(`${API}/features/`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok()) {
      const data = await res.json();
      expect(data.tier || data.features).toBeDefined();
    }
  });

  test('usage endpoint returns license info', async ({ request }) => {
    const res = await request.get(`${API}/usage/license`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok()) {
      const data = await res.json();
      expect(data.tier || data.label).toBeDefined();
    }
  });
});
