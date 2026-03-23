import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Mail, HardDrive, Globe, Shield, Activity, Building2, FileText, LogOut, ShieldAlert, KeyRound, MessageSquare, Bell, Brain, Search, Command } from 'lucide-react';
import { api } from '../api/client';
import CommandPalette from './CommandPalette';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/exchange', label: 'Exchange', icon: Mail },
  { path: '/onedrive', label: 'OneDrive', icon: HardDrive },
  { path: '/sharepoint', label: 'SharePoint', icon: Globe },
  { path: '/teams', label: 'Teams', icon: MessageSquare },
  { path: '/entra-id', label: 'Entra ID', icon: KeyRound },
  { path: '/sla-policies', label: 'SLA Policies', icon: Shield },
  { path: '/jobs', label: 'Jobs', icon: Activity },
  { path: '/failed-items', label: 'Failed Items', icon: ShieldAlert },
  { path: '/tenants', label: 'Tenants', icon: Building2 },
  { path: '/smart-engine', label: 'Smart Engine', icon: Brain },
  { path: '/alerts', label: 'Alerts', icon: Bell },
  { path: '/audit', label: 'Audit Log', icon: FileText },
];

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [commandOpen, setCommandOpen] = useState(false);

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

  const handleLogout = () => {
    api.clearToken();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-white flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <Shield className="w-8 h-8 text-blue-400" />
            <div>
              <h1 className="text-lg font-bold leading-tight">M365 Vault</h1>
              <p className="text-xs text-gray-400">Data Protection</p>
            </div>
          </div>
        </div>

        {/* Search trigger */}
        <button
          onClick={() => setCommandOpen(true)}
          className="mx-3 mt-3 flex items-center gap-2 px-3 py-2 text-sm text-gray-400 bg-gray-800 rounded-lg hover:bg-gray-700 hover:text-gray-200 transition-colors"
        >
          <Search className="w-4 h-4" />
          <span className="flex-1 text-left">Search...</span>
          <kbd className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] bg-gray-700 rounded font-mono">
            <Command className="w-2.5 h-2.5" />K
          </kbd>
        </button>

        <nav className="flex-1 p-2 mt-1 space-y-1 overflow-y-auto">
          {navItems.map(item => {
            const active = location.pathname === item.path ||
              (item.path !== '/' && location.pathname.startsWith(item.path));
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-gray-700">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-3 py-2 w-full text-sm text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6">
          <Outlet />
        </div>
      </main>

      {/* Command Palette (⌘K) */}
      <CommandPalette isOpen={commandOpen} onClose={() => setCommandOpen(false)} />
    </div>
  );
}
