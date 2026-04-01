import { useQuery } from '@tanstack/react-query';
import { Gauge, Users, HardDrive, TrendingUp, AlertTriangle, Crown, Loader2 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { api } from '../api/client';

function UsageBar({ label, current, limit, unit = '' }: { label: string; current: number; limit: number | string; unit?: string }) {
  const isUnlimited = typeof limit === 'string';
  const pct = isUnlimited ? 0 : Math.min((current / (limit as number)) * 100, 100);
  const color = pct >= 90 ? 'bg-red-500' : pct >= 75 ? 'bg-amber-500' : 'bg-green-500';

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="text-gray-500">{current}{unit} / {isUnlimited ? 'Unlimited' : `${limit}${unit}`}</span>
      </div>
      <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${isUnlimited ? 'bg-green-400 w-[5%]' : color}`}
          style={{ width: isUnlimited ? '5%' : `${pct}%` }} />
      </div>
      {!isUnlimited && pct >= 80 && (
        <p className="text-xs text-amber-600 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> {pct >= 100 ? 'Limit exceeded!' : 'Approaching limit'}</p>
      )}
    </div>
  );
}

export default function Usage() {
  const { data: license, isLoading: loadingLicense } = useQuery({
    queryKey: ['license-status'],
    queryFn: () => api.get<any>('/usage/license'),
  });

  const { data: platform, isLoading: loadingPlatform } = useQuery({
    queryKey: ['platform-usage'],
    queryFn: () => api.get<any>('/usage/platform'),
  });

  const { data: trends } = useQuery({
    queryKey: ['usage-trends'],
    queryFn: () => api.get<any>('/usage/trends?period=30d'),
  });

  if (loadingLicense || loadingPlatform) {
    return <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-indigo-400" /></div>;
  }

  const tierColors: Record<string, string> = {
    community: 'border-gray-300 bg-gray-50',
    professional: 'border-blue-300 bg-blue-50',
    enterprise: 'border-purple-300 bg-purple-50',
  };

  const tierBadge: Record<string, string> = {
    community: 'bg-gray-200 text-gray-700',
    professional: 'bg-blue-200 text-blue-700',
    enterprise: 'bg-purple-200 text-purple-700',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Gauge className="w-7 h-7 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold">Usage & License</h1>
          <p className="text-sm text-gray-500">Platform usage metrics, license utilization, and growth trends</p>
        </div>
      </div>

      {/* License Status */}
      {license && (
        <div className={`rounded-xl border-2 p-6 ${tierColors[license.tier] || tierColors.community}`}>
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <Crown className="w-6 h-6 text-amber-500" />
              <div>
                <h2 className="text-lg font-bold">{license.tier_label}</h2>
                <p className="text-xs text-gray-500">
                  Features: {license.features?.join(', ')} | Smart Engine: {license.smart_engine} | Support: {license.support}
                </p>
              </div>
            </div>
            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${tierBadge[license.tier] || tierBadge.community}`}>
              {license.tier.toUpperCase()}
            </span>
          </div>

          <div className="space-y-4">
            {license.usage?.map((d: any) => (
              <UsageBar key={d.name} label={d.name} current={d.current} limit={d.limit} />
            ))}
          </div>

          {/* Alerts */}
          {license.alerts?.length > 0 && (
            <div className="mt-4 space-y-2">
              {license.alerts.map((a: any, i: number) => (
                <div key={i} className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${a.level === 'error' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                  {a.message}
                </div>
              ))}
            </div>
          )}

          {license.upgrade_available && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <p className="text-sm text-gray-600">Need more capacity? <span className="font-semibold text-indigo-600 cursor-pointer hover:underline">Upgrade to {license.tier === 'community' ? 'Professional' : 'Enterprise'}</span></p>
            </div>
          )}
        </div>
      )}

      {/* Platform Summary */}
      {platform && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1"><Users className="w-3.5 h-3.5" /> Tenants</div>
            <p className="text-2xl font-bold">{platform.total_tenants}</p>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1"><Users className="w-3.5 h-3.5" /> Protected Users</div>
            <p className="text-2xl font-bold">{platform.total_protected_users}</p>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1"><HardDrive className="w-3.5 h-3.5" /> Storage</div>
            <p className="text-2xl font-bold">{platform.total_storage_gb} GB</p>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1"><TrendingUp className="w-3.5 h-3.5" /> Jobs (30d)</div>
            <p className="text-2xl font-bold">{platform.backup_jobs_30d}</p>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1">$ Est. Cost</div>
            <p className="text-2xl font-bold">${platform.estimated_monthly_cost}</p>
            <p className="text-[10px] text-gray-400">${platform.cost_per_user}/user</p>
          </div>
        </div>
      )}

      {/* Growth Trend */}
      {trends?.trend && (
        <div className="bg-white rounded-xl border p-5">
          <h3 className="font-semibold text-gray-800 mb-4">Usage Trends (30 days)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trends.trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d.slice(5)} />
              <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="protected_users" stroke="#3b82f6" strokeWidth={2} dot={false} name="Protected Users" />
              <Line yAxisId="left" type="monotone" dataKey="jobs" stroke="#10b981" strokeWidth={2} dot={false} name="Jobs" />
              <Line yAxisId="right" type="monotone" dataKey="storage_bytes" stroke="#f59e0b" strokeWidth={2} dot={false} name="Storage (bytes)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
