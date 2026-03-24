import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Mail, RefreshCw, Download, ArrowRight, Loader2, Search } from 'lucide-react';
import { api } from '../api/client';
import DataTable, { type Column } from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import { useTenantId } from '../hooks/useTenant';
import { formatSize, timeAgo } from '../utils/format';
import type { ProtectedObject, Snapshot, SnapshotItem } from '../types';

export default function Exchange() {
  const [selectedMailbox, setSelectedMailbox] = useState<ProtectedObject | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<Snapshot | null>(null);
  const [emailSearch, setEmailSearch] = useState('');
  const [backupMsg, setBackupMsg] = useState('');
  const tenantId = useTenantId();
  const qc = useQueryClient();

  const backupAllMutation = useMutation({
    mutationFn: () => api.post(`/exchange/backup-all?tenant_id=${tenantId}`),
    onSuccess: (data: any) => {
      setBackupMsg(`Backup All complete! ${data.succeeded}/${data.total} succeeded, ${data.results?.reduce((s: number, r: any) => s + (r.item_count || 0), 0)} total items`);
      qc.invalidateQueries({ queryKey: ['exchange-mailboxes'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      setTimeout(() => setBackupMsg(''), 8000);
    },
    onError: (err: any) => {
      setBackupMsg(`Backup All failed: ${err.message}`);
      setTimeout(() => setBackupMsg(''), 5000);
    },
  });

  const backupMutation = useMutation({
    mutationFn: (mailboxId: number) => api.post(`/exchange/mailboxes/${mailboxId}/backup`),
    onSuccess: (data: any) => {
      setBackupMsg(`Backup started! Snapshot ID: ${data.snapshot_id}, Items: ${data.item_count}`);
      qc.invalidateQueries({ queryKey: ['exchange-snapshots'] });
      qc.invalidateQueries({ queryKey: ['exchange-mailboxes'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      setTimeout(() => setBackupMsg(''), 5000);
    },
    onError: (err: any) => {
      setBackupMsg(`Backup failed: ${err.message}`);
      setTimeout(() => setBackupMsg(''), 5000);
    },
  });

  const { data: snapshots } = useQuery({
    queryKey: ['exchange-snapshots', selectedMailbox?.id],
    queryFn: () => api.get<Snapshot[]>(`/exchange/mailboxes/${selectedMailbox!.id}/snapshots`),
    enabled: !!selectedMailbox,
  });

  const { data: browseData } = useQuery({
    queryKey: ['exchange-browse', selectedSnapshot?.id],
    queryFn: () => api.get<{ items: SnapshotItem[] }>(
      `/exchange/mailboxes/${selectedMailbox!.id}/snapshots/${selectedSnapshot!.id}/browse`
    ),
    enabled: !!selectedSnapshot,
  });

  const { data: searchResults } = useQuery({
    queryKey: ['exchange-search', emailSearch],
    queryFn: () => api.get<{ results: any[] }>(`/exchange/search?tenant_id=${tenantId}&query=${emailSearch}`),
    enabled: emailSearch.length > 2,
  });

  // ── Snapshot browse view ──
  if (selectedSnapshot) {
    return (
      <div>
        <button onClick={() => setSelectedSnapshot(null)} className="text-blue-600 hover:underline text-sm mb-4 flex items-center gap-1">
          &larr; Back to snapshots
        </button>
        <h2 className="text-xl font-bold mb-4">
          Browse Snapshot — {selectedSnapshot.started_at?.slice(0, 16)}
        </h2>
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Type</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Subject / Name</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Sender</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Date</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Size</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {browseData?.items?.map((item, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3"><StatusBadge status={item.item_type} /></td>
                  <td className="px-4 py-3 font-medium">{item.subject || item.name}</td>
                  <td className="px-4 py-3 text-gray-500">{item.sender || '—'}</td>
                  <td className="px-4 py-3 text-gray-500">{item.received_at?.slice(0, 16) || item.last_modified?.slice(0, 16) || '—'}</td>
                  <td className="px-4 py-3 text-gray-500">{formatSize(item.size_bytes)}</td>
                </tr>
              ))}
              {(!browseData?.items?.length) && (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No items in this snapshot</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // ── Mailbox detail / snapshots view ──
  if (selectedMailbox) {
    return (
      <div>
        <button onClick={() => setSelectedMailbox(null)} className="text-blue-600 hover:underline text-sm mb-4 flex items-center gap-1">
          &larr; Back to mailboxes
        </button>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold">{selectedMailbox.display_name}</h2>
            <p className="text-gray-500">{selectedMailbox.email}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => backupMutation.mutate(selectedMailbox.id)}
              disabled={backupMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50"
            >
              {backupMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              {backupMutation.isPending ? 'Backing up...' : 'Backup Now'}
            </button>
            <button className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 flex items-center gap-2">
              <Download className="w-4 h-4" /> Restore
            </button>
          </div>
        </div>
        {backupMsg && (
          <div className={`rounded-lg p-3 mb-4 text-sm ${backupMsg.includes('failed') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-green-50 border border-green-200 text-green-700'}`}>
            {backupMsg}
          </div>
        )}
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <div className="p-4 border-b bg-gray-50">
            <h3 className="font-semibold">Snapshots ({snapshots?.length || 0})</h3>
          </div>
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
                    <button
                      onClick={() => setSelectedSnapshot(s)}
                      className="text-blue-600 hover:underline text-sm flex items-center gap-1"
                    >
                      Browse <ArrowRight className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              ))}
              {(!snapshots?.length) && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No snapshots yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // ── Main mailbox list (DataTable) ──
  const columns: Column<ProtectedObject>[] = [
    {
      key: 'display_name',
      label: 'Mailbox',
      sortable: true,
      render: (row) => (
        <span className="font-medium flex items-center gap-2">
          <Mail className="w-4 h-4 text-blue-500" />
          {row.display_name}
        </span>
      ),
    },
    { key: 'email', label: 'Email', sortable: true },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: 'last_backup_at',
      label: 'Last Backup',
      sortable: true,
      render: (row) => (
        <span className="text-gray-500">{row.last_backup_at ? timeAgo(row.last_backup_at) : 'Never'}</span>
      ),
    },
    { key: 'total_items', label: 'Items', sortable: true },
    {
      key: 'total_size_bytes',
      label: 'Size',
      sortable: true,
      render: (row) => <span>{formatSize(row.total_size_bytes)}</span>,
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Exchange</h1>
          <p className="text-gray-500">Manage and protect Exchange mailboxes</p>
        </div>
        <button
          onClick={() => backupAllMutation.mutate()}
          disabled={backupAllMutation.isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50"
        >
          {backupAllMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {backupAllMutation.isPending ? 'Backing up all...' : 'Backup All Mailboxes'}
        </button>
      </div>

      {backupMsg && (
        <div className={`rounded-lg p-3 mb-4 text-sm ${backupMsg.includes('failed') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-green-50 border border-green-200 text-green-700'}`}>
          {backupMsg}
        </div>
      )}

      {/* Cross-snapshot email search */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search emails across all snapshots..."
            value={emailSearch}
            onChange={e => setEmailSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      </div>

      {/* Email search results */}
      {searchResults?.results?.length ? (
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden mb-6">
          <div className="p-4 border-b bg-blue-50">
            <h3 className="font-semibold text-blue-800">Email Search Results ({searchResults.results.length})</h3>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Subject</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Sender</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Mailbox</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Date</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Snapshot</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {searchResults.results.slice(0, 10).map((r: any, i: number) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{r.subject}</td>
                  <td className="px-4 py-3 text-gray-500">{r.sender}</td>
                  <td className="px-4 py-3 text-gray-500">{r.object_name}</td>
                  <td className="px-4 py-3 text-gray-500">{r.received_at?.slice(0, 16)}</td>
                  <td className="px-4 py-3 text-gray-500">{r.snapshot_date?.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {/* Mailbox list — DataTable */}
      <DataTable<ProtectedObject>
        queryKey="exchange-mailboxes"
        endpoint="/exchange/mailboxes"
        columns={columns}
        extraParams={{ tenant_id: tenantId || '' }}
        searchable
        searchPlaceholder="Search mailboxes..."
        filters={[
          {
            key: 'status',
            label: 'All Statuses',
            options: [
              { value: 'protected', label: 'Protected' },
              { value: 'unprotected', label: 'Unprotected' },
              { value: 'error', label: 'Error' },
              { value: 'pending', label: 'Pending' },
            ],
          },
        ]}
        exportable
        exportEndpoint="/export/csv?source=exchange_mailboxes"
        defaultSortBy="display_name"
        defaultSortOrder="asc"
        emptyMessage="No mailboxes found. Configure a tenant and run discovery first."
        onRowClick={(row) => setSelectedMailbox(row)}
        rowKey="id"
      />
    </div>
  );
}
