import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Download, AlertTriangle, Shield, Loader2, X, CheckCircle } from 'lucide-react';
import { api } from '../api/client';

interface RestoreDialogProps {
  objectId: number;
  objectName: string;
  workload: string;  // exchange, onedrive, sharepoint, teams, entra_id
  snapshotId: number;
  snapshotDate?: string;
  itemCount?: number;
  onClose: () => void;
}

const WORKLOAD_ENDPOINTS: Record<string, string> = {
  exchange: '/exchange/mailboxes',
  onedrive: '/onedrive/accounts',
  sharepoint: '/sharepoint/sites',
  teams: '/teams/teams',
  entra_id: '/entra-id',
};

export default function RestoreDialog({
  objectId, objectName, workload, snapshotId, snapshotDate, itemCount, onClose,
}: RestoreDialogProps) {
  const [restoreType, setRestoreType] = useState<string>('full_inplace');
  const [confirmed, setConfirmed] = useState(false);
  const qc = useQueryClient();

  const restoreMutation = useMutation({
    mutationFn: async () => {
      const endpoint = workload === 'entra_id'
        ? `/entra-id/restore?tenant_id=${objectId}`
        : `${WORKLOAD_ENDPOINTS[workload]}/${objectId}/restore`;
      return api.post(endpoint, {
        snapshot_id: snapshotId,
        restore_type: restoreType,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['restore-jobs'] });
    },
  });

  const result = restoreMutation.data as any;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-card rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-green-600 to-emerald-600 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-foreground">
            <Download className="w-5 h-5" />
            <h3 className="font-semibold text-lg">Restore Data</h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* Success */}
          {restoreMutation.isSuccess && (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center space-y-2">
              <CheckCircle className="w-10 h-10 text-green-500 mx-auto" />
              <p className="font-semibold text-green-800">Restore {result?.status === 'queued' ? 'Queued' : 'Complete'}</p>
              <p className="text-sm text-green-600">
                {result?.items_restored != null ? `${result.items_restored} items restored` : 'Job queued for processing'}
              </p>
              <p className="text-xs text-green-500">Job ID: {result?.restore_job_id}</p>
              <button onClick={onClose} className="mt-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">
                Close
              </button>
            </div>
          )}

          {/* Error */}
          {restoreMutation.isError && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center space-y-2">
              <AlertTriangle className="w-10 h-10 text-red-500 mx-auto" />
              <p className="font-semibold text-red-800">Restore Failed</p>
              <p className="text-sm text-red-600">{(restoreMutation.error as any)?.message || 'Unknown error'}</p>
              <button onClick={() => restoreMutation.reset()} className="mt-2 px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700">
                Try Again
              </button>
            </div>
          )}

          {/* Form (only show before submit) */}
          {!restoreMutation.isSuccess && !restoreMutation.isError && (
            <>
              {/* Object info */}
              <div className="bg-muted/50 rounded-xl p-4">
                <p className="text-sm font-medium text-foreground">{objectName}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Snapshot: {snapshotDate?.slice(0, 16) || `#${snapshotId}`}
                  {itemCount ? ` • ${itemCount} items` : ''}
                </p>
              </div>

              {/* Restore type */}
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-2">Restore Type</label>
                <div className="space-y-2">
                  {[
                    { value: 'full_inplace', label: 'Full Restore (In-Place)', desc: 'Restore all items to original location' },
                    { value: 'item_level', label: 'Item-Level Restore', desc: 'Restore specific items only' },
                    ...(workload !== 'entra_id' ? [
                      { value: 'cross_user', label: 'Cross-User Restore', desc: 'Restore to a different user/location' },
                    ] : []),
                  ].map(opt => (
                    <label key={opt.value} className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                      restoreType === opt.value ? 'border-green-400 bg-green-50' : 'border-border hover:border-green-200'
                    }`}>
                      <input
                        type="radio" name="restoreType" value={opt.value}
                        checked={restoreType === opt.value}
                        onChange={() => setRestoreType(opt.value)}
                        className="mt-0.5"
                      />
                      <div>
                        <p className="text-sm font-medium text-foreground">{opt.label}</p>
                        <p className="text-xs text-muted-foreground">{opt.desc}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Malware scan notice */}
              <div className="flex items-start gap-2 bg-blue-50 border border-blue-100 rounded-lg p-3">
                <Shield className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-blue-700">
                  Malware scan will run automatically before restore. If threats are detected, the restore will be blocked.
                </p>
              </div>

              {/* Confirmation */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} className="rounded" />
                <span className="text-sm text-muted-foreground">I confirm I want to restore this data</span>
              </label>

              {/* Actions */}
              <div className="flex gap-3">
                <button onClick={onClose} className="flex-1 px-4 py-2.5 border border-border rounded-xl text-sm font-medium text-muted-foreground hover:bg-muted/50">
                  Cancel
                </button>
                <button
                  onClick={() => restoreMutation.mutate()}
                  disabled={!confirmed || restoreMutation.isPending}
                  className="flex-1 px-4 py-2.5 bg-green-600 text-white rounded-xl text-sm font-semibold hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {restoreMutation.isPending ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Restoring...</>
                  ) : (
                    <><Download className="w-4 h-4" /> Restore Now</>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
