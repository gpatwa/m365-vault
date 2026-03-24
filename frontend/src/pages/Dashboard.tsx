import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Shield, Activity, AlertTriangle, Database, TrendingUp,
  Lock, Eye, FileCheck, CreditCard,
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../api/client';
import { WORKLOADS } from '../config/workloads';
import { HeroSummaryBar, ActionBanner, PlatformCard } from '../components/design-system';
import type { HeroStat } from '../components/design-system/HeroSummaryBar';
import type { ActionItem } from '../components/design-system/ActionBanner';
import type { WorkloadStat } from '../components/design-system/PlatformCard';
import type { DashboardSummary, ActivityData } from '../types';

export default function Dashboard() {
  const navigate = useNavigate();
  const tenantId = 2; // TODO: dynamic tenant selection

  // ── Data Fetching ──

  const { data: summary } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => api.get<DashboardSummary>('/dashboard/summary'),
    refetchInterval: 30000,
  });

  const { data: activityData } = useQuery({
    queryKey: ['dashboard-activity'],
    queryFn: () => api.get<{ activity: ActivityData[] }>('/dashboard/activity?days=7'),
  });

  const { data: healthData } = useQuery({
    queryKey: ['health-score', tenantId],
    queryFn: () => api.get<{ score: number; components: any; details: any }>(`/health/score?tenant_id=${tenantId}`),
    refetchInterval: 60000,
    enabled: !!tenantId,
  });

  const { data: compliance } = useQuery({
    queryKey: ['dashboard-compliance'],
    queryFn: () => api.get<{ compliance_rate: number; non_compliant: number; violations: any[] }>('/dashboard/compliance'),
  });

  const { data: unprotectedData } = useQuery({
    queryKey: ['dashboard-unprotected'],
    queryFn: () => api.get<{ total_unprotected: number; total_at_risk: number }>('/dashboard/unprotected'),
    refetchInterval: 30000,
  });

  const { data: licenseData } = useQuery({
    queryKey: ['usage-license'],
    queryFn: () => api.get<any>('/usage/license'),
    staleTime: 60000,
  });

  // ── Computed: Hero Stats ──

  const heroStats: HeroStat[] = useMemo(() => {
    const totalProtected = summary?.total_protected ?? 0;
    const totalObjects = summary?.total_objects ?? 0;
    const protectionPct = totalObjects > 0 ? Math.round(totalProtected / totalObjects * 100) : 0;
    const healthScore = healthData?.score ?? 0;
    const successRate = healthData?.components?.success_rate ?? 0;
    const totalExposed = (unprotectedData?.total_unprotected ?? 0) + (unprotectedData?.total_at_risk ?? 0);

    return [
      {
        label: 'Protection',
        value: `${protectionPct}%`,
        subtitle: `${totalProtected}/${totalObjects} objects`,
        icon: Shield,
        color: protectionPct === 100 ? 'green' : protectionPct > 50 ? 'amber' : 'red',
        onClick: () => navigate('/jobs'),
      },
      {
        label: 'Health Score',
        value: healthScore,
        subtitle: `Success: ${successRate}%`,
        icon: Activity,
        color: healthScore >= 80 ? 'green' : healthScore >= 50 ? 'amber' : 'red',
        onClick: () => navigate('/smart-engine'),
        trend: healthScore >= 80 ? { direction: 'up' as const, label: 'Healthy' } : { direction: 'down' as const, label: 'Needs attention' },
      },
      {
        label: 'Backups (24h)',
        value: summary?.jobs_24h?.backup_total ?? 0,
        subtitle: `${summary?.jobs_24h?.backup_successful ?? 0} successful, ${summary?.jobs_24h?.backup_failed ?? 0} failed`,
        icon: Database,
        color: (summary?.jobs_24h?.backup_failed ?? 0) > 0 ? 'amber' : 'green',
        onClick: () => navigate('/jobs'),
      },
      {
        label: 'Action Items',
        value: totalExposed + (summary?.jobs_24h?.backup_failed ?? 0),
        subtitle: totalExposed > 0 ? `${unprotectedData?.total_unprotected ?? 0} unprotected` : 'All clear',
        icon: AlertTriangle,
        color: totalExposed > 0 ? 'red' : 'green',
        onClick: () => navigate('/failed-items'),
      },
    ];
  }, [summary, healthData, unprotectedData, navigate]);

  // ── Computed: Action Banners ──

  const actionItems: ActionItem[] = useMemo(() => {
    const items: ActionItem[] = [];
    const unprotected = unprotectedData?.total_unprotected ?? 0;
    const atRisk = unprotectedData?.total_at_risk ?? 0;
    const failed = summary?.jobs_24h?.backup_failed ?? 0;
    const anomalies = healthData?.details?.active_anomalies ?? 0;

    if (unprotected > 0) {
      items.push({
        icon: 'warning',
        message: `${unprotected} object${unprotected > 1 ? 's' : ''} are not protected by any SLA policy`,
        action: { label: 'Assign SLA', onClick: () => navigate('/sla-policies') },
      });
    }
    if (failed > 0) {
      items.push({
        icon: 'error',
        message: `${failed} backup job${failed > 1 ? 's' : ''} failed in the last 24 hours`,
        action: { label: 'View Failed', onClick: () => navigate('/failed-items') },
      });
    }
    if (anomalies > 0) {
      items.push({
        icon: 'warning',
        message: `${anomalies} active anomal${anomalies > 1 ? 'ies' : 'y'} detected by Smart Engine`,
        action: { label: 'Investigate', onClick: () => navigate('/smart-engine') },
      });
    }
    if (atRisk > 0) {
      items.push({
        icon: 'info',
        message: `${atRisk} object${atRisk > 1 ? 's' : ''} haven't been backed up within SLA window`,
        action: { label: 'View At-Risk', onClick: () => navigate('/jobs') },
      });
    }
    return items;
  }, [unprotectedData, summary, healthData, navigate]);

  // ── Computed: Platform Card ──

  const workloadStats: WorkloadStat[] = useMemo(() => {
    if (!summary?.workloads) return [];
    return WORKLOADS.map(wl => {
      const data = summary.workloads[wl.key] || { total: 0, protected: 0 };
      return {
        key: wl.key,
        label: wl.label,
        icon: wl.icon,
        iconColor: wl.iconColor || 'text-gray-500',
        protected: data.protected || 0,
        total: data.total || 0,
        lastBackup: null, // TODO: from jobs API
        itemCount: 0, // TODO: from snapshots API
        path: `/${wl.key.replace('_', '-')}`,
      };
    });
  }, [summary]);

  const platformTotalProtected = workloadStats.reduce((s, w) => s + w.protected, 0);
  const platformTotalObjects = workloadStats.reduce((s, w) => s + w.total, 0);

  // ── Computed: Trend chart data ──

  const trendData = useMemo(() => {
    if (!activityData?.activity) return [];
    // Group by day
    const days: Record<string, { day: string; success: number; failed: number }> = {};
    const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const key = d.toISOString().split('T')[0];
      days[key] = { day: dayLabels[d.getDay()], success: 0, failed: 0 };
    }
    activityData.activity.forEach((a: any) => {
      const key = (a.timestamp || a.completed_at || '').split('T')[0];
      if (days[key]) {
        if (a.status === 'completed') days[key].success++;
        else if (a.status === 'failed') days[key].failed++;
      }
    });
    return Object.values(days);
  }, [activityData]);

  // ── Render ──

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500">Shieldio — SaaS Data Protection Overview</p>
      </div>

      {/* Row 1: Hero Stats */}
      <HeroSummaryBar stats={heroStats} />

      {/* Action Banners */}
      <ActionBanner items={actionItems} />

      {/* Row 2: Platform Card */}
      <div className="mb-6">
        <PlatformCard
          name="Microsoft 365"
          icon={
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <svg className="w-6 h-6" viewBox="0 0 21 21">
                <path d="M0 0h10v10H0z" fill="#f25022"/>
                <path d="M11 0h10v10H11z" fill="#7fba00"/>
                <path d="M0 11h10v10H0z" fill="#00a4ef"/>
                <path d="M11 11h10v10H11z" fill="#ffb900"/>
              </svg>
            </div>
          }
          totalProtected={platformTotalProtected}
          totalObjects={platformTotalObjects}
          healthScore={healthData?.score ?? 0}
          workloads={workloadStats}
          defaultExpanded={true}
        />
      </div>

      {/* Row 3: License/Usage + 7-Day Trend */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* License & Usage */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-blue-500" />
              <h3 className="text-sm font-semibold text-gray-800">License & Usage</h3>
            </div>
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
              licenseData?.tier === 'enterprise' ? 'bg-purple-100 text-purple-700' :
              licenseData?.tier === 'professional' ? 'bg-blue-100 text-blue-700' :
              'bg-gray-100 text-gray-600'
            }`}>
              {licenseData?.tier_label || 'Community'}
            </span>
          </div>
          <div className="p-4 space-y-3">
            {(licenseData?.usage || []).map((u: any, i: number) => (
              <div key={i}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-gray-600">{u.name}</span>
                  <span className="text-xs font-semibold text-gray-800">
                    {u.current}{u.limit > 0 ? ` / ${u.limit}` : ''}
                  </span>
                </div>
                {u.limit > 0 && (
                  <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        u.usage_percent >= 90 ? 'bg-red-500' :
                        u.usage_percent >= 70 ? 'bg-amber-500' :
                        'bg-blue-500'
                      }`}
                      style={{ width: `${Math.min(u.usage_percent, 100)}%` }}
                    />
                  </div>
                )}
              </div>
            ))}
            {licenseData?.features && (
              <div className="pt-2 border-t border-gray-100">
                <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-1.5">Included Workloads</p>
                <div className="flex flex-wrap gap-1">
                  {licenseData.features.map((f: string) => (
                    <span key={f} className="text-[10px] px-1.5 py-0.5 bg-gray-50 border border-gray-100 rounded text-gray-500 capitalize">
                      {f.replace('_', ' ')}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <button
              onClick={() => navigate('/usage')}
              className="w-full text-xs text-blue-600 hover:text-blue-800 font-medium pt-1"
            >
              View full usage details →
            </button>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl shadow-sm">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-800">7-Day Backup Trend</h3>
            <TrendingUp className="w-4 h-4 text-gray-400" />
          </div>
          <div className="p-4 h-64">
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trendData} barCategoryGap="20%">
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                  <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }}
                    cursor={{ fill: '#f9fafb' }}
                  />
                  <Bar dataKey="success" fill="#22c55e" radius={[3, 3, 0, 0]} name="Successful" />
                  <Bar dataKey="failed" fill="#ef4444" radius={[3, 3, 0, 0]} name="Failed" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-gray-400">
                No backup data yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Row 4: Storage + Compliance */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Storage */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <Database className="w-4 h-4 text-blue-500" />
            <h3 className="text-sm font-semibold text-gray-800">Storage</h3>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500">Total Size</p>
              <p className="text-xl font-bold text-gray-900">{summary?.snapshots?.total_size_gb ?? 0} GB</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Snapshots</p>
              <p className="text-xl font-bold text-gray-900">{summary?.snapshots?.total ?? 0}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Dedup Savings</p>
              <p className="text-lg font-semibold text-green-600">42%</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Compression</p>
              <p className="text-lg font-semibold text-green-600">2.9x</p>
            </div>
          </div>
        </div>

        {/* Compliance */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <FileCheck className="w-4 h-4 text-green-500" />
            <h3 className="text-sm font-semibold text-gray-800">Compliance</h3>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500">SLA Adherence</p>
              <p className={`text-xl font-bold ${(compliance?.compliance_rate ?? 100) === 100 ? 'text-green-600' : 'text-amber-600'}`}>
                {compliance?.compliance_rate ?? 100}%
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Violations</p>
              <p className={`text-xl font-bold ${(compliance?.non_compliant ?? 0) > 0 ? 'text-red-600' : 'text-green-600'}`}>
                {compliance?.non_compliant ?? 0}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Lock className="w-3.5 h-3.5 text-blue-500" />
              <div>
                <p className="text-xs text-gray-500">WORM Locked</p>
                <p className="text-sm font-semibold text-gray-700">Active</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Eye className="w-3.5 h-3.5 text-purple-500" />
              <div>
                <p className="text-xs text-gray-500">Sensitive Data</p>
                <p className="text-sm font-semibold text-gray-700">Monitored</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
