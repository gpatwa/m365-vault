import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Shield, ShieldAlert, Clock, CheckCircle, XCircle, AlertTriangle, ArrowRight, PlayCircle, Loader2, BookOpen, RotateCcw, KeyRound } from 'lucide-react';
import { api } from '../api/client';
import { useTenantId } from '../hooks/useTenant';
import { PRIORITY_WORKLOAD_KEYS } from '../config/workloads';

interface ConfidenceScore {
  score: number;
  grade: string;
  label: string;
  color: string;
  factors: Record<string, { score: number; weight: number; detail: string }>;
  recommendations: { priority: string; action: string; detail: string; link?: string; link_label?: string; action_tab?: string }[];
}

interface RPORTOData {
  overall_rpo_compliance: number;
  overall_status: string;
  workloads: {
    workload: string; objects: number; rpo_target_hours: number;
    rpo_compliance_pct: number; rpo_met: number; rpo_violated: number;
    worst_rpo_hours: number; avg_rto_seconds: number; status: string;
  }[];
}

interface Runbook {
  id: string; name: string; severity: string; icon: string;
  description: string; estimated_time: string;
  steps: { order: number; action: string; detail: string }[];
}

interface TestResult {
  total_tested: number; passed: number; failed: number; pass_rate: number;
  results: { object: string; workload: string; status: string; items_tested: number; items_verified: number; errors: string[] }[];
}

const GRADE_COLORS: Record<string, string> = {
  A: 'text-green-600 bg-green-500/10 border-green-500/20',
  B: 'text-blue-600 bg-blue-500/10 border-blue-500/20',
  C: 'text-amber-600 bg-amber-500/10 border-amber-500/20',
  D: 'text-red-600 bg-red-500/10 border-red-500/20',
};

const STATUS_ICONS: Record<string, typeof CheckCircle> = {
  compliant: CheckCircle,
  at_risk: AlertTriangle,
  violated: XCircle,
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'border-red-500/20 bg-red-500/10',
  high: 'border-amber-500/20 bg-amber-500/10',
  medium: 'border-blue-500/20 bg-blue-500/10',
  low: 'border-border bg-muted/50',
};

export default function Recovery() {
  const navigate = useNavigate();
  const tenantId = useTenantId();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<'overview' | 'runbooks' | 'test'>('overview');
  const [expandedRunbook, setExpandedRunbook] = useState<string | null>(null);

  const { data: confidence, isLoading: loadingConfidence } = useQuery({
    queryKey: ['recovery-confidence', tenantId],
    queryFn: () => api.get<ConfidenceScore>(`/recovery/confidence?tenant_id=${tenantId}`),
    enabled: !!tenantId,
  });

  const { data: rpoRto } = useQuery({
    queryKey: ['recovery-rpo-rto', tenantId],
    queryFn: () => api.get<RPORTOData>(`/recovery/rpo-rto?tenant_id=${tenantId}`),
    enabled: !!tenantId,
  });

  const { data: runbooks } = useQuery({
    queryKey: ['recovery-runbooks'],
    queryFn: () => api.get<{ runbooks: Runbook[] }>('/recovery/runbooks'),
  });

  const testMutation = useMutation({
    mutationFn: () => api.post<TestResult>(`/recovery/test-restore?tenant_id=${tenantId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recovery-confidence'] }),
  });

  const tabs = [
    { key: 'overview' as const, label: 'Overview', icon: Shield },
    { key: 'runbooks' as const, label: 'Runbooks', icon: BookOpen },
    { key: 'test' as const, label: 'Test Restore', icon: PlayCircle },
  ];

  if (!tenantId) {
    return <div className="p-8 text-center text-muted-foreground">Connect a tenant to view recovery dashboard.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <RotateCcw className="w-6 h-6 text-green-600" />
            Recovery Dashboard
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Verify recoverability, track RPO/RTO compliance, and prepare for incidents
          </p>
        </div>
        <button
          onClick={() => testMutation.mutate()}
          disabled={testMutation.isPending}
          className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 flex items-center gap-2 disabled:opacity-50"
        >
          {testMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}
          Run Test Restore
        </button>
        <button
          onClick={async () => {
            if (!tenantId) {
              alert('No tenant selected. Please connect a Microsoft 365 tenant first.');
              return;
            }
            try {
              const data: any = await api.get(`/restore-consent/authorize?tenant_id=${tenantId}`);
              if (data.auth_url) {
                window.location.href = data.auth_url;
              } else {
                alert('Failed to generate authorization URL. Please try again.');
              }
            } catch (err: any) {
              if (err?.status === 401 || err?.message?.includes('401')) {
                window.location.href = '/login';
              } else {
                alert(`Restore consent failed: ${err?.message || 'Unknown error'}`);
              }
            }
          }}
          disabled={!tenantId}
          className="px-4 py-2 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <KeyRound className="w-4 h-4" />
          Authorize Live Restore
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium flex items-center gap-2 border-b-2 transition-all ${
              activeTab === tab.key
                ? 'border-green-600 text-green-400'
                : 'border-transparent text-muted-foreground hover:text-muted-foreground'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Overview Tab ── */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Confidence Score + RPO/RTO side by side */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Confidence Score */}
            <div className="bg-card rounded-xl border shadow-sm p-6">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">Recovery Confidence</h3>
              {loadingConfidence ? (
                <div className="flex justify-center py-8"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
              ) : confidence ? (
                <div className="text-center">
                  <div className={`inline-flex items-center justify-center w-24 h-24 rounded-full border-4 ${GRADE_COLORS[confidence.grade] || GRADE_COLORS.C}`}>
                    <div>
                      <p className="text-3xl font-bold">{confidence.score}</p>
                      <p className="text-xs font-medium">{confidence.grade}</p>
                    </div>
                  </div>
                  <p className="text-lg font-semibold mt-3">{confidence.label}</p>

                  {/* Factor bars */}
                  <div className="mt-4 space-y-2 text-left">
                    {Object.entries(confidence.factors).map(([key, factor]) => (
                      <div key={key}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-muted-foreground capitalize">{key.replace('_', ' ')}</span>
                          <span className="font-medium">{factor.score}%</span>
                        </div>
                        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${factor.score >= 80 ? 'bg-green-500/100' : factor.score >= 50 ? 'bg-amber-500/100' : 'bg-red-500/100'}`}
                            style={{ width: `${Math.min(factor.score, 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>

            {/* RPO/RTO Compliance */}
            <div className="lg:col-span-2 bg-card rounded-xl border shadow-sm p-6">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">RPO / RTO Compliance</h3>
              {rpoRto ? (
                <div>
                  <div className="flex items-center gap-3 mb-4">
                    {(() => {
                      const Icon = STATUS_ICONS[rpoRto.overall_status] || AlertTriangle;
                      const color = rpoRto.overall_status === 'compliant' ? 'text-green-600' : rpoRto.overall_status === 'at_risk' ? 'text-amber-600' : 'text-red-600';
                      return <Icon className={`w-5 h-5 ${color}`} />;
                    })()}
                    <span className="text-2xl font-bold">{rpoRto.overall_rpo_compliance}%</span>
                    <span className="text-sm text-muted-foreground">RPO Compliance</span>
                  </div>

                  <div className="space-y-3">
                    {rpoRto.workloads.filter(wl => PRIORITY_WORKLOAD_KEYS.includes(wl.workload)).map(wl => (
                      <div key={wl.workload} className="flex items-center gap-3">
                        <span className="w-24 text-sm font-medium capitalize">{wl.workload.replace('_', ' ')}</span>
                        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${wl.status === 'compliant' ? 'bg-green-500/100' : wl.status === 'at_risk' ? 'bg-amber-500/100' : 'bg-red-500/100'}`}
                            style={{ width: `${wl.rpo_compliance_pct}%` }}
                          />
                        </div>
                        <span className="w-16 text-xs text-right font-medium">{wl.rpo_compliance_pct}%</span>
                        <span className="w-20 text-xs text-muted-foreground">{wl.rpo_met}/{wl.objects} met</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-muted-foreground text-center py-8">Loading RPO/RTO data...</p>
              )}
            </div>
          </div>

          {/* Recommendations */}
          {confidence?.recommendations && confidence.recommendations.length > 0 && (
            <div className="bg-card rounded-xl border shadow-sm p-6">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">Recommendations</h3>
              <div className="space-y-2">
                {confidence.recommendations.map((rec, i) => (
                  <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border ${
                    rec.priority === 'high' ? 'border-red-500/20 bg-red-500/10' :
                    rec.priority === 'medium' ? 'border-amber-500/20 bg-amber-500/10' :
                    'border-border bg-muted/50'
                  }`}>
                    <ArrowRight className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                      rec.priority === 'high' ? 'text-red-500' : rec.priority === 'medium' ? 'text-amber-500' : 'text-muted-foreground'
                    }`} />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-foreground">{rec.action}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{rec.detail}</p>
                    </div>
                    {rec.link && (
                      <button
                        onClick={() => {
                          if (rec.action_tab) setActiveTab(rec.action_tab as any);
                          else navigate(rec.link!);
                        }}
                        className="px-3 py-1 bg-teal-600 text-white text-xs font-medium rounded-lg hover:bg-teal-500 whitespace-nowrap flex-shrink-0"
                      >
                        {rec.link_label || 'Fix →'}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Runbooks Tab ── */}
      {activeTab === 'runbooks' && (
        <div className="space-y-4">
          {runbooks?.runbooks.map(rb => (
            <div key={rb.id} className={`bg-card rounded-xl border shadow-sm overflow-hidden ${SEVERITY_COLORS[rb.severity] || ''}`}>
              <button
                onClick={() => setExpandedRunbook(expandedRunbook === rb.id ? null : rb.id)}
                className="w-full p-5 text-left flex items-center justify-between hover:bg-muted/50/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <ShieldAlert className={`w-5 h-5 ${
                    rb.severity === 'critical' ? 'text-red-500' :
                    rb.severity === 'high' ? 'text-amber-500' :
                    rb.severity === 'medium' ? 'text-blue-500' : 'text-muted-foreground'
                  }`} />
                  <div>
                    <p className="font-semibold text-foreground">{rb.name}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{rb.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {rb.estimated_time}
                  </span>
                  <ArrowRight className={`w-4 h-4 text-muted-foreground transition-transform ${expandedRunbook === rb.id ? 'rotate-90' : ''}`} />
                </div>
              </button>

              {expandedRunbook === rb.id && (
                <div className="px-5 pb-5 border-t">
                  <div className="mt-4 space-y-3">
                    {rb.steps.map(step => (
                      <div key={step.order} className="flex gap-3">
                        <div className="w-7 h-7 rounded-full bg-card border-2 border-green-300 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span className="text-xs font-bold text-green-600">{step.order}</span>
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-foreground">{step.action}</p>
                          <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{step.detail}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Test Restore Tab ── */}
      {activeTab === 'test' && (
        <div className="space-y-4">
          <div className="bg-card rounded-xl border shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-semibold text-foreground">Test Restore Validation</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Verifies that backup data can be decrypted and read — proving recoverability without actually restoring to M365.
                </p>
              </div>
              <button
                onClick={() => testMutation.mutate()}
                disabled={testMutation.isPending}
                className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 flex items-center gap-2 disabled:opacity-50"
              >
                {testMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}
                Run Test
              </button>
            </div>

            {testMutation.data && (() => {
              const data = testMutation.data as TestResult;
              return (
                <div className="space-y-4">
                  {/* Summary */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 text-center">
                      <p className="text-2xl font-bold text-green-400">{data.passed}</p>
                      <p className="text-xs text-green-600">Passed</p>
                    </div>
                    <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-center">
                      <p className="text-2xl font-bold text-red-400">{data.failed}</p>
                      <p className="text-xs text-red-600">Failed</p>
                    </div>
                    <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 text-center">
                      <p className="text-2xl font-bold text-blue-400">{data.pass_rate}%</p>
                      <p className="text-xs text-blue-600">Pass Rate</p>
                    </div>
                  </div>

                  {/* Details */}
                  <div className="space-y-2">
                    {data.results.map((r, i) => (
                      <div key={i} className={`flex items-center justify-between p-3 rounded-lg border ${
                        r.status === 'passed' ? 'border-green-500/20 bg-green-500/10' :
                        r.status === 'partial' ? 'border-amber-500/20 bg-amber-500/10' :
                        'border-red-500/20 bg-red-500/10'
                      }`}>
                        <div className="flex items-center gap-3">
                          {r.status === 'passed' ? <CheckCircle className="w-4 h-4 text-green-500" /> :
                           r.status === 'partial' ? <AlertTriangle className="w-4 h-4 text-amber-500" /> :
                           <XCircle className="w-4 h-4 text-red-500" />}
                          <div>
                            <p className="text-sm font-medium">{r.object}</p>
                            <p className="text-xs text-muted-foreground capitalize">{r.workload}</p>
                          </div>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {r.items_verified}/{r.items_tested} items verified
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}

            {!testMutation.data && !testMutation.isPending && (
              <div className="text-center py-8 text-muted-foreground">
                <PlayCircle className="w-12 h-12 mx-auto mb-3 text-muted-foreground" />
                <p>Click "Run Test" to verify backup recoverability</p>
                <p className="text-xs mt-1">Tests decrypt and validate backup data without restoring to M365</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
