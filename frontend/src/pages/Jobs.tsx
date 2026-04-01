import { useState, useMemo } from 'react';
import { getActivePlatformLabel } from '../config/platforms';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Loader2, RotateCcw, Briefcase, CheckCircle2, PlayCircle } from 'lucide-react';
import { api } from '../api/client';
import { WORKLOAD_KEYS, WORKLOAD_MAP } from '../config/workloads';
import WorkloadSwimlane from '../components/jobs/WorkloadSwimlane';
import type { WorkloadStats } from '../components/jobs/WorkloadSwimlane';
import type { BackupJob, RestoreJob, PaginatedResponse, FailedJobsSummary } from '../types';
import DataTable, { type Column, type FilterOption } from '../components/DataTable';
import { formatSize, formatDuration, timeAgo } from '../utils/format';
import Breadcrumb from '../components/design-system/Breadcrumb';
import HeroSummaryBar, { type HeroStat } from '../components/design-system/HeroSummaryBar';

type Workload = string;
const WORKLOADS = WORKLOAD_KEYS;

// ── DataTable column definitions for "All Jobs" view ──

const statusBadge = (status: string) => {
  const colors: Record<string, string> = {
    completed: 'bg-green-500/15 text-green-400',
    failed: 'bg-red-500/15 text-red-400',
    in_progress: 'bg-blue-500/15 text-blue-400',
    queued: 'bg-yellow-100 text-yellow-700',
    partial: 'bg-orange-100 text-orange-700',
    cancelled: 'bg-gray-100 text-gray-600',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-600'}`}>
      {status.replace('_', ' ')}
    </span>
  );
};

const allJobsColumns: Column<BackupJob>[] = [
  {
    key: 'id',
    label: 'ID',
    sortable: true,
    width: 'w-16',
    render: (row) => <span className="font-mono text-xs text-gray-500">#{row.id}</span>,
  },
  {
    key: 'workload_type',
    label: 'Workload',
    sortable: true,
    render: (row) => {
      const wl = WORKLOAD_MAP[row.workload_type];
      if (!wl) return <span>{row.workload_type}</span>;
      const Icon = wl.icon;
      return (
        <div className="flex items-center gap-1.5">
          <Icon className={`w-3.5 h-3.5 ${wl.iconColor}`} />
          <span className="font-medium">{wl.label}</span>
        </div>
      );
    },
  },
  {
    key: 'status',
    label: 'Status',
    sortable: true,
    render: (row) => statusBadge(row.status),
  },
  {
    key: 'objects_total',
    label: 'Objects',
    sortable: true,
    render: (row) => (
      <span className="text-xs">
        {row.objects_processed}/{row.objects_total}
        {row.objects_failed > 0 && <span className="text-red-500 ml-1">({row.objects_failed} failed)</span>}
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
    key: 'started_at',
    label: 'Duration',
    sortable: true,
    render: (row) => <span className="text-gray-500">{formatDuration(row.started_at, row.completed_at)}</span>,
  },
  {
    key: 'created_at',
    label: 'Created',
    sortable: true,
    render: (row) => <span className="text-gray-500">{row.started_at ? timeAgo(row.started_at) : '\u2014'}</span>,
  },
];

const workloadFilter: FilterOption = {
  key: 'workload_type',
  label: 'All Workloads',
  options: WORKLOADS.map(w => ({
    value: w,
    label: WORKLOAD_MAP[w]?.label || w,
  })),
};

const statusFilter: FilterOption = {
  key: 'status',
  label: 'All Statuses',
  options: [
    { value: 'queued', label: 'Queued' },
    { value: 'in_progress', label: 'In Progress' },
    { value: 'completed', label: 'Completed' },
    { value: 'failed', label: 'Failed' },
    { value: 'partial', label: 'Partial' },
    { value: 'cancelled', label: 'Cancelled' },
  ],
};

export default function Jobs() {
  const [expandedWorkload, setExpandedWorkload] = useState<Workload | null>(null);
  const [retryMsg, setRetryMsg] = useState('');
  const [activeTab, setActiveTab] = useState<'swimlanes' | 'all'>('swimlanes');
  const qc = useQueryClient();

  // Fetch ALL backup jobs (no status filter) for summary stats
  const { data: allBackupJobs, isLoading: loadingBackup } = useQuery({
    queryKey: ['backup-jobs-all'],
    queryFn: () => api.get<PaginatedResponse<BackupJob>>('/jobs/backup?page_size=100'),
    refetchInterval: 5000,
  });

  // Fetch ALL restore jobs
  const { data: allRestoreJobs, isLoading: loadingRestore } = useQuery({
    queryKey: ['restore-jobs-all'],
    queryFn: () => api.get<PaginatedResponse<RestoreJob>>('/jobs/restore?page_size=100'),
    refetchInterval: 10000,
  });

  // Failed summary
  const { data: failedSummary } = useQuery({
    queryKey: ['failed-jobs-summary'],
    queryFn: () => api.get<FailedJobsSummary>('/jobs/failed-summary'),
    refetchInterval: 15000,
  });

  // Retry mutations
  const retryJobMutation = useMutation({
    mutationFn: (jobId: number) => api.post(`/jobs/backup/${jobId}/retry`),
    onSuccess: (data: any) => {
      setRetryMsg(`Retry complete \u2014 status: ${data.status}, retries: ${data.retry_count}`);
      qc.invalidateQueries({ queryKey: ['backup-jobs-all'] });
      qc.invalidateQueries({ queryKey: ['failed-jobs-summary'] });
      qc.invalidateQueries({ queryKey: ['all-backup-jobs'] });
      setTimeout(() => setRetryMsg(''), 5000);
    },
    onError: (err: any) => { setRetryMsg(`Retry failed: ${err.message}`); setTimeout(() => setRetryMsg(''), 5000); },
  });

  const retryAllMutation = useMutation({
    mutationFn: () => api.post('/jobs/retry-all-failed'),
    onSuccess: (data: any) => {
      setRetryMsg(`Retried ${data.retried} jobs \u2014 ${data.succeeded} succeeded, ${data.still_failed} still failed`);
      qc.invalidateQueries({ queryKey: ['backup-jobs-all'] });
      qc.invalidateQueries({ queryKey: ['failed-jobs-summary'] });
      qc.invalidateQueries({ queryKey: ['all-backup-jobs'] });
      setTimeout(() => setRetryMsg(''), 8000);
    },
    onError: (err: any) => { setRetryMsg(`Retry all failed: ${err.message}`); setTimeout(() => setRetryMsg(''), 5000); },
  });

  // Compute per-workload stats
  const workloadData = useMemo(() => {
    const backupJobs = allBackupJobs?.items ?? [];
    const restoreJobs = allRestoreJobs?.items ?? [];

    const result: Record<Workload, { stats: WorkloadStats; backupJobs: BackupJob[]; restoreJobs: RestoreJob[] }> = {} as any;

    for (const w of WORKLOADS) {
      const wBackup = backupJobs.filter(j => j.workload_type === w);
      const wRestore = restoreJobs;

      const completedJobs = wBackup.filter(j => j.status === 'completed' && j.completed_at);
      const lastBackup = completedJobs.length > 0
        ? completedJobs.reduce((latest, j) =>
            !latest || new Date(j.completed_at!) > new Date(latest) ? j.completed_at! : latest, '' as string)
        : null;

      let avgDurationSec = 0;
      if (completedJobs.length > 0) {
        const totalSec = completedJobs.reduce((sum, j) => {
          if (j.started_at && j.completed_at) {
            return sum + (new Date(j.completed_at).getTime() - new Date(j.started_at).getTime()) / 1000;
          }
          return sum;
        }, 0);
        avgDurationSec = totalSec / completedJobs.length;
      }

      result[w] = {
        stats: {
          total: wBackup.length,
          completed: wBackup.filter(j => j.status === 'completed').length,
          failed: wBackup.filter(j => j.status === 'failed').length,
          in_progress: wBackup.filter(j => j.status === 'in_progress').length,
          queued: wBackup.filter(j => j.status === 'queued').length,
          partial: wBackup.filter(j => j.status === 'partial').length,
          lastBackup,
          avgDurationSec,
          totalSize: wBackup.reduce((sum, j) => sum + (j.total_size_bytes || 0), 0),
        },
        backupJobs: wBackup,
        restoreJobs: wRestore,
      };
    }

    return result;
  }, [allBackupJobs, allRestoreJobs]);

  // Total stats across all workloads
  const totalStats = useMemo(() => {
    const all = allBackupJobs?.items ?? [];
    return {
      total: all.length,
      completed: all.filter(j => j.status === 'completed').length,
      failed: all.filter(j => j.status === 'failed').length,
      in_progress: all.filter(j => j.status === 'in_progress').length,
      queued: all.filter(j => j.status === 'queued').length,
    };
  }, [allBackupJobs]);

  const toggleWorkload = (w: Workload) => {
    setExpandedWorkload(expandedWorkload === w ? null : w);
  };

  const heroStats: HeroStat[] = [
    {
      label: 'Total Jobs',
      value: totalStats.total,
      subtitle: 'All workloads',
      icon: Briefcase,
      color: 'blue',
    },
    {
      label: 'Completed',
      value: totalStats.completed,
      subtitle: totalStats.total > 0 ? `${Math.round(totalStats.completed / totalStats.total * 100)}% success rate` : 'No jobs yet',
      icon: CheckCircle2,
      color: 'green',
    },
    {
      label: 'Running',
      value: totalStats.in_progress + totalStats.queued,
      subtitle: `${totalStats.in_progress} active, ${totalStats.queued} queued`,
      icon: PlayCircle,
      color: totalStats.in_progress > 0 ? 'blue' : 'gray',
    },
    {
      label: 'Failed',
      value: totalStats.failed,
      subtitle: failedSummary ? `${failedSummary.ready_now} ready to retry` : 'No failures',
      icon: AlertTriangle,
      color: totalStats.failed > 0 ? 'red' : 'gray',
    },
  ];

  return (
    <div>
      {/* Breadcrumb + Search */}
      <Breadcrumb
        items={[
          { label: getActivePlatformLabel(), path: '/' },
          { label: 'Jobs' },
        ]}
      />

      {/* Page Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-50">
            <Briefcase className="w-6 h-6 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Jobs</h1>
            <p className="text-xs text-gray-500">
              {totalStats.total} total
              {totalStats.in_progress > 0 && <span className="text-blue-600 ml-2">{totalStats.in_progress} running</span>}
              {totalStats.failed > 0 && <span className="text-red-600 ml-2">{totalStats.failed} failed</span>}
            </p>
          </div>
        </div>
        {failedSummary && failedSummary.total_failed > 0 && (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-red-500/10 border border-red-200 rounded-lg px-3 py-2 text-sm">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <span className="text-red-400 font-medium">{failedSummary.total_failed} failed</span>
              <span className="text-red-500">({failedSummary.ready_now} ready to retry)</span>
            </div>
            <button
              onClick={() => retryAllMutation.mutate()}
              disabled={retryAllMutation.isPending || failedSummary.ready_now === 0}
              className="px-4 py-2 bg-orange-600 text-white rounded-lg text-sm font-medium hover:bg-orange-700 flex items-center gap-2 disabled:opacity-50"
            >
              {retryAllMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
              {retryAllMutation.isPending ? 'Retrying...' : 'Retry All'}
            </button>
          </div>
        )}
      </div>

      {/* Retry message */}
      {retryMsg && (
        <div className={`rounded-lg p-3 mb-4 text-sm ${retryMsg.includes('failed') ? 'bg-red-500/10 border border-red-200 text-red-400' : 'bg-green-500/10 border border-green-200 text-green-400'}`}>
          {retryMsg}
        </div>
      )}

      {/* Hero Stats */}
      <HeroSummaryBar stats={heroStats} />

      {/* View Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit mb-6">
        <button
          onClick={() => setActiveTab('swimlanes')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'swimlanes' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          By Workload
        </button>
        <button
          onClick={() => setActiveTab('all')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'all' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          All Jobs
        </button>
      </div>

      {activeTab === 'swimlanes' ? (
        <>
          {/* Workload Swimlanes */}
          <div className="space-y-4">
            {WORKLOADS.map(w => (
              <WorkloadSwimlane
                key={w}
                workload={w}
                stats={workloadData[w]?.stats ?? { total: 0, completed: 0, failed: 0, in_progress: 0, queued: 0, partial: 0, lastBackup: null, avgDurationSec: 0, totalSize: 0 }}
                backupJobs={workloadData[w]?.backupJobs ?? []}
                restoreJobs={workloadData[w]?.restoreJobs ?? []}
                isExpanded={expandedWorkload === w}
                onToggle={() => toggleWorkload(w)}
                loadingBackup={loadingBackup}
                loadingRestore={loadingRestore}
                onRetryJob={(id) => retryJobMutation.mutate(id)}
                isRetrying={retryJobMutation.isPending}
              />
            ))}
          </div>

          {/* Loading state */}
          {loadingBackup && !allBackupJobs && (
            <div className="flex items-center justify-center py-12 text-gray-400">
              <Loader2 className="w-6 h-6 animate-spin mr-2" />
              Loading jobs...
            </div>
          )}
        </>
      ) : (
        /* All Jobs DataTable — server-side paginated, sorted, filtered */
        <DataTable<BackupJob>
          queryKey="all-backup-jobs"
          endpoint="/jobs/backup"
          columns={allJobsColumns}
          searchable
          searchPlaceholder="Search jobs by workload, status, error..."
          filters={[workloadFilter, statusFilter]}
          defaultSortBy="created_at"
          defaultSortOrder="desc"
          defaultPageSize={25}
          emptyMessage="No backup jobs found"
          refetchInterval={5000}
          actions={(row) =>
            row.status === 'failed' ? (
              <button
                onClick={() => retryJobMutation.mutate(row.id)}
                disabled={retryJobMutation.isPending}
                className="px-2.5 py-1 border border-orange-200 text-orange-700 rounded-lg text-xs font-medium hover:bg-orange-50 flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" /> Retry
              </button>
            ) : null
          }
        />
      )}
    </div>
  );
}
