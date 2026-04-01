import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, AlertTriangle, ShieldCheck, Lock, Download, Loader2 } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, AreaChart, Area, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../api/client';
import { useTenantId } from '../hooks/useTenant';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];
const TABS = ['Performance', 'Storage', 'Failures', 'Compliance', 'Security'] as const;
type Tab = typeof TABS[number];
const PERIODS = ['7d', '30d', '90d'] as const;

function formatBytes(bytes: number) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function StatBox({ label, value, sub, color = 'blue' }: { label: string; value: string | number; sub?: string; color?: string }) {
  const colors: Record<string, string> = { blue: 'bg-blue-50 text-blue-700', green: 'bg-green-50 text-green-700', red: 'bg-red-50 text-red-700', amber: 'bg-amber-50 text-amber-700', purple: 'bg-purple-50 text-purple-700' };
  return (
    <div className={`rounded-lg p-4 ${colors[color] || colors.blue}`}>
      <p className="text-xs font-medium opacity-70">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {sub && <p className="text-xs mt-1 opacity-60">{sub}</p>}
    </div>
  );
}

export default function Reports() {
  const [tab, setTab] = useState<Tab>('Performance');
  const [period, setPeriod] = useState('30d');
  const tenantId = useTenantId();

  const { data: perfData, isLoading: loadingPerf } = useQuery({
    queryKey: ['report-performance', period, tenantId],
    queryFn: () => api.get<any>(`/reports/backup-performance?period=${period}${tenantId ? `&tenant_id=${tenantId}` : ''}`),
    enabled: tab === 'Performance',
  });

  const { data: storageData, isLoading: loadingStorage } = useQuery({
    queryKey: ['report-storage', tenantId],
    queryFn: () => api.get<any>(`/reports/storage-analytics${tenantId ? `?tenant_id=${tenantId}` : ''}`),
    enabled: tab === 'Storage',
  });

  const { data: failureData, isLoading: loadingFailures } = useQuery({
    queryKey: ['report-failures', period, tenantId],
    queryFn: () => api.get<any>(`/reports/failure-analysis?period=${period}${tenantId ? `&tenant_id=${tenantId}` : ''}`),
    enabled: tab === 'Failures',
  });

  const { data: complianceData, isLoading: loadingCompliance } = useQuery({
    queryKey: ['report-compliance', tenantId],
    queryFn: () => api.get<any>(`/reports/sla-compliance${tenantId ? `?tenant_id=${tenantId}` : ''}`),
    enabled: tab === 'Compliance',
  });

  const { data: securityData, isLoading: loadingSecurity } = useQuery({
    queryKey: ['report-security', tenantId],
    queryFn: () => api.get<any>(`/reports/security-summary${tenantId ? `?tenant_id=${tenantId}` : ''}`),
    enabled: tab === 'Security',
  });

  const handleExport = (report: string) => {
    const url = `/reports/export?report=${report}&format=csv&period=${period}${tenantId ? `&tenant_id=${tenantId}` : ''}`;
    window.open(`${(window as any).__RUNTIME_CONFIG__?.API_BASE || import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'}${url.startsWith('/') ? url : '/' + url}`, '_blank');
  };

  const isLoading = tab === 'Performance' ? loadingPerf : tab === 'Storage' ? loadingStorage : tab === 'Failures' ? loadingFailures : tab === 'Compliance' ? loadingCompliance : loadingSecurity;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BarChart3 className="w-7 h-7 text-indigo-600" />
          <div>
            <h1 className="text-2xl font-bold">Reports & Analytics</h1>
            <p className="text-sm text-muted-foreground">Comprehensive backup performance, storage, and compliance reporting</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {PERIODS.map(p => (
            <button key={p} onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${period === p ? 'bg-indigo-600 text-white' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-muted rounded-xl p-1">
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${tab === t ? 'bg-card text-indigo-700 shadow-sm' : 'text-muted-foreground hover:text-foreground/80'}`}>
            {t}
          </button>
        ))}
      </div>

      {isLoading && <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-indigo-400" /></div>}

      {/* ── Performance Tab ── */}
      {tab === 'Performance' && perfData && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatBox label="Total Jobs" value={perfData.summary.total_jobs} color="blue" />
            <StatBox label="Success Rate" value={`${perfData.summary.success_rate}%`} color="green" />
            <StatBox label="Failed" value={perfData.summary.failed} color="red" />
            <StatBox label="Avg Duration" value={`${Math.round(perfData.summary.avg_duration_sec / 60)}m`} color="purple" />
            <StatBox label="Data Protected" value={formatBytes(perfData.summary.total_size_bytes)} color="amber" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-card rounded-xl border p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-foreground">Success Rate Trend</h3>
                <button onClick={() => handleExport('backup-performance')} className="text-xs text-indigo-600 hover:underline flex items-center gap-1"><Download className="w-3 h-3" /> CSV</button>
              </div>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={perfData.trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d.slice(5)} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="success_rate" stroke="#10b981" strokeWidth={2} dot={false} name="Success %" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-card rounded-xl border p-5">
              <h3 className="font-semibold text-foreground mb-4">Jobs by Workload</h3>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={Object.entries(perfData.by_workload).map(([wl, d]: [string, any]) => ({ workload: wl, ...d }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="workload" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="completed" fill="#10b981" name="Completed" />
                  <Bar dataKey="failed" fill="#ef4444" name="Failed" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* ── Storage Tab ── */}
      {tab === 'Storage' && storageData && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatBox label="Total Storage" value={`${storageData.total_size_gb} GB`} color="blue" />
            <StatBox label="Snapshots" value={storageData.total_snapshots} color="purple" />
            <StatBox label="Dedup Ratio" value={`${storageData.dedup.ratio}x`} color="green" />
            <StatBox label="Space Saved" value={`${storageData.dedup.space_saved_pct}%`} color="amber" />
            <StatBox label="Monthly Cost" value={`$${storageData.cost_projection.monthly_storage_cost}`} color="red" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-card rounded-xl border p-5">
              <h3 className="font-semibold text-foreground mb-4">Storage Growth (30d)</h3>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={storageData.growth_trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d.slice(5)} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={v => formatBytes(v)} />
                  <Tooltip formatter={(v) => formatBytes(Number(v))} />
                  <Area type="monotone" dataKey="cumulative_bytes" stroke="#3b82f6" fill="#dbeafe" name="Storage" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-card rounded-xl border p-5">
              <h3 className="font-semibold text-foreground mb-4">Storage by Workload</h3>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie data={Object.entries(storageData.by_workload).map(([wl, d]: [string, any]) => ({ name: wl, value: d.size_bytes }))}
                    cx="50%" cy="50%" outerRadius={90} dataKey="value" label={({ name, percent }: any) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}>
                    {Object.keys(storageData.by_workload).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v) => formatBytes(Number(v))} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* ── Failures Tab ── */}
      {tab === 'Failures' && failureData && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatBox label="Total Failed Items" value={failureData.total_failed_items} color="red" />
            <StatBox label="Resolved" value={failureData.resolved} color="green" />
            <StatBox label="Unresolved" value={failureData.unresolved} color="amber" />
            <StatBox label="Resolution Rate" value={`${failureData.resolution_rate}%`} color="blue" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-card rounded-xl border p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-foreground">Errors by Category</h3>
                <button onClick={() => handleExport('failure-analysis')} className="text-xs text-indigo-600 hover:underline flex items-center gap-1"><Download className="w-3 h-3" /> CSV</button>
              </div>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={Object.entries(failureData.by_category).map(([cat, count]) => ({ category: cat.replace('_', ' '), count }))} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="category" tick={{ fontSize: 10 }} width={120} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#ef4444" name="Errors" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-card rounded-xl border p-5">
              <h3 className="font-semibold text-foreground mb-4">Failed Jobs Trend</h3>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={failureData.trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d.slice(5)} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="failed_jobs" stroke="#ef4444" strokeWidth={2} dot={false} name="Failed Jobs" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* ── Compliance Tab ── */}
      {tab === 'Compliance' && complianceData && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatBox label="Compliance Rate" value={`${complianceData.compliance_rate}%`} color={complianceData.compliance_rate >= 95 ? 'green' : complianceData.compliance_rate >= 80 ? 'amber' : 'red'} />
            <StatBox label="Compliant" value={complianceData.compliant} color="green" />
            <StatBox label="Non-Compliant" value={complianceData.non_compliant} color="red" />
            <StatBox label="Total Protected" value={complianceData.total_protected} color="blue" />
          </div>

          {/* Per-policy breakdown */}
          <div className="bg-card rounded-xl border p-5">
            <h3 className="font-semibold text-foreground mb-4">Compliance by SLA Policy</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">Policy</th>
                    <th className="text-center px-4 py-2 font-medium text-muted-foreground">Objects</th>
                    <th className="text-center px-4 py-2 font-medium text-muted-foreground">Compliant</th>
                    <th className="text-center px-4 py-2 font-medium text-muted-foreground">Rate</th>
                    <th className="text-center px-4 py-2 font-medium text-muted-foreground">Frequency</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {Object.entries(complianceData.by_policy || {}).map(([name, p]: [string, any]) => (
                    <tr key={name}>
                      <td className="px-4 py-2 font-medium">{name}</td>
                      <td className="px-4 py-2 text-center">{p.total}</td>
                      <td className="px-4 py-2 text-center text-green-600">{p.compliant}</td>
                      <td className="px-4 py-2 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${p.compliance_rate >= 95 ? 'bg-green-100 text-green-700' : p.compliance_rate >= 80 ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}`}>
                          {p.compliance_rate}%
                        </span>
                      </td>
                      <td className="px-4 py-2 text-center text-muted-foreground">Every {p.frequency_hours}h</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Violations */}
          {complianceData.violations?.length > 0 && (
            <div className="bg-card rounded-xl border p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-foreground">SLA Violations</h3>
                <button onClick={() => handleExport('sla-compliance')} className="text-xs text-indigo-600 hover:underline flex items-center gap-1"><Download className="w-3 h-3" /> CSV</button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-red-50">
                    <tr>
                      <th className="text-left px-4 py-2 font-medium text-red-700">Object</th>
                      <th className="text-left px-4 py-2 font-medium text-red-700">Workload</th>
                      <th className="text-left px-4 py-2 font-medium text-red-700">Policy</th>
                      <th className="text-left px-4 py-2 font-medium text-red-700">Hours Overdue</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {complianceData.violations.map((v: any, i: number) => (
                      <tr key={i}>
                        <td className="px-4 py-2 font-medium">{v.object}</td>
                        <td className="px-4 py-2 capitalize">{v.workload}</td>
                        <td className="px-4 py-2">{v.policy}</td>
                        <td className="px-4 py-2 text-red-600 font-medium">{v.hours_overdue}h</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Security Tab ── */}
      {tab === 'Security' && securityData && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatBox label="Sensitive Data Items" value={securityData.sensitive_data?.flagged_items || 0} color="amber" />
            <StatBox label="WORM Policies" value={securityData.worm?.policies_enabled || 0} color="green" />
            <StatBox label="Locked Snapshots" value={securityData.worm?.locked_snapshots || 0} color="blue" />
            <StatBox label="Active Anomalies" value={securityData.anomalies?.active || 0} color={securityData.anomalies?.critical > 0 ? 'red' : 'green'} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-card rounded-xl border p-5">
              <div className="flex items-center gap-2 mb-3">
                <ShieldCheck className="w-5 h-5 text-green-600" />
                <h3 className="font-semibold text-foreground">Malware Scans</h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-muted-foreground">Total Scanned</span><span className="font-medium">{securityData.malware_scans?.total_scanned || 0}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Clean</span><span className="font-medium text-green-600">{securityData.malware_scans?.clean || 0}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Blocked</span><span className="font-medium text-red-600">{securityData.malware_scans?.blocked || 0}</span></div>
              </div>
            </div>

            <div className="bg-card rounded-xl border p-5">
              <div className="flex items-center gap-2 mb-3">
                <Lock className="w-5 h-5 text-blue-600" />
                <h3 className="font-semibold text-foreground">WORM / Legal Hold</h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-muted-foreground">WORM Policies</span><span className="font-medium">{securityData.worm?.policies_enabled || 0}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Legal Hold</span><span className="font-medium">{securityData.worm?.legal_hold_policies || 0}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Immutable Snapshots</span><span className="font-medium text-blue-600">{securityData.worm?.locked_snapshots || 0}</span></div>
              </div>
            </div>

            <div className="bg-card rounded-xl border p-5">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-5 h-5 text-amber-600" />
                <h3 className="font-semibold text-foreground">Anomalies</h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-muted-foreground">Active</span><span className="font-medium">{securityData.anomalies?.active || 0}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Critical</span><span className="font-medium text-red-600">{securityData.anomalies?.critical || 0}</span></div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
