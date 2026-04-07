/**
 * Organization Settings — customer-facing view of their connected tenant.
 *
 * Shows: connection status, connected workloads, permission health,
 * and actionable fix buttons. No raw GUIDs or admin-only actions.
 *
 * Dashboard = "Is my data safe?" (operational)
 * Organization = "What's connected and how do I change it?" (configuration)
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Shield, CheckCircle, XCircle, AlertTriangle, Loader2,
  Mail, HardDrive, Globe, KeyRound, MessageSquare,
  ArrowRight, RefreshCw, Users, Settings,
} from 'lucide-react';
import { api } from '../api/client';
import { useTenantSwitcher } from '../hooks/useTenant';

const WORKLOAD_META: Record<string, { label: string; icon: any; description: string }> = {
  exchange: { label: 'Exchange', icon: Mail, description: 'Emails, calendars, contacts' },
  entra_id: { label: 'Entra ID', icon: KeyRound, description: 'Users, groups, roles, policies' },
  sharepoint: { label: 'SharePoint', icon: Globe, description: 'Sites, document libraries' },
  onedrive: { label: 'OneDrive', icon: HardDrive, description: 'Personal files and folders' },
  teams: { label: 'Teams', icon: MessageSquare, description: 'Channels, messages, chats' },
};

export default function Organization() {
  const navigate = useNavigate();
  const { selectedTenant } = useTenantSwitcher();
  const [checkingPerms, setCheckingPerms] = useState(false);

  const { data: tenant, isLoading } = useQuery({
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

  const handleCheckPermissions = async () => {
    setCheckingPerms(true);
    try {
      await recheckPerms();
    } finally {
      setCheckingPerms(false);
    }
  };

  if (isLoading || !selectedTenant) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  const t = tenant || selectedTenant;
  const isActive = t.status === 'active';

  // Build workload status from tenant counts
  const workloads = [
    { key: 'exchange', count: t.total_mailboxes || 0, unit: 'mailboxes' },
    { key: 'entra_id', count: t.total_entra_objects || 0, unit: 'objects' },
    { key: 'sharepoint', count: t.total_sites || 0, unit: 'sites' },
    { key: 'onedrive', count: t.total_onedrives || 0, unit: 'drives' },
    { key: 'teams', count: t.total_teams || 0, unit: 'teams' },
  ];

  const connectedWorkloads = workloads.filter(w => w.count > 0);
  const availableWorkloads = workloads.filter(w => w.count === 0);

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Organization</h1>
          <p className="text-muted-foreground">Manage your connected platform and workloads</p>
        </div>
      </div>

      {/* Connection Status Card */}
      <div className="bg-card border border-border rounded-xl p-5 mb-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${isActive ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
              {isActive ? <CheckCircle className="w-5 h-5 text-green-500" /> : <XCircle className="w-5 h-5 text-red-500" />}
            </div>
            <div>
              <h2 className="text-lg font-bold text-foreground">{t.name}</h2>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${isActive ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                  {isActive ? 'Connected' : 'Disconnected'}
                </span>
                <span>Microsoft 365</span>
              </div>
            </div>
          </div>
          <button
            onClick={handleCheckPermissions}
            disabled={checkingPerms}
            className="px-3 py-1.5 text-sm border border-border rounded-lg hover:bg-accent transition-colors flex items-center gap-1.5"
          >
            {checkingPerms ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            Verify Connection
          </button>
        </div>

        {/* Permission Status (if checked) */}
        {permStatus && !permStatus.error && (
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

      {/* Connected Workloads */}
      <div className="mb-4">
        <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-3">Protected Workloads</h3>
        <div className="space-y-2">
          {connectedWorkloads.length > 0 ? connectedWorkloads.map(w => {
            const meta = WORKLOAD_META[w.key];
            const Icon = meta?.icon || Shield;
            return (
              <div key={w.key} className="bg-card border border-border rounded-xl p-4 flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-teal-500/10 flex items-center justify-center">
                  <Icon className="w-4.5 h-4.5 text-teal-400" />
                </div>
                <div className="flex-1">
                  <div className="font-medium text-foreground">{meta?.label || w.key}</div>
                  <div className="text-xs text-muted-foreground">{meta?.description}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-foreground">{w.count}</div>
                  <div className="text-xs text-muted-foreground">{w.unit}</div>
                </div>
                <CheckCircle className="w-4 h-4 text-green-500 ml-2" />
              </div>
            );
          }) : (
            <div className="text-sm text-muted-foreground py-4 text-center">
              No workloads discovered yet.
              <button onClick={() => navigate('/onboard')} className="text-blue-400 hover:text-blue-300 ml-1">Run Discovery</button>
            </div>
          )}
        </div>
      </div>

      {/* Available Workloads (not yet enabled) */}
      {availableWorkloads.length > 0 && (
        <div className="mb-4">
          <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-3">Available to Enable</h3>
          <div className="space-y-2">
            {availableWorkloads.map(w => {
              const meta = WORKLOAD_META[w.key];
              const Icon = meta?.icon || Shield;
              return (
                <div key={w.key} className="bg-card border border-border rounded-xl p-4 flex items-center gap-3 opacity-60">
                  <div className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center">
                    <Icon className="w-4.5 h-4.5 text-muted-foreground" />
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-foreground">{meta?.label || w.key}</div>
                    <div className="text-xs text-muted-foreground">{meta?.description}</div>
                  </div>
                  <button
                    onClick={() => navigate('/onboard')}
                    className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                  >
                    Enable <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Quick Links */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-6">
        <button
          onClick={() => navigate('/usage')}
          className="bg-card border border-border rounded-xl p-4 text-left hover:border-blue-500/30 transition-colors"
        >
          <Settings className="w-5 h-5 text-muted-foreground mb-2" />
          <div className="text-sm font-medium text-foreground">Usage & Billing</div>
          <div className="text-xs text-muted-foreground">License, storage, costs</div>
        </button>

        <button
          onClick={() => navigate('/sla-policies')}
          className="bg-card border border-border rounded-xl p-4 text-left hover:border-blue-500/30 transition-colors"
        >
          <Shield className="w-5 h-5 text-muted-foreground mb-2" />
          <div className="text-sm font-medium text-foreground">Backup Policies</div>
          <div className="text-xs text-muted-foreground">Schedule, retention, WORM</div>
        </button>

        <button
          onClick={() => navigate('/audit')}
          className="bg-card border border-border rounded-xl p-4 text-left hover:border-blue-500/30 transition-colors"
        >
          <Users className="w-5 h-5 text-muted-foreground mb-2" />
          <div className="text-sm font-medium text-foreground">Audit Log</div>
          <div className="text-xs text-muted-foreground">Who did what, when</div>
        </button>
      </div>
    </div>
  );
}
