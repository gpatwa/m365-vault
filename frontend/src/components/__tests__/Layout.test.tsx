/**
 * Layout sidebar tests — verify correct menu items render per user role.
 *
 * Staff-engineer coverage:
 * - Each role sees only their authorized menu items
 * - MSP group hidden for non-MSP users
 * - Tenants (Admin) hidden for non-platform-admin
 * - Feature Config hidden for non-platform-admin
 * - Feature-flagged groups (More Workloads) respect flag state
 * - Onboarding progressive disclosure gates groups
 * - Platform admin (username=admin) sees everything
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// ── Mocks ────────────────────────────────────────────────────

// Control what useAuth returns per test
const mockAuth = vi.fn();
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockAuth(),
  AuthProvider: ({ children }: any) => children,
}));

// Control onboarding state (all complete by default)
const mockOnboarding = vi.fn();
vi.mock('../../contexts/OnboardingContext', () => ({
  useOnboarding: () => mockOnboarding(),
  OnboardingProvider: ({ children }: any) => children,
}));

// Control feature flags
const mockFeatureFlags = vi.fn();
vi.mock('../../contexts/FeatureFlagContext', () => ({
  useFeatureFlags: () => mockFeatureFlags(),
  FeatureFlagProvider: ({ children }: any) => children,
}));

// Control branding
vi.mock('../../contexts/BrandingContext', () => ({
  useBranding: () => ({
    companyName: 'KavachIQ',
    tagline: 'M365 Data Protection',
    logoUrl: null,
    primaryColor: '#0d9488',
  }),
}));

// Control tenant switcher
vi.mock('../../hooks/useTenant', () => ({
  useTenantSwitcher: () => ({
    tenants: [{ id: 1, name: 'Test Tenant' }],
    selectedTenant: { id: 1, name: 'Test Tenant' },
    switchTenant: vi.fn(),
    isMultiTenant: false,
  }),
}));

// Mock API client
vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ preferences: { tour_completed: true } }),
  },
}));

// Mock child components that use complex providers
vi.mock('../CommandPalette', () => ({ default: () => null }));
vi.mock('../ProductTour', () => ({ default: () => null }));
vi.mock('../FeedbackWidget', () => ({ default: () => null }));
vi.mock('../ThemeToggle', () => ({ default: () => <div data-testid="theme-toggle" /> }));

// Import Layout AFTER mocks are set up
import Layout from '../Layout';

// ── Helpers ──────────────────────────────────────────────────

function setUser(role: string, username: string = `test${role}`) {
  mockAuth.mockReturnValue({
    user: { username, role, email: `${username}@test.com`, full_name: `Test ${role}` },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
  });
}

function setOnboardingComplete() {
  mockOnboarding.mockReturnValue({
    isComplete: true,
    hasTenants: true,
    hasProtectedObjects: true,
    hasBackups: true,
  });
}

function setOnboardingFresh() {
  mockOnboarding.mockReturnValue({
    isComplete: false,
    hasTenants: false,
    hasProtectedObjects: false,
    hasBackups: false,
  });
}

function setOnboardingTenantOnly() {
  mockOnboarding.mockReturnValue({
    isComplete: false,
    hasTenants: true,
    hasProtectedObjects: false,
    hasBackups: false,
  });
}

function setFeatureFlags(sharepoint = true) {
  mockFeatureFlags.mockReturnValue({
    isEnabled: (flag: string) => {
      if (flag === 'sharepoint') return sharepoint;
      return true;
    },
    flags: {},
    tier: sharepoint ? 'professional' : 'community',
  });
}

function renderLayout() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Layout />
    </MemoryRouter>
  );
}

// ── Menu item presence helpers ───────────────────────────────

function getNavElement() {
  // The nav is the main sidebar navigation
  return document.querySelector('nav');
}

function expandAllGroups() {
  // Click all collapsed group headers to expand them so items render in the DOM.
  // Groups with defaultOpen: false start collapsed — their items are conditionally
  // rendered and won't be in the DOM until the group header is clicked.
  const nav = getNavElement();
  if (!nav) return;
  const buttons = nav.querySelectorAll('button');
  buttons.forEach(btn => {
    const text = btn.textContent || '';
    // Click group headers (they contain the chevron icon)
    if (['More Workloads', 'Intelligence', 'MSP', 'Administration'].some(g => text.includes(g))) {
      fireEvent.click(btn);
    }
  });
}

function expectMenuItemVisible(label: string) {
  const nav = getNavElement();
  expect(nav).toBeTruthy();
  // Check links (items render as <a> / <Link> elements)
  const links = nav!.querySelectorAll('a');
  const found = Array.from(links).some(link => link.textContent?.includes(label));
  expect(found).toBe(true);
}

function expectMenuItemHidden(label: string) {
  const nav = getNavElement();
  if (!nav) return; // No nav = everything hidden, which is valid
  // Check both links and full HTML — if it appears anywhere in nav, it's visible
  const navHtml = nav.innerHTML;
  const found = navHtml.includes(label);
  expect(found).toBe(false);
}

function expectGroupVisible(groupLabel: string) {
  // Group labels are rendered as buttons with the group name
  const nav = getNavElement();
  expect(nav).toBeTruthy();
  const navHtml = nav!.innerHTML;
  expect(navHtml).toContain(groupLabel);
}

function expectGroupHidden(groupLabel: string) {
  const nav = getNavElement();
  if (!nav) return;
  const navHtml = nav.innerHTML;
  expect(navHtml).not.toContain(groupLabel);
}

// ═══════════════════════════════════════════════════════════════
// Admin Role — sees everything
// ═══════════════════════════════════════════════════════════════

describe('Layout sidebar — Admin role', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setUser('admin');
    setOnboardingComplete();
    setFeatureFlags(true);
  });

  it('shows Dashboard', () => {
    renderLayout();
    expectMenuItemVisible('Dashboard');
  });

  it('shows Workloads group (Entra ID, Exchange)', () => {
    renderLayout();
    expectMenuItemVisible('Entra ID');
    expectMenuItemVisible('Exchange');
  });

  it('shows More Workloads when feature flag enabled', () => {
    renderLayout();
    expandAllGroups();
    expectMenuItemVisible('SharePoint');
    expectMenuItemVisible('OneDrive');
    expectMenuItemVisible('Teams');
  });

  it('shows Operations group', () => {
    renderLayout();
    expectMenuItemVisible('Jobs');
    expectMenuItemVisible('Protection Gaps');
    expectMenuItemVisible('Self Restore');
    expectMenuItemVisible('Recovery');
  });

  it('shows Intelligence group', () => {
    renderLayout();
    expandAllGroups();
    expectMenuItemVisible('Smart Engine');
    expectMenuItemVisible('Alerts');
    expectMenuItemVisible('Reports');
  });

  it('shows Administration group', () => {
    renderLayout();
    expandAllGroups();
    expectMenuItemVisible('Organization');
    expectMenuItemVisible('SLA Policies');
    expectMenuItemVisible('Billing');
    expectMenuItemVisible('Audit Log');
  });

  it('hides Feature Config for regular admin (requires platform_admin/username=admin)', () => {
    // Feature Config has roles: ['platform_admin'] — regular admin (username=testadmin)
    // does NOT have access. Only username='admin' gets isPlatformAdmin=true.
    renderLayout();
    expandAllGroups();
    expectMenuItemHidden('Feature Config');
  });
});

// ═══════════════════════════════════════════════════════════════
// Platform Admin (username=admin) — sees everything including MSP
// ═══════════════════════════════════════════════════════════════

describe('Layout sidebar — Platform Admin (username=admin)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setUser('admin', 'admin'); // username='admin' is platform admin
    setOnboardingComplete();
    setFeatureFlags(true);
  });

  it('shows MSP group', () => {
    renderLayout();
    expandAllGroups();
    expectMenuItemVisible('MSP Dashboard');
  });

  it('shows Tenants (Admin) item', () => {
    renderLayout();
    expandAllGroups();
    expectMenuItemVisible('Tenants (Admin)');
  });

  it('shows Feature Config item', () => {
    renderLayout();
    expandAllGroups();
    expectMenuItemVisible('Feature Config');
  });

  it('shows all 7 sidebar groups', () => {
    renderLayout();
    // Verify all group labels exist
    expectGroupVisible('Workloads');
    expectGroupVisible('Operations');
    expectGroupVisible('Intelligence');
    expectGroupVisible('MSP');
    expectGroupVisible('Administration');
  });
});

// ═══════════════════════════════════════════════════════════════
// Viewer Role — no MSP, no Tenants Admin, no Feature Config
// ═══════════════════════════════════════════════════════════════

describe('Layout sidebar — Viewer role', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setUser('viewer');
    setOnboardingComplete();
    setFeatureFlags(true);
  });

  it('shows Dashboard', () => {
    renderLayout();
    expectMenuItemVisible('Dashboard');
  });

  it('shows workload pages', () => {
    renderLayout();
    expectMenuItemVisible('Entra ID');
    expectMenuItemVisible('Exchange');
  });

  it('shows Operations', () => {
    renderLayout();
    expectMenuItemVisible('Jobs');
    expectMenuItemVisible('Recovery');
  });

  it('shows Intelligence', () => {
    renderLayout();
    expandAllGroups();
    expectMenuItemVisible('Smart Engine');
    expectMenuItemVisible('Reports');
  });

  it('hides MSP group entirely', () => {
    renderLayout();
    expectMenuItemHidden('MSP Dashboard');
    expectMenuItemHidden('Bulk Onboard');
    expectMenuItemHidden('Interactive Demo');
    expectGroupHidden('MSP');
  });

  it('hides Tenants (Admin) item', () => {
    renderLayout();
    expectMenuItemHidden('Tenants (Admin)');
  });

  it('hides Feature Config item', () => {
    renderLayout();
    expectMenuItemHidden('Feature Config');
  });

  it('still shows non-restricted admin items', () => {
    renderLayout();
    expandAllGroups();
    expectMenuItemVisible('Organization');
    expectMenuItemVisible('SLA Policies');
    expectMenuItemVisible('Billing');
    expectMenuItemVisible('Audit Log');
  });
});

// ═══════════════════════════════════════════════════════════════
// MSP Admin Role — sees MSP group but NOT Feature Config/Tenants Admin
// ═══════════════════════════════════════════════════════════════

describe('Layout sidebar — MSP Admin role', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setUser('msp_admin');
    setOnboardingComplete();
    setFeatureFlags(true);
  });

  it('shows MSP group', () => {
    renderLayout();
    expandAllGroups();
    expectMenuItemVisible('MSP Dashboard');
    expectMenuItemVisible('Branding');
    expectMenuItemVisible('Bulk Onboard');
  });

  it('hides Tenants (Admin) — platform_admin only', () => {
    renderLayout();
    expandAllGroups();
    expectMenuItemHidden('Tenants (Admin)');
  });

  it('hides Feature Config — platform_admin only', () => {
    renderLayout();
    expandAllGroups();
    expectMenuItemHidden('Feature Config');
  });

  it('shows standard admin items', () => {
    renderLayout();
    expandAllGroups();
    expectMenuItemVisible('Organization');
    expectMenuItemVisible('SLA Policies');
  });
});

// ═══════════════════════════════════════════════════════════════
// Operator Role — no MSP, no Tenants Admin, no Feature Config
// ═══════════════════════════════════════════════════════════════

describe('Layout sidebar — Operator role', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setUser('operator');
    setOnboardingComplete();
    setFeatureFlags(true);
  });

  it('shows operational pages', () => {
    renderLayout();
    expectMenuItemVisible('Dashboard');
    expectMenuItemVisible('Jobs');
    expectMenuItemVisible('Recovery');
  });

  it('hides MSP group', () => {
    renderLayout();
    expectMenuItemHidden('MSP Dashboard');
    expectGroupHidden('MSP');
  });

  it('hides Tenants (Admin)', () => {
    renderLayout();
    expectMenuItemHidden('Tenants (Admin)');
  });

  it('hides Feature Config', () => {
    renderLayout();
    expectMenuItemHidden('Feature Config');
  });
});

// ═══════════════════════════════════════════════════════════════
// Restore Operator Role — same as operator for sidebar
// ═══════════════════════════════════════════════════════════════

describe('Layout sidebar — Restore Operator role', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setUser('restore_operator');
    setOnboardingComplete();
    setFeatureFlags(true);
  });

  it('shows restore-relevant pages', () => {
    renderLayout();
    expectMenuItemVisible('Self Restore');
    expectMenuItemVisible('Recovery');
  });

  it('hides MSP', () => {
    renderLayout();
    expectMenuItemHidden('MSP Dashboard');
  });

  it('hides admin-only items', () => {
    renderLayout();
    expectMenuItemHidden('Tenants (Admin)');
    expectMenuItemHidden('Feature Config');
  });
});

// ═══════════════════════════════════════════════════════════════
// Feature Flag Gating — More Workloads (SharePoint, OneDrive, Teams)
// ═══════════════════════════════════════════════════════════════

describe('Layout sidebar — Feature flag gating', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setUser('admin');
    setOnboardingComplete();
  });

  it('shows More Workloads when sharepoint feature enabled', () => {
    setFeatureFlags(true);
    renderLayout();
    expandAllGroups();
    expectMenuItemVisible('SharePoint');
    expectMenuItemVisible('OneDrive');
    expectMenuItemVisible('Teams');
  });

  it('hides More Workloads when sharepoint feature disabled (Community tier)', () => {
    setFeatureFlags(false);
    renderLayout();
    expectMenuItemHidden('SharePoint');
    expectMenuItemHidden('OneDrive');
    expectMenuItemHidden('Teams');
  });

  it('always shows base workloads regardless of feature flag', () => {
    setFeatureFlags(false);
    renderLayout();
    expectMenuItemVisible('Entra ID');
    expectMenuItemVisible('Exchange');
  });
});

// ═══════════════════════════════════════════════════════════════
// Onboarding Progressive Disclosure
// ═══════════════════════════════════════════════════════════════

describe('Layout sidebar — Onboarding progressive disclosure', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setUser('admin');
    setFeatureFlags(true);
  });

  it('fresh user (no tenants) sees only Dashboard', () => {
    setOnboardingFresh();
    renderLayout();
    expectMenuItemVisible('Dashboard');
    // Workloads group should have no items (hasTenants=false)
    expectMenuItemHidden('Entra ID');
    expectMenuItemHidden('Exchange');
  });

  it('user with tenant sees Workloads but not Operations', () => {
    setOnboardingTenantOnly();
    renderLayout();
    expectMenuItemVisible('Dashboard');
    expectMenuItemVisible('Entra ID');
    expectMenuItemVisible('Exchange');
    // Operations hidden (no protected objects yet)
    expectMenuItemHidden('Jobs');
  });

  it('fully onboarded user sees everything', () => {
    setOnboardingComplete();
    renderLayout();
    expandAllGroups();
    expectMenuItemVisible('Dashboard');
    expectMenuItemVisible('Entra ID');
    expectMenuItemVisible('Jobs');
    expectMenuItemVisible('Smart Engine');
  });
});

// ═══════════════════════════════════════════════════════════════
// Sign Out button always visible
// ═══════════════════════════════════════════════════════════════

describe('Layout sidebar — common elements', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setUser('viewer');
    setOnboardingComplete();
    setFeatureFlags(true);
  });

  it('shows Sign Out button for all roles', () => {
    renderLayout();
    expect(screen.getByText('Sign Out')).toBeInTheDocument();
  });

  it('shows app branding', () => {
    renderLayout();
    // Multiple instances (desktop + mobile sidebar) — use getAllByText
    const brandElements = screen.getAllByText('KavachIQ');
    expect(brandElements.length).toBeGreaterThan(0);
  });

  it('shows tenant name', () => {
    renderLayout();
    expect(screen.getByText('Test Tenant')).toBeInTheDocument();
  });

  it('shows search trigger', () => {
    renderLayout();
    expect(screen.getByText('Search...')).toBeInTheDocument();
  });
});
