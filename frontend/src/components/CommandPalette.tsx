import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Mail, FileText, MessageSquare, Shield, Calendar, User, Command, ArrowRight, Clock, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import { useTenantId } from '../hooks/useTenant';
import { WORKLOAD_MAP } from '../config/workloads';
import { formatSize } from '../utils/format';

interface SearchResult {
  item_id: number; snapshot_id: number; workload: string; object_name: string;
  item_type: string; name: string; path: string; size_bytes: number;
  subject?: string; sender?: string; file_name?: string; snapshot_date?: string;
}

const ITEM_ICONS: Record<string, typeof Mail> = {
  email: Mail, calendar_event: Calendar, contact: User, file: FileText, folder: FileText,
  list: FileText, list_item: FileText, user: User, group: User, directory_role: Shield,
  conditional_access_policy: Shield, app_registration: Shield, named_location: Shield,
  chat_message: MessageSquare, channel_message: MessageSquare, team_channel: MessageSquare,
};

const QUICK_LINKS = [
  { label: 'Dashboard', path: '/', shortcut: 'D' },
  { label: 'Jobs', path: '/jobs', shortcut: 'J' },
  { label: 'SLA Policies', path: '/sla-policies', shortcut: 'P' },
  { label: 'Smart Engine', path: '/smart-engine', shortcut: 'S' },
  { label: 'Tenants', path: '/tenants', shortcut: 'T' },
  { label: 'Failed Items', path: '/failed-items', shortcut: 'F' },
  { label: 'Alerts', path: '/alerts', shortcut: 'A' },
  { label: 'Audit Log', path: '/audit', shortcut: 'L' },
];

export default function CommandPalette({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [recentSearches, setRecentSearches] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem('m365v_recent_searches') || '[]'); } catch { return []; }
  });
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const tenantId = useTenantId();
  const navigate = useNavigate();
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setResults([]);
      setSelectedIdx(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query || query.length < 2) { setResults([]); return; }

    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await api.get<{ items: SearchResult[] }>(
          `/search?q=${encodeURIComponent(query)}&tenant_id=${tenantId}&limit=20`
        );
        setResults(data.items || []);
        setSelectedIdx(0);
      } catch { setResults([]); }
      setLoading(false);
    }, 300);

    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, tenantId]);

  // Save recent search
  const saveRecent = useCallback((q: string) => {
    const updated = [q, ...recentSearches.filter(s => s !== q)].slice(0, 5);
    setRecentSearches(updated);
    localStorage.setItem('m365v_recent_searches', JSON.stringify(updated));
  }, [recentSearches]);

  // Navigate to full search page
  const goToFullSearch = () => {
    if (query) saveRecent(query);
    navigate(`/search?q=${encodeURIComponent(query)}`);
    onClose();
  };

  // Navigate to quick link
  const goToLink = (path: string) => {
    navigate(path);
    onClose();
  };

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    const totalItems = query.length >= 2 ? results.length + 1 : filteredLinks.length; // +1 for "View all"
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIdx(prev => Math.min(prev + 1, totalItems - 1)); }
    if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIdx(prev => Math.max(prev - 1, 0)); }
    if (e.key === 'Enter') {
      e.preventDefault();
      if (query.length >= 2) {
        if (selectedIdx < results.length) {
          // Navigate to workload page
          const r = results[selectedIdx];
          const wlPath = r.workload === 'entra_id' ? 'entra-id' : r.workload;
          navigate(`/${wlPath}`);
          saveRecent(query);
          onClose();
        } else {
          goToFullSearch();
        }
      } else if (filteredLinks.length > 0) {
        goToLink(filteredLinks[selectedIdx]?.path || '/');
      }
    }
    if (e.key === 'Escape') onClose();
  };

  // Scroll selected into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${selectedIdx}"]`);
    el?.scrollIntoView({ block: 'nearest' });
  }, [selectedIdx]);

  // Filter quick links by query
  const filteredLinks = query
    ? QUICK_LINKS.filter(l => l.label.toLowerCase().includes(query.toLowerCase()))
    : QUICK_LINKS;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]" onClick={onClose}>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl border overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Search Input */}
        <div className="flex items-center px-4 border-b">
          <Search className="w-5 h-5 text-gray-400 flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search across all workloads or jump to a page..."
            className="flex-1 px-3 py-4 text-sm outline-none border-none"
          />
          {loading && <Loader2 className="w-4 h-4 text-blue-500 animate-spin mr-2" />}
          <kbd className="hidden sm:inline-flex items-center px-2 py-0.5 text-[10px] text-gray-400 bg-gray-100 rounded font-mono">ESC</kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-[400px] overflow-auto">
          {/* Search results */}
          {query.length >= 2 && results.length > 0 && (
            <div className="p-2">
              <p className="px-2 py-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Results</p>
              {results.map((r, i) => {
                const Icon = ITEM_ICONS[r.item_type] || FileText;
                const wl = WORKLOAD_MAP[r.workload];
                return (
                  <button
                    key={`${r.snapshot_id}-${r.item_id}`}
                    data-idx={i}
                    onClick={() => {
                      const wlPath = r.workload === 'entra_id' ? 'entra-id' : r.workload;
                      navigate(`/${wlPath}`);
                      saveRecent(query);
                      onClose();
                    }}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                      selectedIdx === i ? 'bg-blue-50 text-blue-900' : 'hover:bg-gray-50 text-gray-700'
                    }`}
                  >
                    <div className={`p-1.5 rounded-md ${wl?.bgColor || 'bg-gray-100'}`}>
                      <Icon className={`w-4 h-4 ${wl?.iconColor || 'text-gray-500'}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{r.subject || r.file_name || r.name}</p>
                      <p className="text-[11px] text-gray-400 truncate">
                        {wl?.label || r.workload} · {r.object_name} · {r.path || r.item_type.replace('_', ' ')}
                      </p>
                    </div>
                    <span className="text-[10px] text-gray-400 flex-shrink-0">{formatSize(r.size_bytes)}</span>
                  </button>
                );
              })}
              {/* View all link */}
              <button
                data-idx={results.length}
                onClick={goToFullSearch}
                className={`w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm ${
                  selectedIdx === results.length ? 'bg-blue-50 text-blue-700' : 'text-blue-600 hover:bg-blue-50'
                }`}
              >
                <ArrowRight className="w-4 h-4" /> View all results for "{query}"
              </button>
            </div>
          )}

          {/* No results */}
          {query.length >= 2 && !loading && results.length === 0 && (
            <div className="p-6 text-center text-gray-400 text-sm">No results found for "{query}"</div>
          )}

          {/* Quick links (when no search query) */}
          {query.length < 2 && (
            <div className="p-2">
              {/* Recent searches */}
              {recentSearches.length > 0 && !query && (
                <>
                  <p className="px-2 py-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Recent</p>
                  {recentSearches.map((s) => (
                    <button
                      key={s}
                      onClick={() => { setQuery(s); }}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left hover:bg-gray-50 text-gray-600"
                    >
                      <Clock className="w-4 h-4 text-gray-300" />
                      <span className="text-sm">{s}</span>
                    </button>
                  ))}
                  <div className="border-t my-1" />
                </>
              )}
              <p className="px-2 py-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Quick Navigation</p>
              {filteredLinks.map((link, i) => (
                <button
                  key={link.path}
                  data-idx={i}
                  onClick={() => goToLink(link.path)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${
                    selectedIdx === i ? 'bg-blue-50 text-blue-900' : 'hover:bg-gray-50 text-gray-700'
                  }`}
                >
                  <ArrowRight className="w-4 h-4 text-gray-300" />
                  <span className="text-sm flex-1">{link.label}</span>
                  <kbd className="px-1.5 py-0.5 text-[10px] text-gray-400 bg-gray-100 rounded font-mono">{link.shortcut}</kbd>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t px-4 py-2 flex items-center gap-4 text-[10px] text-gray-400">
          <span className="flex items-center gap-1"><kbd className="px-1 bg-gray-100 rounded">↑↓</kbd> navigate</span>
          <span className="flex items-center gap-1"><kbd className="px-1 bg-gray-100 rounded">↵</kbd> select</span>
          <span className="flex items-center gap-1"><kbd className="px-1 bg-gray-100 rounded">esc</kbd> close</span>
          <span className="ml-auto flex items-center gap-1"><Command className="w-3 h-3" />K to open</span>
        </div>
      </div>
    </div>
  );
}
