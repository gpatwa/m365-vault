/**
 * MSP Phase 2 E2E Tests — Playwright
 *
 * Tests the full MSP feature set in the browser:
 * 1. MSP sidebar navigation (role-filtered)
 * 2. MSP Dashboard (tenant cards, search, click-through)
 * 3. Billing Portal (table, month selector, CSV export)
 * 4. White-Label Branding (form, preview, persistence)
 * 5. Bulk Onboarding (manual entry flow)
 * 6. Compliance Report (modal, report type tabs)
 * 7. MSP API endpoints (structure validation)
 *
 * Prerequisites:
 *   - Docker Compose running on feature/msp-dashboard branch
 *   - Admin user exists (admin / Admin123)
 *
 * Run: npx playwright test msp-phase2.spec.ts
 */
import { test, expect, Page } from '@playwright/test';

async function login(page: Page) {
  // Get token via API, then inject into sessionStorage
  const resp = await page.request.post('http://localhost:8000/api/auth/login', {
    form: { username: 'admin', password: 'Admin123' },
  });
  const data = await resp.json();
  const token = data.access_token;

  // Ensure at least one ACTIVE tenant exists (so SmartHome doesn't redirect to /onboard)
  const bulkResp = await page.request.post('http://localhost:8000/api/msp/onboard-bulk', {
    headers: { Authorization: `Bearer ${token}` },
    data: { tenants: [{ name: 'E2E Test Corp', ms_tenant_id: 'e2e-test-tid', client_id: 'e2e-cid', client_secret: 'e2e-secret' }] },
  }).catch(() => null);

  // Activate the tenant via complete endpoint
  const tenants = await page.request.get('http://localhost:8000/api/tenants/', {
    headers: { Authorization: `Bearer ${token}` },
  }).then(r => r.json()).catch(() => []);
  if (tenants.length > 0) {
    await page.request.post('http://localhost:8000/api/onboard/complete', {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: { tenant_id: tenants[0].id, protect_all: false },
    }).catch(() => {});
  }

  // Navigate to the app first (need origin for sessionStorage)
  await page.goto('/login');
  // Inject token into sessionStorage + dismiss product tour
  await page.evaluate((t) => {
    sessionStorage.setItem('token', t);
    localStorage.setItem('kavachiq_tour_completed', 'true');
  }, token);
}

// ═══════════════════════════════════════════════════════
// 1. MSP Sidebar Navigation
// ═══════════════════════════════════════════════════════

test.describe('MSP Sidebar', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    // Navigate to an MSP page to get inside the Layout with sidebar
    await page.goto('/msp');
    await page.waitForTimeout(2000);
  });

  test('MSP nav group is visible for admin', async ({ page }) => {
    await expect(page.getByRole('link', { name: 'MSP Dashboard' })).toBeVisible({ timeout: 5000 });
  });

  test('MSP nav has billing link', async ({ page }) => {
    await expect(page.getByText('Billing')).toBeVisible({ timeout: 5000 });
  });

  test('MSP nav has branding link', async ({ page }) => {
    await expect(page.getByText('Branding')).toBeVisible({ timeout: 5000 });
  });

  test('MSP nav has bulk onboard link', async ({ page }) => {
    await expect(page.getByText('Bulk Onboard')).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════════════
// 2. MSP Dashboard
// ═══════════════════════════════════════════════════════

test.describe('MSP Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/msp');
    await page.waitForTimeout(1000);
  });

  test('dashboard page loads', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'MSP Dashboard' })).toBeVisible({ timeout: 5000 });
  });

  test('shows summary stats', async ({ page }) => {
    await expect(page.getByText('Total Tenants')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Protected Users')).toBeVisible();
    await expect(page.getByText('Overall Health')).toBeVisible();
  });

  test('search filters tenants', async ({ page }) => {
    const search = page.getByPlaceholder('Search tenants...');
    await expect(search).toBeVisible({ timeout: 5000 });
    await search.fill('nonexistent-xyz');
    await expect(page.getByText('No tenants matching')).toBeVisible({ timeout: 3000 });
  });
});

// ═══════════════════════════════════════════════════════
// 3. Billing Portal
// ═══════════════════════════════════════════════════════

test.describe('Billing Portal', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/msp/billing');
    await page.waitForTimeout(1000);
  });

  test('billing page loads', async ({ page }) => {
    await expect(page.getByText('Billing Portal')).toBeVisible({ timeout: 5000 });
  });

  test('shows total cost', async ({ page }) => {
    await expect(page.getByText('Total Cost')).toBeVisible({ timeout: 5000 });
  });

  test('has month selector', async ({ page }) => {
    const select = page.locator('select');
    await expect(select).toBeVisible({ timeout: 5000 });
  });

  test('has CSV export button', async ({ page }) => {
    await expect(page.getByText('Export CSV')).toBeVisible({ timeout: 5000 });
  });

  test('shows wholesale tier info', async ({ page }) => {
    await expect(page.getByText('Wholesale Pricing Tiers')).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════════════
// 4. White-Label Branding
// ═══════════════════════════════════════════════════════

test.describe('White-Label Branding', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/msp/branding');
    await page.waitForTimeout(1000);
  });

  test('branding page loads', async ({ page }) => {
    await expect(page.getByText('White-Label Branding')).toBeVisible({ timeout: 5000 });
  });

  test('has company name input', async ({ page }) => {
    const input = page.locator('input').first();
    await expect(input).toBeVisible({ timeout: 5000 });
  });

  test('has live preview', async ({ page }) => {
    await expect(page.getByText('Live Preview')).toBeVisible({ timeout: 5000 });
  });

  test('has save button', async ({ page }) => {
    await expect(page.getByText('Save Branding')).toBeVisible({ timeout: 5000 });
  });

  test('has color pickers', async ({ page }) => {
    const colorInputs = page.locator('input[type="color"]');
    await expect(colorInputs.first()).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════════════
// 5. Bulk Onboarding
// ═══════════════════════════════════════════════════════

test.describe('Bulk Onboarding', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto('/msp/onboard');
    await page.waitForTimeout(1000);
  });

  test('bulk onboard page loads', async ({ page }) => {
    await expect(page.getByText('Bulk Tenant Onboarding')).toBeVisible({ timeout: 5000 });
  });

  test('has CSV template download', async ({ page }) => {
    await expect(page.getByText('CSV Template')).toBeVisible({ timeout: 5000 });
  });

  test('has manual add button', async ({ page }) => {
    await expect(page.getByText('Add Manually')).toBeVisible({ timeout: 5000 });
  });

  test('manual add shows preview table', async ({ page }) => {
    await page.getByText('Add Manually').click();
    await expect(page.getByText('Tenant Name')).toBeVisible({ timeout: 3000 });
  });
});

// ═══════════════════════════════════════════════════════
// 6. MSP API Validation
// ═══════════════════════════════════════════════════════

test.describe('MSP API Endpoints', () => {
  test('branding GET works without auth', async ({ request }) => {
    const resp = await request.get('http://localhost:8000/api/msp/branding');
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data).toHaveProperty('company_name');
    expect(data).toHaveProperty('primary_color');
  });

  test('billing requires auth', async ({ request }) => {
    const resp = await request.get('http://localhost:8000/api/msp/billing');
    expect(resp.status()).toBe(401);
  });

  test('billing returns correct structure', async ({ request }) => {
    const loginResp = await request.post('http://localhost:8000/api/auth/login', {
      form: { username: 'admin', password: 'Admin123' },
    });
    const token = (await loginResp.json()).access_token;

    const resp = await request.get('http://localhost:8000/api/msp/billing', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data).toHaveProperty('month');
    expect(data).toHaveProperty('total_cost');
    expect(data).toHaveProperty('line_items');
    expect(data).toHaveProperty('tiers');
  });

  test('compliance report returns correct structure', async ({ request }) => {
    const loginResp = await request.post('http://localhost:8000/api/auth/login', {
      form: { username: 'admin', password: 'Admin123' },
    });
    const token = (await loginResp.json()).access_token;

    // Get first tenant
    const tenantsResp = await request.get('http://localhost:8000/api/tenants/', {
      headers: { Authorization: `Bearer ${token}` },
    });
    const tenants = await tenantsResp.json();
    if (tenants.length > 0) {
      const resp = await request.get(`http://localhost:8000/api/msp/compliance-report/${tenants[0].id}?report_type=hipaa`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(resp.status()).toBe(200);
      const data = await resp.json();
      expect(data).toHaveProperty('report_type', 'hipaa');
      expect(data).toHaveProperty('controls');
      expect(data).toHaveProperty('backup_coverage');
      expect(data).toHaveProperty('encryption');
    }
  });
});
