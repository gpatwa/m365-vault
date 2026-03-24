import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Mail, HardDrive, Globe, Shield, Activity, Building2, FileText, LogOut, ShieldAlert, KeyRound, MessageSquare, Bell, Brain, Search, RotateCcw, BarChart3, Gauge, ChevronDown } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import CommandPalette from './CommandPalette';

interface NavItem {
  path: string;
  label: string;
  icon: any;
}

interface NavGroup {
  label: string;
  items: NavItem[];
  defaultOpen?: boolean;
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
      { path: '/exchange', label: 'Exchange', icon: Mail },
      { path: '/onedrive', label: 'OneDrive', icon: HardDrive },
      { path: '/sharepoint', label: 'SharePoint', icon: Globe },
      { path: '/teams', label: 'Teams', icon: MessageSquare },
      { path: '/entra-id', label: 'Entra ID', icon: KeyRound },
    ],
  },
  {
    label: 'Operations',
    defaultOpen: true,
    items: [
      { path: '/jobs', label: 'Jobs', icon: Activity },
      { path: '/failed-items', label: 'Failed Items', icon: ShieldAlert },
      { path: '/restore', label: 'Restore', icon: RotateCcw },
    ],
  },
  {
    label: 'Intelligence',
    defaultOpen: false,
    items: [
      { path: '/smart-engine', label: 'Smart Engine', icon: Brain },
      { path: '/alerts', label: 'Alerts', icon: Bell },
      { path: '/reports', label: 'Reports', icon: BarChart3 },
    ],
  },
  {
    label: 'Administration',
    defaultOpen: false,
    items: [
      { path: '/tenants', label: 'Tenants', icon: Building2 },
      { path: '/sla-policies', label: 'SLA Policies', icon: Shield },
      { path: '/usage', label: 'Usage & License', icon: Gauge },
      { path: '/audit', label: 'Audit Log', icon: FileText },
    ],
  },
];

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [commandOpen, setCommandOpen] = useState(false);
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

  const toggleGroup = (label: string) => {
    setCollapsed(prev => ({ ...prev, [label]: !prev[label] }));
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-gray-900 text-white flex flex-col">
        <div className="px-4 py-3 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <Shield className="w-7 h-7 text-blue-400" />
            <div>
              <h1 className="text-base font-bold leading-tight">Shieldio</h1>
              <p className="text-[10px] text-gray-500">Protect Your Cloud Data</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-2 mt-2 overflow-y-auto">
          {navGroups.map((group, gi) => (
            <div key={gi} className={group.label ? 'mt-2' : ''}>
              {group.label && (
                <button
                  onClick={() => toggleGroup(group.label)}
                  className="flex items-center justify-between w-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-gray-500 hover:text-gray-300 transition-colors"
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
                            ? 'bg-blue-600 text-white'
                            : 'text-gray-300 hover:bg-gray-800 hover:text-white'
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

        <div className="p-2 border-t border-gray-700">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-2.5 py-1.5 w-full text-xs text-gray-400 hover:text-white rounded-md hover:bg-gray-800 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {/* Top bar with search */}
        <div className="sticky top-0 z-10 bg-white/80 backdrop-blur-sm border-b border-gray-100 px-6 py-2.5 flex items-center justify-between">
          <button
            onClick={() => setCommandOpen(true)}
            className="flex items-center gap-2.5 px-3.5 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-400 hover:border-gray-300 hover:text-gray-500 hover:shadow-sm transition-all w-full max-w-md"
          >
            <Search className="w-4 h-4" />
            <span className="flex-1 text-left">Search backups, check status, investigate...</span>
            <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-white border border-gray-200 rounded text-[10px] text-gray-400 font-mono">
              ⌘K
            </kbd>
          </button>
        </div>
        <div className="p-6">
          <Outlet />
        </div>
      </main>

      {/* Command Palette (⌘K) */}
      <CommandPalette isOpen={commandOpen} onClose={() => setCommandOpen(false)} onOpen={() => setCommandOpen(true)} />
    </div>
  );
}
