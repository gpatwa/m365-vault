import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Shield, Activity, AlertTriangle, Database, TrendingUp,
  Lock, Eye, FileCheck, CreditCard, Loader2, ArrowRight,
  Globe, MessageSquare, CheckCircle, Circle, ChevronDown, ChevronUp,
  Link2, Search, ShieldCheck,
} from 'lucide-react';
import { useOnboarding, type OnboardingStep } from '../contexts/OnboardingContext';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../api/client';
import { PRIORITY_WORKLOADS as WORKLOADS } from '../config/workloads';
import { getActivePlatformLabel } from '../config/platforms';
import { useTenantId, useTenantInfo } from '../hooks/useTenant';
import { HeroSummaryBar, ActionBanner, PlatformCard } from '../components/design-system';
import type { HeroStat } from '../components/design-system/HeroSummaryBar';
import type { ActionItem } from '../components/design-system/ActionBanner';
import type { WorkloadStat } from '../components/design-system/PlatformCard';
import type { DashboardSummary, ActivityData } from '../types';

// Stripe-style Onboarding Checklist

const CHECKLIST_STEPS: {
  key: OnboardingStep;
  title: string;
  description: string;
  action: string;
  path: string;
  icon: any;
}[] = [
  {
    key: 'create_account',
    title: 'Create your account',
    description: 'Sign up and set your admin credentials.',
    action: 'Done',
    path: '/',
    icon: CheckCircle,
  },
  {
    key: 'connect_platform',
    title: 'Connect your SaaS platform',
    description: 'Link your Microsoft 365 tenant with one-click OAuth.',
    action: 'Connect',
    path: '/onboard',
    icon: Link2,
  },
  {
    key: 'discover_workloads',
    title: 'Discover your workloads',
    description: 'We automatically find mailboxes, drives, sites, teams, and identity objects.',
    action: 'Run Discovery',
    path: '/tenants',
    icon: Search,
  },
  {
    key: 'assign_protection',
    title: 'Assign backup protection',
    description: 'Choose a backup schedule and protect your data.',
    action: 'Protect',
    path: '/sla-policies',
    icon: Shield,
  },
  {
    key: 'first_backup',
    title: 'Run your first backup',
    description: 'Pick a workload and verify your first backup works. Exchange is fastest.',
    action: 'inline',
    path: '',
    icon: Database,
  },
  {
    key: 'explore_recovery',
    title: 'Explore recovery capabilities',
    description: 'See your recovery readiness score and simulate a restore.',
    action: 'Explore',
    path: '/recovery',
    icon: ShieldCheck,
  },
];

const BACKUP_WORKLOADS = [
  { key: 'entra_id', label: 'Entra ID', desc: 'Users, groups, policies', icon: '🔑', endpoint: '/entra-id/backup', fast: true },
  { key: 'exchange', label: 'Exchange', desc: 'Emails, calendar, contacts', icon: '✉️', endpoint: '/exchange/backup-all', fast: true },
];

function OnboardingChecklist() {
  const { steps, completedCount, totalSteps, percentComplete, isComplete, completeStep } = useOnboarding();
  const navigate = useNavigate();
  // Start collapsed if user is past onboarding (5+ steps or fully complete)
  const [expanded, setExpanded] = useState(completedCount < 5 && !isComplete);
  const [dismissed, setDismissed] = useState(false);
  // Load from server session
  useEffect(() => {
    api.get<any>('/auth/session')
      .then(s => { if (s?.preferences?.checklist_dismissed) setDismissed(true); })
      .catch(() => {});
  }, []);
  const [backupRunning, setBackupRunning] = useState<Record<string, 'idle' | 'running' | 'done' | 'error'>>({});
  const tenantId = useTenantId();

  const triggerBackup = async (workload: typeof BACKUP_WORKLOADS[0]) => {
    if (!tenantId) return;
    setBackupRunning(prev => ({ ...prev, [workload.key]: 'running' }));
    try {
      await api.post(`${workload.endpoint}?tenant_id=${tenantId}`);
      setBackupRunning(prev => ({ ...prev, [workload.key]: 'done' }));
      completeStep('first_backup');
    } catch {
      setBackupRunning(prev => ({ ...prev, [workload.key]: 'error' }));
    }
  };

  const anyBackupDone = Object.values(backupRunning).some(s => s === 'done');

  // Auto-hide when: explicitly dismissed, fully complete, or user is clearly past onboarding
  // A user with 5+ steps done (has backups running) doesn't need "Getting started"
  if (dismissed || (isComplete && !expanded) || (completedCount >= 5 && !expanded)) return null;

  const handleDismiss = () => {
    setDismissed(true);
    api.put('/auth/preferences/checklist_dismissed', { value: 'true' }).catch(() => {});
  };

  return (
    <div className="mb-6 bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="relative">
            <svg className="w-10 h-10 -rotate-90" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="15" fill="none" stroke="var(--border)" strokeWidth="3" />
              <circle
                cx="18" cy="18" r="15" fill="none"
                stroke={isComplete ? '#22c55e' : '#3b82f6'}
                strokeWidth="3"
                strokeDasharray={`${percentComplete} 100`}
                strokeLinecap="round"
              />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-muted-foreground">
              {completedCount}/{totalSteps}
            </span>
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-foreground text-sm">
              {isComplete ? 'Setup complete! 🎉' : 'Getting started with KavachIQ'}
            </h3>
            <p className="text-xs text-muted-foreground">
              {isComplete
                ? 'Your data is fully protected.'
                : `${completedCount} of ${totalSteps} steps complete`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isComplete && (
            <button
              onClick={(e) => { e.stopPropagation(); handleDismiss(); }}
              className="text-xs text-muted-foreground hover:text-foreground px-2 py-1"
            >
              Dismiss
            </button>
          )}
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {/* Expanded checklist */}
      {expanded && (
        <div className="border-t border-border">
          {CHECKLIST_STEPS.map((step, i) => {
            const done = steps[step.key];
            const isCurrent = !done && CHECKLIST_STEPS.slice(0, i).every(s => steps[s.key]);
            return (
              <div
                key={step.key}
                className={`flex items-center gap-3 px-4 py-3 border-b border-border/50 last:border-0 transition-colors ${
                  isCurrent ? 'bg-blue-500/5' : ''
                }`}
              >
                {/* Status indicator */}
                <div className="flex-shrink-0">
                  {done ? (
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  ) : isCurrent ? (
                    <div className="w-5 h-5 rounded-full border-2 border-blue-500 bg-blue-500/10 flex items-center justify-center">
                      <div className="w-2 h-2 bg-blue-500/100 rounded-full" />
                    </div>
                  ) : (
                    <Circle className="w-5 h-5 text-muted-foreground/40" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className={`text-sm font-medium ${done ? 'text-muted-foreground line-through' : 'text-foreground'}`}>
                    {step.title}
                  </div>
                  {isCurrent && step.key !== 'first_backup' && (
                    <p className="text-xs text-muted-foreground mt-0.5">{step.description}</p>
                  )}

                  {/* Inline workload picker for first_backup step */}
                  {isCurrent && step.key === 'first_backup' && (
                    <div className="mt-2">
                      <p className="text-xs text-muted-foreground mb-2">{step.description}</p>
                      <div className="flex flex-wrap gap-2">
                        {BACKUP_WORKLOADS.map(wl => {
                          const status = backupRunning[wl.key] || 'idle';
                          return (
                            <button
                              key={wl.key}
                              onClick={() => triggerBackup(wl)}
                              disabled={status === 'running' || status === 'done'}
                              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                                status === 'done'
                                  ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                                  : status === 'running'
                                  ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse'
                                  : status === 'error'
                                  ? 'bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20'
                                  : 'bg-muted text-muted-foreground border border-border hover:bg-accent'
                              }`}
                            >
                              <span>{wl.icon}</span>
                              <span>{wl.label}</span>
                              {status === 'running' && <Loader2 className="w-3 h-3 animate-spin" />}
                              {status === 'done' && <CheckCircle className="w-3 h-3 text-green-400" />}
                              {wl.fast && status === 'idle' && (
                                <span className="text-[9px] text-muted-foreground ml-0.5">fast</span>
                              )}
                            </button>
                          );
                        })}
                      </div>
                      {anyBackupDone && (
                        <p className="text-[10px] text-green-400 mt-1.5 flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" /> Backup verified — your data is protected!
                        </p>
                      )}
                    </div>
                  )}
                </div>

                {/* Action button */}
                {!done && isCurrent && step.action !== 'inline' && (
                  <button
                    onClick={() => {
                      if (step.key === 'explore_recovery') completeStep('explore_recovery');
                      navigate(step.path);
                    }}
                    className="flex-shrink-0 px-3 py-1.5 bg-primary text-primary-foreground rounded-lg text-xs font-semibold hover:bg-primary/90 transition-colors flex items-center gap-1"
                  >
                    {step.action} <ArrowRight className="w-3 h-3" />
                  </button>
                )}
                {done && (
                  <span className="text-[10px] text-green-400 font-medium flex-shrink-0">Done</span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const tenantId = useTenantId();
  const { isDemoTenant, tenantName } = useTenantInfo();

  // Data Fetching

  // Dashboard uses ACTIVE cadence (30s global default) — no overrides needed
  const { data: summary } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => api.get<DashboardSummary>('/dashboard/summary'),
  });

  const { data: activityData } = useQuery({
    queryKey: ['dashboard-activity'],
    queryFn: () => api.get<{ activity: ActivityData[] }>('/dashboard/activity?days=7'),
  });

  const { data: healthData } = useQuery({
    queryKey: ['health-score', tenantId],
    queryFn: () => api.get<{ score: number; components: any; details: any }>(`/health/score?tenant_id=${tenantId}`),
    enabled: !!tenantId,
  });

  const { data: compliance } = useQuery({
    queryKey: ['dashboard-compliance'],
    queryFn: () => api.get<{ compliance_rate: number; non_compliant: number; violations: any[] }>('/dashboard/compliance'),
  });

  const { data: unprotectedData } = useQuery({
    queryKey: ['dashboard-unprotected'],
    queryFn: () => api.get<{ total_unprotected: number; total_at_risk: number }>('/dashboard/unprotected'),
  });

  const { data: licenseData } = useQuery({
    queryKey: ['usage-license'],
    queryFn: () => api.get<any>('/usage/license'),
    staleTime: 300_000, // STATIC: license/usage doesn't change often
    refetchInterval: 300_000,
  });

  // Computed: Hero Stats

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
        value: summary?.jobs_24h?.backup_successful ?? 0,
        subtitle: (summary?.jobs_24h?.backup_failed ?? 0) > 0
          ? `${summary?.jobs_24h?.backup_failed} failed`
          : `${summary?.jobs_24h?.backup_successful ?? 0} successful, 0 failed`,
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

  // Computed: Action Banners

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
        message: `${failed} protection gap${failed > 1 ? 's' : ''} detected in the last 24 hours`,
        action: { label: 'View Gaps', onClick: () => navigate('/failed-items') },
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

  // Computed: Platform Card

  const workloadStats: WorkloadStat[] = useMemo(() => {
    if (!summary?.workloads) return [];
    return WORKLOADS.map(wl => {
      const data = summary.workloads[wl.key] || { total: 0, protected: 0 };
      return {
        key: wl.key,
        label: wl.label,
        icon: wl.icon,
        iconColor: wl.iconColor || 'text-muted-foreground',
        protected: data.protected || 0,
        total: data.total || 0,
        lastBackup: (data as any).last_backup || null,
        itemCount: (data as any).item_count || 0,
        path: `/${wl.key.replace('_', '-')}`,
      };
    });
  }, [summary]);

  const platformTotalProtected = workloadStats.reduce((s, w) => s + w.protected, 0);
  const platformTotalObjects = workloadStats.reduce((s, w) => s + w.total, 0);

  // Computed: Trend chart data

  const trendData = useMemo(() => {
    if (!activityData?.activity) return [];
    const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    return activityData.activity.map((a: any) => {
      const d = new Date(a.date);
      const success = a.backups_successful || 0;
      const failed = (a.backups || 0) - success;
      return {
        day: dayLabels[d.getDay()],
        success,
        failed: Math.max(failed, 0),
      };
    });
  }, [activityData]);

  // Render

  const noTenants = !summary || summary.tenants === 0;
  const hasTenantsNoBackups = summary && summary.tenants > 0 && summary.total_protected === 0;
  const [connecting, setConnecting] = useState(false);

  const handleConnect = async (platform: string) => {
    setConnecting(true);
    try {
      const data: any = await api.get(`/onboard/connect/${platform}`);
      if (data.auth_url) window.location.href = data.auth_url;
    } catch (err) {
      console.error('Connect failed:', err);
      setConnecting(false);
    }
  };

  // STATE 1: No tenants — Full onboarding experience
  if (noTenants) {
    return (
      <div className="max-w-3xl mx-auto py-4">
        {/* Hero */}
        <div className="text-center mb-10">
          <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-3xl flex items-center justify-center mx-auto mb-5 shadow-lg shadow-blue-500/20">
            <Shield className="w-10 h-10 text-foreground" />
          </div>
          <h1 className="text-3xl font-extrabold text-foreground mb-3">Welcome to KavachIQ</h1>
          <p className="text-lg text-muted-foreground max-w-lg mx-auto">
            Protect your SaaS data in minutes. Connect your platform, discover workloads, and start backing up automatically.
          </p>
        </div>

        {/* Connect platform */}
        <div className="bg-card rounded-2xl border border-border shadow-sm p-8 mb-6">
          <h2 className="text-lg font-bold text-foreground mb-1">Step 1: Connect Your Platform</h2>
          <p className="text-sm text-muted-foreground mb-6">One-click OAuth — no credentials to copy or paste.</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Microsoft 365 — active */}
            <button
              onClick={() => handleConnect('microsoft365')}
              disabled={connecting}
              className="relative p-5 rounded-xl border-2 border-blue-500/30 bg-blue-500/5 hover:border-blue-500/50 hover:shadow-md transition-all text-left group"
            >
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-card border border-border flex items-center justify-center shadow-sm">
                  <svg className="w-6 h-6" viewBox="0 0 21 21"><path d="M0 0h10v10H0z" fill="#f25022"/><path d="M11 0h10v10H11z" fill="#7fba00"/><path d="M0 11h10v10H0z" fill="#00a4ef"/><path d="M11 11h10v10H11z" fill="#ffb900"/></svg>
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-foreground">Microsoft 365</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">Entra ID, Exchange + 3 more workloads</p>
                  <div className="mt-2 flex items-center gap-1 text-sm font-medium text-primary">
                    {connecting ? (
                      <><Loader2 className="w-4 h-4 animate-spin" /> Connecting...</>
                    ) : (
                      <>Connect <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" /></>
                    )}
                  </div>
                </div>
              </div>
            </button>

            {/* Coming soon platforms */}
            {[
              { name: 'Google Workspace', desc: 'Gmail, Drive, Calendar, Chat', icon: Globe, color: 'green' },
              { name: 'Salesforce', desc: 'Accounts, Contacts, Opportunities', icon: Database, color: 'sky' },
              { name: 'Slack', desc: 'Channels, Messages, Files', icon: MessageSquare, color: 'purple' },
            ].map(p => (
              <div key={p.name} className="p-5 rounded-xl border-2 border-border bg-muted/50 opacity-60 text-left relative">
                <span className="absolute top-3 right-3 px-2 py-0.5 bg-muted text-muted-foreground text-[9px] font-semibold rounded-full">Coming Soon</span>
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-xl bg-card border border-border flex items-center justify-center">
                    <p.icon className="w-6 h-6 text-muted-foreground" />
                  </div>
                  <div>
                    <h3 className="font-bold text-muted-foreground">{p.name}</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">{p.desc}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* What happens after connecting */}
        <div className="bg-muted rounded-2xl border border-border p-6">
          <h3 className="font-bold text-foreground mb-4">What happens when you connect?</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { step: '1', title: 'Discover', desc: 'We find all your mailboxes, drives, sites, teams, and identity objects.', icon: Eye, color: 'blue' },
              { step: '2', title: 'Protect', desc: 'Choose a backup schedule. One click protects everything.', icon: Shield, color: 'green' },
              { step: '3', title: 'Recover', desc: 'Instant restore if anything is deleted, corrupted, or encrypted.', icon: Activity, color: 'purple' },
            ].map(s => (
              <div key={s.step} className="flex items-start gap-3">
                <div className={`w-8 h-8 rounded-lg bg-${s.color}-500/10 flex items-center justify-center flex-shrink-0`}>
                  <s.icon className={`w-4 h-4 text-${s.color}-400`} />
                </div>
                <div>
                  <div className="font-semibold text-foreground text-sm">{s.title}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{s.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="text-center text-xs text-muted-foreground mt-6">
          KavachIQ uses OAuth admin consent — your credentials are never stored. Only read-only permissions for backup.
        </p>
      </div>
    );
  }

  // STATE 2+3: Tenants exist

  return (
    <div>
      {/* Action banner for unprotected state */}
      {hasTenantsNoBackups && (
        <div className="mb-6 bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
          <div className="flex-1">
            <p className="font-semibold text-amber-400 text-sm">Your data isn't protected yet</p>
            <p className="text-xs text-amber-400/70">Assign an SLA policy to start automatic backups.</p>
          </div>
          <button onClick={() => navigate('/sla-policies')} className="px-3 py-1.5 bg-amber-600 text-white rounded-lg text-xs font-semibold hover:bg-amber-500/100">
            Protect Now →
          </button>
        </div>
      )}

      {/* Sandbox Banner — shown when viewing demo tenant data */}
      {isDemoTenant && (
        <div className="mb-6 bg-gradient-to-r from-teal-500/10 to-cyan-500/10 border border-teal-500/20 rounded-xl p-4 flex items-center gap-3">
          <div className="p-2 bg-teal-500/20 rounded-lg flex-shrink-0">
            <Eye className="w-5 h-5 text-teal-400" />
          </div>
          <div className="flex-1">
            <p className="font-semibold text-teal-300 text-sm">
              You're viewing demo data{tenantName ? ` for ${tenantName}` : ''}
            </p>
            <p className="text-xs text-teal-400/70">
              Explore the product with realistic sample data. Connect your real Microsoft 365 tenant to protect actual data.
            </p>
          </div>
          <button
            onClick={() => navigate('/onboard')}
            className="px-4 py-2 bg-teal-600 text-white rounded-lg text-xs font-semibold hover:bg-teal-500 flex items-center gap-1.5 whitespace-nowrap"
          >
            Connect Real M365 <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Stripe-style Onboarding Checklist */}
      <OnboardingChecklist />

      {/* STATE 3: Normal operational dashboard */}

      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground">SaaS Data Protection Overview</p>
      </div>


      {/* Row 1: Hero Stats */}
      <HeroSummaryBar stats={heroStats} />

      {/* Action Banners */}
      <ActionBanner items={actionItems} />

      {/* Row 2: Platform Card */}
      <div className="mb-6">
        <PlatformCard
          name={getActivePlatformLabel()}
          icon={
            <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
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
        <div className="bg-card border border-border rounded-xl shadow-sm">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-semibold text-foreground">License & Usage</h3>
            </div>
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
              licenseData?.tier === 'enterprise' ? 'bg-purple-500/10 text-purple-400' :
              licenseData?.tier === 'professional' ? 'bg-blue-500/10 text-blue-400' :
              'bg-muted text-muted-foreground'
            }`}>
              {licenseData?.tier_label || 'Community'}
            </span>
          </div>
          <div className="p-4 space-y-3">
            {(licenseData?.usage || []).map((u: any, i: number) => (
              <div key={i}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-muted-foreground">{u.name}</span>
                  <span className="text-xs font-semibold text-foreground">
                    {u.current}{u.limit > 0 ? ` / ${u.limit}` : ''}
                  </span>
                </div>
                {u.limit > 0 && (
                  <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        u.usage_percent >= 90 ? 'bg-red-500/100' :
                        u.usage_percent >= 70 ? 'bg-amber-500/100' :
                        'bg-blue-500/100'
                      }`}
                      style={{ width: `${Math.min(u.usage_percent, 100)}%` }}
                    />
                  </div>
                )}
              </div>
            ))}

            {/* Storage — merged into license card */}
            <div className="pt-2 border-t border-border">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">Storage</p>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <p className="text-lg font-bold text-foreground">{summary?.snapshots?.total_size_gb ?? 0} GB</p>
                  <p className="text-[10px] text-muted-foreground">Backup Size</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-foreground">{summary?.snapshots?.total ?? 0}</p>
                  <p className="text-[10px] text-muted-foreground">Snapshots</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-foreground">{licenseData?.retention_days ?? 30}d</p>
                  <p className="text-[10px] text-muted-foreground">Retention</p>
                </div>
              </div>
            </div>

            {licenseData?.features && (
              <div className="pt-2 border-t border-border">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5">Included Workloads</p>
                <div className="flex flex-wrap gap-1">
                  {licenseData.features.map((f: string) => (
                    <span key={f} className="text-[10px] px-1.5 py-0.5 bg-muted border border-border rounded text-muted-foreground capitalize">
                      {f.replace('_', ' ')}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <button
              onClick={() => navigate('/usage')}
              className="w-full text-xs text-primary hover:text-primary/80 font-medium pt-1"
            >
              View full usage details →
            </button>
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl shadow-sm">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">7-Day Backup Trend</h3>
            <TrendingUp className="w-4 h-4 text-muted-foreground" />
          </div>
          <div className="p-4 h-64">
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trendData} barCategoryGap="20%">
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                  <XAxis dataKey="day" tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid var(--border)', background: 'var(--card)', color: 'var(--foreground)' }}
                    cursor={{ fill: 'var(--muted)' }}
                  />
                  <Bar dataKey="success" fill="#22c55e" radius={[3, 3, 0, 0]} name="Successful" />
                  <Bar dataKey="failed" fill="#ef4444" radius={[3, 3, 0, 0]} name="Failed" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                No backup data yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Row 4: Compliance */}
      <div className="mb-6">
        <div className="bg-card border border-border rounded-xl shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <FileCheck className="w-4 h-4 text-green-400" />
            <h3 className="text-sm font-semibold text-foreground">Compliance</h3>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-muted-foreground">SLA Adherence</p>
              <p className={`text-xl font-bold ${(compliance?.compliance_rate ?? 100) === 100 ? 'text-green-400' : 'text-amber-400'}`}>
                {compliance?.compliance_rate ?? 100}%
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Violations</p>
              <p className={`text-xl font-bold ${(compliance?.non_compliant ?? 0) > 0 ? 'text-red-400' : 'text-green-400'}`}>
                {compliance?.non_compliant ?? 0}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Lock className="w-3.5 h-3.5 text-blue-400" />
              <div>
                <p className="text-xs text-muted-foreground">WORM Locked</p>
                <p className="text-sm font-semibold text-muted-foreground">Active</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Eye className="w-3.5 h-3.5 text-purple-400" />
              <div>
                <p className="text-xs text-muted-foreground">Sensitive Data</p>
                <p className="text-sm font-semibold text-muted-foreground">Monitored</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
