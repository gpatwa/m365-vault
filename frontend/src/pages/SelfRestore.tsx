import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Search, RotateCcw, Mail, HardDrive, Globe, FileText, Calendar, User, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { api } from '../api/client';
import { formatSize, timeAgo } from '../utils/format';

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
  { key: 'exchange', label: 'Exchange', icon: Mail },
  { key: 'onedrive', label: 'OneDrive', icon: HardDrive },
  { key: 'sharepoint', label: 'SharePoint', icon: Globe },
];

const ITEM_ICONS: Record<string, typeof Mail> = {
  email: Mail, calendar_event: Calendar, contact: User,
  file: FileText, folder: FileText, list_item: FileText,
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Restore Items</h1>
        <p className="text-gray-500 mt-1">Search and restore your deleted or modified items from backup</p>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search for emails, files, documents..."
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
          />
        </div>
        <button type="submit" className="px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700">
          Search
        </button>
      </form>

      {/* Workload Tabs */}
      <div className="flex gap-2">
        {WORKLOAD_TABS.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => { setWorkload(tab.key); if (searchQuery) setSearchQuery(searchQuery); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                workload === tab.key
                  ? 'bg-blue-100 text-blue-700 ring-1 ring-blue-300'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <Icon className="w-4 h-4" /> {tab.label}
            </button>
          );
        })}
      </div>

      {/* Alert Messages */}
      {restoreMsg && (
        <div className={`flex items-center gap-2 px-4 py-3 rounded-lg text-sm ${
          restoreMsg.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {restoreMsg.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
          {restoreMsg.text}
        </div>
      )}

      {/* Results */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
          <span className="ml-2 text-gray-500">Searching...</span>
        </div>
      ) : searchQuery && data ? (
        <div className="bg-white rounded-xl border shadow-sm">
          <div className="px-5 py-3 border-b flex items-center justify-between">
            <span className="text-sm text-gray-500">
              {data.total} result{data.total !== 1 ? 's' : ''} for "{searchQuery}"
            </span>
          </div>
          {data.items.length === 0 ? (
            <div className="py-12 text-center text-gray-400">
              No items found. Try a different search term.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-5 py-2 font-medium text-gray-600">Item</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Workload</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Size</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Backed Up</th>
                  <th className="text-right px-5 py-2 font-medium text-gray-600">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.items.map(item => {
                  const Icon = ITEM_ICONS[item.item_type] || FileText;
                  return (
                    <tr key={`${item.snapshot_id}-${item.id}`} className="hover:bg-gray-50">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <Icon className="w-4 h-4 text-gray-400 flex-shrink-0" />
                          <div>
                            <p className="font-medium text-gray-900 truncate max-w-md">{item.subject || item.name}</p>
                            <p className="text-xs text-gray-400 truncate max-w-md">
                              {item.sender ? `From: ${item.sender}` : item.path}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3 capitalize text-gray-500">{item.workload}</td>
                      <td className="px-3 py-3 text-gray-500">{formatSize(item.size_bytes)}</td>
                      <td className="px-3 py-3 text-gray-500">{item.backed_up_at ? timeAgo(item.backed_up_at) : '-'}</td>
                      <td className="px-5 py-3 text-right">
                        <button
                          onClick={() => restoreMutation.mutate({ snapshotId: item.snapshot_id, itemIds: String(item.id) })}
                          disabled={restoreMutation.isPending}
                          className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-xs font-medium hover:bg-blue-100 disabled:opacity-50"
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
        <div className="text-center py-16 bg-gray-50 rounded-xl border border-dashed border-gray-300">
          <Search className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Search for items to restore from backup</p>
          <p className="text-xs text-gray-400 mt-1">Try searching for email subjects, file names, or document titles</p>
        </div>
      ) : null}
    </div>
  );
}
