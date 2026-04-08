import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Mail, HardDrive, Globe, Shield, ShieldCheck, Activity, Building2, FileText, LogOut, ShieldAlert, KeyRound, MessageSquare, Bell, Brain, Search, RotateCcw, BarChart3, Gauge, ChevronDown, Menu, X, Users, Palette, Play, Bot, CreditCard, Scale } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useOnboarding } from '../contexts/OnboardingContext';
import { useFeatureFlags } from '../contexts/FeatureFlagContext';
import { useBranding } from '../contexts/BrandingContext';
import CommandPalette from './CommandPalette';
import ProductTour from './ProductTour';
import FeedbackWidget from './FeedbackWidget';
import ThemeToggle from './ThemeToggle';
import { useTenantSwitcher } from '../hooks/useTenant';
import { api } from '../api/client';

interface NavItem {
  path: string;
  label: string;
  icon: any;
  roles?: string[];  // If set, only visible to these roles
}

interface NavGroup {
  label: string;
  items: NavItem[];
  defaultOpen?: boolean;
  roles?: string[];  // If set, entire group only visible to these roles
  featureFlag?: string; // If set, group only visible when this feature is enabled
}

const navGroups: NavGroup[] = [
  {
    label: '',
    defaultOpen: true,
    items: [
      { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    ],
  },
  {
    label: 'Workloads',
    defaultOpen: true,
    items: [
      { path: '/entra-id', label: 'Entra ID', icon: KeyRound },
      { path: '/exchange', label: 'Exchange', icon: Mail },
    ],
  },
  {
    label: 'More Workloads',
    defaultOpen: false,
    featureFlag: 'sharepoint',  // Gated — only shows when SharePoint workload is enabled (Professional+)
    items: [
      { path: '/sharepoint', label: 'SharePoint', icon: Globe },
      { path: '/onedrive', label: 'OneDrive', icon: HardDrive },
      { path: '/teams', label: 'Teams', icon: MessageSquare },
    ],
  },
  {
    label: 'Operations',
    defaultOpen: true,
    items: [
      { path: '/jobs', label: 'Jobs', icon: Activity },
      { path: '/failed-items', label: 'Protection Gaps', icon: ShieldAlert },
      { path: '/restore', label: 'Self Restore', icon: RotateCcw },
      { path: '/recovery', label: 'Recovery', icon: ShieldCheck },
    ],
  },
  {
    label: 'Intelligence',
    defaultOpen: false,
    items: [
      { path: '/smart-engine', label: 'Smart Engine', icon: Brain },
      { path: '/agent-shield', label: 'Agent Shield', icon: Bot },
      { path: '/ediscovery', label: 'eDiscovery', icon: Scale },
      { path: '/org-context', label: 'Org Context', icon: Shield },
      { path: '/alerts', label: 'Alerts', icon: Bell },
      { path: '/reports', label: 'Reports', icon: BarChart3 },
    ],
  },
  {
    label: 'MSP',
    defaultOpen: false,
    roles: ['platform_admin', 'msp_admin'],
    items: [
      { path: '/msp', label: 'MSP Dashboard', icon: Building2 },
      { path: '/msp/billing', label: 'Billing', icon: BarChart3 },
      { path: '/msp/branding', label: 'Branding', icon: Palette },
      { path: '/msp/onboard', label: 'Bulk Onboard', icon: Users },
      { path: '/msp/demo', label: 'Interactive Demo', icon: Play },
    ],
  },
  {
    label: 'Administration',
    defaultOpen: false,
    items: [
      { path: '/settings', label: 'Organization', icon: Building2 },
      { path: '/tenants', label: 'Tenants (Admin)', icon: Building2, roles: ['platform_admin'] },
      { path: '/sla-policies', label: 'SLA Policies', icon: Shield },
      { path: '/usage', label: 'Usage & License', icon: Gauge },
      { path: '/billing', label: 'Billing', icon: CreditCard },
      { path: '/security-posture', label: 'Security', icon: Shield },
      { path: '/audit', label: 'Audit Log', icon: FileText },
      { path: '/performance', label: 'Performance', icon: Activity },
      { path: '/features', label: 'Feature Config', icon: Shield, roles: ['platform_admin'] },
    ],
  },
];

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [commandOpen, setCommandOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [showTour, setShowTour] = useState(false);
  // Load tour status from server session
  useEffect(() => {
    api.get<any>('/auth/session')
      .then(session => {
        if (!session?.preferences?.tour_completed) setShowTour(true);
      })
      .catch(() => {});
  }, []);

  // Close mobile sidebar on route change
  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  // Get user role for role-based nav filtering
  const { user } = useAuth();
  const userRole = user?.role || 'viewer';
  // Platform superadmin (username=admin) vs tenant admin (any other ADMIN user)
  const isPlatformAdmin = user?.username === 'admin';
  const branding = useBranding();

  // Progressive sidebar based on onboarding state
  let onboarding: any = null;
  try { onboarding = useOnboarding(); } catch { /* OnboardingProvider not mounted yet */ }

  // Feature flags for workload gating
  let featureFlags: any = null;
  try { featureFlags = useFeatureFlags(); } catch { /* FeatureFlagProvider not mounted yet */ }
  const isFeatureEnabled = (flag: string) => featureFlags?.isEnabled?.(flag) ?? true;

  const visibleGroups = navGroups
    // Filter groups by role
    .filter(group => !group.roles || group.roles.includes(userRole) || (group.roles.includes('platform_admin') && isPlatformAdmin))
    // Filter groups by feature flag
    .filter(group => !group.featureFlag || isFeatureEnabled(group.featureFlag))
    // Filter items within groups by role
    .map(group => ({
      ...group,
      items: group.items.filter(item => !item.roles || item.roles.includes(userRole) || (item.roles.includes('platform_admin') && isPlatformAdmin)),
    }))
    .map(group => {
    if (!onboarding || onboarding.isComplete) return group; // Show all when complete

    // Always show Dashboard
    if (!group.label) return group;

    // Show workloads only after tenant connected
    if (group.label === 'Workloads' && !onboarding.hasTenants) return { ...group, items: [] };

    // Hide "More Workloads" (SharePoint, OneDrive, Teams) until tenant connected
    if (group.label === 'More Workloads' && !onboarding.hasTenants) return { ...group, items: [] };

    // Show operations only after first backup
    if (group.label === 'Operations' && !onboarding.hasProtectedObjects) return { ...group, items: [] };

    // Show intelligence only after backups exist
    if (group.label === 'Intelligence' && !onboarding.hasBackups) return { ...group, items: [] };

    // MSP group: always gated by role (already handled above), no onboarding gate needed

    // Administration: only show Billing before tenant connected (prospect needs to see pricing)
    // After tenant connected, show all admin items
    if (group.label === 'Administration' && !onboarding.hasTenants) {
      return {
        ...group,
        items: group.items.filter(item =>
          item.path === '/billing' || item.path === '/settings'
        ),
      };
    }

    return group;
  }).filter(g => !g.label || g.items.length > 0);

  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    navGroups.forEach(g => { if (g.label) init[g.label] = !g.defaultOpen; });
    return init;
  });

  // Auto-expand group if current path is in it
  useEffect(() => {
    navGroups.forEach(g => {
      if (g.label && g.items.some(i => location.pathname === i.path || (i.path !== '/' && location.pathname.startsWith(i.path)))) {
        setCollapsed(prev => ({ ...prev, [g.label]: false }));
      }
    });
  }, [location.pathname]);

  // ⌘K / Ctrl+K to open command palette
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const { logout } = useAuth();
  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Tenant switcher
  const { tenants: userTenants, selectedTenant, switchTenant, isMultiTenant } = useTenantSwitcher();
  const [tenantDropdownOpen, setTenantDropdownOpen] = useState(false);

  const toggleGroup = (label: string) => {
    setCollapsed(prev => ({ ...prev, [label]: !prev[label] }));
  };

  // Sidebar content (shared between desktop and mobile)
  const sidebarContent = (
    <>
        <div className="px-4 py-3 border-b border-sidebar-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {branding.logoUrl ? (
                <img src={branding.logoUrl} alt={branding.companyName} className="w-7 h-7 rounded" />
              ) : (
                <Shield className="w-7 h-7 text-blue-400" />
              )}
              <div>
                <h1 className="text-base font-bold leading-tight">{branding.companyName}</h1>
                <p className="text-[10px] text-muted-foreground">{branding.tagline}</p>
              </div>
            </div>
            <button
              onClick={() => setCommandOpen(true)}
              title="Search (⌘K)"
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            >
              <Search className="w-4 h-4" />
            </button>
          </div>
          {/* Search trigger */}
          <button
            onClick={() => setCommandOpen(true)}
            className="mt-2 w-full flex items-center gap-2 px-2.5 py-1.5 bg-muted border border-border rounded-lg text-xs text-muted-foreground hover:text-foreground hover:border-border transition-colors"
          >
            <Search className="w-3.5 h-3.5" />
            <span className="flex-1 text-left">Search...</span>
            <kbd className="px-1 py-0.5 bg-secondary rounded text-[9px] text-muted-foreground font-mono">⌘K</kbd>
          </button>
        </div>

        {/* Tenant Switcher — shown when user has tenants */}
        {selectedTenant && (
          <div className="px-3 mt-2 relative">
            <button
              onClick={() => isMultiTenant && setTenantDropdownOpen(!tenantDropdownOpen)}
              className={`w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-sm border transition-colors ${
                isMultiTenant
                  ? 'border-border hover:border-blue-500/30 hover:bg-accent cursor-pointer'
                  : 'border-transparent cursor-default'
              }`}
            >
              <Building2 className="w-4 h-4 text-blue-400 shrink-0" />
              <span className="flex-1 text-left font-medium text-foreground truncate">{selectedTenant.name}</span>
              {isMultiTenant && <ChevronDown className={`w-3.5 h-3.5 text-muted-foreground transition-transform ${tenantDropdownOpen ? 'rotate-180' : ''}`} />}
            </button>
            {tenantDropdownOpen && isMultiTenant && (
              <div className="absolute left-3 right-3 top-full mt-1 bg-card border border-border rounded-lg shadow-xl z-50 py-1">
                {userTenants.map(t => (
                  <button
                    key={t.id}
                    onClick={() => { setTenantDropdownOpen(false); if (t.id !== selectedTenant.id) switchTenant(t.id); }}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-accent transition-colors ${
                      t.id === selectedTenant.id ? 'text-blue-400 font-medium' : 'text-foreground'
                    }`}
                  >
                    <Building2 className="w-3.5 h-3.5 shrink-0" />
                    <span className="flex-1 truncate">{t.name}</span>
                    {t.id === selectedTenant.id && <span className="text-xs text-blue-400">●</span>}
                  </button>
                ))}
                <div className="border-t border-border mt-1 pt-1">
                  <button
                    onClick={() => { setTenantDropdownOpen(false); navigate('/onboard'); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                  >
                    <span className="text-xs">＋</span>
                    <span>Connect New Tenant</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        <nav className="flex-1 px-2 mt-2 overflow-y-auto">
          {visibleGroups.map((group, gi) => (
            <div key={gi} className={group.label ? 'mt-2' : ''}>
              {group.label && (
                <button
                  onClick={() => toggleGroup(group.label)}
                  className="flex items-center justify-between w-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors"
                >
                  {group.label}
                  <ChevronDown className={`w-3 h-3 transition-transform ${collapsed[group.label] ? '-rotate-90' : ''}`} />
                </button>
              )}
              {!collapsed[group.label] && (
                <div className="space-y-0.5">
                  {group.items.map(item => {
                    const active = location.pathname === item.path ||
                      (item.path !== '/' && location.pathname.startsWith(item.path));
                    return (
                      <Link
                        key={item.path}
                        to={item.path}
                        className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-[13px] font-medium transition-colors ${
                          active
                            ? 'bg-primary text-primary-foreground'
                            : 'text-sidebar-foreground/70 hover:bg-accent hover:text-foreground'
                        }`}
                      >
                        <item.icon className="w-4 h-4 flex-shrink-0" />
                        {item.label}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </nav>

        <div className="p-2 border-t border-sidebar-border">
          <div className="flex items-center justify-between px-2.5 py-1">
            <ThemeToggle />
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-2.5 py-1.5 w-full text-xs text-muted-foreground hover:text-foreground rounded-md hover:bg-accent transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign Out
          </button>
        </div>
    </>
  );

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Mobile header — visible on small screens only */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-40 px-4 py-3 flex items-center justify-between bg-card border-b border-border">
        <button onClick={() => setMobileOpen(true)} className="p-1 text-muted-foreground hover:text-foreground">
          <Menu className="w-6 h-6" />
        </button>
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-blue-400" />
          <span className="text-sm font-bold text-foreground">KavachIQ</span>
        </div>
        <button onClick={() => setCommandOpen(true)} className="p-1 text-muted-foreground hover:text-foreground">
          <Search className="w-5 h-5" />
        </button>
      </div>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <aside className="relative w-72 h-full bg-sidebar text-sidebar-foreground flex flex-col shadow-xl">
            <div className="absolute top-3 right-3">
              <button onClick={() => setMobileOpen(false)} className="p-1 text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>
            {sidebarContent}
          </aside>
        </div>
      )}

      {/* Desktop sidebar — hidden on mobile */}
      <aside className="hidden lg:flex w-56 flex-col bg-sidebar text-sidebar-foreground">
        {sidebarContent}
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto pt-14 lg:pt-0 bg-background text-foreground">
        <div className="p-4 sm:p-6">
          <Outlet />
        </div>
      </main>

      {/* Command Palette (⌘K) */}
      <CommandPalette isOpen={commandOpen} onClose={() => setCommandOpen(false)} onOpen={() => setCommandOpen(true)} visiblePaths={visibleGroups.flatMap(g => g.items.map(i => i.path))} />

      {/* Product Tour (first-time users) */}
      {showTour && <ProductTour onComplete={() => setShowTour(false)} />}

      {/* Feedback Widget */}
      <FeedbackWidget />
    </div>
  );
}
