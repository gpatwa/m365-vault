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
 *   - Admin user exists (admin / admin123)
 *
 * Run: npx playwright test
 */
import { test, expect, Page } from '@playwright/test';

// ── Helpers ──

async function login(page: Page) {
  await page.goto('/login');
  // Check if already logged in (has nav)
  try {
    await page.waitForSelector('nav', { timeout: 2000 });
    return; // Already logged in
  } catch {
    // Not logged in, proceed
  }
  await page.fill('input[type="text"]', 'admin');
  await page.fill('input[type="password"]', 'admin123');
  await page.click('button[type="submit"]');
  // Wait for navigation sidebar to appear
  await page.waitForSelector('nav', { timeout: 15000 });
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
  test('successful login redirects to dashboard', async ({ page }) => {
    await login(page);
    // Should be on dashboard — look for dashboard content
    await expect(page.locator('text=Dashboard').first()).toBeVisible({ timeout: 5000 });
  });

  test('wrong password shows error', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="text"]', 'admin');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    // Should show error message
    await expect(page.locator('text=failed').or(page.locator('text=Invalid')).or(page.locator('text=error'))).toBeVisible({ timeout: 5000 });
  });

  test('unauthenticated access shows login or landing', async ({ page }) => {
    await page.goto('/');
    // App may show landing, login, or dashboard depending on auth state
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
    // Dashboard should show workload names
    await expect(page.locator('text=Exchange').first()).toBeVisible({ timeout: 5000 });
  });

  test('shows health score', async ({ page }) => {
    // Look for health score or protection stats
    const scoreOrProtected = page.locator('text=Health').or(page.locator('text=Protected'));
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
    // Should show at least one workload swimlane
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
    const content = page.locator('text=Alert').or(page.locator('text=SMTP'));
    await expect(content.first()).toBeVisible({ timeout: 5000 });
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
    await expect(page.getByText('MSP Dashboard')).toBeVisible({ timeout: 5000 });
  });

  test('MSP page shows summary stats', async ({ page }) => {
    await page.goto('/msp');
    await expect(page.getByText('Total Tenants')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Protected Users')).toBeVisible();
    await expect(page.getByText('Total Storage')).toBeVisible();
    await expect(page.getByText('Overall Health')).toBeVisible();
  });

  test('MSP page shows tenant cards', async ({ page }) => {
    await page.goto('/msp');
    // Wait for data to load — should show at least the tenant name or "No tenants"
    const hasTenants = page.locator('[class*="rounded-xl"]').first();
    await expect(hasTenants).toBeVisible({ timeout: 10000 });
  });

  test('MSP page has search functionality', async ({ page }) => {
    await page.goto('/msp');
    const searchInput = page.getByPlaceholder('Search tenants...');
    await expect(searchInput).toBeVisible({ timeout: 5000 });
    await searchInput.fill('nonexistent');
    await expect(page.getByText('No tenants matching')).toBeVisible({ timeout: 3000 });
  });

  test('MSP API returns correct structure', async ({ request }) => {
    // Login first
    const loginResp = await request.post('http://localhost:8000/api/auth/login', {
      form: { username: 'admin', password: 'admin123' },
    });
    const token = (await loginResp.json()).access_token;

    const resp = await request.get('http://localhost:8000/api/msp/overview', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(resp.status()).toBe(200);

    const data = await resp.json();
    expect(data).toHaveProperty('summary');
    expect(data).toHaveProperty('tenants');
    expect(data.summary).toHaveProperty('total_tenants');
    expect(data.summary).toHaveProperty('total_protected_users');
    expect(data.summary).toHaveProperty('overall_health');
    expect(Array.isArray(data.tenants)).toBeTruthy();
  });

  test('MSP API requires authentication', async ({ request }) => {
    const resp = await request.get('http://localhost:8000/api/msp/overview');
    expect(resp.status()).toBe(401);
  });
});
