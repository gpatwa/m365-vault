import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MessageSquare, RefreshCw, Loader2, Users, ArrowRight, Download } from 'lucide-react';
import { api } from '../api/client';
import { WorkloadPageLayout, Breadcrumb } from '../components/design-system';
import { useTenantId, useWorkloadEnabled } from '../hooks/useTenant';
import { formatSize, timeAgo } from '../utils/format';
import { getActivePlatformLabel } from '../config/platforms';
import DataTable, { type Column } from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import CriticalityBadge from '../components/CriticalityBadge';
import { ItemCountDelta, HealthDots, ValidationBadge } from '../components/BackupIndicators';
import RestoreDialog from '../components/RestoreDialog';
import type { Snapshot } from '../types';

interface Team {
  id: number;
  display_name: string;
  ms_object_id: string;
  status: string;
  last_backup_at: string | null;
  total_items_backed_up: number;
  total_size_bytes: number;
}

interface TeamsSnapshotItem {
  id: number;
  item_type: string;
  ms_item_id: string;
  name: string;
  path: string;
  size_bytes: number;
  metadata: any;
}

export default function Teams() {
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<Snapshot | null>(null);
  const [backupMsg, setBackupMsg] = useState('');
  const [showRestore, setShowRestore] = useState(false);
  const tenantId = useTenantId();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const workloadEnabled = useWorkloadEnabled('teams');

  // ═══ ALL HOOKS ABOVE CONDITIONAL RETURNS ═══

  const { data: teamsData } = useQuery({
    queryKey: ['teams-stats', tenantId],
    queryFn: () => api.get<{ total: number; items: Team[] }>(`/teams/teams?tenant_id=${tenantId}&page_size=100`),
    enabled: !!tenantId,
    staleTime: 15000,
  });

  const workloadStats = useMemo(() => {
    const items = teamsData?.items || [];
    const protectedCount = items.filter(t => t.status === 'protected').length;
    const totalItems = items.reduce((sum, t) => sum + (t.total_items_backed_up || 0), 0);
    const totalSize = items.reduce((sum, t) => sum + (t.total_size_bytes || 0), 0);
    const backupTimes = items.map(t => t.last_backup_at).filter(Boolean).sort().reverse();
    return {
      protected: protectedCount,
      total: items.length,
      lastBackup: backupTimes[0] || null,
      totalItems,
      totalSize,
      successRate: 100,
    };
  }, [teamsData]);

  const backupAllMutation = useMutation({
    mutationFn: () => api.post(`/teams/backup-all?tenant_id=${tenantId}`),
    onSuccess: (data: any) => {
      setBackupMsg(`Backup complete! ${data.backed_up || 0} teams backed up.`);
      qc.invalidateQueries({ queryKey: ['teams'] });
      qc.invalidateQueries({ queryKey: ['teams-stats'] });
      setTimeout(() => setBackupMsg(''), 5000);
    },
    onError: (err: any) => {
      setBackupMsg(`Backup failed: ${err.message}`);
      setTimeout(() => setBackupMsg(''), 5000);
    },
  });

  const backupMutation = useMutation({
    mutationFn: (teamId: number) => api.post(`/teams/teams/${teamId}/backup`),
    onSuccess: (data: any) => {
      setBackupMsg(`Backup started! Snapshot: ${data.snapshot_id}, Items: ${data.item_count}`);
      qc.invalidateQueries({ queryKey: ['teams-snapshots'] });
      qc.invalidateQueries({ queryKey: ['teams-stats'] });
      setTimeout(() => setBackupMsg(''), 5000);
    },
    onError: (err: any) => {
      setBackupMsg(`Backup failed: ${err.message}`);
      setTimeout(() => setBackupMsg(''), 5000);
    },
  });

  // Snapshots for selected team
  const { data: snapshots } = useQuery({
    queryKey: ['teams-snapshots', selectedTeam?.id],
    queryFn: () => api.get<Snapshot[]>(`/teams/teams/${selectedTeam!.id}/snapshots`),
    enabled: !!selectedTeam,
  });

  // Browse items in selected snapshot
  const { data: browseData } = useQuery({
    queryKey: ['teams-browse', selectedSnapshot?.id],
    queryFn: () => api.get<{ items: TeamsSnapshotItem[] }>(`/teams/snapshot/${selectedSnapshot!.id}/items?page_size=100`),
    enabled: !!selectedSnapshot,
  });

  // Column definitions
  const teamColumns: Column<Team>[] = [
    {
      key: 'display_name',
      label: 'Team Name',
      sortable: true,
      render: (row) => (
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-pink-600 flex-shrink-0" />
          <span className="font-medium text-foreground">{row.display_name.replace(' (Team)', '').replace(' (Chats)', '')}</span>
          {row.display_name.includes('(Chats)') && (
            <span className="px-1.5 py-0.5 bg-purple-500/10 text-purple-600 rounded text-[10px] font-medium">Chat</span>
          )}
        </div>
      ),
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
      key: 'criticality_tier',
      label: 'Criticality',
      sortable: true,
      render: (row: any) => row.criticality_tier ? <CriticalityBadge tier={row.criticality_tier} score={row.criticality_score} /> : <span className="text-muted-foreground">—</span>,
    },
    {
      key: 'total_items_backed_up',
      label: 'Items',
      sortable: true,
      render: (row) => (
        <span className="text-muted-foreground">
          {row.total_items_backed_up ?? '—'}
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
  ];

  // ═══ CONDITIONAL RETURNS ═══

  // ── "Available" state — workload not enabled for this tenant ──
  if (workloadEnabled === false) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
          <MessageSquare className="w-8 h-8 text-muted-foreground" />
        </div>
        <h2 className="text-xl font-semibold mb-2">Teams is available</h2>
        <p className="text-muted-foreground mb-6 max-w-md">
          Enable Teams protection to start backing up your channels, messages, and files.
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

  if (!tenantId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <MessageSquare className="w-12 h-12 mb-3 text-muted-foreground" />
        <p className="text-lg font-medium text-muted-foreground">No Tenant Connected</p>
        <p className="text-sm mt-1">Connect a SaaS platform from the <a href="/tenants" className="text-blue-600 hover:underline">Tenants</a> page.</p>
      </div>
    );
  }

  // ── Snapshot browse view ──
  if (selectedSnapshot && selectedTeam) {
    return (
      <div>
        <Breadcrumb items={[
          { label: getActivePlatformLabel(), path: '/' },
          { label: 'Teams', path: '/teams' },
          { label: selectedTeam.display_name },
        ]} />
        <button onClick={() => setSelectedSnapshot(null)} className="text-blue-600 hover:underline text-sm mb-4 flex items-center gap-1">
          &larr; Back to {selectedTeam.display_name}
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
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Name / Content</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Path</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Size</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {browseData?.items?.map((item, i) => (
                <tr key={i} className="hover:bg-muted/50">
                  <td className="px-4 py-3"><StatusBadge status={item.item_type} /></td>
                  <td className="px-4 py-3 font-medium max-w-md truncate">{item.name}</td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{item.path || '—'}</td>
                  <td className="px-4 py-3 text-muted-foreground">{formatSize(item.size_bytes)}</td>
                </tr>
              ))}
              {(!browseData?.items?.length) && (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">No items in this snapshot</td></tr>
              )}
            </tbody>
          </table>
          </div>
        </div>
      </div>
    );
  }

  // ── Team detail / snapshots view ──
  if (selectedTeam) {
    return (
      <div>
        <Breadcrumb items={[
          { label: getActivePlatformLabel(), path: '/' },
          { label: 'Teams', path: '/teams' },
          { label: selectedTeam.display_name },
        ]} />
        <button onClick={() => setSelectedTeam(null)} className="text-blue-600 hover:underline text-sm mb-4 flex items-center gap-1">
          &larr; Back to Teams
        </button>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div className="min-w-0">
            <h2 className="text-xl font-bold truncate">{selectedTeam.display_name}</h2>
            <p className="text-muted-foreground">
              {selectedTeam.total_items_backed_up} items • {formatSize(selectedTeam.total_size_bytes)}
              {selectedTeam.last_backup_at && ` • Last backup: ${timeAgo(selectedTeam.last_backup_at)}`}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => backupMutation.mutate(selectedTeam.id)}
              disabled={backupMutation.isPending}
              className="px-4 py-2 bg-pink-600 text-foreground rounded-lg text-sm font-medium hover:bg-pink-700 flex items-center gap-2 disabled:opacity-50"
            >
              {backupMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              {backupMutation.isPending ? 'Backing up...' : 'Backup Now'}
            </button>
            <button onClick={() => setShowRestore(true)} disabled={!snapshots?.length} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 flex items-center gap-2 disabled:opacity-50">
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
                <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No snapshots yet. Run a backup first.</td></tr>
              )}
            </tbody>
          </table>
          </div>
        </div>

        {showRestore && snapshots && snapshots.length > 0 && (
          <RestoreDialog
            objectId={selectedTeam.id}
            objectName={selectedTeam.display_name}
            workload="teams"
            snapshotId={snapshots[0].id}
            snapshotDate={snapshots[0].started_at || undefined}
            itemCount={snapshots[0].item_count}
            onClose={() => setShowRestore(false)}
          />
        )}
      </div>
    );
  }

  // ── Main teams list ──
  return (
    <WorkloadPageLayout
      workloadLabel="Teams"
      workloadIcon={MessageSquare}
      iconColor="text-pink-600"
      stats={workloadStats}
      onBackupAll={() => backupAllMutation.mutate()}
      isBackingUp={backupAllMutation.isPending}
      statusMessage={backupMsg}
    >
      <DataTable<Team>
        queryKey="teams"
        endpoint="/teams/teams"
        columns={teamColumns}
        extraParams={{ tenant_id: tenantId ?? '' }}
        enabled={!!tenantId}
        defaultSortBy="display_name"
        defaultSortOrder="asc"
        emptyMessage="No Teams discovered. Run discovery on your tenant from the Tenants page."
        onRowClick={(row) => setSelectedTeam(row)}
        rowKey="id"
      />
    </WorkloadPageLayout>
  );
}
