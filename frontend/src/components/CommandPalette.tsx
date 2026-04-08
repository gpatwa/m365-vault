/**
 * ⌘K Command Palette — intent-aware unified search.
 *
 * Classifies queries into intents (find_recover, investigate, navigate, etc.)
 * and shows categorized results with inline actions.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, Mail, FileText, MessageSquare, Shield, Calendar, User,
  Command, ArrowRight, Clock, Loader2, RotateCcw, Eye, Download,
  AlertTriangle, XCircle, CheckCircle, Bookmark, ExternalLink,
} from 'lucide-react';
import { api } from '../api/client';
import { useTenantId } from '../hooks/useTenant';
import { WORKLOAD_MAP } from '../config/workloads';
import { formatSize } from '../utils/format';

// ── Types ──

interface IntentResult {
  id: number;
  type: string;
  name: string;
  subtitle?: string;
  workload?: string;
  status?: string;
  date?: string;
  size_bytes?: number;
  severity?: string;
  actions?: string[];
  path?: string;
  can_retry?: boolean;
  resolution?: string;
}

interface IntentCategory {
  icon: string;
  items: IntentResult[];
}

interface IntentSearchResponse {
  query: string;
  intent: string;
  intents: { intent: string; confidence: number }[];
  categories: Record<string, IntentCategory>;
  navigation: { label: string; path: string; score: number }[];
  total: number;
}

// ── Icons ──

const TYPE_ICONS: Record<string, typeof Mail> = {
  email: Mail, calendar_event: Calendar, contact: User, file: FileText,
  folder: FileText, object: Shield, failed_item: XCircle, audit_log: Bookmark,
  anomaly: AlertTriangle, link: ExternalLink, channel_message: MessageSquare,
  chat_message: MessageSquare, user: User, group: User,
  directory_role: Shield, conditional_access_policy: Shield,
  app_registration: Shield, named_location: Shield,
};

const CATEGORY_ICONS: Record<string, typeof Mail> = {
  Emails: Mail, Files: FileText, Messages: MessageSquare,
  Identity: User, Configuration: Shield, Failures: XCircle,
  'Audit Trail': Bookmark, Anomalies: AlertTriangle,
  'Protected Objects': Shield, Compliance: CheckCircle,
};

const INTENT_LABELS: Record<string, string> = {
  find_recover: '🔍 Finding items to recover',
  status_check: '📊 Checking protection status',
  investigate: '🔧 Investigating issues',
  navigate: '🧭 Navigating',
  audit: '📋 Searching audit trail',
  compliance: '✅ Checking compliance',
};

const ACTION_ICONS: Record<string, typeof Mail> = {
  restore: RotateCcw, preview: Eye, download: Download,
  view: ArrowRight, backup: RotateCcw, retry: RotateCcw,
  dismiss: XCircle, investigate: AlertTriangle,
};

// ── Quick Links ──

const QUICK_LINKS = [
  { label: 'Dashboard', path: '/', shortcut: 'D' },
  { label: 'Jobs', path: '/jobs', shortcut: 'J' },
  { label: 'Entra ID', path: '/entra-id', shortcut: 'I' },
  { label: 'Exchange', path: '/exchange', shortcut: 'E' },
  { label: 'Agent Shield', path: '/agent-shield', shortcut: 'G' },
  { label: 'SLA Policies', path: '/sla-policies', shortcut: 'P' },
  { label: 'Smart Engine', path: '/smart-engine', shortcut: 'H' },
  { label: 'Failed Items', path: '/failed-items', shortcut: 'F' },
  { label: 'Alerts', path: '/alerts', shortcut: 'A' },
  { label: 'Reports', path: '/reports', shortcut: 'R' },
];

// ── Component ──

export default function CommandPalette({ isOpen, onClose, onOpen, visiblePaths }: {
  isOpen: boolean; onClose: () => void; onOpen?: () => void;
  /** Paths visible in the sidebar — used to filter quick links to match progressive disclosure.
   * If not provided, all QUICK_LINKS are shown (backward compat). */
  visiblePaths?: string[];
}) {
  const [query, setQuery] = useState('');
  const [searchData, setSearchData] = useState<IntentSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [workloadFilter, setWorkloadFilter] = useState<string | null>(null);
  const [recentSearches, setRecentSearches] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem('kavachiq_recent') || '[]'); } catch { return []; }
  });

  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const tenantId = useTenantId();
  const navigate = useNavigate();
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Listen for SearchTrigger events
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      setWorkloadFilter(detail?.workloadFilter || null);
      onOpen?.();
    };
    window.addEventListener('open-command-palette', handler);
    return () => window.removeEventListener('open-command-palette', handler);
  }, [onOpen]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSearchData(null);
      setSelectedIdx(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Debounced intent search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query || query.length < 2) { setSearchData(null); return; }

    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const filterParam = workloadFilter ? `&workload=${workloadFilter}` : '';
        const data = await api.get<IntentSearchResponse>(
          `/search/intent?q=${encodeURIComponent(query)}&tenant_id=${tenantId}&limit=15${filterParam}`
        );
        setSearchData(data);
        setSelectedIdx(0);
      } catch {
        setSearchData(null);
      }
      setLoading(false);
    }, 300);

    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, tenantId, workloadFilter]);

  const saveRecent = useCallback((q: string) => {
    const updated = [q, ...recentSearches.filter(s => s !== q)].slice(0, 5);
    setRecentSearches(updated);
    localStorage.setItem('kavachiq_recent', JSON.stringify(updated));
  }, [recentSearches]);

  const handleAction = (item: IntentResult, action: string) => {
    saveRecent(query);
    onClose();
    // Route based on action type
    if (action === 'view' || action === 'preview') {
      if (item.path) { navigate(item.path); return; }
      if (item.workload) {
        const path = item.workload === 'entra_id' ? '/entra-id' : `/${item.workload}`;
        navigate(path);
      }
    } else if (action === 'restore') {
      navigate('/self-restore');
    } else if (action === 'investigate') {
      navigate('/smart-engine');
    } else if (action === 'retry') {
      navigate('/failed-items');
    }
  };

  const goToLink = (path: string) => { navigate(path); onClose(); };

  // Keyboard
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') { onClose(); return; }
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIdx(p => p + 1); }
    if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIdx(p => Math.max(0, p - 1)); }
    if (e.key === 'Enter') {
      e.preventDefault();
      if (query.length < 2 && filteredLinks.length > 0) {
        goToLink(filteredLinks[selectedIdx % filteredLinks.length]?.path || '/');
      }
    }
  };

  // Filter quick links to match sidebar progressive disclosure.
  // Only show navigation items that are visible in the sidebar.
  // This ensures ⌘K and sidebar are always in sync — same source of truth.
  const accessibleLinks = visiblePaths
    ? QUICK_LINKS.filter(l => visiblePaths.includes(l.path))
    : QUICK_LINKS;

  const filteredLinks = query
    ? accessibleLinks.filter(l => l.label.toLowerCase().includes(query.toLowerCase()))
    : accessibleLinks;

  const allCategories = searchData?.categories ? Object.entries(searchData.categories) : [];
  const hasResults = (searchData?.total || 0) > 0 || (searchData?.navigation?.length || 0) > 0;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh]" onClick={onClose}>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
      <div className="relative w-full max-w-2xl bg-card rounded-2xl shadow-2xl border overflow-hidden" onClick={e => e.stopPropagation()}>

        {/* Search Input */}
        <div className="flex items-center px-4 border-b">
          <Search className="w-5 h-5 text-muted-foreground flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={workloadFilter
              ? `Search ${workloadFilter.replace('_', ' ')} backups...`
              : 'Search backups, check status, investigate issues...'}
            className="flex-1 px-3 py-4 text-sm outline-none border-none bg-transparent text-foreground"
          />
          {loading && <Loader2 className="w-4 h-4 text-blue-500 animate-spin mr-2" />}
          {workloadFilter && (
            <button onClick={() => setWorkloadFilter(null)} className="mr-2 px-2 py-0.5 text-[10px] bg-teal-500/15 text-teal-400 rounded-full hover:bg-teal-500/25">
              {workloadFilter.replace('_', ' ')} ×
            </button>
          )}
          <kbd className="hidden sm:inline-flex px-2 py-0.5 text-[10px] text-muted-foreground bg-muted rounded font-mono">ESC</kbd>
        </div>

        {/* Results Area */}
        <div ref={listRef} className="max-h-[420px] overflow-auto">

          {/* Intent indicator */}
          {searchData?.intent && query.length >= 2 && (
            <div className="px-4 py-2 text-[10px] text-muted-foreground border-b border-gray-50">
              {INTENT_LABELS[searchData.intent] || searchData.intent}
              {searchData.total > 0 && <span className="ml-2 text-muted-foreground font-medium">{searchData.total} results</span>}
            </div>
          )}

          {/* Navigation results */}
          {searchData?.navigation && searchData.navigation.length > 0 && (
            <div className="p-2">
              <p className="px-2 py-1 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Pages</p>
              {searchData.navigation.map((nav) => (
                <button
                  key={nav.path}
                  onClick={() => goToLink(nav.path)}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left hover:bg-muted/50 text-muted-foreground"
                >
                  <ArrowRight className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm flex-1">{nav.label}</span>
                </button>
              ))}
            </div>
          )}

          {/* Categorized results */}
          {allCategories.map(([category, data]) => (
            <div key={category} className="p-2">
              <div className="flex items-center gap-2 px-2 py-1">
                {(() => { const CatIcon = CATEGORY_ICONS[category] || FileText; return <CatIcon className="w-3 h-3 text-muted-foreground" />; })()}
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">{category}</p>
                <span className="text-[10px] text-muted-foreground">{data.items.length}</span>
              </div>
              {data.items.slice(0, 5).map((item, i) => {
                const ItemIcon = TYPE_ICONS[item.type] || FileText;
                const wl = item.workload ? WORKLOAD_MAP[item.workload] : null;
                return (
                  <div
                    key={`${category}-${item.id}-${i}`}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-muted/50 group"
                  >
                    <div className={`p-1.5 rounded-md ${wl?.bgColor || 'bg-muted'}`}>
                      <ItemIcon className={`w-4 h-4 ${wl?.iconColor || 'text-muted-foreground'}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate text-foreground">{item.name}</p>
                      <p className="text-[11px] text-muted-foreground truncate">
                        {item.subtitle || ''}
                        {item.date && ` · ${new Date(item.date).toLocaleDateString()}`}
                        {item.size_bytes ? ` · ${formatSize(item.size_bytes)}` : ''}
                      </p>
                    </div>
                    {/* Inline actions */}
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {(item.actions || []).slice(0, 2).map(action => {
                        const ActionIcon = ACTION_ICONS[action] || ArrowRight;
                        return (
                          <button
                            key={action}
                            onClick={() => handleAction(item, action)}
                            className="px-2 py-1 text-[10px] font-medium text-blue-600 bg-blue-500/10 rounded hover:bg-blue-100 flex items-center gap-1 capitalize"
                            title={action}
                          >
                            <ActionIcon className="w-3 h-3" />
                            {action}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          ))}

          {/* No results */}
          {query.length >= 2 && !loading && !hasResults && (
            <div className="p-8 text-center">
              <Search className="w-8 h-8 text-gray-200 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No results for "{query}"</p>
              <p className="text-[11px] text-muted-foreground mt-1">Try different keywords or check spelling</p>
            </div>
          )}

          {/* Quick links (when no query) */}
          {query.length < 2 && (
            <div className="p-2">
              {recentSearches.length > 0 && !query && (
                <>
                  <p className="px-2 py-1 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Recent</p>
                  {recentSearches.map(s => (
                    <button key={s} onClick={() => setQuery(s)}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left hover:bg-muted/50 text-muted-foreground">
                      <Clock className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm">{s}</span>
                    </button>
                  ))}
                  <div className="border-t my-1" />
                </>
              )}
              <p className="px-2 py-1 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Quick Navigation</p>
              {filteredLinks.map((link, i) => (
                <button
                  key={link.path}
                  data-idx={i}
                  onClick={() => goToLink(link.path)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${
                    selectedIdx === i ? 'bg-blue-500/10 text-blue-900' : 'hover:bg-muted/50 text-muted-foreground'
                  }`}
                >
                  <ArrowRight className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm flex-1">{link.label}</span>
                  <kbd className="px-1.5 py-0.5 text-[10px] text-muted-foreground bg-muted rounded font-mono">{link.shortcut}</kbd>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t px-4 py-2 flex items-center gap-4 text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1"><kbd className="px-1 bg-muted rounded">↑↓</kbd> navigate</span>
          <span className="flex items-center gap-1"><kbd className="px-1 bg-muted rounded">↵</kbd> select</span>
          <span className="flex items-center gap-1"><kbd className="px-1 bg-muted rounded">esc</kbd> close</span>
          <span className="ml-auto flex items-center gap-1"><Command className="w-3 h-3" />K</span>
        </div>
      </div>
    </div>
  );
}
