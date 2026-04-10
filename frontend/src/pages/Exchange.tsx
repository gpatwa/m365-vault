import { useState, useMemo } from 'react';
import { getActivePlatformLabel } from '../config/platforms';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Mail, RefreshCw, Download, ArrowRight, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import DataTable, { type Column } from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import CriticalityBadge from '../components/CriticalityBadge';
import { WorkloadPageLayout, Breadcrumb } from '../components/design-system';
import { useTenantId } from '../hooks/useTenant';
import { useFeatureFlags } from '../contexts/FeatureFlagContext';
import { formatSize, timeAgo } from '../utils/format';
import RestoreDialog from '../components/RestoreDialog';
import type { ProtectedObject, Snapshot, SnapshotItem } from '../types';

export default function Exchange() {
  const [selectedMailbox, setSelectedMailbox] = useState<ProtectedObject | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<Snapshot | null>(null);
  const [showRestore, setShowRestore] = useState(false);
  const [backupMsg, setBackupMsg] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const tenantId = useTenantId();
  const qc = useQueryClient();

  // ═══ ALL HOOKS MUST BE ABOVE ANY CONDITIONAL RETURNS ═══

  const backupAllMutation = useMutation({
    mutationFn: () => api.post(`/exchange/backup-all?tenant_id=${tenantId}`),
    onSuccess: (data: any) => {
      setBackupMsg(`Backup queued! Job #${data.job_id || 'N/A'} — ${data.total || 0} objects scheduled.`);
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

  // Workload stats from actual mailbox data (not dashboard summary — it lacks items/size)
  const { data: statsData } = useQuery({
    queryKey: ['exchange-stats', tenantId],
    queryFn: () => api.get<{ total: number; items: ProtectedObject[] }>(`/exchange/mailboxes?tenant_id=${tenantId}&page_size=100`),
    enabled: !!tenantId,
    staleTime: 15000,
  });

  const workloadStats = useMemo(() => {
    const items = statsData?.items || [];
    const protectedCount = items.filter(m => m.status === 'protected').length;
    const totalItems = items.reduce((sum, m) => sum + (m.total_items || 0), 0);
    const totalSize = items.reduce((sum, m) => sum + (m.total_size_bytes || 0), 0);
    const backupTimes = items.map(m => m.last_backup_at).filter(Boolean).sort().reverse();

    // Derive SLA status: objects overdue if last_backup_at is older than 24h (default SLA window)
    const SLA_WINDOW_MS = 24 * 60 * 60 * 1000; // 24 hours
    const now = Date.now();
    const overdueCount = items.filter(m =>
      m.status === 'protected' && m.last_backup_at &&
      (now - new Date(m.last_backup_at).getTime()) > SLA_WINDOW_MS
    ).length;
    const unprotectedCount = items.filter(m => m.status !== 'protected').length;

    return {
      protected: protectedCount,
      total: items.length,
      lastBackup: backupTimes[0] || null,
      totalItems,
      totalSize,
      successRate: 100,
      slaStatus: {
        status: (overdueCount > 0 || unprotectedCount > 0) ? 'at_risk' as const : 'on_track' as const,
        overdueCount: overdueCount + unprotectedCount,
      },
    };
  }, [statsData]);

  // Column definitions (not a hook, but keep here for readability)
  const columns: Column<ProtectedObject>[] = [
    {
      key: 'display_name',
      label: 'Mailbox',
      sortable: true,
      render: (row) => (
        <span className="font-medium flex items-center gap-2">
          <Mail className="w-4 h-4 text-blue-500" />
          {row.display_name}
          {(row as any).object_subtype === 'shared_mailbox' && (
            <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">Shared</span>
          )}
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
        <span className="text-muted-foreground">{row.last_backup_at ? timeAgo(row.last_backup_at) : 'Never'}</span>
      ),
    },
    {
      key: 'criticality_tier',
      label: 'Criticality',
      sortable: true,
      render: (row) => row.criticality_tier ? <CriticalityBadge tier={row.criticality_tier} score={row.criticality_score} /> : <span className="text-muted-foreground">—</span>,
    },
    { key: 'total_items', label: 'Items', sortable: true },
    {
      key: 'total_size_bytes',
      label: 'Size',
      sortable: true,
      render: (row) => <span>{formatSize(row.total_size_bytes)}</span>,
    },
  ];

  // ═══ CONDITIONAL RETURNS (after all hooks) ═══

  // ── Snapshot browse view ──
  if (selectedSnapshot) {
    return (
      <div>
        <Breadcrumb items={[
          { label: getActivePlatformLabel(), path: '/' },
          { label: 'Exchange', path: '/exchange' },
          { label: selectedMailbox?.display_name || 'Mailbox' },
        ]} />
        <button onClick={() => setSelectedSnapshot(null)} className="text-blue-600 hover:underline text-sm mb-4 flex items-center gap-1">
          &larr; Back to {selectedMailbox?.display_name || 'snapshots'}
        </button>
        <h2 className="text-xl font-bold mb-4">
          Browse Snapshot — {selectedSnapshot.started_at?.slice(0, 16)}
        </h2>
        <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Type</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Subject / Name</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Sender</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Date</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Size</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {browseData?.items?.map((item, i) => (
                <tr key={i} className="hover:bg-muted/50">
                  <td className="px-4 py-3"><StatusBadge status={item.item_type} /></td>
                  <td className="px-4 py-3 font-medium">{item.subject || item.name}</td>
                  <td className="px-4 py-3 text-muted-foreground">{item.sender || '—'}</td>
                  <td className="px-4 py-3 text-muted-foreground">{item.received_at?.slice(0, 16) || item.last_modified?.slice(0, 16) || '—'}</td>
                  <td className="px-4 py-3 text-muted-foreground">{formatSize(item.size_bytes)}</td>
                </tr>
              ))}
              {(!browseData?.items?.length) && (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">No items in this snapshot</td></tr>
              )}
            </tbody>
          </table>
          </div>
        </div>
      </div>
    );
  }

  // ── Mailbox detail / snapshots view ──
  if (selectedMailbox) {
    return (
      <div>
        <Breadcrumb items={[
          { label: getActivePlatformLabel(), path: '/' },
          { label: 'Exchange', path: '/exchange' },
          { label: selectedMailbox.display_name },
        ]} />
        <button onClick={() => setSelectedMailbox(null)} className="text-blue-600 hover:underline text-sm mb-4 flex items-center gap-1">
          &larr; Back to Exchange
        </button>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div className="min-w-0">
            <h2 className="text-xl font-bold truncate">{selectedMailbox.display_name}</h2>
            <p className="text-muted-foreground truncate">{selectedMailbox.email}</p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <button
              onClick={() => backupMutation.mutate(selectedMailbox.id)}
              disabled={backupMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50"
            >
              {backupMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              {backupMutation.isPending ? 'Backing up...' : 'Backup Now'}
            </button>
            <button
              onClick={() => setShowRestore(true)}
              disabled={!snapshots?.length}
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 flex items-center gap-2 disabled:opacity-50"
            >
              <Download className="w-4 h-4" /> Restore
            </button>
          </div>
        </div>
        {backupMsg && (
          <div className={`rounded-lg p-3 mb-4 text-sm ${backupMsg.includes('failed') ? 'bg-red-500/10 border border-red-500/20 text-red-400' : 'bg-green-500/10 border border-green-500/20 text-green-400'}`}>
            {backupMsg}
          </div>
        )}
        <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
          <div className="p-4 border-b bg-muted/50">
            <h3 className="font-semibold">Snapshots ({snapshots?.length || 0})</h3>
          </div>
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
                <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No snapshots yet</td></tr>
              )}
            </tbody>
          </table>
          </div>
        </div>

        {/* Restore Dialog */}
        {showRestore && snapshots && snapshots.length > 0 && (
          <RestoreDialog
            objectId={selectedMailbox.id}
            objectName={selectedMailbox.display_name}
            workload="exchange"
            snapshotId={snapshots[0].id}
            snapshotDate={snapshots[0].started_at || undefined}
            itemCount={snapshots[0].item_count}
            onClose={() => setShowRestore(false)}
          />
        )}
      </div>
    );
  }

  // ── Main mailbox list ──
  return (
    <WorkloadPageLayout
      workloadLabel="Exchange"
      workloadIcon={Mail}
      iconColor="text-blue-600"
      stats={workloadStats}
      onBackupAll={() => backupAllMutation.mutate()}
      isBackingUp={backupAllMutation.isPending}
      statusMessage={backupMsg}
    >
      {/* Status filter pills */}
      <div className="flex items-center gap-2 flex-wrap">
        {[
          { key: '', label: 'All' },
          { key: 'protected', label: 'Protected' },
          { key: 'unprotected', label: 'Unprotected' },
          { key: 'error', label: 'Error' },
        ].map(s => (
          <button key={s.key} onClick={() => setStatusFilter(s.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              statusFilter === s.key
                ? 'bg-teal-500/15 text-teal-400 ring-1 ring-teal-500/30'
                : 'bg-card border border-border text-muted-foreground hover:text-foreground hover:border-teal-500/20'
            }`}>
            {s.label}
          </button>
        ))}
      </div>

      <DataTable<ProtectedObject>
        queryKey={`exchange-mailboxes-${statusFilter}`}
        endpoint="/exchange/mailboxes"
        columns={columns}
        extraParams={{ tenant_id: tenantId ?? '', ...(statusFilter ? { status: statusFilter } : {}) }}
        enabled={!!tenantId}
        exportable
        exportEndpoint="/export/csv?source=exchange_mailboxes"
        defaultSortBy="display_name"
        defaultSortOrder="asc"
        emptyMessage="No mailboxes found. Configure a tenant and run discovery first."
        onRowClick={(row) => setSelectedMailbox(row)}
        rowKey="id"
      />

      {/* Feature-gated upgrade prompts */}
      <FeatureGatedSection />
    </WorkloadPageLayout>
  );
}

function FeatureGatedSection() {
  const { isEnabled } = useFeatureFlags();
  const upgrades = [];

  if (!isEnabled('shared_mailbox')) {
    upgrades.push({ feature: 'Shared Mailbox Backup', desc: 'Protect shared mailboxes alongside regular mailboxes', tier: 'Professional' });
  }
  if (!isEnabled('archive_mailbox')) {
    upgrades.push({ feature: 'Archive Mailbox Backup', desc: 'Back up In-Place Archive mailboxes for compliance', tier: 'Professional' });
  }
  if (!isEnabled('mail_rules_backup')) {
    upgrades.push({ feature: 'Mail Rules Backup', desc: 'Protect inbox rules and auto-forwarding configurations', tier: 'Professional' });
  }
  if (!isEnabled('pst_export')) {
    upgrades.push({ feature: 'PST Export', desc: 'Export mailbox snapshots as downloadable PST-compatible archives', tier: 'Business' });
  }

  if (upgrades.length === 0) return null;

  return (
    <div className="mt-6 bg-card border border-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-foreground mb-3">Available with Upgrade</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {upgrades.map(u => (
          <div key={u.feature} className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg border border-border">
            <div className="w-8 h-8 bg-teal-500/10 rounded-lg flex items-center justify-center shrink-0">
              <Download className="w-4 h-4 text-teal-400" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">{u.feature}</div>
              <div className="text-xs text-muted-foreground">{u.desc}</div>
              <div className="text-[10px] text-teal-400 font-semibold mt-1">{u.tier} plan</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
