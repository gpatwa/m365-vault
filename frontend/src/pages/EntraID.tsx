import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Shield, Users, KeyRound, ShieldCheck, AppWindow, MapPin, UserCog, Server, Building2, Lock, Laptop, Globe, Download } from 'lucide-react';
import { api } from '../api/client';
import { WorkloadPageLayout } from '../components/design-system';
import RestoreDialog from '../components/RestoreDialog';
import { useTenantId } from '../hooks/useTenant';
import { formatSize } from '../utils/format';
import DataTable, { type Column, type FilterOption } from '../components/DataTable';

interface EntraSummary {
  protected: boolean;
  object_id?: number;
  status?: string;
  last_backup?: string;
  snapshot_id?: number;
  item_count?: number;
  size_bytes?: number;
  counts?: Record<string, number>;
  message?: string;
}

interface SnapshotItem {
  id: number;
  item_type: string;
  ms_item_id: string;
  name: string;
  path: string;
  size_bytes: number;
  metadata: Record<string, any> | null;
}

const ITEM_TYPE_CONFIG: Record<string, { label: string; icon: typeof Users; color: string }> = {
  user: { label: 'Users', icon: Users, color: 'text-blue-600' },
  group: { label: 'Groups', icon: Users, color: 'text-purple-600' },
  directory_role: { label: 'Directory Roles', icon: UserCog, color: 'text-amber-600' },
  role_assignment: { label: 'Role Assignments', icon: KeyRound, color: 'text-orange-600' },
  conditional_access_policy: { label: 'Conditional Access', icon: ShieldCheck, color: 'text-red-600' },
  app_registration: { label: 'App Registrations', icon: AppWindow, color: 'text-green-600' },
  named_location: { label: 'Named Locations', icon: MapPin, color: 'text-indigo-600' },
  service_principal: { label: 'Service Principals', icon: Server, color: 'text-cyan-600' },
  administrative_unit: { label: 'Admin Units', icon: Building2, color: 'text-teal-600' },
  oauth_permission_grant: { label: 'OAuth Grants', icon: Lock, color: 'text-pink-600' },
  device: { label: 'Devices', icon: Laptop, color: 'text-muted-foreground' },
  domain: { label: 'Domains', icon: Globe, color: 'text-emerald-600' },
};

const itemTypeFilterOptions: FilterOption = {
  key: 'item_type',
  label: 'All Types',
  options: Object.entries(ITEM_TYPE_CONFIG).map(([value, cfg]) => ({
    value,
    label: cfg.label,
  })),
};

const itemColumns: Column<SnapshotItem>[] = [
  {
    key: 'item_type',
    label: 'Type',
    sortable: true,
    render: (row) => {
      const config = ITEM_TYPE_CONFIG[row.item_type];
      const Icon = config?.icon || Shield;
      return (
        <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${config?.color || 'text-muted-foreground'}`}>
          <Icon className="w-3.5 h-3.5" />
          {config?.label || row.item_type}
        </span>
      );
    },
  },
  {
    key: 'name',
    label: 'Name',
    sortable: true,
    width: 'min-w-[200px]',
    render: (row) => <span className="font-medium text-foreground">{row.name}</span>,
  },
  {
    key: 'metadata',
    label: 'Details',
    render: (row) => (
      <span className="text-muted-foreground text-xs">
        {row.metadata && Object.entries(row.metadata)
          .filter(([, v]) => v !== null && v !== undefined && v !== '')
          .slice(0, 3)
          .map(([k, v]) => `${k}: ${v}`)
          .join(' \u2022 ')}
      </span>
    ),
  },
  {
    key: 'size_bytes',
    label: 'Size',
    sortable: true,
    className: 'text-right',
    render: (row) => <span className="text-muted-foreground">{formatSize(row.size_bytes)}</span>,
  },
];

interface DiffResult {
  snapshot_a: number;
  snapshot_b: number;
  summary: { added: number; removed: number; changed: number; unchanged: number; total_a: number; total_b: number };
  added: { ms_item_id: string; item_type: string; name: string }[];
  removed: { ms_item_id: string; item_type: string; name: string }[];
  changed: { ms_item_id: string; item_type: string; name: string; old_size: number; new_size: number }[];
}

interface SnapshotInfo {
  id: number;
  snapshot_type: string;
  status: string;
  started_at: string;
  completed_at: string;
  item_count: number;
  size_bytes: number;
}

export default function EntraID() {
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const [showRestore, setShowRestore] = useState(false);
  const [diffSnapA, setDiffSnapA] = useState<number | null>(null);
  const [diffSnapB, setDiffSnapB] = useState<number | null>(null);
  const tenantId = useTenantId();
  const qc = useQueryClient();

  // ═══ ALL HOOKS ABOVE CONDITIONAL RETURNS ═══

  const { data: summary, isLoading } = useQuery({
    queryKey: ['entra-summary', tenantId],
    queryFn: () => api.get<EntraSummary>(`/entra-id/summary?tenant_id=${tenantId}`),
    enabled: !!tenantId,
  });

  const backupMutation = useMutation({
    mutationFn: () => api.post(`/entra-id/backup?tenant_id=${tenantId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entra-summary'] });
      qc.invalidateQueries({ queryKey: ['entra-items'] });
      qc.invalidateQueries({ queryKey: ['entra-snapshots'] });
    },
  });

  const { data: snapshots } = useQuery({
    queryKey: ['entra-snapshots', tenantId],
    queryFn: () => api.get<{ items: SnapshotInfo[] }>(`/entra-id/snapshots?tenant_id=${tenantId}&page_size=10`),
    enabled: !!tenantId && !!summary?.protected,
  });

  const { data: diffResult } = useQuery({
    queryKey: ['entra-diff', diffSnapA, diffSnapB],
    queryFn: () => api.get<DiffResult>(`/entra-id/compare?snapshot_a=${diffSnapA}&snapshot_b=${diffSnapB}`),
    enabled: !!diffSnapA && !!diffSnapB && diffSnapA !== diffSnapB,
  });

  // ═══ CONDITIONAL RETURNS ═══

  if (!tenantId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <KeyRound className="w-12 h-12 mb-3 text-muted-foreground" />
        <p className="text-lg font-medium text-muted-foreground">No Tenant Connected</p>
        <p className="text-sm mt-1">Connect a SaaS platform from the <a href="/tenants" className="text-blue-600 hover:underline">Tenants</a> page to get started.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-600" />
      </div>
    );
  }

  if (!summary?.protected) {
    return (
      <div className="text-center py-16">
        <Shield className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
        <h2 className="text-xl font-semibold text-muted-foreground mb-2">Entra ID Not Discovered</h2>
        <p className="text-muted-foreground">Run discovery on your tenant from the Settings page to enable Entra ID backup.</p>
      </div>
    );
  }

  // Build extra params for DataTable — include item_type from card selection
  const extraParams: Record<string, string | number> = {};
  if (selectedType) {
    extraParams.item_type = selectedType;
  }

  return (
    <>
    <WorkloadPageLayout
      workloadLabel="Entra ID"
      workloadIcon={Shield}
      iconColor="text-amber-600"
      stats={{
        protected: summary.protected ? 1 : 0,
        total: 1,
        lastBackup: summary.last_backup || null,
        totalItems: summary.item_count || 0,
        totalSize: summary.size_bytes || 0,
        successRate: 100,
      }}
      onBackupAll={() => backupMutation.mutate()}
      isBackingUp={backupMutation.isPending}
      statusMessage={backupMutation.isSuccess ? `Backup completed — ${(backupMutation.data as any)?.item_count || 0} objects backed up` : undefined}
    >

      {/* Restore Button */}
      <div className="flex justify-end">
        <button
          onClick={() => setShowRestore(true)}
          disabled={!summary.snapshot_id}
          className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 flex items-center gap-2 disabled:opacity-50"
        >
          <Download className="w-4 h-4" /> Restore Entra ID Objects
        </button>
      </div>

      {/* Object Type Cards — 12 types in responsive grid */}
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-6 gap-2.5">
        {Object.entries(ITEM_TYPE_CONFIG).map(([type, config]) => {
          const count = summary.counts?.[type] || 0;
          const Icon = config.icon;
          const isSelected = selectedType === type;
          return (
            <button
              key={type}
              onClick={() => setSelectedType(isSelected ? null : type)}
              className={`p-2.5 rounded-lg border text-left transition-all ${
                isSelected
                  ? 'border-amber-400 bg-amber-500/10 ring-2 ring-amber-200'
                  : count > 0
                    ? 'border-border bg-card hover:border-amber-500/20 hover:bg-amber-500/10/50'
                    : 'border-border bg-muted/50/50 opacity-60'
              }`}
            >
              <Icon className={`w-4 h-4 mb-0.5 ${config.color}`} />
              <p className="text-base font-bold">{count}</p>
              <p className="text-[10px] text-muted-foreground truncate">{config.label}</p>
            </button>
          );
        })}
      </div>

      {/* Snapshot Diff Toggle */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setShowDiff(!showDiff)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
            showDiff ? 'bg-amber-500/10 border-amber-300 text-amber-400' : 'bg-card border-border text-muted-foreground hover:border-amber-500/20'
          }`}
        >
          {showDiff ? '✕ Close Diff' : '🔍 Compare Snapshots'}
        </button>
        {showDiff && snapshots?.items && snapshots.items.length >= 2 && (
          <div className="flex items-center gap-2 text-xs">
            <select
              className="border border-border rounded-lg px-2 py-1 text-xs"
              value={diffSnapA || ''}
              onChange={e => setDiffSnapA(Number(e.target.value) || null)}
            >
              <option value="">Older snapshot...</option>
              {snapshots.items.map(s => (
                <option key={s.id} value={s.id}>#{s.id} ({s.item_count} items, {s.started_at?.slice(0, 10)})</option>
              ))}
            </select>
            <span className="text-muted-foreground">→</span>
            <select
              className="border border-border rounded-lg px-2 py-1 text-xs"
              value={diffSnapB || ''}
              onChange={e => setDiffSnapB(Number(e.target.value) || null)}
            >
              <option value="">Newer snapshot...</option>
              {snapshots.items.map(s => (
                <option key={s.id} value={s.id}>#{s.id} ({s.item_count} items, {s.started_at?.slice(0, 10)})</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Diff Results */}
      {showDiff && diffResult && (
        <div className="bg-card border border-amber-500/20 rounded-xl p-4 space-y-3">
          <h3 className="text-sm font-semibold text-amber-400">Configuration Drift: Snapshot #{diffResult.snapshot_a} → #{diffResult.snapshot_b}</h3>
          <div className="grid grid-cols-4 gap-3">
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-green-400">{diffResult.summary.added}</p>
              <p className="text-[10px] text-green-600 font-medium">Added</p>
            </div>
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-red-400">{diffResult.summary.removed}</p>
              <p className="text-[10px] text-red-600 font-medium">Removed</p>
            </div>
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-amber-400">{diffResult.summary.changed}</p>
              <p className="text-[10px] text-amber-600 font-medium">Changed</p>
            </div>
            <div className="bg-muted/50 border border-border rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-muted-foreground">{diffResult.summary.unchanged}</p>
              <p className="text-[10px] text-muted-foreground font-medium">Unchanged</p>
            </div>
          </div>
          {(diffResult.added.length > 0 || diffResult.removed.length > 0 || diffResult.changed.length > 0) && (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {diffResult.added.map(a => (
                <div key={a.ms_item_id} className="flex items-center gap-2 text-xs text-green-400 bg-green-500/10/50 px-2 py-1 rounded">
                  <span className="font-mono">+</span>
                  <span className="font-medium">{ITEM_TYPE_CONFIG[a.item_type]?.label || a.item_type}:</span>
                  <span>{a.name}</span>
                </div>
              ))}
              {diffResult.removed.map(r => (
                <div key={r.ms_item_id} className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10/50 px-2 py-1 rounded">
                  <span className="font-mono">-</span>
                  <span className="font-medium">{ITEM_TYPE_CONFIG[r.item_type]?.label || r.item_type}:</span>
                  <span>{r.name}</span>
                </div>
              ))}
              {diffResult.changed.map(c => (
                <div key={c.ms_item_id} className="flex items-center gap-2 text-xs text-amber-400 bg-amber-500/10/50 px-2 py-1 rounded">
                  <span className="font-mono">~</span>
                  <span className="font-medium">{ITEM_TYPE_CONFIG[c.item_type]?.label || c.item_type}:</span>
                  <span>{c.name}</span>
                  <span className="text-muted-foreground">({formatSize(c.old_size)} → {formatSize(c.new_size)})</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Items DataTable */}
      {summary.snapshot_id && !showDiff && (
        <DataTable<SnapshotItem>
          queryKey="entra-items"
          endpoint={`/entra-id/snapshot/${summary.snapshot_id}/items`}
          columns={itemColumns}
          extraParams={extraParams}
          filters={[itemTypeFilterOptions]}
          defaultPageSize={50}
          emptyMessage={selectedType ? 'No items of this type' : 'No backed-up objects yet'}
        />
      )}
    </WorkloadPageLayout>

    {showRestore && summary.snapshot_id && summary.object_id && (
      <RestoreDialog
        objectId={summary.object_id}
        objectName="Entra ID Directory"
        workload="entra_id"
        snapshotId={summary.snapshot_id}
        snapshotDate={summary.last_backup || undefined}
        itemCount={summary.item_count}
        onClose={() => setShowRestore(false)}
      />
    )}
    </>
  );
}
