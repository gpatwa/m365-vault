import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Shield, Users, KeyRound, ShieldCheck, AppWindow, MapPin, UserCog } from 'lucide-react';
import { api } from '../api/client';
import { WorkloadPageLayout } from '../components/design-system';
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
        <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${config?.color || 'text-gray-600'}`}>
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
    render: (row) => <span className="font-medium text-gray-900">{row.name}</span>,
  },
  {
    key: 'metadata',
    label: 'Details',
    render: (row) => (
      <span className="text-gray-500 text-xs">
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
    render: (row) => <span className="text-gray-500">{formatSize(row.size_bytes)}</span>,
  },
];

export default function EntraID() {
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const tenantId = useTenantId();
  const qc = useQueryClient();

  const { data: summary, isLoading } = useQuery({
    queryKey: ['entra-summary', tenantId],
    queryFn: () => api.get<EntraSummary>(`/entra-id/summary?tenant_id=${tenantId}`),
    enabled: !!tenantId,
  });

  if (!tenantId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <KeyRound className="w-12 h-12 mb-3 text-gray-300" />
        <p className="text-lg font-medium text-gray-600">No Tenant Connected</p>
        <p className="text-sm mt-1">Add a Microsoft 365 tenant from the <a href="/tenants" className="text-blue-600 hover:underline">Tenants</a> page to get started.</p>
      </div>
    );
  }

  const backupMutation = useMutation({
    mutationFn: () => api.post(`/entra-id/backup?tenant_id=${tenantId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entra-summary'] });
      qc.invalidateQueries({ queryKey: ['entra-items'] });
    },
  });

  if (isLoading || !tenantId) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-600" />
      </div>
    );
  }

  if (!summary?.protected) {
    return (
      <div className="text-center py-16">
        <Shield className="w-16 h-16 mx-auto mb-4 text-gray-300" />
        <h2 className="text-xl font-semibold text-gray-700 mb-2">Entra ID Not Discovered</h2>
        <p className="text-gray-500">Run discovery on your tenant from the Settings page to enable Entra ID backup.</p>
      </div>
    );
  }

  // Build extra params for DataTable — include item_type from card selection
  const extraParams: Record<string, string | number> = {};
  if (selectedType) {
    extraParams.item_type = selectedType;
  }

  return (
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

      {/* Object Type Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {Object.entries(ITEM_TYPE_CONFIG).map(([type, config]) => {
          const count = summary.counts?.[type] || 0;
          const Icon = config.icon;
          const isSelected = selectedType === type;
          return (
            <button
              key={type}
              onClick={() => setSelectedType(isSelected ? null : type)}
              className={`p-3 rounded-lg border text-left transition-all ${
                isSelected
                  ? 'border-amber-400 bg-amber-50 ring-2 ring-amber-200'
                  : 'border-gray-200 bg-white hover:border-amber-200 hover:bg-amber-50/50'
              }`}
            >
              <Icon className={`w-5 h-5 mb-1 ${config.color}`} />
              <p className="text-lg font-bold">{count}</p>
              <p className="text-xs text-gray-500 truncate">{config.label}</p>
            </button>
          );
        })}
      </div>

      {/* Items DataTable */}
      {summary.snapshot_id && (
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
  );
}
