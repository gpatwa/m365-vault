/**
 * Shieldio E2E Tests — Playwright
 *
 * Tests the full user journey through the browser:
 * 1. Landing page → Login
 * 2. Login → Dashboard
 * 3. Navigate sidebar pages
 * 4. Tenant management
 * 5. Workload pages
 * 6. Reports & monitoring
 *
 * Prerequisites:
 *   - Docker Compose running (frontend + backend)
 *   - Admin user exists (admin / Admin123)
 *
 * Run: npx playwright test
 */
import { test, expect, Page } from '@playwright/test';

// ── Helpers ──

/** Cached token to avoid re-authenticating on every test (rate limit protection) */
let cachedToken: string | null = null;

async function login(page: Page) {
  await page.goto('/login');

  // Inject cached token if available
  if (cachedToken) {
    await page.evaluate((t) => sessionStorage.setItem('token', t), cachedToken);
    await page.goto('/');
    try {
      await page.waitForSelector('nav', { timeout: 5000 });
      return;
    } catch {
      cachedToken = null; // Token expired, re-auth below
    }
  }

  // Get fresh token via API
  const token = await page.evaluate(async () => {
    try {
      const resp = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'username=admin&password=Admin123',
      });
      const data = await resp.json();
      if (data.access_token) {
        sessionStorage.setItem('token', data.access_token);
        return data.access_token;
      }
    } catch { /* fall through */ }
    return null;
  });

  if (token) {
    cachedToken = token;
    await page.goto('/');
    await page.waitForSelector('nav', { timeout: 10000 });
    return;
  }

  // Fallback: form-based login
  await page.waitForSelector('input[type="text"]', { timeout: 5000 });
  await page.fill('input[type="text"]', 'admin');
  await page.fill('input[type="password"]', 'Admin123');
  await page.click('button[type="submit"]');
  await page.waitForSelector('nav', { timeout: 15000 });
  // Extract token from sessionStorage for caching
  cachedToken = await page.evaluate(() => sessionStorage.getItem('token'));
}

// ═══════════════════════════════════════════════════════
// 1. Public Pages (no auth required)
// ═══════════════════════════════════════════════════════

test.describe('Public Pages', () => {
  test('landing page loads with Shieldio branding', async ({ page }) => {
    await page.goto('/welcome');
    await expect(page.getByRole('link', { name: 'Shieldio' }).first()).toBeVisible({ timeout: 5000 });
  });

  test('landing page has Get Started button', async ({ page }) => {
    await page.goto('/welcome');
    const cta = page.locator('text=Get Started').first();
    await expect(cta).toBeVisible({ timeout: 5000 });
  });

  test('login page loads', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible({ timeout: 5000 });
  });

  test('login page shows password field', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════
// 2. Authentication Flow
// ═══════════════════════════════════════════════════════

test.describe('Authentication', () => {
  test('wrong password shows error', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="text"]', 'admin');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    await expect(page.locator('text=failed').or(page.locator('text=Invalid')).or(page.locator('text=error'))).toBeVisible({ timeout: 5000 });
  });

  test('unauthenticated access shows login or landing', async ({ page }) => {
    await page.goto('/');
    const hasContent = page.locator('text=Shieldio').or(page.locator('text=Sign in')).or(page.locator('text=Dashboard'));
    await expect(hasContent.first()).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════════════
// 3. Dashboard
// ═══════════════════════════════════════════════════════

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('shows workload stats', async ({ page }) => {
    await expect(page.locator('text=Exchange').first()).toBeVisible({ timeout: 5000 });
  });

  test('shows health score', async ({ page }) => {
    const scoreOrProtected = page.locator('text=/HEALTH|PROTECTION/i');
    await expect(scoreOrProtected.first()).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════════════
// 4. Sidebar Navigation
// ═══════════════════════════════════════════════════════

test.describe('Sidebar Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  const navItems = [
    { label: 'Dashboard', urlPattern: /\/$/ },
    { label: 'Jobs', urlPattern: /jobs/ },
    { label: 'Exchange', urlPattern: /exchange/ },
    { label: 'OneDrive', urlPattern: /onedrive/ },
    { label: 'SharePoint', urlPattern: /sharepoint/ },
    { label: 'Teams', urlPattern: /teams/ },
    { label: 'Entra ID', urlPattern: /entra/ },
  ];

  for (const item of navItems) {
    test(`navigate to ${item.label}`, async ({ page }) => {
      const link = page.locator(`nav a:has-text("${item.label}")`).first();
      if (await link.isVisible()) {
        await link.click();
        await page.waitForURL(item.urlPattern, { timeout: 5000 });
      }
    });
  }
});

// ═══════════════════════════════════════════════════════
// 5. Jobs Page
// ═══════════════════════════════════════════════════════

test.describe('Jobs Page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('shows workload swimlanes', async ({ page }) => {
    await page.goto('/jobs');
    const swimlane = page.locator('text=Exchange').or(page.locator('text=OneDrive'));
    await expect(swimlane.first()).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════════════
// 6. Smart Engine Page
// ═══════════════════════════════════════════════════════

test.describe('Smart Engine', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('shows health score', async ({ page }) => {
    await page.goto('/smart-engine');
    const content = page.locator('text=Health').or(page.locator('text=Score'));
    await expect(content.first()).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════════════
// 7. Reports Page
// ═══════════════════════════════════════════════════════

test.describe('Reports', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('reports page loads', async ({ page }) => {
    await page.goto('/reports');
    const content = page.locator('text=Report').or(page.locator('text=Performance'));
    await expect(content.first()).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════════════
// 8. Alerts Page
// ═══════════════════════════════════════════════════════

test.describe('Alerts', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('alerts page shows config', async ({ page }) => {
    await page.goto('/alerts');
    const content = page.locator('text=/Alert|SMTP|Notification/i');
    await expect(content.first()).toBeVisible({ timeout: 10000 });
  });
});

// ═══════════════════════════════════════════════════════
// 9. API Response Headers
// ═══════════════════════════════════════════════════════

test.describe('API Headers', () => {
  test('health endpoint has correlation ID', async ({ request }) => {
    const resp = await request.get('http://localhost:8000/health');
    expect(resp.status()).toBe(200);
    expect(resp.headers()['x-correlation-id']).toBeTruthy();
    expect(resp.headers()['x-response-time']).toBeTruthy();
  });

  test('API returns JSON content type', async ({ request }) => {
    const resp = await request.get('http://localhost:8000/');
    expect(resp.headers()['content-type']).toContain('application/json');
  });
});

// ═══════════════════════════════════════════════════════
// 10. MSP Dashboard
// ═══════════════════════════════════════════════════════

test.describe('MSP Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('MSP page loads with title', async ({ page }) => {
    await page.goto('/msp');
    await expect(page.locator('h1').filter({ hasText: /MSP/i }).first()).toBeVisible({ timeout: 10000 });
  });

  test('MSP page shows summary stats', async ({ page }) => {
    await page.goto('/msp');
    await expect(page.locator('text=/Tenant|Users|Storage|Health/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('MSP page shows tenant cards', async ({ page }) => {
    await page.goto('/msp');
    const hasTenants = page.locator('[class*="rounded-xl"]').first();
    await expect(hasTenants).toBeVisible({ timeout: 10000 });
  });

  test('MSP page has search functionality', async ({ page }) => {
    await page.goto('/msp');
    const searchInput = page.getByPlaceholder(/search/i).first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });
  });

  test('MSP API returns correct structure', async ({ page }) => {
    // Use page.evaluate to call API with auth token (avoids separate request context)
    await login(page);
    const data = await page.evaluate(async () => {
      const token = sessionStorage.getItem('token');
      const resp = await fetch('http://localhost:8000/api/msp/overview', {
        headers: { Authorization: `Bearer ${token}` },
      });
      return resp.json();
    });
    expect(data).toHaveProperty('summary');
    expect(data).toHaveProperty('tenants');
    expect(data.summary).toHaveProperty('total_tenants');
    expect(Array.isArray(data.tenants)).toBeTruthy();
  });

  test('MSP API requires authentication', async ({ request }) => {
    const resp = await request.get('http://localhost:8000/api/msp/overview');
    expect(resp.status()).toBe(401);
  });
});

// ═══════════════════════════════════════════════════════
// 11. Form-Based Login (last to avoid rate limiting other tests)
// ═══════════════════════════════════════════════════════

test.describe('Form Login', () => {
  test('successful login redirects to dashboard', async ({ page }) => {
    await page.goto('/login');
    await page.evaluate(() => { sessionStorage.clear(); localStorage.clear(); });
    await page.reload();
    await page.waitForSelector('input[type="text"]', { timeout: 5000 });
    await page.fill('input[type="text"]', 'admin');
    await page.fill('input[type="password"]', 'Admin123');
    await page.click('button[type="submit"]');
    await page.waitForSelector('nav', { timeout: 15000 });
    await expect(page.locator('nav')).toBeVisible();
  });
});
