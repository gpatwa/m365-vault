import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Shield, Users, KeyRound, ShieldCheck, AppWindow, MapPin, UserCog, RefreshCw, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import { Breadcrumb } from '../components/design-system';
import { useTenantId } from '../hooks/useTenant';
import { formatSize, timeAgo } from '../utils/format';
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
    <div className="space-y-6">
      <Breadcrumb items={[{ label: 'Microsoft 365', path: '/' }, { label: 'Entra ID' }]} />
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-50 rounded-lg">
            <Shield className="w-6 h-6 text-amber-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Entra ID</h1>
            <p className="text-sm text-gray-500">
              {summary.last_backup ? `Last backup ${timeAgo(summary.last_backup)}` : 'No backups yet'}
              {summary.item_count ? ` \u2022 ${summary.item_count} objects \u2022 ${formatSize(summary.size_bytes || 0)}` : ''}
            </p>
          </div>
        </div>
        <button
          onClick={() => backupMutation.mutate()}
          disabled={backupMutation.isPending}
          className="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 disabled:opacity-50 flex items-center gap-2"
        >
          {backupMutation.isPending
            ? <><Loader2 className="w-4 h-4 animate-spin" /> Backing up...</>
            : <><RefreshCw className="w-4 h-4" /> Backup Now</>
          }
        </button>
      </div>

      {backupMutation.isSuccess && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4" /> Backup completed successfully — {(backupMutation.data as any)?.item_count || 0} objects backed up
        </div>
      )}

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
          searchable
          searchPlaceholder="Search backed-up objects..."
          filters={[itemTypeFilterOptions]}
          defaultPageSize={50}
          emptyMessage={selectedType ? 'No items of this type' : 'No backed-up objects yet'}
        />
      )}
    </div>
  );
}
