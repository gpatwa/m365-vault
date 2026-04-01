import { useQuery } from '@tanstack/react-query';
import { Activity, Zap, Database, Shield, Server, CheckCircle2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../api/client';

interface BenchmarkData {
  timestamp: string;
  version: string;
  benchmarks: {
    health_check?: { status: string; latency_ms: number };
    api_latency?: Record<string, { avg_ms: number; p50_ms: number; p95_ms: number; p99_ms: number }>;
    backup?: Record<string, { objects?: number; items?: number; size_bytes?: number; duration_sec?: number; items_per_sec?: number; status?: string }>;
    storage?: { total_size_bytes?: number; compression_ratio?: number; dedup_ratio?: string };
    success_rate?: { period?: string; rate?: number; total_jobs?: number };
    concurrent?: { [key: string]: number };
    recovery?: { confidence_score?: number; rpo_adherence?: number };
  };
}

function MetricCard({ icon: Icon, label, value, unit, color }: { icon: typeof Activity; label: string; value: string | number; unit?: string; color: string }) {
  return (
    <div className="bg-card rounded-xl border border-border p-5">
      <div className="flex items-center gap-3">
        <div className={`p-2.5 rounded-lg ${color}`}>
          <Icon className="w-5 h-5 text-foreground" />
        </div>
        <div>
          <div className="text-2xl font-bold text-foreground">{value}{unit && <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>}</div>
          <div className="text-xs text-muted-foreground">{label}</div>
        </div>
      </div>
    </div>
  );
}

export default function Performance() {
  const { data, isLoading } = useQuery({
    queryKey: ['benchmarks'],
    queryFn: () => api.get<BenchmarkData>('/benchmarks/latest'),
  });

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" /></div>;
  }

  const noResults = !data?.benchmarks;
  const b = data?.benchmarks || {};

  // Prepare API latency chart data
  const latencyData = Object.entries(b.api_latency || {}).map(([name, v]) => ({
    name: name.length > 12 ? name.slice(0, 12) + '...' : name,
    fullName: name,
    avg: v.avg_ms,
    p50: v.p50_ms,
    p95: v.p95_ms,
    p99: v.p99_ms,
  }));

  // Compute aggregates
  const allAvg = latencyData.map(d => d.avg);
  const avgLatency = allAvg.length > 0 ? Math.round(allAvg.reduce((a, b) => a + b, 0) / allAvg.length * 10) / 10 : 0;

  // Concurrent load data
  const concurrentData = b.concurrent ? [
    { load: '5 req', avg: b.concurrent['5_concurrent_avg_ms'] },
    { load: '10 req', avg: b.concurrent['10_concurrent_avg_ms'] },
    { load: '25 req', avg: b.concurrent['25_concurrent_avg_ms'] },
  ] : [];

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Performance</h1>
        <p className="text-sm text-muted-foreground">
          Benchmark results from real system measurements
          {data?.timestamp && <span className="ml-2 text-muted-foreground">• Last run: {new Date(data.timestamp).toLocaleDateString()}</span>}
          {data?.version && <span className="ml-2 text-muted-foreground">• v{data.version}</span>}
        </p>
      </div>

      {noResults ? (
        <div className="bg-muted/50 border border-border rounded-xl p-8 text-center">
          <Server className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground font-medium">No benchmark results available</p>
          <p className="text-sm text-muted-foreground mt-1">Run <code className="bg-gray-200 px-2 py-0.5 rounded text-xs">make benchmark</code> to generate performance data</p>
        </div>
      ) : (
        <>
          {/* Hero Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <MetricCard icon={Zap} label="Health Check" value={b.health_check?.latency_ms || '—'} unit="ms" color="bg-green-500" />
            <MetricCard icon={Activity} label="API Avg Latency" value={avgLatency} unit="ms" color="bg-blue-500" />
            <MetricCard icon={Database} label="Compression" value={b.storage?.compression_ratio || '—'} unit="x" color="bg-purple-500" />
            <MetricCard icon={Shield} label="Total Storage" value={b.storage?.total_size_bytes ? `${(b.storage.total_size_bytes / 1024 / 1024).toFixed(1)}` : '—'} unit="MB" color="bg-amber-500" />
          </div>

          {/* API Latency Chart */}
          {latencyData.length > 0 && (
            <div className="bg-card rounded-xl border border-border p-5 mb-6">
              <h2 className="text-sm font-semibold text-foreground mb-1">API Response Latency</h2>
              <p className="text-xs text-muted-foreground mb-4">Per-endpoint performance (5 samples each, milliseconds)</p>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={latencyData} margin={{ top: 5, right: 20, bottom: 40, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" />
                    <YAxis tick={{ fontSize: 11 }} label={{ value: 'ms', position: 'insideTopLeft', fontSize: 10 }} />
                    <Tooltip formatter={(v: any) => [`${Number(v).toFixed(1)}ms`]} labelFormatter={(l: any) => {
                      const item = latencyData.find(d => d.name === l);
                      return item?.fullName || l;
                    }} />
                    <Bar dataKey="p50" name="p50" fill="#3b82f6" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="p95" name="p95" fill="#f59e0b" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="p99" name="p99" fill="#ef4444" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="flex items-center justify-center gap-6 mt-2 text-xs">
                <div className="flex items-center gap-1.5"><div className="w-3 h-3 bg-blue-500 rounded" /> p50 (median)</div>
                <div className="flex items-center gap-1.5"><div className="w-3 h-3 bg-amber-500 rounded" /> p95</div>
                <div className="flex items-center gap-1.5"><div className="w-3 h-3 bg-red-500 rounded" /> p99</div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Concurrent Load */}
            {concurrentData.length > 0 && (
              <div className="bg-card rounded-xl border border-border p-5">
                <h2 className="text-sm font-semibold text-foreground mb-1">Concurrent Load Test</h2>
                <p className="text-xs text-muted-foreground mb-4">Average response time under parallel requests</p>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={concurrentData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="load" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} label={{ value: 'ms', position: 'insideTopLeft', fontSize: 10 }} />
                      <Tooltip formatter={(v: any) => [`${Number(v).toFixed(1)}ms`]} />
                      <Bar dataKey="avg" name="Avg Response" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Endpoint Details Table */}
            <div className="bg-card rounded-xl border border-border p-5">
              <h2 className="text-sm font-semibold text-foreground mb-1">Endpoint Details</h2>
              <p className="text-xs text-muted-foreground mb-4">Per-endpoint latency percentiles</p>
              <div className="overflow-auto max-h-48">
                <table className="w-full text-xs">
                  <thead className="bg-muted/50 sticky top-0">
                    <tr>
                      <th className="text-left px-2 py-1.5 font-medium text-muted-foreground">Endpoint</th>
                      <th className="text-right px-2 py-1.5 font-medium text-muted-foreground">Avg</th>
                      <th className="text-right px-2 py-1.5 font-medium text-muted-foreground">p50</th>
                      <th className="text-right px-2 py-1.5 font-medium text-muted-foreground">p95</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {Object.entries(b.api_latency || {}).map(([name, v]) => (
                      <tr key={name} className="hover:bg-muted/50">
                        <td className="px-2 py-1.5 text-muted-foreground">{name}</td>
                        <td className="px-2 py-1.5 text-right font-mono">{v.avg_ms.toFixed(1)}</td>
                        <td className="px-2 py-1.5 text-right font-mono">{v.p50_ms.toFixed(1)}</td>
                        <td className="px-2 py-1.5 text-right font-mono">{v.p95_ms.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Backup + Storage + Success */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            {/* Storage */}
            <div className="bg-card rounded-xl border border-border p-5">
              <h2 className="text-sm font-semibold text-foreground mb-3">Storage Efficiency</h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Total Size</span>
                  <span className="text-sm font-semibold">{b.storage?.total_size_bytes ? `${(b.storage.total_size_bytes / 1024 / 1024).toFixed(1)} MB` : '—'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Compression</span>
                  <span className="text-sm font-semibold text-green-600">{b.storage?.compression_ratio || '—'}x</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Dedup Ratio</span>
                  <span className="text-sm font-semibold">{b.storage?.dedup_ratio || 'N/A'}</span>
                </div>
              </div>
            </div>

            {/* Success Rate */}
            <div className="bg-card rounded-xl border border-border p-5">
              <h2 className="text-sm font-semibold text-foreground mb-3">Success Rate</h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Period</span>
                  <span className="text-sm">{b.success_rate?.period || '30d'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Rate</span>
                  <span className="text-sm font-semibold text-green-600">{b.success_rate?.rate != null ? `${b.success_rate.rate}%` : 'N/A'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Total Jobs</span>
                  <span className="text-sm">{b.success_rate?.total_jobs ?? 'N/A'}</span>
                </div>
              </div>
            </div>

            {/* System Info */}
            <div className="bg-card rounded-xl border border-border p-5">
              <h2 className="text-sm font-semibold text-foreground mb-3">System</h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Health</span>
                  <span className="flex items-center gap-1 text-sm text-green-600"><CheckCircle2 className="w-3.5 h-3.5" /> {b.health_check?.status || '—'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Version</span>
                  <span className="text-sm">{data?.version || '—'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Last Benchmark</span>
                  <span className="text-sm">{data?.timestamp ? new Date(data.timestamp).toLocaleString() : '—'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* How to run */}
          <div className="bg-muted/50 border border-border rounded-xl p-4 text-center">
            <p className="text-xs text-muted-foreground">
              Run <code className="bg-gray-200 px-2 py-0.5 rounded">make benchmark</code> to refresh these results.
              Benchmarks measure real API performance against the running system.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
