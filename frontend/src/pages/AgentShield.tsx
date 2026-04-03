import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Shield, Bot, AlertTriangle, Activity, Eye, Loader2, RefreshCw } from 'lucide-react';
import { api } from '../api/client';
import { useTenantId } from '../hooks/useTenant';
import Breadcrumb from '../components/design-system/Breadcrumb';
import HeroSummaryBar, { type HeroStat } from '../components/design-system/HeroSummaryBar';

interface AgentProfile {
  id: number; agent_id: string; agent_name: string; agent_type: string;
  first_seen: string; last_seen: string; total_actions: number;
  is_managed: boolean; is_shadow: boolean; risk_score: number;
  permissions: string[];
}

interface AgentActivityItem {
  id: number; agent_name: string; agent_type: string; action: string;
  resource_type: string; resource_name: string; resource_count: number;
  risk_level: string; detected_at: string;
}

const TYPE_COLORS: Record<string, string> = {
  copilot: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  custom: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  openclaw: 'bg-red-500/10 text-red-400 border-red-500/20',
  unknown: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
};

const RISK_COLORS: Record<string, string> = {
  low: 'text-green-400',
  medium: 'text-amber-400',
  high: 'text-orange-400',
  critical: 'text-red-400',
};

const ACTION_ICONS: Record<string, string> = {
  read: '👁️', modify: '✏️', delete: '🗑️', permission_change: '🔑',
};

export default function AgentShield() {
  const tenantId = useTenantId();
  const qc = useQueryClient();
  const [tab, setTab] = useState<'profiles' | 'activity'>('profiles');

  const { data: dashboard } = useQuery({
    queryKey: ['agent-dashboard', tenantId],
    queryFn: () => api.get<any>(`/agents/dashboard?tenant_id=${tenantId}`),
    enabled: !!tenantId,
  });

  const { data: profiles } = useQuery({
    queryKey: ['agent-profiles', tenantId],
    queryFn: () => api.get<{ profiles: AgentProfile[] }>(`/agents/profiles?tenant_id=${tenantId}`),
    enabled: !!tenantId,
  });

  const { data: activity } = useQuery({
    queryKey: ['agent-activity', tenantId],
    queryFn: () => api.get<{ items: AgentActivityItem[]; total: number }>(`/agents/activity?tenant_id=${tenantId}`),
    enabled: !!tenantId && tab === 'activity',
  });

  const scanMutation = useMutation({
    mutationFn: () => api.post<any>(`/agents/scan?tenant_id=${tenantId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agent-dashboard'] });
      qc.invalidateQueries({ queryKey: ['agent-profiles'] });
      qc.invalidateQueries({ queryKey: ['agent-activity'] });
    },
  });

  const d = dashboard || { total_agents: 0, shadow_agents: 0, actions_24h: 0, avg_risk_score: 0, high_risk_actions_24h: 0 };

  const heroStats: HeroStat[] = [
    { label: 'Total Agents', value: d.total_agents, color: 'blue', icon: Bot },
    { label: 'Shadow Agents', value: d.shadow_agents, color: d.shadow_agents > 0 ? 'red' : 'green', icon: AlertTriangle },
    { label: 'Actions (24h)', value: d.actions_24h, subtitle: `${d.high_risk_actions_24h} high risk`, color: 'amber', icon: Activity },
    { label: 'Risk Score', value: d.avg_risk_score, color: d.avg_risk_score > 60 ? 'red' : d.avg_risk_score > 30 ? 'amber' : 'green', icon: Shield },
  ];

  return (
    <div>
      <Breadcrumb items={[{ label: 'Intelligence', path: '/smart-engine' }, { label: 'Agent Shield' }]} />

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-violet-500/10 rounded-xl flex items-center justify-center">
            <Bot className="w-5 h-5 text-violet-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Agent Shield</h1>
            <p className="text-xs text-muted-foreground">Monitor AI agent activity, detect shadow agents, assess risk</p>
          </div>
        </div>
        <button
          onClick={() => scanMutation.mutate()}
          disabled={scanMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700 transition-colors disabled:opacity-50"
        >
          {scanMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          Scan Now
        </button>
      </div>

      <HeroSummaryBar stats={heroStats} />

      {/* Shadow agent alert */}
      {d.shadow_agents > 0 && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <p className="text-sm font-medium text-red-400">
              {d.shadow_agents} unmanaged agent{d.shadow_agents > 1 ? 's' : ''} detected — accessing M365 data without IT approval
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-4 mb-4 border-b border-border">
        <button onClick={() => setTab('profiles')}
          className={`pb-2 text-sm font-medium transition-colors ${tab === 'profiles' ? 'text-teal-500 border-b-2 border-teal-500' : 'text-muted-foreground'}`}>
          <Bot className="w-4 h-4 inline mr-1.5" /> Agent Profiles
        </button>
        <button onClick={() => setTab('activity')}
          className={`pb-2 text-sm font-medium transition-colors ${tab === 'activity' ? 'text-teal-500 border-b-2 border-teal-500' : 'text-muted-foreground'}`}>
          <Eye className="w-4 h-4 inline mr-1.5" /> Activity Log
        </button>
      </div>

      {/* Profiles tab */}
      {tab === 'profiles' && (
        <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Agent</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Type</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">Actions</th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">Risk</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Last Seen</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {(profiles?.profiles || []).map(p => (
                <tr key={p.id} className="hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-foreground">{p.agent_name}</div>
                    <div className="text-[10px] text-muted-foreground">{p.agent_id}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${TYPE_COLORS[p.agent_type] || TYPE_COLORS.unknown}`}>
                      {p.agent_type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {p.is_shadow ? (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-500/10 text-red-400 border border-red-500/20">Shadow</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-green-500/10 text-green-400 border border-green-500/20">Managed</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-foreground">{p.total_actions}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={`font-bold ${p.risk_score > 60 ? 'text-red-400' : p.risk_score > 30 ? 'text-amber-400' : 'text-green-400'}`}>
                      {p.risk_score}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">
                    {p.last_seen ? new Date(p.last_seen).toLocaleDateString() : '—'}
                  </td>
                </tr>
              ))}
              {(!profiles?.profiles || profiles.profiles.length === 0) && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                    No agents detected. Click "Scan Now" to check for agent activity.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Activity tab */}
      {tab === 'activity' && (
        <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Agent</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Action</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Resource</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Risk</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {(activity?.items || []).map(a => (
                <tr key={a.id} className="hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <span className="text-foreground font-medium">{a.agent_name}</span>
                    <span className={`ml-2 px-1.5 py-0.5 rounded text-[9px] font-semibold border ${TYPE_COLORS[a.agent_type] || TYPE_COLORS.unknown}`}>
                      {a.agent_type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="mr-1">{ACTION_ICONS[a.action] || '📋'}</span>
                    <span className="text-foreground">{a.action}</span>
                    {a.resource_count > 1 && <span className="text-muted-foreground ml-1">({a.resource_count})</span>}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    <span className="text-foreground">{a.resource_type}</span>
                    {a.resource_name && <span className="text-muted-foreground ml-1">— {a.resource_name}</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`font-semibold text-xs ${RISK_COLORS[a.risk_level] || 'text-muted-foreground'}`}>
                      {a.risk_level}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">
                    {a.detected_at ? new Date(a.detected_at).toLocaleString() : '—'}
                  </td>
                </tr>
              ))}
              {(!activity?.items || activity.items.length === 0) && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                    No agent activity recorded. Run a scan to detect agent actions.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
