import { ChevronDown, ChevronRight, CheckCircle2, XCircle, Loader2, Clock, Mail, HardDrive, Globe, Activity, RotateCcw } from 'lucide-react';
import StatusBadge from '../StatusBadge';
import { formatSize, formatDuration } from '../../utils/format';
import type { BackupJob, RestoreJob } from '../../types';

const WorkloadIcon = ({ type }: { type: string }) => {
  switch (type) {
    case 'exchange': return <Mail className="w-4 h-4 text-blue-500" />;
    case 'onedrive': return <HardDrive className="w-4 h-4 text-purple-500" />;
    case 'sharepoint': return <Globe className="w-4 h-4 text-green-500" />;
    default: return <Activity className="w-4 h-4 text-gray-500" />;
  }
};

const ObjectStatusIcon = ({ status }: { status: string }) => {
  switch (status) {
    case 'completed': return <CheckCircle2 className="w-4 h-4 text-green-500" />;
    case 'failed': return <XCircle className="w-4 h-4 text-red-500" />;
    case 'in_progress': return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
    default: return <Clock className="w-4 h-4 text-gray-400" />;
  }
};

interface JobTableProps {
  jobs: BackupJob[] | RestoreJob[];
  type: 'backup' | 'restore';
  isLoading: boolean;
  expandedJob: number | null;
  onToggleExpand: (id: number) => void;
  onRetry?: (id: number) => void;
  isRetrying?: boolean;
  showWorkloadColumn?: boolean;
}

export default function JobTable({
  jobs, type, isLoading, expandedJob, onToggleExpand, onRetry, isRetrying, showWorkloadColumn = false,
}: JobTableProps) {
  if (type === 'restore') {
    const restoreJobs = jobs as RestoreJob[];
    return (
      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-500">ID</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Type</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Started</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Duration</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Items Restored</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Failed</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Error</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {restoreJobs.map(j => (
              <tr key={j.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">#{j.id}</td>
                <td className="px-4 py-3 capitalize">{j.restore_type.replace(/_/g, ' ')}</td>
                <td className="px-4 py-3"><StatusBadge status={j.status} /></td>
                <td className="px-4 py-3 text-gray-500">{j.started_at?.slice(0, 16) || '—'}</td>
                <td className="px-4 py-3 text-gray-500">{formatDuration(j.started_at, j.completed_at)}</td>
                <td className="px-4 py-3">{j.items_restored}</td>
                <td className="px-4 py-3 text-red-500">{j.items_failed || 0}</td>
                <td className="px-4 py-3 text-red-500 text-xs max-w-[200px] truncate">{j.error_message || '—'}</td>
              </tr>
            ))}
            {isLoading && <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>}
            {!isLoading && !restoreJobs.length && <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No restore jobs found</td></tr>}
          </tbody>
        </table>
      </div>
    );
  }

  const backupJobs = jobs as BackupJob[];
  return (
    <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-500 w-8"></th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">ID</th>
            {showWorkloadColumn && <th className="px-4 py-3 text-left font-medium text-gray-500">Workload</th>}
            <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Progress</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Items</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Size</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Started</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Duration</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Retry</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {backupJobs.map((j) => {
            const progress = j.progress_details;
            const summary = progress?.summary;
            const hasProgress = !!progress?.objects && Object.keys(progress.objects).length > 0;
            const isExpanded = expandedJob === j.id;
            const colCount = showWorkloadColumn ? 10 : 9;

            return (
              <tbody key={j.id}>
                <tr className={`hover:bg-gray-50 ${hasProgress ? 'cursor-pointer' : ''}`}
                    onClick={() => hasProgress && onToggleExpand(j.id)}>
                  <td className="px-4 py-3">
                    {hasProgress ? (
                      isExpanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />
                    ) : null}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">#{j.id}</td>
                  {showWorkloadColumn && (
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1.5 capitalize">
                        <WorkloadIcon type={j.workload_type} />
                        {j.workload_type}
                      </span>
                    </td>
                  )}
                  <td className="px-4 py-3"><StatusBadge status={j.status} /></td>
                  <td className="px-4 py-3">
                    {j.objects_total > 0 ? (
                      <div className="flex items-center gap-2">
                        <div className="flex-1 max-w-[120px] bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full transition-all ${j.objects_failed > 0 ? 'bg-orange-500' : 'bg-green-500'}`}
                            style={{ width: `${Math.round(((j.objects_processed + j.objects_failed) / j.objects_total) * 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-500">
                          {j.objects_processed + j.objects_failed}/{j.objects_total}
                          {j.objects_failed > 0 && <span className="text-red-500 ml-1">({j.objects_failed} failed)</span>}
                        </span>
                      </div>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">{summary?.total_items || j.total_items || '—'}</td>
                  <td className="px-4 py-3">{formatSize(summary?.total_size_bytes || j.total_size_bytes)}</td>
                  <td className="px-4 py-3 text-gray-500">{j.started_at?.slice(0, 16) || '—'}</td>
                  <td className="px-4 py-3 text-gray-500">{formatDuration(j.started_at, j.completed_at)}</td>
                  <td className="px-4 py-3">
                    {(j.status === 'failed' || j.status === 'partial') && onRetry ? (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => { e.stopPropagation(); onRetry(j.id); }}
                          disabled={isRetrying}
                          className="text-orange-600 hover:text-orange-800 text-xs font-medium flex items-center gap-1"
                        >
                          <RotateCcw className="w-3 h-3" /> Retry
                        </button>
                        {j.retry_count > 0 && (
                          <span className="text-xs text-gray-400">({j.retry_count}/{j.max_retries})</span>
                        )}
                      </div>
                    ) : j.retry_count > 0 ? (
                      <span className="text-xs text-gray-400">retried {j.retry_count}x</span>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                </tr>
                {isExpanded && hasProgress && (
                  <tr>
                    <td colSpan={colCount} className="px-0 py-0">
                      <div className="bg-gray-50 border-t border-b px-8 py-3">
                        <div className="text-xs font-semibold text-gray-500 uppercase mb-2">Per-Object Progress</div>
                        <div className="space-y-1.5">
                          {Object.entries(progress.objects).map(([objId, obj]: [string, any]) => (
                            <div key={objId} className="flex items-center gap-3 py-1.5 px-3 bg-white rounded-lg border text-sm">
                              <ObjectStatusIcon status={obj.status} />
                              <div className="flex-1 min-w-0">
                                <span className="font-medium truncate block">{obj.name}</span>
                                {obj.email && <span className="text-gray-400 text-xs">{obj.email}</span>}
                              </div>
                              <div className="flex items-center gap-4 text-xs text-gray-500">
                                {obj.detail && <span className="italic">{obj.detail}</span>}
                                {obj.item_count !== undefined && (
                                  <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full font-medium">
                                    {obj.item_count} items
                                  </span>
                                )}
                                {obj.size_bytes !== undefined && (
                                  <span className="bg-purple-50 text-purple-700 px-2 py-0.5 rounded-full font-medium">
                                    {formatSize(obj.size_bytes)}
                                  </span>
                                )}
                                {obj.error && (
                                  <span className="bg-red-50 text-red-700 px-2 py-0.5 rounded-full font-medium max-w-[300px] truncate" title={obj.error}>
                                    {obj.error}
                                  </span>
                                )}
                              </div>
                              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                                obj.status === 'completed' ? 'bg-green-100 text-green-700' :
                                obj.status === 'failed' ? 'bg-red-100 text-red-700' :
                                obj.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                                'bg-gray-100 text-gray-500'
                              }`}>
                                {obj.status.replace('_', ' ')}
                              </span>
                            </div>
                          ))}
                        </div>
                        {j.error_message && (
                          <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                            {j.error_message}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            );
          })}
          {isLoading && <tr><td colSpan={showWorkloadColumn ? 10 : 9} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>}
          {!isLoading && !backupJobs.length && <tr><td colSpan={showWorkloadColumn ? 10 : 9} className="px-4 py-8 text-center text-gray-400">No backup jobs found</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
