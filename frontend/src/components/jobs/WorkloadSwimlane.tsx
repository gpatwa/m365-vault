import { useState, useEffect, useMemo } from 'react';
import { ChevronRight, Mail, HardDrive, Globe, Shield, X, CheckCircle2, XCircle, Loader2, Clock } from 'lucide-react';
import StatusFilterBar from './StatusFilterBar';
import JobTable from './JobTable';
import { formatSize, timeAgo } from '../../utils/format';
import type { BackupJob, RestoreJob } from '../../types';

type Workload = 'exchange' | 'onedrive' | 'sharepoint' | 'entra_id';

const WORKLOAD_CONFIG: Record<Workload, {
  label: string;
  icon: typeof Mail;
  color: string;
  bgColor: string;
  borderColor: string;
  barColor: string;
  ringColor: string;
}> = {
  exchange: {
    label: 'Exchange',
    icon: Mail,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    barColor: 'bg-blue-500',
    ringColor: 'ring-blue-400',
  },
  onedrive: {
    label: 'OneDrive',
    icon: HardDrive,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    barColor: 'bg-purple-500',
    ringColor: 'ring-purple-400',
  },
  sharepoint: {
    label: 'SharePoint',
    icon: Globe,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    barColor: 'bg-green-500',
    ringColor: 'ring-green-400',
  },
  entra_id: {
    label: 'Entra ID',
    icon: Shield,
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    barColor: 'bg-amber-500',
    ringColor: 'ring-amber-400',
  },
};

export interface WorkloadStats {
  total: number;
  completed: number;
  failed: number;
  in_progress: number;
  queued: number;
  partial: number;
  lastBackup: string | null;
  avgDurationSec: number;
  totalSize: number;
}

interface WorkloadSwimlaneProps {
  workload: Workload;
  stats: WorkloadStats;
  backupJobs: BackupJob[];
  restoreJobs: RestoreJob[];
  isExpanded: boolean;
  onToggle: () => void;
  loadingBackup: boolean;
  loadingRestore: boolean;
  onRetryJob: (id: number) => void;
  isRetrying: boolean;
}

export default function WorkloadSwimlane({
  workload, stats, backupJobs, restoreJobs,
  isExpanded, onToggle, loadingBackup, loadingRestore,
  onRetryJob, isRetrying,
}: WorkloadSwimlaneProps) {
  const config = WORKLOAD_CONFIG[workload];
  const Icon = config.icon;

  const [tab, setTab] = useState<'backup' | 'restore'>('backup');
  const [statusFilter, setStatusFilter] = useState('');
  const [expandedJob, setExpandedJob] = useState<number | null>(null);

  // Reset state when collapsing
  useEffect(() => {
    if (!isExpanded) {
      setStatusFilter('');
      setExpandedJob(null);
      setTab('backup');
    }
  }, [isExpanded]);

  // Filter jobs by status
  const filteredBackupJobs = useMemo(() => {
    if (!statusFilter) return backupJobs;
    return backupJobs.filter(j => j.status === statusFilter);
  }, [backupJobs, statusFilter]);

  const filteredRestoreJobs = useMemo(() => {
    if (!statusFilter) return restoreJobs;
    return restoreJobs.filter(j => j.status === statusFilter);
  }, [restoreJobs, statusFilter]);

  // Status counts for filter bar
  const statusCounts = useMemo(() => {
    const jobs = tab === 'backup' ? backupJobs : restoreJobs;
    return {
      all: jobs.length,
      queued: jobs.filter(j => j.status === 'queued').length,
      in_progress: jobs.filter(j => j.status === 'in_progress').length,
      completed: jobs.filter(j => j.status === 'completed').length,
      failed: jobs.filter(j => j.status === 'failed').length,
      partial: jobs.filter(j => j.status === 'partial').length,
    };
  }, [backupJobs, restoreJobs, tab]);

  // Progress bar segments
  const progressPercent = stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;
  const failedPercent = stats.total > 0 ? Math.round((stats.failed / stats.total) * 100) : 0;
  const activePercent = stats.total > 0 ? Math.round((stats.in_progress / stats.total) * 100) : 0;

  const formatAvgDuration = (sec: number) => {
    if (!sec) return '—';
    if (sec < 60) return `${Math.round(sec)}s`;
    return `${Math.floor(sec / 60)}m ${Math.round(sec % 60)}s`;
  };

  return (
    <div className={`rounded-xl border transition-all duration-200 ${
      isExpanded
        ? `${config.borderColor} ring-2 ${config.ringColor} shadow-md`
        : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
    }`}>
      {/* Header — always visible */}
      <div
        className={`px-5 py-4 cursor-pointer select-none ${isExpanded ? config.bgColor : 'bg-white hover:bg-gray-50'} rounded-t-xl ${!isExpanded ? 'rounded-b-xl' : ''}`}
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          {/* Left: Icon + Name */}
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${config.bgColor}`}>
              <Icon className={`w-5 h-5 ${config.color}`} />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">{config.label}</h3>
              <span className="text-xs text-gray-500">{stats.total} jobs</span>
            </div>
          </div>

          {/* Center: Status badges */}
          <div className="flex items-center gap-3">
            {stats.completed > 0 && (
              <div className="flex items-center gap-1 text-xs">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                <span className="font-medium text-green-700">{stats.completed}</span>
              </div>
            )}
            {stats.failed > 0 && (
              <div className="flex items-center gap-1 text-xs">
                <XCircle className="w-3.5 h-3.5 text-red-500" />
                <span className="font-medium text-red-700">{stats.failed}</span>
              </div>
            )}
            {stats.in_progress > 0 && (
              <div className="flex items-center gap-1 text-xs">
                <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin" />
                <span className="font-medium text-blue-700">{stats.in_progress}</span>
              </div>
            )}
            {stats.queued > 0 && (
              <div className="flex items-center gap-1 text-xs">
                <Clock className="w-3.5 h-3.5 text-yellow-500" />
                <span className="font-medium text-yellow-700">{stats.queued}</span>
              </div>
            )}
          </div>

          {/* Right: Chevron / Close */}
          <div className="flex items-center gap-2">
            {isExpanded ? (
              <button
                onClick={(e) => { e.stopPropagation(); onToggle(); }}
                className="p-1 hover:bg-white rounded-lg transition-colors"
              >
                <X className="w-4 h-4 text-gray-500" />
              </button>
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-3 w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div className="h-full flex">
            {progressPercent > 0 && (
              <div className="bg-green-500 h-full transition-all" style={{ width: `${progressPercent}%` }} />
            )}
            {activePercent > 0 && (
              <div className="bg-blue-500 h-full transition-all" style={{ width: `${activePercent}%` }} />
            )}
            {failedPercent > 0 && (
              <div className="bg-red-500 h-full transition-all" style={{ width: `${failedPercent}%` }} />
            )}
          </div>
        </div>

        {/* Metrics row */}
        <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
          <span>Last: <strong className="text-gray-700">{timeAgo(stats.lastBackup)}</strong></span>
          <span className="text-gray-300">|</span>
          <span>Avg: <strong className="text-gray-700">{formatAvgDuration(stats.avgDurationSec)}</strong></span>
          <span className="text-gray-300">|</span>
          <span>Size: <strong className="text-gray-700">{formatSize(stats.totalSize)}</strong></span>
          {stats.total > 0 && (
            <>
              <span className="text-gray-300">|</span>
              <span>Success: <strong className={progressPercent >= 90 ? 'text-green-700' : progressPercent >= 70 ? 'text-yellow-700' : 'text-red-700'}>{progressPercent}%</strong></span>
            </>
          )}
        </div>
      </div>

      {/* Expanded: Job table */}
      {isExpanded && (
        <div className="border-t px-5 py-4 bg-white rounded-b-xl">
          {/* Tabs */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
              <button
                onClick={() => { setTab('backup'); setStatusFilter(''); setExpandedJob(null); }}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  tab === 'backup' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Backup Jobs ({backupJobs.length})
              </button>
              <button
                onClick={() => { setTab('restore'); setStatusFilter(''); setExpandedJob(null); }}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  tab === 'restore' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Restore Jobs ({restoreJobs.length})
              </button>
            </div>
          </div>

          {/* Status filter */}
          <div className="mb-4">
            <StatusFilterBar value={statusFilter} onChange={setStatusFilter} counts={statusCounts} />
          </div>

          {/* Table */}
          <JobTable
            jobs={tab === 'backup' ? filteredBackupJobs : filteredRestoreJobs}
            type={tab}
            isLoading={tab === 'backup' ? loadingBackup : loadingRestore}
            expandedJob={expandedJob}
            onToggleExpand={(id) => setExpandedJob(expandedJob === id ? null : id)}
            onRetry={onRetryJob}
            isRetrying={isRetrying}
          />
        </div>
      )}
    </div>
  );
}
