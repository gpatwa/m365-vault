import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Loader2, RotateCcw, Briefcase } from 'lucide-react';
import { api } from '../api/client';
import WorkloadSwimlane from '../components/jobs/WorkloadSwimlane';
import type { WorkloadStats } from '../components/jobs/WorkloadSwimlane';
import type { BackupJob, RestoreJob, PaginatedResponse, FailedJobsSummary } from '../types';

type Workload = 'exchange' | 'onedrive' | 'sharepoint' | 'entra_id';
const WORKLOADS: Workload[] = ['exchange', 'onedrive', 'sharepoint', 'entra_id'];

export default function Jobs() {
  const [expandedWorkload, setExpandedWorkload] = useState<Workload | null>(null);
  const [retryMsg, setRetryMsg] = useState('');
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
      setRetryMsg(`Retry complete — status: ${data.status}, retries: ${data.retry_count}`);
      qc.invalidateQueries({ queryKey: ['backup-jobs-all'] });
      qc.invalidateQueries({ queryKey: ['failed-jobs-summary'] });
      setTimeout(() => setRetryMsg(''), 5000);
    },
    onError: (err: any) => { setRetryMsg(`Retry failed: ${err.message}`); setTimeout(() => setRetryMsg(''), 5000); },
  });

  const retryAllMutation = useMutation({
    mutationFn: () => api.post('/jobs/retry-all-failed'),
    onSuccess: (data: any) => {
      setRetryMsg(`Retried ${data.retried} jobs — ${data.succeeded} succeeded, ${data.still_failed} still failed`);
      qc.invalidateQueries({ queryKey: ['backup-jobs-all'] });
      qc.invalidateQueries({ queryKey: ['failed-jobs-summary'] });
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
      // RestoreJob doesn't have workload_type — show all in each workload for now
      const wRestore = restoreJobs;

      // Find last completed backup time
      const completedJobs = wBackup.filter(j => j.status === 'completed' && j.completed_at);
      const lastBackup = completedJobs.length > 0
        ? completedJobs.reduce((latest, j) =>
            !latest || new Date(j.completed_at!) > new Date(latest) ? j.completed_at! : latest, '' as string)
        : null;

      // Average duration of completed jobs
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
    };
  }, [allBackupJobs]);

  const toggleWorkload = (w: Workload) => {
    setExpandedWorkload(expandedWorkload === w ? null : w);
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-50 rounded-lg">
              <Briefcase className="w-6 h-6 text-indigo-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
              <p className="text-gray-500 text-sm">
                {totalStats.total} total
                {totalStats.in_progress > 0 && <span className="text-blue-600 ml-2">{totalStats.in_progress} running</span>}
                {totalStats.failed > 0 && <span className="text-red-600 ml-2">{totalStats.failed} failed</span>}
              </p>
            </div>
          </div>
        </div>
        {failedSummary && failedSummary.total_failed > 0 && (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <span className="text-red-700 font-medium">{failedSummary.total_failed} failed</span>
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
        <div className={`rounded-lg p-3 mb-4 text-sm ${retryMsg.includes('failed') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-green-50 border border-green-200 text-green-700'}`}>
          {retryMsg}
        </div>
      )}

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
    </div>
  );
}
