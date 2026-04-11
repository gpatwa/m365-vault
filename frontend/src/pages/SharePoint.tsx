import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { getActivePlatformLabel } from '../config/platforms';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Globe, ArrowRight, RefreshCw, Download, Folder, FileText, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import DataTable, { type Column } from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import CriticalityBadge from '../components/CriticalityBadge';
import { ItemCountDelta, HealthDots, ValidationBadge } from '../components/BackupIndicators';
import { WorkloadPageLayout, Breadcrumb } from '../components/design-system';
import { useTenantId, useWorkloadEnabled } from '../hooks/useTenant';
import { formatSize, timeAgo } from '../utils/format';
import RestoreDialog from '../components/RestoreDialog';
import type { ProtectedObject, Snapshot, SnapshotItem } from '../types';

export default function SharePoint() {
  const [selectedSite, setSelectedSite] = useState<ProtectedObject | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<Snapshot | null>(null);
  const [backupMsg, setBackupMsg] = useState('');
  const [showRestore, setShowRestore] = useState(false);
  const tenantId = useTenantId();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const workloadEnabled = useWorkloadEnabled('sharepoint');

  const backupAllMutation = useMutation({
    mutationFn: () => api.post(`/sharepoint/backup-all?tenant_id=${tenantId}`),
    onSuccess: (data: any) => {
      setBackupMsg(`Backup queued! Job #${data.job_id || 'N/A'} — ${data.total || 0} objects scheduled.`);
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

  const { data: statsData } = useQuery({
    queryKey: ['sharepoint-stats', tenantId],
    queryFn: () => api.get<{ total: number; items: ProtectedObject[] }>(`/sharepoint/sites?tenant_id=${tenantId}&page_size=100`),
    enabled: !!tenantId,
    staleTime: 15000,
  });
  const wlStats = useMemo(() => {
    const items = statsData?.items || [];
    const protectedCount = items.filter(s => s.status === 'protected').length;
    const totalItems = items.reduce((sum, s) => sum + (s.total_items || 0), 0);
    const totalSize = items.reduce((sum, s) => sum + (s.total_size_bytes || 0), 0);
    const backupTimes = items.map(s => s.last_backup_at).filter(Boolean).sort().reverse();
    return {
      protected: protectedCount, total: items.length,
      lastBackup: backupTimes[0] || null, totalItems, totalSize, successRate: 100,
    };
  }, [statsData]);

  // ── "Available" state — workload not enabled for this tenant ──
  if (workloadEnabled === false) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
          <Globe className="w-8 h-8 text-muted-foreground" />
        </div>
        <h2 className="text-xl font-semibold mb-2">SharePoint is available</h2>
        <p className="text-muted-foreground mb-6 max-w-md">
          Enable SharePoint protection to start backing up your sites, lists, and documents.
        </p>
        <button
          onClick={() => navigate('/settings')}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          Enable in Organization Settings &rarr;
        </button>
      </div>
    );
  }

  // ── Snapshot browse view ──
  if (selectedSnapshot) {
    return (
      <div>
        <Breadcrumb items={[{ label: getActivePlatformLabel(), path: '/' }, { label: 'SharePoint', path: '/sharepoint' }, { label: selectedSite?.display_name || 'Site' }]} />
        <button onClick={() => setSelectedSnapshot(null)} className="text-blue-600 hover:underline text-sm mb-4">&larr; Back to {selectedSite?.display_name || 'snapshots'}</button>
        <h2 className="text-xl font-bold mb-4">Site Content — {selectedSnapshot.started_at?.slice(0, 16)}</h2>
        <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Name</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Path</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Type</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Size</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Modified</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {browseData?.items?.map((item, i) => (
                <tr key={i} className="hover:bg-muted/50">
                  <td className="px-4 py-3 font-medium flex items-center gap-2">
                    {['folder', 'document_library', 'list'].includes(item.item_type) ? <Folder className="w-4 h-4 text-yellow-500" /> : <FileText className="w-4 h-4 text-green-500" />}
                    {item.file_name || item.name}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{item.path}</td>
                  <td className="px-4 py-3"><StatusBadge status={item.item_type} /></td>
                  <td className="px-4 py-3">{formatSize(item.size_bytes)}</td>
                  <td className="px-4 py-3 text-muted-foreground">{item.last_modified?.slice(0, 16) || '—'}</td>
                </tr>
              ))}
              {!browseData?.items?.length && <tr><td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">No items</td></tr>}
            </tbody>
          </table>
          </div>
        </div>
      </div>
    );
  }

  // ── Site detail / snapshots view ──
  if (selectedSite) {
    return (
      <div>
        <Breadcrumb items={[{ label: getActivePlatformLabel(), path: '/' }, { label: 'SharePoint', path: '/sharepoint' }, { label: selectedSite?.display_name || 'Site' }]} />
        <button onClick={() => setSelectedSite(null)} className="text-blue-600 hover:underline text-sm mb-4">&larr; Back to SharePoint</button>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div className="min-w-0">
            <h2 className="text-xl font-bold truncate">{selectedSite.display_name}</h2>
            <p className="text-muted-foreground text-sm truncate">{selectedSite.site_url}</p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <button
              onClick={() => backupMutation.mutate(selectedSite.id)}
              disabled={backupMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50"
            >
              {backupMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              {backupMutation.isPending ? 'Backing up...' : 'Backup'}
            </button>
            <button onClick={() => setShowRestore(true)} disabled={!snapshots?.length} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 flex items-center gap-2 disabled:opacity-50"><Download className="w-4 h-4" /> Restore</button>
          </div>
        </div>
        {backupMsg && (
          <div className={`rounded-lg p-3 mb-4 text-sm ${backupMsg.includes('failed') ? 'bg-red-500/10 border border-red-500/20 text-red-400' : 'bg-green-500/10 border border-green-500/20 text-green-400'}`}>
            {backupMsg}
          </div>
        )}
        <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
          <div className="p-4 border-b bg-muted/50"><h3 className="font-semibold">Snapshots</h3></div>
          <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Date</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Type</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Items</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Size</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {snapshots?.map(s => (
                <tr key={s.id} className="hover:bg-muted/50">
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
              {!snapshots?.length && <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No snapshots</td></tr>}
            </tbody>
          </table>
          </div>
        </div>

        {showRestore && snapshots && snapshots.length > 0 && (
          <RestoreDialog
            objectId={selectedSite.id}
            objectName={selectedSite.display_name}
            workload="sharepoint"
            snapshotId={snapshots[0].id}
            snapshotDate={snapshots[0].started_at || undefined}
            itemCount={snapshots[0].item_count}
            onClose={() => setShowRestore(false)}
          />
        )}
      </div>
    );
  }

  // ── Main sites list (DataTable) ──
  const columns: Column<ProtectedObject>[] = [
    {
      key: 'display_name',
      label: 'Site',
      sortable: true,
      render: (row) => (
        <span className="font-medium flex items-center gap-2">
          <Globe className="w-4 h-4 text-green-500" />
          {row.display_name}
        </span>
      ),
    },
    {
      key: 'site_url',
      label: 'URL',
      sortable: true,
      render: (row) => <span className="text-muted-foreground text-xs">{row.site_url}</span>,
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (row) => (
        <span className="inline-flex items-center">
          <StatusBadge status={row.status} />
          <ValidationBadge status={(row as any).validation_status} />
        </span>
      ),
    },
    {
      key: 'last_backup_at',
      label: 'Last Backup',
      sortable: true,
      render: (row) => (
        <div className="flex flex-col gap-1">
          <span className="text-muted-foreground">{row.last_backup_at ? timeAgo(row.last_backup_at) : 'Never'}</span>
          <HealthDots history={(row as any).backup_history_7d} />
        </div>
      ),
    },
    {
      key: 'criticality_tier',
      label: 'Criticality',
      sortable: true,
      render: (row) => row.criticality_tier ? <CriticalityBadge tier={row.criticality_tier} score={row.criticality_score} /> : <span className="text-muted-foreground">—</span>,
    },
    {
      key: 'total_items',
      label: 'Items',
      sortable: true,
      render: (row) => (
        <span className="text-muted-foreground">
          {row.total_items ?? '—'}
          <ItemCountDelta delta={(row as any).item_count_delta} />
        </span>
      ),
    },
    {
      key: 'total_size_bytes',
      label: 'Size',
      sortable: true,
      render: (row) => <span>{formatSize(row.total_size_bytes)}</span>,
    },
  ];

  return (
    <WorkloadPageLayout
      workloadLabel="SharePoint"
      workloadIcon={Globe}
      iconColor="text-green-600"
      stats={wlStats}
      onBackupAll={() => backupAllMutation.mutate()}
      isBackingUp={backupAllMutation.isPending}
      statusMessage={backupMsg}
    >
      {backupMsg && !selectedSite && (
        <div className={`rounded-lg p-3 mb-4 text-sm ${backupMsg.includes('failed') ? 'bg-red-500/10 border border-red-500/20 text-red-400' : 'bg-green-500/10 border border-green-500/20 text-green-400'}`}>
          {backupMsg}
        </div>
      )}

      {/* Site list — DataTable */}
      <DataTable<ProtectedObject>
        queryKey="sharepoint-sites"
        endpoint="/sharepoint/sites"
        columns={columns}
        extraParams={{ tenant_id: tenantId ?? '' }}
        enabled={!!tenantId}
        searchPlaceholder="Search sites..."
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
        exportEndpoint="/export/csv?source=sharepoint_sites"
        defaultSortBy="display_name"
        defaultSortOrder="asc"
        emptyMessage="No sites found. Configure a tenant and run discovery first."
        onRowClick={(row) => setSelectedSite(row)}
        rowKey="id"
      />
    </WorkloadPageLayout>
  );
}
