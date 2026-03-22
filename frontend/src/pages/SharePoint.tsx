import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Globe, Search, ArrowRight, RefreshCw, Download, Folder, FileText, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import { useTenantId } from '../hooks/useTenant';
import type { ProtectedObject, PaginatedResponse, Snapshot, SnapshotItem } from '../types';

export default function SharePoint() {
  const [search, setSearch] = useState('');
  const [selectedSite, setSelectedSite] = useState<ProtectedObject | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<Snapshot | null>(null);
  const [fileSearch, setFileSearch] = useState('');
  const [backupMsg, setBackupMsg] = useState('');
  const tenantId = useTenantId();
  const qc = useQueryClient();

  const backupAllMutation = useMutation({
    mutationFn: () => api.post(`/sharepoint/backup-all?tenant_id=${tenantId}`),
    onSuccess: (data: any) => {
      setBackupMsg(`Backup All complete! ${data.succeeded}/${data.total} succeeded, ${data.results?.reduce((s: number, r: any) => s + (r.item_count || 0), 0)} total items`);
      qc.invalidateQueries({ queryKey: ['sharepoint-sites'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      setTimeout(() => setBackupMsg(''), 8000);
    },
    onError: (err: any) => { setBackupMsg(`Backup All failed: ${err.message}`); setTimeout(() => setBackupMsg(''), 5000); },
  });

  const backupMutation = useMutation({
    mutationFn: (siteId: number) => api.post(`/sharepoint/sites/${siteId}/backup`),
    onSuccess: (data: any) => {
      setBackupMsg(`Backup complete! Snapshot ID: ${data.snapshot_id}, Items: ${data.item_count}`);
      qc.invalidateQueries({ queryKey: ['sharepoint-snapshots'] });
      qc.invalidateQueries({ queryKey: ['sharepoint-sites'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      setTimeout(() => setBackupMsg(''), 5000);
    },
    onError: (err: any) => { setBackupMsg(`Backup failed: ${err.message}`); setTimeout(() => setBackupMsg(''), 5000); },
  });

  const { data: sites, isLoading } = useQuery({
    queryKey: ['sharepoint-sites', search],
    queryFn: () => api.get<PaginatedResponse<ProtectedObject>>(`/sharepoint/sites?tenant_id=${tenantId}&search=${search}`),
  });

  const { data: snapshots } = useQuery({
    queryKey: ['sharepoint-snapshots', selectedSite?.id],
    queryFn: () => api.get<Snapshot[]>(`/sharepoint/sites/${selectedSite!.id}/snapshots`),
    enabled: !!selectedSite,
  });

  const { data: browseData } = useQuery({
    queryKey: ['sharepoint-browse', selectedSnapshot?.id],
    queryFn: () => api.get<{ items: SnapshotItem[] }>(`/sharepoint/sites/${selectedSite!.id}/snapshots/${selectedSnapshot!.id}/browse`),
    enabled: !!selectedSnapshot,
  });

  const { data: searchResults } = useQuery({
    queryKey: ['sharepoint-search', fileSearch],
    queryFn: () => api.get<{ results: any[] }>(`/sharepoint/search?tenant_id=${tenantId}&query=${fileSearch}`),
    enabled: fileSearch.length > 2,
  });

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MB`;
    return `${(bytes / 1073741824).toFixed(2)} GB`;
  };

  if (selectedSnapshot) {
    return (
      <div>
        <button onClick={() => setSelectedSnapshot(null)} className="text-blue-600 hover:underline text-sm mb-4">&larr; Back</button>
        <h2 className="text-xl font-bold mb-4">Site Content — {selectedSnapshot.started_at?.slice(0, 16)}</h2>
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Name</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Path</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Type</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Size</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Modified</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {browseData?.items?.map((item, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium flex items-center gap-2">
                    {['folder', 'document_library', 'list'].includes(item.item_type) ? <Folder className="w-4 h-4 text-yellow-500" /> : <FileText className="w-4 h-4 text-green-500" />}
                    {item.file_name || item.name}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{item.path}</td>
                  <td className="px-4 py-3"><StatusBadge status={item.item_type} /></td>
                  <td className="px-4 py-3">{formatSize(item.size_bytes)}</td>
                  <td className="px-4 py-3 text-gray-500">{item.last_modified?.slice(0, 16) || '—'}</td>
                </tr>
              ))}
              {!browseData?.items?.length && <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No items</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (selectedSite) {
    return (
      <div>
        <button onClick={() => setSelectedSite(null)} className="text-blue-600 hover:underline text-sm mb-4">&larr; Back</button>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold">{selectedSite.display_name}</h2>
            <p className="text-gray-500 text-sm">{selectedSite.site_url}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => backupMutation.mutate(selectedSite.id)}
              disabled={backupMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50"
            >
              {backupMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              {backupMutation.isPending ? 'Backing up...' : 'Backup'}
            </button>
            <button className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 flex items-center gap-2"><Download className="w-4 h-4" /> Restore</button>
          </div>
        </div>
        {backupMsg && (
          <div className={`rounded-lg p-3 mb-4 text-sm ${backupMsg.includes('failed') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-green-50 border border-green-200 text-green-700'}`}>
            {backupMsg}
          </div>
        )}
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <div className="p-4 border-b bg-gray-50"><h3 className="font-semibold">Snapshots</h3></div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Date</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Type</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Items</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Size</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {snapshots?.map(s => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{s.started_at?.slice(0, 16)}</td>
                  <td className="px-4 py-3 capitalize">{s.snapshot_type}</td>
                  <td className="px-4 py-3"><StatusBadge status={s.status} /></td>
                  <td className="px-4 py-3">{s.item_count}</td>
                  <td className="px-4 py-3">{formatSize(s.size_bytes)}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => setSelectedSnapshot(s)} className="text-blue-600 hover:underline text-sm flex items-center gap-1">Browse <ArrowRight className="w-3 h-3" /></button>
                  </td>
                </tr>
              ))}
              {!snapshots?.length && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No snapshots</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">SharePoint</h1>
          <p className="text-gray-500">Manage and protect SharePoint sites</p>
        </div>
        <button
          onClick={() => backupAllMutation.mutate()}
          disabled={backupAllMutation.isPending}
          className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 flex items-center gap-2 disabled:opacity-50"
        >
          {backupAllMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {backupAllMutation.isPending ? 'Backing up all...' : 'Backup All Sites'}
        </button>
      </div>

      {backupMsg && !selectedSite && (
        <div className={`rounded-lg p-3 mb-4 text-sm ${backupMsg.includes('failed') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-green-50 border border-green-200 text-green-700'}`}>
          {backupMsg}
        </div>
      )}
      <div className="flex gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
          <input type="text" placeholder="Search sites..." value={search} onChange={e => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
        </div>
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
          <input type="text" placeholder="Search files across sites..." value={fileSearch} onChange={e => setFileSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>

      {searchResults?.results?.length ? (
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden mb-6">
          <div className="p-4 border-b bg-green-50"><h3 className="font-semibold text-green-800">Search Results ({searchResults.results.length})</h3></div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">File</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Site</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Path</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Size</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {searchResults.results.slice(0, 10).map((r: any, i: number) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{r.file_name}</td>
                  <td className="px-4 py-3 text-gray-500">{r.object_name}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{r.path}</td>
                  <td className="px-4 py-3">{formatSize(r.size_bytes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Site</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">URL</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Last Backup</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Items</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Size</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {sites?.items?.map(s => (
              <tr key={s.id} onClick={() => setSelectedSite(s)} className="hover:bg-gray-50 cursor-pointer">
                <td className="px-4 py-3 font-medium flex items-center gap-2"><Globe className="w-4 h-4 text-green-500" />{s.display_name}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">{s.site_url}</td>
                <td className="px-4 py-3"><StatusBadge status={s.status} /></td>
                <td className="px-4 py-3 text-gray-500">{s.last_backup_at?.slice(0, 16) || 'Never'}</td>
                <td className="px-4 py-3">{s.total_items}</td>
                <td className="px-4 py-3">{formatSize(s.total_size_bytes)}</td>
              </tr>
            ))}
            {isLoading && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>}
            {!isLoading && !sites?.items?.length && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No sites found.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
