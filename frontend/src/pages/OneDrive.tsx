import { useState, useMemo } from 'react';
import { getActivePlatformLabel } from '../config/platforms';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { HardDrive, Folder, FileText, ArrowRight, RefreshCw, Download, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import DataTable, { type Column } from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import { useTenantId } from '../hooks/useTenant';
import { WorkloadPageLayout, Breadcrumb } from '../components/design-system';
import { formatSize, timeAgo } from '../utils/format';
import type { ProtectedObject, Snapshot, SnapshotItem } from '../types';

export default function OneDrive() {
  const [selectedAccount, setSelectedAccount] = useState<ProtectedObject | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<Snapshot | null>(null);
  const [backupMsg, setBackupMsg] = useState('');
  const tenantId = useTenantId();
  const qc = useQueryClient();

  const backupAllMutation = useMutation({
    mutationFn: () => api.post(`/onedrive/backup-all?tenant_id=${tenantId}`),
    onSuccess: (data: any) => {
      setBackupMsg(`Backup queued! Job #${data.job_id || 'N/A'} — ${data.total || 0} objects scheduled.`);
      qc.invalidateQueries({ queryKey: ['onedrive-accounts'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      setTimeout(() => setBackupMsg(''), 8000);
    },
    onError: (err: any) => { setBackupMsg(`Backup All failed: ${err.message}`); setTimeout(() => setBackupMsg(''), 5000); },
  });

  const backupMutation = useMutation({
    mutationFn: (accountId: number) => api.post(`/onedrive/accounts/${accountId}/backup`),
    onSuccess: (data: any) => {
      setBackupMsg(`Backup complete! Snapshot ID: ${data.snapshot_id}, Items: ${data.item_count}`);
      qc.invalidateQueries({ queryKey: ['onedrive-snapshots'] });
      qc.invalidateQueries({ queryKey: ['onedrive-accounts'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      setTimeout(() => setBackupMsg(''), 5000);
    },
    onError: (err: any) => { setBackupMsg(`Backup failed: ${err.message}`); setTimeout(() => setBackupMsg(''), 5000); },
  });

  const { data: snapshots } = useQuery({
    queryKey: ['onedrive-snapshots', selectedAccount?.id],
    queryFn: () => api.get<Snapshot[]>(`/onedrive/accounts/${selectedAccount!.id}/snapshots`),
    enabled: !!selectedAccount,
  });

  const { data: browseData } = useQuery({
    queryKey: ['onedrive-browse', selectedSnapshot?.id],
    queryFn: () => api.get<{ items: SnapshotItem[] }>(`/onedrive/accounts/${selectedAccount!.id}/snapshots/${selectedSnapshot!.id}/browse`),
    enabled: !!selectedSnapshot,
  });

  const { data: wlSummary } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => api.get<any>('/dashboard/summary'),
    staleTime: 30000,
  });
  const wlStats = useMemo(() => {
    const wl = wlSummary?.workloads?.onedrive || {};
    return {
      protected: wl.protected || 0, total: wl.total || 0,
      lastBackup: null as string | null, totalItems: 0, totalSize: 0, successRate: 100,
    };
  }, [wlSummary]);

  // ── Snapshot browse view ──
  if (selectedSnapshot) {
    return (
      <div>
        <Breadcrumb items={[{ label: getActivePlatformLabel(), path: '/' }, { label: 'OneDrive', path: '/onedrive' }, { label: selectedAccount?.display_name || 'Account' }]} />
        <button onClick={() => setSelectedSnapshot(null)} className="text-blue-600 hover:underline text-sm mb-4">&larr; Back to {selectedAccount?.display_name || 'snapshots'}</button>
        <h2 className="text-xl font-bold mb-4">Files — {selectedSnapshot.started_at?.slice(0, 16)}</h2>
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
                    {item.item_type === 'folder' ? <Folder className="w-4 h-4 text-yellow-500" /> : <FileText className="w-4 h-4 text-blue-500" />}
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

  // ── Account detail / snapshots view ──
  if (selectedAccount) {
    return (
      <div>
        <Breadcrumb items={[{ label: getActivePlatformLabel(), path: '/' }, { label: 'OneDrive', path: '/onedrive' }, { label: selectedAccount?.display_name || 'Account' }]} />
        <button onClick={() => setSelectedAccount(null)} className="text-blue-600 hover:underline text-sm mb-4">&larr; Back to OneDrive</button>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold">{selectedAccount.display_name}</h2>
            <p className="text-gray-500">{selectedAccount.email}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => backupMutation.mutate(selectedAccount.id)}
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
                    <button onClick={() => setSelectedSnapshot(s)} className="text-blue-600 hover:underline text-sm flex items-center gap-1">
                      Browse <ArrowRight className="w-3 h-3" />
                    </button>
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

  // ── Main accounts list (DataTable) ──
  const columns: Column<ProtectedObject>[] = [
    {
      key: 'display_name',
      label: 'Account',
      sortable: true,
      render: (row) => (
        <span className="font-medium flex items-center gap-2">
          <HardDrive className="w-4 h-4 text-purple-500" />
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
    <WorkloadPageLayout
      workloadLabel="OneDrive"
      workloadIcon={HardDrive}
      iconColor="text-purple-600"
      stats={wlStats}
      onBackupAll={() => backupAllMutation.mutate()}
      isBackingUp={backupAllMutation.isPending}
      statusMessage={backupMsg}
    >

      {/* Account list — DataTable (search via ⌘K) */}
      <DataTable<ProtectedObject>
        queryKey="onedrive-accounts"
        endpoint="/onedrive/accounts"
        columns={columns}
        extraParams={{ tenant_id: tenantId ?? '' }}
        enabled={!!tenantId}
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
        exportEndpoint="/export/csv?source=onedrive_accounts"
        defaultSortBy="display_name"
        defaultSortOrder="asc"
        emptyMessage="No accounts found. Configure a tenant and run discovery first."
        onRowClick={(row) => setSelectedAccount(row)}
        rowKey="id"
      />
    </WorkloadPageLayout>
  );
}
