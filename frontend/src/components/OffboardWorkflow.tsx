import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  AlertTriangle, CheckCircle, XCircle, Shield,
  Clock, Lock, Loader2, X, ArrowRight, Download, RotateCcw,
} from 'lucide-react';
import { api } from '../api/client';

interface OffboardWorkflowProps {
  tenantId: number;
  tenantName: string;
  onClose: () => void;
  onComplete: () => void;
}

type Step = 'review' | 'retention' | 'confirm' | 'done';

export default function OffboardWorkflow({ tenantId, tenantName, onClose, onComplete }: OffboardWorkflowProps) {
  const [step, setStep] = useState<Step>('review');

  const { data: preCheck, isLoading } = useQuery({
    queryKey: ['offboard-precheck', tenantId],
    queryFn: () => api.get<any>(`/msp/offboard/${tenantId}/pre-check`),
  });

  const offboardMutation = useMutation({
    mutationFn: () => api.post<any>(`/msp/offboard/${tenantId}?confirm=true`),
    onSuccess: () => { setStep('done'); },
  });

  const inventory = preCheck?.data_inventory || preCheck?.data_inventory || {};
  const timeline = preCheck?.retention_timeline || [];
  const blockers = preCheck?.blockers || [];
  const canOffboard = preCheck?.can_offboard !== false;
  const postOffboard = preCheck?.post_offboard || {};

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 rounded-2xl border border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gray-900 border-b border-gray-700 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-amber-500/10 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Offboard Client</h2>
              <p className="text-xs text-gray-400">{tenantName}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-gray-500 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        {/* Step indicators */}
        <div className="px-6 py-3 border-b border-gray-800 flex items-center justify-center gap-2">
          {(['review', 'retention', 'confirm', 'done'] as Step[]).map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                step === s ? 'bg-blue-600 text-white' :
                (['review', 'retention', 'confirm', 'done'].indexOf(step) > i) ? 'bg-green-500 text-white' :
                'bg-gray-800 text-gray-500'
              }`}>{(['review', 'retention', 'confirm', 'done'].indexOf(step) > i) ? <CheckCircle className="w-4 h-4" /> : i + 1}</div>
              <span className={`text-[10px] ${step === s ? 'text-white' : 'text-gray-500'}`}>{s === 'review' ? 'Review' : s === 'retention' ? 'Retention' : s === 'confirm' ? 'Confirm' : 'Done'}</span>
              {i < 3 && <div className={`w-8 h-0.5 ${(['review', 'retention', 'confirm', 'done'].indexOf(step) > i) ? 'bg-green-500' : 'bg-gray-700'}`} />}
            </div>
          ))}
        </div>

        <div className="px-6 py-6">
          {isLoading ? (
            <div className="text-center py-12"><Loader2 className="w-8 h-8 animate-spin text-blue-400 mx-auto" /><p className="text-gray-500 mt-2">Analyzing tenant data...</p></div>
          ) : (
            <>
              {/* Step 1: Review data inventory */}
              {step === 'review' && (
                <div className="space-y-5">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-300 mb-3">Data Inventory</h3>
                    <div className="grid grid-cols-3 gap-3 mb-4">
                      <div className="bg-gray-800 rounded-lg p-3 text-center">
                        <div className="text-xl font-bold text-white">{inventory.total_objects || 0}</div>
                        <div className="text-[10px] text-gray-500">Protected Objects</div>
                      </div>
                      <div className="bg-gray-800 rounded-lg p-3 text-center">
                        <div className="text-xl font-bold text-white">{inventory.total_snapshots || 0}</div>
                        <div className="text-[10px] text-gray-500">Backup Snapshots</div>
                      </div>
                      <div className="bg-gray-800 rounded-lg p-3 text-center">
                        <div className="text-xl font-bold text-white">{inventory.total_storage_gb || 0} GB</div>
                        <div className="text-[10px] text-gray-500">Storage Used</div>
                      </div>
                    </div>
                    {(inventory.workloads || []).map((wl: any) => (
                      <div key={wl.workload} className="flex items-center justify-between py-2 px-3 bg-gray-800/50 rounded-lg mb-1 text-xs">
                        <span className="text-gray-300 capitalize font-medium">{wl.workload}</span>
                        <span className="text-gray-500">{wl.objects} objects | {wl.snapshots} snapshots | {wl.storage_gb} GB</span>
                      </div>
                    ))}
                  </div>

                  {preCheck?.active_jobs > 0 && (
                    <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 flex items-start gap-2">
                      <XCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                      <div className="text-xs text-red-300">
                        <strong>{preCheck.active_jobs} active backup job(s)</strong> — wait for completion before offboarding.
                      </div>
                    </div>
                  )}

                  {blockers.filter((b: any) => b.type === 'worm_lock').map((b: any, i: number) => (
                    <div key={i} className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 flex items-start gap-2">
                      <Lock className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                      <div className="text-xs text-amber-300">{b.message} — {b.action}</div>
                    </div>
                  ))}

                  <button onClick={() => setStep('retention')} disabled={!canOffboard}
                    className="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-40 flex items-center justify-center gap-2">
                    Review Retention Timeline <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              )}

              {/* Step 2: Retention timeline */}
              {step === 'retention' && (
                <div className="space-y-5">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-300 mb-3">Data Retention Timeline</h3>
                    <p className="text-xs text-gray-500 mb-4">After offboarding, backup data is retained per SLA policy. No data is immediately deleted.</p>

                    {timeline.length > 0 ? timeline.map((rt: any, i: number) => (
                      <div key={i} className="bg-gray-800 rounded-lg p-4 mb-2 border border-gray-700">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4 text-blue-400" />
                            <span className="text-sm font-medium text-white">{rt.policy_name}</span>
                            {rt.worm_enabled && <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-300">WORM</span>}
                          </div>
                          <span className="text-xs text-gray-400">{rt.objects_covered} objects</span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-gray-400">Retention: {rt.retention_days} days</span>
                          <span className="text-gray-300 font-medium">Data purge: {rt.data_purge_date}</span>
                        </div>
                        <div className="mt-2 w-full bg-gray-700 rounded-full h-1.5">
                          <div className="bg-blue-500 rounded-full h-1.5" style={{ width: '100%' }} />
                        </div>
                        <div className="flex justify-between text-[9px] text-gray-500 mt-1">
                          <span>Today (offboard)</span>
                          <span>{rt.data_purge_date} (purge eligible)</span>
                        </div>
                      </div>
                    )) : (
                      <div className="text-center py-4 text-gray-500 text-xs">No SLA policies — default 30-day retention applies</div>
                    )}
                  </div>

                  <div className="bg-gray-800/50 rounded-lg p-3 space-y-2">
                    <div className="text-xs font-medium text-gray-300 mb-2">After offboarding, you can still:</div>
                    {[
                      { icon: Shield, text: 'View and browse existing backups', ok: postOffboard.backups_accessible },
                      { icon: Download, text: 'Export data during retention period', ok: postOffboard.data_export_available },
                      { icon: RotateCcw, text: 'Reactivate the tenant if needed', ok: postOffboard.reactivation_possible },
                    ].map((item, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <CheckCircle className="w-3.5 h-3.5 text-green-400 shrink-0" />
                        <span className="text-gray-400">{item.text}</span>
                      </div>
                    ))}
                    <div className="flex items-center gap-2 text-xs mt-1">
                      <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                      <span className="text-gray-400">New backups will be stopped immediately</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <button onClick={() => setStep('review')} className="px-4 py-2 text-gray-400 text-sm hover:text-white">Back</button>
                    <button onClick={() => setStep('confirm')}
                      className="flex-1 py-2.5 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-500 flex items-center justify-center gap-2">
                      Proceed to Confirmation <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}

              {/* Step 3: Final confirmation */}
              {step === 'confirm' && (
                <div className="space-y-5">
                  <div className="bg-red-500/5 border border-red-500/30 rounded-xl p-6 text-center">
                    <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-3" />
                    <h3 className="text-lg font-bold text-white mb-2">Confirm Offboard</h3>
                    <p className="text-sm text-gray-400">
                      You are about to deactivate <strong className="text-white">{tenantName}</strong>.
                    </p>
                    <div className="mt-4 text-left max-w-sm mx-auto space-y-2 text-xs">
                      <div className="flex items-start gap-2 text-gray-300">
                        <span className="text-amber-400 mt-0.5">1.</span> All scheduled backups will stop immediately
                      </div>
                      <div className="flex items-start gap-2 text-gray-300">
                        <span className="text-amber-400 mt-0.5">2.</span> Existing backup data retained per SLA ({timeline[0]?.retention_days || 30}+ days)
                      </div>
                      <div className="flex items-start gap-2 text-gray-300">
                        <span className="text-amber-400 mt-0.5">3.</span> You can still access and export data during retention
                      </div>
                      <div className="flex items-start gap-2 text-gray-300">
                        <span className="text-amber-400 mt-0.5">4.</span> Tenant can be reactivated if needed
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <button onClick={() => setStep('retention')} className="px-4 py-2 text-gray-400 text-sm hover:text-white">Back</button>
                    <button onClick={() => offboardMutation.mutate()} disabled={offboardMutation.isPending}
                      className="flex-1 py-3 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-500 disabled:opacity-50 flex items-center justify-center gap-2">
                      {offboardMutation.isPending ? <><Loader2 className="w-4 h-4 animate-spin" /> Offboarding...</> : <><AlertTriangle className="w-4 h-4" /> Offboard {tenantName}</>}
                    </button>
                  </div>
                </div>
              )}

              {/* Step 4: Done */}
              {step === 'done' && (
                <div className="space-y-5 text-center">
                  <div className="w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center mx-auto">
                    <CheckCircle className="w-8 h-8 text-green-400" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white">{tenantName} Offboarded</h3>
                    <p className="text-sm text-gray-400 mt-1">Backups stopped. Data retained per SLA policies.</p>
                  </div>

                  <div className="bg-gray-800 rounded-xl p-4 text-left space-y-2">
                    <div className="text-xs font-medium text-gray-300 mb-2">What happens next:</div>
                    {(offboardMutation.data?.what_happened || [
                      'Tenant status set to INACTIVE',
                      'Scheduled backups stopped',
                      'Existing data preserved per SLA retention',
                      'Connector credentials retained for reactivation',
                    ]).map((item: string, i: number) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <CheckCircle className="w-3.5 h-3.5 text-green-400 shrink-0" />
                        <span className="text-gray-400">{item}</span>
                      </div>
                    ))}
                  </div>

                  {offboardMutation.data?.retention && (
                    <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 text-xs text-blue-300">
                      Data accessible until <strong>{offboardMutation.data.retention.data_purge_date}</strong> ({offboardMutation.data.retention.max_retention_days} days)
                    </div>
                  )}

                  <button onClick={() => { onComplete(); onClose(); }}
                    className="px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500">
                    Return to MSP Dashboard
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
