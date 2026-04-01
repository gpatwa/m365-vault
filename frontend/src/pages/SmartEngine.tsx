import { useQuery, useMutation } from '@tanstack/react-query';
import { Brain, AlertTriangle, Activity, RefreshCw, CheckCircle, TrendingUp, Shield } from 'lucide-react';
import { api } from '../api/client';
import { useTenantId } from '../hooks/useTenant';

interface HealthScore {
  score: number;
  components: { success_rate: number; sla_adherence: number; anomaly_score: number; storage_score: number };
  details: { total_jobs_7d: number; completed_jobs_7d: number; protected_objects: number; backed_up_objects: number; active_anomalies: number };
}

interface Anomaly {
  id: number; workload: string; metric: string; expected: number; actual: number;
  z_score: number; severity: string; message: string; resolved: boolean; detected_at: string;
}

interface Baseline {
  workload: string; metric: string; avg: number; std_dev: number;
  min: number; max: number; samples: number; last_updated: string;
}

export default function SmartEngine() {
  const tenantId = useTenantId();

  const { data: health, refetch: refetchHealth } = useQuery({
    queryKey: ['health-score', tenantId],
    queryFn: () => api.get<HealthScore>(`/health/score?tenant_id=${tenantId}`),
    refetchInterval: 30000,
  });

  const { data: anomalies } = useQuery({
    queryKey: ['anomalies', tenantId],
    queryFn: () => api.get<{ total: number; items: Anomaly[] }>(`/health/anomalies?tenant_id=${tenantId}&active_only=false&page_size=50`),
    refetchInterval: 30000,
  });

  const { data: baselines } = useQuery({
    queryKey: ['baselines', tenantId],
    queryFn: () => api.get<{ total: number; items: Baseline[] }>(`/health/baselines?tenant_id=${tenantId}`),
  });

  const checkMutation = useMutation({
    mutationFn: () => api.post(`/health/check?tenant_id=${tenantId}`),
    onSuccess: () => refetchHealth(),
  });

  const scoreColor = (score: number) =>
    score >= 80 ? 'text-green-600' : score >= 50 ? 'text-yellow-600' : 'text-red-600';
  const scoreBg = (score: number) =>
    score >= 80 ? 'bg-green-500/10 border-green-200' : score >= 50 ? 'bg-yellow-50 border-yellow-200' : 'bg-red-500/10 border-red-200';

  const formatMetric = (metric: string, value: number) => {
    if (metric === 'size_bytes') return `${(value / 1024).toFixed(1)} KB`;
    if (metric === 'error_rate') return `${value.toFixed(1)}%`;
    if (metric === 'duration_sec') return `${value.toFixed(0)}s`;
    return value.toFixed(0);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Brain className="w-7 h-7 text-purple-600" /> Smart Engine
          </h1>
          <p className="text-gray-500">Zero-cost intelligence: health scoring, anomaly detection, baselines</p>
        </div>
        <button
          onClick={() => checkMutation.mutate()}
          disabled={checkMutation.isPending}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 flex items-center gap-2 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${checkMutation.isPending ? 'animate-spin' : ''}`} />
          {checkMutation.isPending ? 'Running...' : 'Run Health Check'}
        </button>
      </div>

      {/* Health Score */}
      {health && (
        <div className={`rounded-xl border p-6 mb-6 ${scoreBg(health.score)}`}>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className={`text-5xl font-bold ${scoreColor(health.score)}`}>{health.score}</div>
              <p className="text-sm text-gray-500 mt-1">Health Score</p>
            </div>
            <div className="flex-1 grid grid-cols-4 gap-4">
              {[
                { label: 'Success Rate', value: health.components.success_rate, icon: CheckCircle, color: 'text-green-600' },
                { label: 'SLA Adherence', value: health.components.sla_adherence, icon: Shield, color: 'text-blue-600' },
                { label: 'Anomaly Score', value: health.components.anomaly_score, icon: AlertTriangle, color: 'text-orange-600' },
                { label: 'Storage Health', value: health.components.storage_score, icon: Activity, color: 'text-purple-600' },
              ].map(({ label, value, icon: Icon, color }) => (
                <div key={label} className="bg-white/60 rounded-lg p-3 text-center">
                  <Icon className={`w-5 h-5 ${color} mx-auto mb-1`} />
                  <div className="text-lg font-bold text-gray-800">{value}%</div>
                  <p className="text-xs text-gray-500">{label}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-4 flex gap-6 text-xs text-gray-500 border-t border-gray-200/50 pt-3">
            <span>Jobs (7d): {health.details.total_jobs_7d}</span>
            <span>Completed: {health.details.completed_jobs_7d}</span>
            <span>Protected: {health.details.protected_objects}</span>
            <span>Backed up: {health.details.backed_up_objects}</span>
            <span>Active anomalies: {health.details.active_anomalies}</span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Anomalies */}
        <div className="bg-white rounded-xl border shadow-sm">
          <div className="p-4 border-b flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-orange-500" />
            <h3 className="font-semibold text-gray-900">Anomalies</h3>
            <span className="ml-auto px-2 py-0.5 bg-orange-100 text-orange-700 text-xs rounded-full font-medium">
              {anomalies?.items.filter(a => !a.resolved).length || 0} active
            </span>
          </div>
          <div className="divide-y divide-gray-100 max-h-96 overflow-auto">
            {anomalies?.items.length === 0 && (
              <div className="p-8 text-center text-gray-400">
                <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-400" />
                <p>No anomalies detected</p>
              </div>
            )}
            {anomalies?.items.map(a => (
              <div key={a.id} className={`p-3 ${a.resolved ? 'opacity-50' : ''}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                    a.severity === 'critical' ? 'bg-red-500/15 text-red-400' : 'bg-yellow-100 text-yellow-700'
                  }`}>{a.severity}</span>
                  <span className="text-xs font-medium text-gray-700 capitalize">{a.workload}</span>
                  <span className="text-xs text-gray-400">{a.metric}</span>
                  {a.resolved && <span className="ml-auto text-xs text-green-600 font-medium">Resolved</span>}
                </div>
                <p className="text-sm text-gray-600">{a.message}</p>
                <div className="flex gap-4 mt-1 text-xs text-gray-400">
                  <span>Expected: {formatMetric(a.metric, a.expected)}</span>
                  <span>Actual: {formatMetric(a.metric, a.actual)}</span>
                  <span>z-score: {a.z_score}</span>
                  <span>{new Date(a.detected_at).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Baselines */}
        <div className="bg-white rounded-xl border shadow-sm">
          <div className="p-4 border-b flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-blue-500" />
            <h3 className="font-semibold text-gray-900">Baselines</h3>
            <span className="ml-auto text-xs text-gray-400">{baselines?.total || 0} metrics tracked</span>
          </div>
          <div className="overflow-auto max-h-96">
            <table className="w-full text-sm">
              <thead className="bg-gray-800/50 sticky top-0">
                <tr>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Workload</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Metric</th>
                  <th className="text-right px-3 py-2 font-medium text-gray-600">Avg</th>
                  <th className="text-right px-3 py-2 font-medium text-gray-600">Std Dev</th>
                  <th className="text-right px-3 py-2 font-medium text-gray-600">Range</th>
                  <th className="text-right px-3 py-2 font-medium text-gray-600">Samples</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {baselines?.items.length === 0 && (
                  <tr><td colSpan={6} className="p-8 text-center text-gray-400">No baselines yet. Run a health check to start collecting.</td></tr>
                )}
                {baselines?.items.map((b, i) => (
                  <tr key={i} className="hover:bg-gray-800/50">
                    <td className="px-3 py-2 capitalize font-medium text-gray-700">{b.workload.replace('_', ' ')}</td>
                    <td className="px-3 py-2 text-gray-600">{b.metric}</td>
                    <td className="px-3 py-2 text-right font-mono">{formatMetric(b.metric, b.avg)}</td>
                    <td className="px-3 py-2 text-right font-mono text-gray-400">{formatMetric(b.metric, b.std_dev)}</td>
                    <td className="px-3 py-2 text-right font-mono text-gray-400 text-xs">{formatMetric(b.metric, b.min)} – {formatMetric(b.metric, b.max)}</td>
                    <td className="px-3 py-2 text-right text-gray-500">{b.samples}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* How it works */}
      <div className="mt-6 bg-purple-500/10 border border-purple-200 rounded-xl p-5">
        <h3 className="font-semibold text-purple-900 mb-2 flex items-center gap-2">
          <Brain className="w-4 h-4" /> How Smart Engine Works
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-purple-800">
          <div>
            <p className="font-medium mb-1">Health Baselines</p>
            <p className="text-purple-600 text-xs">Tracks running averages of item count, size, error rate per workload. Uses exponential moving average for recent bias.</p>
          </div>
          <div>
            <p className="font-medium mb-1">Anomaly Detection</p>
            <p className="text-purple-600 text-xs">Compares latest backup metrics against baselines using z-score. Flags deviations beyond {'>'}2 standard deviations.</p>
          </div>
          <div>
            <p className="font-medium mb-1">Health Score (0-100)</p>
            <p className="text-purple-600 text-xs">Weighted: 40% success rate + 30% SLA adherence + 20% anomaly score + 10% storage health. Updated every 5 minutes.</p>
          </div>
        </div>
        <p className="text-xs text-purple-500 mt-3">Zero-cost: Pure Python + scipy stats. No LLM tokens. No external APIs. Runs on your existing infrastructure.</p>
      </div>
    </div>
  );
}
