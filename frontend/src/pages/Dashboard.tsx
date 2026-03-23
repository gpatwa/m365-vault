import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Shield, Mail, HardDrive, Globe, MessageSquare, CheckCircle, XCircle, Database, Activity, AlertTriangle, ShieldOff, ShieldAlert, ChevronDown, ChevronRight, Heart } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../api/client';
import StatCard from '../components/StatCard';
import type { DashboardSummary, ActivityData } from '../types';


interface UnprotectedItem {
  id: number;
  display_name: string;
  workload_type: string;
  email: string | null;
  site_url: string | null;
  status: string;
  sla_policy_id: number | null;
  last_backup_at: string | null;
  last_backup_status: string | null;
  total_items_backed_up: number;
  total_size_bytes: number;
}

interface UnprotectedData {
  total_unprotected: number;
  total_at_risk: number;
  by_workload: Record<string, { unprotected: UnprotectedItem[]; at_risk: UnprotectedItem[] }>;
  items: UnprotectedItem[];
  at_risk_items: UnprotectedItem[];
}

const WorkloadIcon = ({ type, className }: { type: string; className?: string }) => {
  switch (type) {
    case 'exchange': return <Mail className={className || 'w-4 h-4 text-blue-500'} />;
    case 'onedrive': return <HardDrive className={className || 'w-4 h-4 text-purple-500'} />;
    case 'sharepoint': return <Globe className={className || 'w-4 h-4 text-green-500'} />;
    case 'teams': return <MessageSquare className={className || 'w-4 h-4 text-pink-500'} />;
    case 'entra_id': return <Shield className={className || 'w-4 h-4 text-amber-500'} />;
    default: return <Shield className={className || 'w-4 h-4 text-gray-500'} />;
  }
};

export default function Dashboard() {
  const [showUnprotected, setShowUnprotected] = useState(false);
  const [expandedWorkloads, setExpandedWorkloads] = useState<string[]>([]);

  const { data: summary } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => api.get<DashboardSummary>('/dashboard/summary'),
    refetchInterval: 30000,
  });

  const { data: activityData } = useQuery({
    queryKey: ['dashboard-activity'],
    queryFn: () => api.get<{ activity: ActivityData[] }>('/dashboard/activity?days=7'),
  });

  const { data: compliance } = useQuery({
    queryKey: ['dashboard-compliance'],
    queryFn: () => api.get<{ compliance_rate: number; compliant: number; non_compliant: number; pending_first_backup: number; violations: any[] }>('/dashboard/compliance'),
  });

  const { data: unprotectedData } = useQuery({
    queryKey: ['dashboard-unprotected'],
    queryFn: () => api.get<UnprotectedData>('/dashboard/unprotected'),
    refetchInterval: 30000,
  });

  const { data: healthData } = useQuery({
    queryKey: ['health-score'],
    queryFn: () => api.get<{ score: number; components: any; details: any }>('/health/score?tenant_id=2'),
    refetchInterval: 60000,
  });

  const totalExposed = (unprotectedData?.total_unprotected ?? 0) + (unprotectedData?.total_at_risk ?? 0);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">M365 Vault Overview</p>
      </div>

      {/* Stats cards */}
      {/* Health Score Banner */}
      {healthData && (
        <div className={`mb-6 rounded-xl border p-4 flex items-center gap-4 ${
          healthData.score >= 80 ? 'bg-green-50 border-green-200' :
          healthData.score >= 50 ? 'bg-yellow-50 border-yellow-200' :
          'bg-red-50 border-red-200'
        }`}>
          <div className={`text-3xl font-bold ${
            healthData.score >= 80 ? 'text-green-700' :
            healthData.score >= 50 ? 'text-yellow-700' :
            'text-red-700'
          }`}>
            {healthData.score}
          </div>
          <div>
            <p className="font-semibold text-gray-800">Health Score</p>
            <p className="text-xs text-gray-500">
              Success: {healthData.components.success_rate}% | SLA: {healthData.components.sla_adherence}% | Anomalies: {healthData.details.active_anomalies}
            </p>
          </div>
          <Heart className={`w-6 h-6 ml-auto ${
            healthData.score >= 80 ? 'text-green-500' :
            healthData.score >= 50 ? 'text-yellow-500' :
            'text-red-500'
          }`} />
        </div>
      )}

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <StatCard
          title="Total Protected"
          value={summary?.total_protected ?? 0}
          subtitle={`${summary?.protection_rate ?? 0}% coverage`}
          icon={Shield}
          color="green"
        />
        <StatCard
          title="Exchange"
          value={summary?.workloads?.exchange?.total ?? 0}
          subtitle={`${summary?.workloads?.exchange?.protected ?? 0} protected`}
          icon={Mail}
          color="blue"
        />
        <StatCard
          title="OneDrive"
          value={summary?.workloads?.onedrive?.total ?? 0}
          subtitle={`${summary?.workloads?.onedrive?.protected ?? 0} protected`}
          icon={HardDrive}
          color="purple"
        />
        <StatCard
          title="SharePoint"
          value={summary?.workloads?.sharepoint?.total ?? 0}
          subtitle={`${summary?.workloads?.sharepoint?.protected ?? 0} protected`}
          icon={Globe}
          color="indigo"
        />
        <StatCard
          title="Teams"
          value={summary?.workloads?.teams?.total ?? 0}
          subtitle={`${summary?.workloads?.teams?.protected ?? 0} protected`}
          icon={MessageSquare}
          color="red"
        />
        <StatCard
          title="Entra ID"
          value={summary?.workloads?.entra_id?.total ?? 0}
          subtitle={`${summary?.workloads?.entra_id?.protected ?? 0} protected`}
          icon={Shield}
          color="amber"
        />
      </div>

      {/* Second row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          title="Backups (24h)"
          value={summary?.jobs_24h?.backup_total ?? 0}
          subtitle={`${summary?.jobs_24h?.backup_successful ?? 0} successful`}
          icon={CheckCircle}
          color="green"
        />
        <StatCard
          title="Failed (24h)"
          value={summary?.jobs_24h?.backup_failed ?? 0}
          icon={XCircle}
          color="red"
        />
        <StatCard
          title="Total Snapshots"
          value={summary?.snapshots?.total ?? 0}
          subtitle={`${summary?.snapshots?.total_size_gb ?? 0} GB`}
          icon={Database}
          color="blue"
        />
        <StatCard
          title="SLA Compliance"
          value={`${compliance?.compliance_rate ?? 100}%`}
          subtitle={`${compliance?.non_compliant ?? 0} violations`}
          icon={Activity}
          color={compliance?.compliance_rate === 100 ? 'green' : 'yellow'}
        />
      </div>

      {/* Unprotected & At-Risk Items — Collapsible Card */}
      {totalExposed > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl mb-6 shadow-sm overflow-hidden">
          {/* Card Header — always visible, click to expand/collapse */}
          <button
            onClick={() => setShowUnprotected(!showUnprotected)}
            className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="p-2.5 bg-amber-100 rounded-xl">
                  <ShieldOff className="w-5 h-5 text-amber-600" />
                </div>
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                  {totalExposed}
                </span>
              </div>
              <div className="text-left">
                <h3 className="text-base font-semibold text-gray-900">Attention Required</h3>
                <div className="flex items-center gap-3 mt-0.5">
                  {unprotectedData!.total_unprotected > 0 && (
                    <span className="inline-flex items-center gap-1 text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full font-medium">
                      <ShieldOff className="w-3 h-3" />
                      {unprotectedData!.total_unprotected} unprotected
                    </span>
                  )}
                  {unprotectedData!.total_at_risk > 0 && (
                    <span className="inline-flex items-center gap-1 text-xs text-red-700 bg-red-50 px-2 py-0.5 rounded-full font-medium">
                      <AlertTriangle className="w-3 h-3" />
                      {unprotectedData!.total_at_risk} at risk
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400 hidden sm:inline">
                {showUnprotected ? 'Hide details' : 'Show details'}
              </span>
              <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${showUnprotected ? 'rotate-180' : ''}`} />
            </div>
          </button>

          {/* Expandable Content */}
          <div className={`transition-all duration-300 ease-in-out ${showUnprotected ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0 overflow-hidden'}`}>
            <div className="px-5 pb-5 space-y-3">

              {/* Workload-grouped sections */}
              {unprotectedData?.by_workload && Object.entries(unprotectedData.by_workload).map(([workload, data]) => {
                const items = [...(data.unprotected || []), ...(data.at_risk || [])];
                if (items.length === 0) return null;
                const isExpanded = expandedWorkloads.includes(workload);

                return (
                  <div key={workload} className="border border-gray-200 rounded-lg overflow-hidden">
                    {/* Workload section header */}
                    <button
                      onClick={() => setExpandedWorkloads(prev =>
                        prev.includes(workload) ? prev.filter(w => w !== workload) : [...prev, workload]
                      )}
                      className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex items-center gap-2.5">
                        <WorkloadIcon type={workload} className="w-4.5 h-4.5" />
                        <span className="text-sm font-semibold text-gray-800 capitalize">{workload}</span>
                        <span className="text-xs text-gray-500 bg-white px-2 py-0.5 rounded-full border border-gray-200">
                          {items.length} item{items.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {data.unprotected?.length > 0 && (
                          <span className="w-2 h-2 rounded-full bg-amber-400" title="Unprotected" />
                        )}
                        {data.at_risk?.length > 0 && (
                          <span className="w-2 h-2 rounded-full bg-red-400" title="At risk" />
                        )}
                        <ChevronRight className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`} />
                      </div>
                    </button>

                    {/* Workload items list */}
                    <div className={`transition-all duration-200 ease-in-out ${isExpanded ? 'max-h-[600px]' : 'max-h-0'} overflow-hidden`}>
                      <div className="divide-y divide-gray-100">
                        {/* Unprotected items */}
                        {data.unprotected?.map(item => (
                          <div key={`unp-${item.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-amber-50/50 transition-colors">
                            <div className="w-1 h-8 rounded-full bg-amber-400 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-gray-900 truncate">{item.display_name}</p>
                              <p className="text-xs text-gray-500 truncate">{item.email || item.site_url || workload}</p>
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                                <ShieldOff className="w-3 h-3" />
                                No policy
                              </span>
                            </div>
                          </div>
                        ))}

                        {/* At-risk items */}
                        {data.at_risk?.map(item => (
                          <div key={`risk-${item.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-red-50/30 transition-colors">
                            <div className="w-1 h-8 rounded-full bg-red-400 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-gray-900 truncate">{item.display_name}</p>
                              <p className="text-xs text-gray-500 truncate">{item.email || item.site_url || workload}</p>
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                                <AlertTriangle className="w-3 h-3" />
                                Failed
                              </span>
                              {item.last_backup_at && (
                                <span className="text-xs text-gray-400">
                                  {new Date(item.last_backup_at).toLocaleDateString()}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Legend */}
              <div className="flex items-center gap-4 pt-2 border-t border-gray-100">
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  No SLA policy assigned
                </div>
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <span className="w-2 h-2 rounded-full bg-red-400" />
                  Last backup failed
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SLA Compliance violations */}
      {compliance && compliance.non_compliant > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-5 mb-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-red-100 rounded-lg">
              <ShieldAlert className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-red-900">SLA Violations</h3>
              <p className="text-sm text-red-700">{compliance.non_compliant} objects are overdue for backup</p>
            </div>
          </div>
          <div className="bg-white rounded-lg border border-red-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-red-50/50 border-b border-red-200">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-red-800">Object</th>
                  <th className="px-4 py-2 text-left font-medium text-red-800">Workload</th>
                  <th className="px-4 py-2 text-left font-medium text-red-800">SLA Policy</th>
                  <th className="px-4 py-2 text-left font-medium text-red-800">Last Backup</th>
                  <th className="px-4 py-2 text-left font-medium text-red-800">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {compliance.violations.map((v: any, i: number) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-medium text-gray-900">{v.object_name}</td>
                    <td className="px-4 py-2.5">
                      <span className="flex items-center gap-1.5 capitalize">
                        <WorkloadIcon type={v.workload} />
                        {v.workload}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-600">{v.sla_name}</td>
                    <td className="px-4 py-2.5 text-gray-500">{v.last_backup === 'Never' ? 'Never' : new Date(v.last_backup).toLocaleString()}</td>
                    <td className="px-4 py-2.5">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        v.reason === 'initial_backup_failed' ? 'bg-red-100 text-red-700' :
                        v.reason === 'never_backed_up' ? 'bg-gray-100 text-gray-700' :
                        'bg-orange-100 text-orange-700'
                      }`}>
                        {(v.reason || 'overdue').replace(/_/g, ' ')}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Backup Activity Chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm mb-6">
        <h3 className="text-lg font-semibold mb-4">Backup Activity (7 Days)</h3>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={activityData?.activity || []}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} tickFormatter={v => v.slice(5)} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="backups_successful" fill="#10b981" name="Successful" radius={[4,4,0,0]} />
            <Bar dataKey="restores" fill="#3b82f6" name="Restores" radius={[4,4,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
