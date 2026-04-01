import DataTable, { type Column } from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import type { AuditLogEntry } from '../types';

export default function AuditLog() {
  const columns: Column<AuditLogEntry>[] = [
    {
      key: 'timestamp',
      label: 'Timestamp',
      sortable: true,
      render: (row) => (
        <span className="text-muted-foreground text-xs font-mono">{row.timestamp?.slice(0, 19)}</span>
      ),
    },
    {
      key: 'severity',
      label: 'Severity',
      sortable: true,
      render: (row) => <StatusBadge status={row.severity} />,
    },
    {
      key: 'action',
      label: 'Action',
      sortable: true,
      render: (row) => <span className="font-medium">{row.action}</span>,
    },
    {
      key: 'resource_type',
      label: 'Resource',
      sortable: true,
      render: (row) => (
        <span className="text-muted-foreground">
          {row.resource_type} {row.resource_id ? `#${row.resource_id}` : ''}
        </span>
      ),
    },
    {
      key: 'details',
      label: 'Details',
      render: (row) => (
        <span className="text-muted-foreground text-xs max-w-[300px] truncate block">
          {row.details || '—'}
        </span>
      ),
    },
    {
      key: 'user_id',
      label: 'User',
      sortable: true,
      render: (row) => <span className="text-muted-foreground">User #{row.user_id || '—'}</span>,
    },
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Audit Log</h1>
        <p className="text-muted-foreground">Track all system operations and changes</p>
      </div>

      <DataTable<AuditLogEntry>
        queryKey="audit-logs"
        endpoint="/audit/logs"
        columns={columns}
        searchable
        searchPlaceholder="Search audit logs..."
        filters={[
          {
            key: 'severity',
            label: 'All Severities',
            options: [
              { value: 'info', label: 'Info' },
              { value: 'warning', label: 'Warning' },
              { value: 'error', label: 'Error' },
              { value: 'critical', label: 'Critical' },
            ],
          },
        ]}
        exportable
        exportEndpoint="/export/csv?source=audit_logs"
        defaultSortBy="timestamp"
        defaultSortOrder="desc"
        defaultPageSize={50}
        emptyMessage="No audit logs found"
        rowKey="id"
      />
    </div>
  );
}
