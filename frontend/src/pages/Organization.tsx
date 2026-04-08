/**
 * Organization Settings — interactive workload lifecycle management.
 *
 * Shows: connection status, workload lifecycle states (disabled -> enabled ->
 * discovered -> protected), enable/disable actions, subscription limits.
 *
 * Dashboard = "Is my data safe?" (operational)
 * Organization = "What's connected and how do I change it?" (configuration)
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Shield, CheckCircle, AlertTriangle, Loader2,
  RefreshCw, Users, Settings, ArrowUpRight,
  Power, PowerOff,
} from 'lucide-react';
import { api } from '../api/client';
import { useTenantSwitcher } from '../hooks/useTenant';
import { useToast } from '../components/Toast';
import { useAuth } from '../contexts/AuthContext';
import { WORKLOADS, WORKLOAD_MAP, type WorkloadConfig } from '../config/workloads';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter,
} from '../components/ui/dialog';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface WorkloadStatus {
  workload: string;
  lifecycle_status: 'disabled' | 'enabled' | 'discovered' | 'protected' | 'paused';
  consent_status: string;
  backup_ready: boolean;
  restore_ready: boolean;
  enabled: boolean;
  client_id: string | null;
  error_message: string | null;
  created_at: string;
}

interface WorkloadStatusResponse {
  tenant_id: number;
  workloads: WorkloadStatus[];
}

interface SubscriptionInfo {
  subscription_tier: string;
  subscription_status: string;
}

interface EnableResponse {
  workloads_created: number;
  consent_urls: Record<string, string>;
  total_workload_apps: number;
}

interface DisableResponse {
  workload: string;
  enabled: boolean;
  lifecycle_status: string;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const TIER_LIMITS: Record<string, number> = {
  community: 2,
  professional: 5,
  business: 5,
  enterprise: 6,
};

const LIFECYCLE_STEPS = ['disabled', 'enabled', 'discovered', 'protected'] as const;

/* ------------------------------------------------------------------ */
/*  LifecycleProgress — 4-step visual indicator                        */
/* ------------------------------------------------------------------ */

function LifecycleProgress({ status }: { status: string }) {
  const currentIndex = LIFECYCLE_STEPS.indexOf(status as typeof LIFECYCLE_STEPS[number]);
  const activeIndex = currentIndex >= 0 ? currentIndex : 0;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="flex items-center gap-0">
        {LIFECYCLE_STEPS.map((step, i) => {
          const filled = i <= activeIndex;
          return (
            <div key={step} className="flex items-center">
              <div
                className={`w-2.5 h-2.5 rounded-full border-2 transition-colors ${
                  filled
                    ? 'bg-blue-500 border-blue-500'
                    : 'bg-transparent border-muted-foreground/40'
                }`}
              />
              {i < LIFECYCLE_STEPS.length - 1 && (
                <div
                  className={`w-4 h-0.5 transition-colors ${
                    i < activeIndex ? 'bg-blue-500' : 'bg-muted-foreground/20'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
      <span className="text-[10px] text-muted-foreground capitalize">
        {status === 'paused' ? 'paused' : LIFECYCLE_STEPS[activeIndex]}
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  WorkloadCard                                                       */
/* ------------------------------------------------------------------ */

function WorkloadCard({
  config,
  status,
  isAdmin,
  atLimit,
  onEnable,
  onDisable,
  enabling,
}: {
  config: WorkloadConfig;
  status: WorkloadStatus | null;
  isAdmin: boolean;
  atLimit: boolean;
  onEnable: (workload: string) => void;
  onDisable: (workload: string) => void;
  enabling: boolean;
}) {
  const Icon = config.icon;
  const lifecycleStatus = status?.lifecycle_status ?? 'disabled';
  const isDisabled = lifecycleStatus === 'disabled';

  return (
    <div className="bg-card rounded-xl border border-border p-5 flex items-center gap-4">
      {/* Left: icon + label */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <div className={`w-9 h-9 rounded-lg ${config.bgColor} flex items-center justify-center shrink-0`}>
          <Icon className={`w-4.5 h-4.5 ${config.textColor}`} />
        </div>
        <div className="min-w-0">
          <div className="font-medium text-foreground truncate">{config.label}</div>
          <div className="text-xs text-muted-foreground truncate">{config.description}</div>
        </div>
      </div>

      {/* Center: lifecycle progress */}
      <div className="shrink-0">
        <LifecycleProgress status={lifecycleStatus} />
      </div>

      {/* Right: action button */}
      {isAdmin && (
        <div className="shrink-0 ml-2">
          {isDisabled ? (
            <div className="relative group">
              <button
                onClick={() => onEnable(config.key)}
                disabled={atLimit || enabling}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
              >
                {enabling ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Power className="w-3.5 h-3.5" />
                )}
                Enable
              </button>
              {atLimit && (
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-popover border border-border rounded text-xs text-muted-foreground whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                  Subscription limit reached
                </div>
              )}
            </div>
          ) : (
            <button
              onClick={() => onDisable(config.key)}
              className="px-3 py-1.5 text-sm border border-border text-muted-foreground rounded-lg hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30 transition-colors flex items-center gap-1.5"
            >
              <PowerOff className="w-3.5 h-3.5" />
              Disable
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function Organization() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { selectedTenant } = useTenantSwitcher();
  const { user } = useAuth();
  const toast = useToast();

  const [checkingPerms, setCheckingPerms] = useState(false);
  const [disableTarget, setDisableTarget] = useState<string | null>(null);
  const [enablingWorkload, setEnablingWorkload] = useState<string | null>(null);

  const isAdmin = user?.role === 'admin' || user?.is_platform_admin === true;

  /* ---- Queries ---- */

  const { data: tenant, isLoading: tenantLoading } = useQuery({
    queryKey: ['org-tenant', selectedTenant?.id],
    queryFn: () => api.get<any>(`/tenants/${selectedTenant?.id}`),
    enabled: !!selectedTenant?.id,
  });

  const { data: permStatus, refetch: recheckPerms } = useQuery({
    queryKey: ['org-perms', selectedTenant?.id],
    queryFn: () => api.get<any>(`/tenants/${selectedTenant?.id}/permissions`),
    enabled: !!selectedTenant?.id,
    retry: false,
  });

  const {
    data: workloadData,
    isLoading: workloadsLoading,
    isError: _workloadsError,
  } = useQuery({
    queryKey: ['workload-statuses', selectedTenant?.id],
    queryFn: () => api.get<WorkloadStatusResponse>(`/tenants/${selectedTenant?.id}/workloads`),
    enabled: !!selectedTenant?.id,
    retry: false,
  });

  const { data: subscription } = useQuery({
    queryKey: ['billing-subscription', selectedTenant?.id],
    queryFn: () => api.get<SubscriptionInfo>(`/billing/subscription?tenant_id=${selectedTenant?.id}`),
    enabled: !!selectedTenant?.id,
    retry: false,
  });

  /* ---- Mutations ---- */

  const enableMutation = useMutation({
    mutationFn: (workload: string) =>
      api.post<EnableResponse>(`/tenants/${selectedTenant?.id}/workloads`, {
        workloads: [workload],
      }),
    onSuccess: (_data, workload) => {
      const label = WORKLOAD_MAP[workload]?.label ?? workload;
      toast.success('Workload enabled', `${label} has been enabled successfully.`);
      queryClient.invalidateQueries({ queryKey: ['workload-statuses', selectedTenant?.id] });
      queryClient.invalidateQueries({ queryKey: ['billing-subscription', selectedTenant?.id] });
      setEnablingWorkload(null);
    },
    onError: (err: any, workload) => {
      const label = WORKLOAD_MAP[workload]?.label ?? workload;
      toast.error(`Failed to enable ${label}`, err?.message || 'Please try again.');
      setEnablingWorkload(null);
    },
  });

  const disableMutation = useMutation({
    mutationFn: (workload: string) =>
      api.post<DisableResponse>(`/tenants/${selectedTenant?.id}/workloads/${workload}/disable`),
    onSuccess: (_data, workload) => {
      const label = WORKLOAD_MAP[workload]?.label ?? workload;
      toast.success('Workload disabled', `${label} has been disabled.`);
      queryClient.invalidateQueries({ queryKey: ['workload-statuses', selectedTenant?.id] });
      queryClient.invalidateQueries({ queryKey: ['billing-subscription', selectedTenant?.id] });
      setDisableTarget(null);
    },
    onError: (err: any, workload) => {
      const label = WORKLOAD_MAP[workload]?.label ?? workload;
      toast.error(`Failed to disable ${label}`, err?.message || 'Please try again.');
      setDisableTarget(null);
    },
  });

  /* ---- Handlers ---- */

  const handleCheckPermissions = async () => {
    setCheckingPerms(true);
    try {
      await recheckPerms();
    } finally {
      setCheckingPerms(false);
    }
  };

  const handleEnable = (workload: string) => {
    setEnablingWorkload(workload);
    enableMutation.mutate(workload);
  };

  const handleDisableConfirm = () => {
    if (disableTarget) {
      disableMutation.mutate(disableTarget);
    }
  };

  /* ---- Loading state ---- */

  if (tenantLoading || !selectedTenant) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  /* ---- Derived state ---- */

  const t = tenant || selectedTenant;
  const isActive = t.status === 'active';

  // Build workload status map from the lifecycle API (source of truth).
  // IMPORTANT: Do NOT fall back to tenant counts — that creates phantom
  // "Discovered" workloads when the user hasn't actually enabled anything.
  // If the API returns empty, all workloads are disabled (correct state).
  let statusMap: Record<string, WorkloadStatus> = {};

  if (workloadData?.workloads && workloadData.workloads.length > 0) {
    for (const ws of workloadData.workloads) {
      statusMap[ws.workload] = ws;
    }
  }
  // No fallback — if no workload apps exist, statusMap stays empty.
  // All workloads render as "disabled" with Enable buttons. This is honest.

  // Determine real connection state:
  // - hasWorkloads: at least one workload enabled (user completed onboarding step 2)
  // - hasConsent: at least one workload has consent granted (Microsoft OAuth completed)
  const hasWorkloads = Object.keys(statusMap).length > 0;
  const hasConsent = Object.values(statusMap).some(ws => ws.consent_status === 'consented' || ws.consent_status === 'granted');

  // Real connection status: "active" in DB is not enough — user must have
  // actually completed OAuth and enabled workloads for a real connection.
  const isReallyConnected = isActive && hasConsent;

  const enabledCount = Object.values(statusMap).filter(
    ws => ws.lifecycle_status !== 'disabled'
  ).length;

  const tier = subscription?.subscription_tier?.toLowerCase() ?? 'community';
  const tierLimit = TIER_LIMITS[tier] ?? 2;
  const atLimit = enabledCount >= tierLimit;

  const disableLabel = disableTarget ? (WORKLOAD_MAP[disableTarget]?.label ?? disableTarget) : '';

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Organization</h1>
          <p className="text-muted-foreground">Manage your connected platform and workloads</p>
        </div>
      </div>

      {/* Connection Status Card — shows REAL connection state, not just DB flag */}
      <div className="bg-card border border-border rounded-xl p-5 mb-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              isReallyConnected ? 'bg-green-500/10'
                : hasWorkloads ? 'bg-amber-500/10'
                : 'bg-muted'
            }`}>
              {isReallyConnected ? <CheckCircle className="w-5 h-5 text-green-500" />
                : hasWorkloads ? <AlertTriangle className="w-5 h-5 text-amber-400" />
                : <Shield className="w-5 h-5 text-muted-foreground" />}
            </div>
            <div>
              <h2 className="text-lg font-bold text-foreground">{t.name}</h2>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  isReallyConnected ? 'bg-green-500/10 text-green-400'
                    : hasWorkloads ? 'bg-amber-500/10 text-amber-400'
                    : 'bg-muted text-muted-foreground'
                }`}>
                  {isReallyConnected ? 'Connected'
                    : hasWorkloads ? 'Pending Consent'
                    : 'Not Connected'}
                </span>
                <span>Microsoft 365</span>
              </div>
            </div>
          </div>
          {isReallyConnected ? (
            <button
              onClick={handleCheckPermissions}
              disabled={checkingPerms}
              className="px-3 py-1.5 text-sm border border-border rounded-lg hover:bg-accent transition-colors flex items-center gap-1.5"
            >
              {checkingPerms ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
              Verify Connection
            </button>
          ) : (
            <button
              onClick={() => navigate('/onboard')}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-1.5"
            >
              Connect Microsoft 365
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Not connected hint */}
        {!isReallyConnected && !hasWorkloads && (
          <div className="rounded-lg p-3 text-sm bg-blue-500/5 border border-blue-500/20">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-blue-400" />
              <span className="text-blue-400">Connect your Microsoft 365 tenant to start protecting workloads</span>
            </div>
          </div>
        )}

        {/* Permission Status (if checked, only for connected tenants) */}
        {isReallyConnected && permStatus && !permStatus.error && (
          <div className={`rounded-lg p-3 text-sm ${permStatus.all_backup_ready ? 'bg-green-500/5 border border-green-500/20' : 'bg-amber-500/5 border border-amber-500/20'}`}>
            <div className="flex items-center gap-2">
              {permStatus.all_backup_ready
                ? <><CheckCircle className="w-4 h-4 text-green-500" /><span className="text-green-400">All permissions verified</span></>
                : <><AlertTriangle className="w-4 h-4 text-amber-400" /><span className="text-amber-400">Some permissions need attention</span></>
              }
            </div>
          </div>
        )}
      </div>

      {/* Workload Cards — only show when connected or at least tenant exists with workload apps */}
      <div className="mb-4">
        <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-3">
          Workloads
        </h3>

        {workloadsLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
          </div>
        ) : !isReallyConnected && !hasWorkloads ? (
          /* Empty state — user hasn't connected Microsoft yet */
          <div className="bg-card border border-border rounded-xl p-8 text-center">
            <Shield className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-foreground mb-1">No workloads configured</h3>
            <p className="text-xs text-muted-foreground mb-4 max-w-sm mx-auto">
              Connect your Microsoft 365 tenant first, then choose which workloads to protect.
              You only pay for what you enable.
            </p>
            <button
              onClick={() => navigate('/onboard')}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Get Started
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {WORKLOADS.map(config => {
              const ws = statusMap[config.key] ?? null;
              return (
                <WorkloadCard
                  key={config.key}
                  config={config}
                  status={ws}
                  isAdmin={isAdmin}
                  atLimit={atLimit && (ws === null || ws.lifecycle_status === 'disabled')}
                  onEnable={handleEnable}
                  onDisable={(workload) => setDisableTarget(workload)}
                  enabling={enablingWorkload === config.key}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* Subscription Banner */}
      {subscription && (
        <div className="bg-card rounded-xl border border-border p-4 mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <Shield className="w-4 h-4 text-muted-foreground" />
            <span className="text-foreground font-medium capitalize">{tier}</span>
            <span className="text-muted-foreground">
              {enabledCount}/{tierLimit} workloads enabled
            </span>
          </div>
          {atLimit && (
            <button
              onClick={() => navigate('/usage')}
              className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-colors"
            >
              Upgrade plan <ArrowUpRight className="w-3 h-3" />
            </button>
          )}
        </div>
      )}

      {/* Quick Links — contextual based on connection state.
          Not connected: only Billing (so prospect can see pricing).
          Connected: Billing + Backup Policies + Audit Log + Alerts. */}
      {(() => {
        const links = [
          // Always show Billing — prospects need to see pricing
          { path: '/billing', icon: Settings, label: 'Billing', desc: 'Plans, usage, invoices', always: true },
          // Show Backup Policies once workloads are enabled
          { path: '/sla-policies', icon: Shield, label: 'Backup Policies', desc: 'Schedule, retention, WORM', always: false },
          // Show Audit Log once connected
          { path: '/audit', icon: Users, label: 'Audit Log', desc: 'Who did what, when', always: false },
          // Show Alerts once connected
          { path: '/alerts', icon: AlertTriangle, label: 'Alert Preferences', desc: 'Events, recipients, frequency', always: false },
        ].filter(l => l.always || isReallyConnected);

        if (links.length === 0) return null;

        return (
          <div className={`grid grid-cols-1 ${links.length >= 3 ? 'sm:grid-cols-2 lg:grid-cols-4' : links.length === 2 ? 'sm:grid-cols-2' : ''} gap-3 mt-6`}>
            {links.map(l => (
              <button
                key={l.path}
                onClick={() => navigate(l.path)}
                className="bg-card border border-border rounded-xl p-4 text-left hover:border-blue-500/30 transition-colors"
              >
                <l.icon className="w-5 h-5 text-muted-foreground mb-2" />
                <div className="text-sm font-medium text-foreground">{l.label}</div>
                <div className="text-xs text-muted-foreground">{l.desc}</div>
              </button>
            ))}
          </div>
        );
      })()}

      {/* Disable Confirmation Dialog */}
      <Dialog open={disableTarget !== null} onOpenChange={(open) => { if (!open) setDisableTarget(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disable {disableLabel}?</DialogTitle>
            <DialogDescription>
              Disabling this workload will stop all backup and restore operations for {disableLabel}.
              Existing backup data will be retained, but no new backups will run until the workload is re-enabled.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <button
              onClick={() => setDisableTarget(null)}
              className="px-4 py-2 text-sm border border-border rounded-lg hover:bg-accent transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleDisableConfirm}
              disabled={disableMutation.isPending}
              className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors flex items-center gap-1.5"
            >
              {disableMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Disable
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
