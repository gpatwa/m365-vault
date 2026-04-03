import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search as SearchIcon, Mail, MessageSquare, Shield, FileText, Calendar, User, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import { useTenantId } from '../hooks/useTenant';
import { WORKLOADS, WORKLOAD_MAP } from '../config/workloads';
import { formatSize, timeAgo } from '../utils/format';

interface SearchResult {
  item_id: number;
  snapshot_id: number;
  workload: string;
  object_name: string;
  item_type: string;
  name: string;
  path: string;
  size_bytes: number;
  blob_path: string;
  snapshot_date: string;
  subject?: string;
  sender?: string;
  file_name?: string;
  mime_type?: string;
  received_at?: string;
  last_modified_at?: string;
  metadata?: Record<string, any>;
}

const ITEM_TYPE_ICONS: Record<string, typeof Mail> = {
  email: Mail, calendar_event: Calendar, contact: User,
  file: FileText, folder: FileText, list: FileText, list_item: FileText,
  user: User, group: User, directory_role: Shield,
  conditional_access_policy: Shield, app_registration: Shield,
  chat_message: MessageSquare, channel_message: MessageSquare,
};

export default function Search() {
  const tenantId = useTenantId();
  const [query, setQuery] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [workloadFilter, setWorkloadFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['global-search', searchQuery, workloadFilter, tenantId],
    queryFn: () => api.get<{ query: string; total: number; items: SearchResult[] }>(
      `/search?q=${encodeURIComponent(searchQuery)}&tenant_id=${tenantId}${workloadFilter ? `&workload=${workloadFilter}` : ''}&limit=100`
    ),
    enabled: !!searchQuery && searchQuery.length >= 1,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(query);
  };

  // Group results by workload
  const groupedResults: Record<string, SearchResult[]> = {};
  data?.items.forEach(item => {
    if (!groupedResults[item.workload]) groupedResults[item.workload] = [];
    groupedResults[item.workload].push(item);
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <SearchIcon className="w-7 h-7 text-blue-600" /> Global Search
        </h1>
        <p className="text-muted-foreground">Search across all workloads — emails, files, Teams messages, Entra ID objects</p>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search emails, files, documents, users, policies..."
              className="w-full pl-10 pr-4 py-3 border border-border rounded-xl bg-background text-foreground focus:ring-2 focus:ring-ring focus:border-ring text-sm"
              autoFocus
            />
          </div>
          <select
            value={workloadFilter}
            onChange={e => { setWorkloadFilter(e.target.value); if (searchQuery) setSearchQuery(query); }}
            className="px-4 py-3 border border-border rounded-xl text-sm bg-card"
          >
            <option value="">All Workloads</option>
            {WORKLOADS.map(w => (
              <option key={w.key} value={w.key}>{w.label}</option>
            ))}
          </select>
          <button
            type="submit"
            disabled={!query || isLoading}
            className="px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <SearchIcon className="w-4 h-4" />}
            Search
          </button>
        </div>
      </form>

      {/* Results */}
      {searchQuery && !isLoading && data && (
        <div className="mb-4 text-sm text-muted-foreground">
          Found <strong className="text-foreground">{data.total}</strong> results for "<strong className="text-foreground">{data.query}</strong>"
          {workloadFilter && <> in <strong className="text-foreground">{WORKLOAD_MAP[workloadFilter]?.label || workloadFilter}</strong></>}
        </div>
      )}

      {searchQuery && !isLoading && data?.total === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <SearchIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-lg">No results found</p>
          <p className="text-sm mt-1">Try different keywords or remove the workload filter</p>
        </div>
      )}

      {/* Grouped Results */}
      {Object.entries(groupedResults).map(([workload, items]) => {
        const wlConfig = WORKLOAD_MAP[workload];
        const WlIcon = wlConfig?.icon || Shield;
        return (
          <div key={workload} className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <WlIcon className={`w-5 h-5 ${wlConfig?.iconColor || 'text-muted-foreground'}`} />
              <h3 className="font-semibold text-foreground">{wlConfig?.label || workload}</h3>
              <span className="px-2 py-0.5 bg-muted text-muted-foreground rounded-full text-xs font-medium">{items.length}</span>
            </div>
            <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 border-b">
                  <tr>
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">Type</th>
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">Name</th>
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">Location</th>
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">Source</th>
                    <th className="text-right px-4 py-2 font-medium text-muted-foreground">Size</th>
                    <th className="text-right px-4 py-2 font-medium text-muted-foreground">Backed Up</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {items.map(item => {
                    const TypeIcon = ITEM_TYPE_ICONS[item.item_type] || FileText;
                    return (
                      <tr key={`${item.snapshot_id}-${item.item_id}`} className="hover:bg-muted/50">
                        <td className="px-4 py-2.5">
                          <div className="flex items-center gap-1.5">
                            <TypeIcon className="w-4 h-4 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground capitalize">{item.item_type.replace('_', ' ')}</span>
                          </div>
                        </td>
                        <td className="px-4 py-2.5">
                          <p className="font-medium text-foreground truncate max-w-xs" title={item.name}>
                            {item.subject || item.file_name || item.name}
                          </p>
                          {item.sender && <p className="text-xs text-muted-foreground">from: {item.sender}</p>}
                        </td>
                        <td className="px-4 py-2.5 text-muted-foreground text-xs truncate max-w-[200px]" title={item.path}>
                          {item.path || '-'}
                        </td>
                        <td className="px-4 py-2.5 text-muted-foreground text-xs truncate max-w-[200px]" title={item.object_name}>
                          {item.object_name}
                        </td>
                        <td className="px-4 py-2.5 text-right text-muted-foreground font-mono text-xs">
                          {formatSize(item.size_bytes)}
                        </td>
                        <td className="px-4 py-2.5 text-right text-muted-foreground text-xs">
                          {item.snapshot_date ? timeAgo(item.snapshot_date) : '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
}
