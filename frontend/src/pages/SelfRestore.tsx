import { useState } from 'react';
import { getActivePlatformLabel } from '../config/platforms';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Search, RotateCcw, Mail, HardDrive, Globe, FileText, Calendar, User,
  Loader2, CheckCircle, XCircle, MessageSquare, KeyRound, DownloadCloud,
} from 'lucide-react';
import { api } from '../api/client';
import { formatSize, timeAgo } from '../utils/format';
import Breadcrumb from '../components/design-system/Breadcrumb';

interface SearchResult {
  id: number;
  snapshot_id: number;
  item_type: string;
  name: string;
  path: string;
  size_bytes: number;
  workload: string;
  protected_object: string;
  backed_up_at: string | null;
  subject: string | null;
  sender: string | null;
  received_at: string | null;
  file_name: string | null;
  mime_type: string | null;
}

const WORKLOAD_TABS = [
  { key: '', label: 'All', icon: Search },
  { key: 'entra_id', label: 'Entra ID', icon: KeyRound },
  { key: 'exchange', label: 'Exchange', icon: Mail },
  { key: 'sharepoint', label: 'SharePoint', icon: Globe },
  { key: 'onedrive', label: 'OneDrive', icon: HardDrive },
  { key: 'teams', label: 'Teams', icon: MessageSquare },
];

const ITEM_ICONS: Record<string, typeof Mail> = {
  email: Mail, calendar_event: Calendar, contact: User,
  file: FileText, folder: FileText, list_item: FileText,
  channel_message: MessageSquare, chat_message: MessageSquare,
  team_channel: MessageSquare, chat: MessageSquare,
  user: User, group: User, directory_role: KeyRound,
  conditional_access_policy: KeyRound, app_registration: KeyRound,
  named_location: Globe, role_assignment: KeyRound,
};

const WORKLOAD_COLORS: Record<string, string> = {
  exchange: 'text-blue-600',
  onedrive: 'text-cyan-600',
  sharepoint: 'text-teal-600',
  teams: 'text-purple-600',
  entra_id: 'text-amber-600',
};

export default function SelfRestore() {
  const [query, setQuery] = useState('');
  const [workload, setWorkload] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [restoreMsg, setRestoreMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['self-restore-search', searchQuery, workload],
    queryFn: () => api.get<{ total: number; items: SearchResult[] }>(
      `/self-restore/search?query=${searchQuery}${workload ? `&workload=${workload}` : ''}`
    ),
    enabled: searchQuery.length >= 2,
  });

  const restoreMutation = useMutation({
    mutationFn: (params: { snapshotId: number; itemIds: string }) =>
      api.post(`/self-restore/restore?snapshot_id=${params.snapshotId}&item_ids=${params.itemIds}`),
    onSuccess: (data: any) => {
      setRestoreMsg({ type: 'success', text: `Restored ${data.items_restored || 1} item(s) successfully` });
      setTimeout(() => setRestoreMsg(null), 5000);
    },
    onError: (err: any) => {
      setRestoreMsg({ type: 'error', text: err.message || 'Restore failed' });
      setTimeout(() => setRestoreMsg(null), 5000);
    },
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(query);
  };

  return (
    <div>
      {/* Breadcrumb + Search */}
      <Breadcrumb
        items={[
          { label: getActivePlatformLabel(), path: '/' },
          { label: 'Restore' },
        ]}
      />

      {/* Page Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-blue-500/10">
            <DownloadCloud className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Restore Items</h1>
            <p className="text-xs text-muted-foreground">Search and restore deleted or modified items from backup</p>
          </div>
        </div>
      </div>

      {/* Search Card */}
      <div className="bg-card rounded-xl border shadow-sm p-5 mb-6">
        <form onSubmit={handleSearch} className="flex gap-3 mb-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search for emails, files, documents..."
              className="w-full pl-10 pr-4 py-2.5 border border-border rounded-xl bg-background text-foreground focus:ring-2 focus:ring-ring focus:border-ring text-sm"
            />
          </div>
          <button
            type="submit"
            className="px-5 py-2.5 bg-teal-600 text-white rounded-xl text-sm font-medium hover:bg-teal-700 transition-colors"
          >
            Search
          </button>
        </form>

        {/* Workload Filter Tabs */}
        <div className="flex flex-wrap gap-2">
          {WORKLOAD_TABS.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.key}
                onClick={() => { setWorkload(tab.key); if (searchQuery) setSearchQuery(searchQuery); }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  workload === tab.key
                    ? 'bg-teal-500/15 text-teal-400 ring-1 ring-teal-500/30'
                    : 'bg-muted text-muted-foreground hover:bg-accent'
                }`}
              >
                <Icon className="w-3.5 h-3.5" /> {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Alert Messages */}
      {restoreMsg && (
        <div className={`flex items-center gap-2 px-4 py-3 rounded-lg text-sm mb-4 ${
          restoreMsg.type === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
        }`}>
          {restoreMsg.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
          {restoreMsg.text}
        </div>
      )}

      {/* Results */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12 bg-card rounded-xl border shadow-sm">
          <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
          <span className="ml-2 text-sm text-muted-foreground">Searching...</span>
        </div>
      ) : searchQuery && data ? (
        <div className="bg-card rounded-xl border shadow-sm">
          <div className="px-5 py-3 border-b flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-foreground">
                {data.total} result{data.total !== 1 ? 's' : ''} for "{searchQuery}"
              </h2>
              {workload && (
                <p className="text-xs text-muted-foreground">Filtered to {WORKLOAD_TABS.find(t => t.key === workload)?.label}</p>
              )}
            </div>
          </div>
          {data.items.length === 0 ? (
            <div className="py-12 text-center">
              <Search className="w-10 h-10 text-gray-200 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No items found. Try a different search term.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="text-left px-5 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Item</th>
                  <th className="text-left px-3 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Workload</th>
                  <th className="text-left px-3 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Size</th>
                  <th className="text-left px-3 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Backed Up</th>
                  <th className="text-right px-5 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.items.map(item => {
                  const Icon = ITEM_ICONS[item.item_type] || FileText;
                  const wlColor = WORKLOAD_COLORS[item.workload] || 'text-muted-foreground';
                  return (
                    <tr key={`${item.snapshot_id}-${item.id}`} className="hover:bg-muted/50 transition-colors">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <Icon className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                          <div>
                            <p className="font-medium text-foreground truncate max-w-md">{item.subject || item.name}</p>
                            <p className="text-xs text-muted-foreground truncate max-w-md">
                              {item.sender ? `From: ${item.sender}` : item.path}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <span className={`text-xs font-medium capitalize ${wlColor}`}>{item.workload.replace('_', ' ')}</span>
                      </td>
                      <td className="px-3 py-3 text-xs text-muted-foreground">{formatSize(item.size_bytes)}</td>
                      <td className="px-3 py-3 text-xs text-muted-foreground">{item.backed_up_at ? timeAgo(item.backed_up_at) : '—'}</td>
                      <td className="px-5 py-3 text-right">
                        <button
                          onClick={() => restoreMutation.mutate({ snapshotId: item.snapshot_id, itemIds: String(item.id) })}
                          disabled={restoreMutation.isPending}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-lg text-xs font-medium hover:bg-blue-100 disabled:opacity-50 transition-colors"
                        >
                          <RotateCcw className="w-3 h-3" /> Restore
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      ) : !searchQuery ? (
        <div className="text-center py-16 bg-card rounded-xl border shadow-sm">
          <div className="p-4 bg-blue-500/10 rounded-2xl w-fit mx-auto mb-4">
            <Search className="w-10 h-10 text-blue-300" />
          </div>
          <p className="text-sm font-medium text-muted-foreground">Search your backup archive</p>
          <p className="text-xs text-muted-foreground mt-1">Try searching for email subjects, file names, or document titles</p>
        </div>
      ) : null}
    </div>
  );
}
