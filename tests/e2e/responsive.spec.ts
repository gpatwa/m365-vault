/**
 * Responsive Design E2E Tests — Playwright
 *
 * Tests the app at desktop (1280×800) and mobile (375×812) viewports.
 * Verifies layout doesn't break, content is accessible, and
 * mobile navigation works.
 *
 * Run: npx playwright test responsive.spec.ts
 */
import { test, expect, Page } from '@playwright/test';

async function login(page: Page) {
  await page.evaluate(() => localStorage.setItem('shieldio_tour_completed', 'true'));
  await page.goto('/login');
  try {
    await page.waitForSelector('nav', { timeout: 2000 });
    return;
  } catch {}
  await page.fill('input[type="text"]', 'admin');
  await page.fill('input[type="password"]', 'Admin123');
  await page.click('button[type="submit"]');
  await page.waitForSelector('text=Dashboard', { timeout: 15000 });
}

// ═══════════════════════════════════════════════════════
// 1. Desktop Viewport (1280×800)
// ═══════════════════════════════════════════════════════

test.describe('Desktop Layout', () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test('sidebar is visible on desktop', async ({ page }) => {
    await login(page);
    // Sidebar should be visible (aside element)
    const sidebar = page.locator('aside');
    await expect(sidebar.first()).toBeVisible({ timeout: 5000 });
  });

  test('dashboard loads with stat cards', async ({ page }) => {
    await login(page);
    await expect(page.getByText('Dashboard')).toBeVisible({ timeout: 5000 });
  });

  test('landing page hero renders', async ({ page }) => {
    await page.goto('/welcome');
    await expect(page.getByText('Your responsibility')).toBeVisible({ timeout: 5000 });
  });

  test('landing page pricing cards visible', async ({ page }) => {
    await page.goto('/welcome');
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);
    await expect(page.getByText('$1.50')).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════════════
// 2. Mobile Viewport (375×812 — iPhone SE/13 mini)
// ═══════════════════════════════════════════════════════

test.describe('Mobile Layout', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test('sidebar is hidden on mobile', async ({ page }) => {
    await login(page);
    // Desktop sidebar should be hidden
    const desktopSidebar = page.locator('aside.hidden');
    await expect(desktopSidebar).toBeAttached({ timeout: 5000 });
  });

  test('mobile header with hamburger is visible', async ({ page }) => {
    await login(page);
    // Mobile header should have hamburger menu
    await expect(page.locator('button').filter({ has: page.locator('svg') }).first()).toBeVisible({ timeout: 5000 });
  });

  test('hamburger opens mobile sidebar', async ({ page }) => {
    await login(page);
    // Click hamburger (first button in mobile header)
    const hamburger = page.locator('.lg\\:hidden button').first();
    await hamburger.click();
    // Mobile sidebar overlay should appear
    await expect(page.getByText('Dashboard')).toBeVisible({ timeout: 3000 });
    await expect(page.getByText('Exchange')).toBeVisible();
  });

  test('mobile sidebar closes on link click', async ({ page }) => {
    await login(page);
    const hamburger = page.locator('.lg\\:hidden button').first();
    await hamburger.click();
    // Click a nav link
    await page.getByText('Exchange').first().click();
    await page.waitForTimeout(500);
    // Sidebar overlay should be gone (navigation happened)
    await expect(page.locator('.fixed.inset-0.z-50')).not.toBeVisible({ timeout: 3000 });
  });

  test('dashboard content is scrollable on mobile', async ({ page }) => {
    await login(page);
    // Should be able to scroll without horizontal overflow
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalScroll).toBe(false);
  });

  test('login page works on mobile', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible({ timeout: 5000 });
    await expect(page.locator('input[type="text"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('landing page hero readable on mobile', async ({ page }) => {
    await page.goto('/welcome');
    await expect(page.getByText('Your responsibility')).toBeVisible({ timeout: 5000 });
    // Hero should not overflow
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(overflow).toBe(false);
  });

  test('landing page pricing visible on mobile', async ({ page }) => {
    await page.goto('/welcome');
    // Scroll to pricing
    await page.evaluate(() => {
      document.querySelector('#pricing')?.scrollIntoView();
    });
    await page.waitForTimeout(500);
    await expect(page.getByText('$1.50')).toBeVisible({ timeout: 5000 });
  });
});

// ═══════════════════════════════════════════════════════
// 3. Tablet Viewport (768×1024 — iPad)
// ═══════════════════════════════════════════════════════

test.describe('Tablet Layout', () => {
  test.use({ viewport: { width: 768, height: 1024 } });

  test('sidebar hidden on tablet', async ({ page }) => {
    await login(page);
    // Below lg breakpoint, sidebar should be hidden
    const desktopSidebar = page.locator('aside.hidden');
    await expect(desktopSidebar).toBeAttached({ timeout: 5000 });
  });

  test('landing page renders without overflow', async ({ page }) => {
    await page.goto('/welcome');
    await page.waitForTimeout(1000);
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(overflow).toBe(false);
  });
});

// ═══════════════════════════════════════════════════════
// 4. Page-Specific Mobile Tests
// ═══════════════════════════════════════════════════════

test.describe('Page Mobile Tests', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('exchange page no horizontal overflow', async ({ page }) => {
    await page.goto('/exchange');
    await page.waitForTimeout(1000);
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(overflow).toBe(false);
  });

  test('jobs page no horizontal overflow', async ({ page }) => {
    await page.goto('/jobs');
    await page.waitForTimeout(1000);
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(overflow).toBe(false);
  });

  test('recovery page no horizontal overflow', async ({ page }) => {
    await page.goto('/recovery');
    await page.waitForTimeout(1000);
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(overflow).toBe(false);
  });

  test('audit page no horizontal overflow', async ({ page }) => {
    await page.goto('/audit');
    await page.waitForTimeout(1000);
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(overflow).toBe(false);
  });
});
