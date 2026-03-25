import { useMutation, useQueryClient } from '@tanstack/react-query';
import { MessageSquare, RefreshCw, Loader2, Users } from 'lucide-react';
import { api } from '../api/client';
import { WorkloadPageLayout } from '../components/design-system';
import { useTenantId } from '../hooks/useTenant';
import { formatSize, timeAgo } from '../utils/format';
import DataTable, { type Column } from '../components/DataTable';

interface Team {
  id: number;
  display_name: string;
  ms_object_id: string;
  status: string;
  last_backup_at: string | null;
  total_items_backed_up: number;
  total_size_bytes: number;
}

const teamColumns: Column<Team>[] = [
  {
    key: 'display_name',
    label: 'Team Name',
    sortable: true,
    width: 'min-w-[200px]',
    render: (row) => (
      <div className="flex items-center gap-2">
        <Users className="w-4 h-4 text-pink-600 flex-shrink-0" />
        <span className="font-medium text-gray-900">{row.display_name.replace(' (Team)', '')}</span>
      </div>
    ),
  },
  {
    key: 'status',
    label: 'Status',
    sortable: true,
    render: (row) => (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
        row.status === 'protected' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
      }`}>
        {row.status}
      </span>
    ),
  },
  {
    key: 'total_items_backed_up',
    label: 'Items',
    sortable: true,
    render: (row) => <span>{row.total_items_backed_up.toLocaleString()}</span>,
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
      <span className="text-gray-500">{row.last_backup_at ? timeAgo(row.last_backup_at) : 'Never'}</span>
    ),
  },
];

export default function Teams() {
  const tenantId = useTenantId();
  const qc = useQueryClient();

  const backupMutation = useMutation({
    mutationFn: (teamId?: number) =>
      teamId
        ? api.post(`/teams/teams/${teamId}/backup`)
        : api.post(`/teams/backup-all?tenant_id=${tenantId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['teams'] });
    },
  });

  if (!tenantId) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-600" />
      </div>
    );
  }

  return (
    <WorkloadPageLayout
      workloadLabel="Teams"
      workloadIcon={MessageSquare}
      iconColor="text-pink-600"
      stats={{
        protected: 0, total: 0,
        lastBackup: null,
        totalItems: 0, totalSize: 0,
        successRate: 100,
      }}
      onBackupAll={() => backupMutation.mutate(undefined)}
      isBackingUp={backupMutation.isPending}
      statusMessage={backupMutation.isSuccess ? 'Backup completed successfully' : undefined}
    >

      {/* Teams DataTable */}
      <DataTable<Team>
        queryKey="teams"
        endpoint="/teams/teams"
        columns={teamColumns}
        extraParams={{ tenant_id: tenantId }}
        defaultSortBy="display_name"
        defaultSortOrder="asc"
        emptyMessage="No Teams discovered. Run discovery on your tenant from the Settings page."
        headerActions={
          <button
            onClick={() => backupMutation.mutate(undefined)}
            disabled={backupMutation.isPending}
            className="px-4 py-2 bg-pink-600 text-white rounded-lg text-sm font-medium hover:bg-pink-700 disabled:opacity-50 flex items-center gap-2"
          >
            {backupMutation.isPending
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Backing up...</>
              : <><RefreshCw className="w-4 h-4" /> Backup All</>
            }
          </button>
        }
        actions={(row) => (
          <button
            onClick={() => backupMutation.mutate(row.id)}
            disabled={backupMutation.isPending}
            className="px-2.5 py-1 border border-pink-200 text-pink-700 rounded-lg text-xs font-medium hover:bg-pink-50 flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" /> Backup
          </button>
        )}
      />
    </WorkloadPageLayout>
  );
}
