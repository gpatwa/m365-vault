import { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Building2, Plus, CheckCircle, XCircle, RefreshCw, Trash2, Wifi, Pause, Play, KeyRound, AlertTriangle, ExternalLink, ShieldCheck, Loader2, ArrowRight } from 'lucide-react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import OnboardingWizard from '../components/OnboardingWizard';
import type { Tenant } from '../types';

export default function Settings() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const connectedTenantId = searchParams.get('connected');
  const connectedTenantName = searchParams.get('tenant_name');
  const [showWizard, setShowWizard] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [purgeConfirm, setPurgeConfirm] = useState<{ id: number; name: string } | null>(null);
  const [purgeInput, setPurgeInput] = useState('');
  const [credentialsEdit, setCredentialsEdit] = useState<{ id: number } | null>(null);
  const [credForm, setCredForm] = useState({ client_id: '', client_secret: '' });
  const [actionMsg, setActionMsg] = useState('');
  const [permsTenant, setPermsTenant] = useState<number | null>(null);
  const [permsData, setPermsData] = useState<any>(null);
  const [permsLoading, setPermsLoading] = useState(false);
  const qc = useQueryClient();

  const checkPerms = async (tenantId: number) => {
    if (permsTenant === tenantId && permsData) {
      setPermsTenant(null); // toggle off
      return;
    }
    setPermsTenant(tenantId);
    setPermsLoading(true);
    try {
      const data = await api.get(`/tenants/${tenantId}/permissions`);
      setPermsData(data);
    } catch {
      setPermsData({ error: 'Failed to check permissions' });
    } finally {
      setPermsLoading(false);
    }
  };

  const { data: tenants, isLoading } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => api.get<Tenant[]>('/tenants/'),
  });

  const testMutation = useMutation({
    mutationFn: (id: number) => api.post<{ success: boolean; message: string }>(`/tenants/${id}/test`),
    onSuccess: (data) => setTestResult(data),
  });

  const discoverMutation = useMutation({
    mutationFn: (id: number) => api.post(`/tenants/${id}/discover`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['tenants'] }); showMsg('Discovery completed'); },
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: number) => api.post(`/tenants/${id}/deactivate`),
    onSuccess: (data: any) => {
      qc.invalidateQueries({ queryKey: ['tenants'] });
      showMsg(`Tenant deactivated: ${data.objects_paused} objects paused`);
    },
  });

  const reactivateMutation = useMutation({
    mutationFn: (id: number) => api.post(`/tenants/${id}/reactivate`),
    onSuccess: (data: any) => {
      qc.invalidateQueries({ queryKey: ['tenants'] });
      showMsg(`Tenant reactivated: ${data.objects_reactivated} objects resumed`);
    },
  });

  const purgeMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      api.del(`/tenants/${id}?confirm=${encodeURIComponent(name)}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tenants'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      setPurgeConfirm(null);
      setPurgeInput('');
      showMsg('Tenant purged — all data deleted');
    },
    onError: (err: any) => showMsg(`Purge failed: ${err.message}`),
  });

  const updateCredentialsMutation = useMutation({
    mutationFn: ({ id, ...data }: { id: number; client_id?: string; client_secret?: string }) =>
      api.post(`/tenants/${id}/update-credentials`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tenants'] });
      setCredentialsEdit(null);
      setCredForm({ client_id: '', client_secret: '' });
      showMsg('Credentials updated');
    },
  });

  const showMsg = (msg: string) => { setActionMsg(msg); setTimeout(() => setActionMsg(''), 5000); };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Tenants</h1>
          <p className="text-muted-foreground">Manage SaaS platform connections and lifecycle</p>
        </div>
        {!showWizard && (
          <button onClick={() => setShowWizard(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2">
            <Plus className="w-4 h-4" /> Add Tenant
          </button>
        )}
      </div>

      {/* Demo onboarding: tenant just connected banner */}
      {connectedTenantId && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-6 h-6 text-green-400" />
              <div>
                <div className="font-semibold text-foreground">
                  {connectedTenantName || 'Tenant'} connected successfully!
                </div>
                <div className="text-sm text-muted-foreground">
                  OAuth admin consent verified. Your tenant is ready for workload discovery.
                </div>
              </div>
            </div>
            <button
              onClick={() => navigate(`/onboard/callback?demo=true&db_tenant_id=${connectedTenantId}&tenant_name=${encodeURIComponent(connectedTenantName || '')}&step=1`)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-500/100 flex items-center gap-2"
            >
              Continue Setup <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {showWizard && (
        <OnboardingWizard
          onComplete={() => {
            setShowWizard(false);
            qc.invalidateQueries({ queryKey: ['tenants'] });
            qc.invalidateQueries({ queryKey: ['dashboard'] });
            showMsg('Tenant onboarded and protection started! Backups will begin automatically based on your schedule.');
          }}
          onCancel={() => setShowWizard(false)}
        />
      )}

      {/* Action messages */}
      {(testResult || actionMsg) && (
        <div className={`rounded-lg p-4 mb-4 flex items-center gap-3 ${
          testResult ? (testResult.success ? 'bg-green-500/10 border border-green-500/20' : 'bg-red-500/10 border border-red-500/20')
            : 'bg-blue-500/10 border border-blue-500/20'
        }`}>
          {testResult ? (
            <>
              {testResult.success ? <CheckCircle className="w-5 h-5 text-green-400" /> : <XCircle className="w-5 h-5 text-red-400" />}
              <span className={testResult.success ? 'text-green-400' : 'text-red-400'}>{testResult.message}</span>
            </>
          ) : (
            <>
              <CheckCircle className="w-5 h-5 text-blue-600" />
              <span className="text-blue-400">{actionMsg}</span>
            </>
          )}
          <button onClick={() => { setTestResult(null); setActionMsg(''); }} className="ml-auto text-muted-foreground hover:text-muted-foreground">&times;</button>
        </div>
      )}

      {/* Purge Confirmation Modal */}
      {purgeConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-foreground">Purge Tenant</h3>
                <p className="text-sm text-muted-foreground">This action is irreversible</p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              This will permanently delete <strong>{purgeConfirm.name}</strong> and ALL associated data including backups, snapshots, jobs, and storage blobs.
            </p>
            <p className="text-sm text-muted-foreground mb-2">
              Type <strong className="font-mono bg-muted px-1 rounded">{purgeConfirm.name}</strong> to confirm:
            </p>
            <input
              type="text" value={purgeInput}
              onChange={e => setPurgeInput(e.target.value)}
              placeholder="Type tenant name to confirm"
              className="w-full px-3 py-2 border border-border rounded-lg mb-4 bg-background text-foreground focus:ring-2 focus:ring-red-500 focus:border-red-500 font-mono text-sm"
              autoFocus
            />
            <div className="flex gap-3 justify-end">
              <button onClick={() => { setPurgeConfirm(null); setPurgeInput(''); }} className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground">
                Cancel
              </button>
              <button
                onClick={() => purgeMutation.mutate({ id: purgeConfirm.id, name: purgeConfirm.name })}
                disabled={purgeInput !== purgeConfirm.name || purgeMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
              >
                {purgeMutation.isPending ? 'Purging...' : 'Permanently Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Update Credentials Modal */}
      {credentialsEdit && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-foreground mb-4">Update Credentials</h3>
            <p className="text-sm text-muted-foreground mb-4">Update your Azure AD App Registration credentials. Leave blank to keep current value.</p>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">Application (Client) ID</label>
                <input
                  type="text" value={credForm.client_id}
                  onChange={e => setCredForm({ ...credForm, client_id: e.target.value })}
                  placeholder="Leave blank to keep current"
                  className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-ring font-mono text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">Client Secret</label>
                <input
                  type="password" value={credForm.client_secret}
                  onChange={e => setCredForm({ ...credForm, client_secret: e.target.value })}
                  placeholder="Leave blank to keep current"
                  className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>
            <div className="flex gap-3 justify-end mt-4">
              <button onClick={() => { setCredentialsEdit(null); setCredForm({ client_id: '', client_secret: '' }); }} className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground">
                Cancel
              </button>
              <button
                onClick={() => {
                  const data: any = { id: credentialsEdit.id };
                  if (credForm.client_id) data.client_id = credForm.client_id;
                  if (credForm.client_secret) data.client_secret = credForm.client_secret;
                  updateCredentialsMutation.mutate(data);
                }}
                disabled={!credForm.client_id && !credForm.client_secret}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                Update
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tenant List */}
      <div className="space-y-4">
        {tenants?.map(t => {
          const isActive = t.status === 'active';
          const isInactive = t.status === 'inactive';

          return (
            <div key={t.id} className={`bg-card rounded-xl border shadow-sm p-5 ${isInactive ? 'opacity-75' : ''}`}>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${isInactive ? 'bg-muted' : 'bg-blue-500/10'}`}>
                    <Building2 className={`w-6 h-6 ${isInactive ? 'text-muted-foreground' : 'text-blue-600'}`} />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold">{t.name}</h3>
                    <p className="text-sm text-muted-foreground font-mono truncate">{t.ms_tenant_id}</p>
                  </div>
                  <StatusBadge status={t.status} />
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Common actions */}
                  <button onClick={() => testMutation.mutate(t.id)} className="px-3 py-1.5 bg-muted text-muted-foreground rounded-lg text-sm hover:bg-accent flex items-center gap-1">
                    <Wifi className="w-4 h-4" /> Test
                  </button>
                  <button onClick={() => setCredentialsEdit({ id: t.id })} className="px-3 py-1.5 bg-muted text-muted-foreground rounded-lg text-sm hover:bg-accent flex items-center gap-1">
                    <KeyRound className="w-4 h-4" />
                  </button>

                  {/* Active tenant actions */}
                  {isActive && (
                    <>
                      <button onClick={() => discoverMutation.mutate(t.id)} className="px-3 py-1.5 bg-blue-100 text-blue-400 rounded-lg text-sm hover:bg-blue-200 flex items-center gap-1">
                        <RefreshCw className="w-4 h-4" /> Discover
                      </button>
                      <button onClick={() => deactivateMutation.mutate(t.id)} className="px-3 py-1.5 bg-yellow-100 text-yellow-700 rounded-lg text-sm hover:bg-yellow-200 flex items-center gap-1">
                        <Pause className="w-4 h-4" /> Deactivate
                      </button>
                    </>
                  )}

                  {/* Inactive tenant actions */}
                  {isInactive && (
                    <>
                      <button onClick={() => reactivateMutation.mutate(t.id)} className="px-3 py-1.5 bg-green-100 text-green-400 rounded-lg text-sm hover:bg-green-200 flex items-center gap-1">
                        <Play className="w-4 h-4" /> Reactivate
                      </button>
                      <button onClick={() => setPurgeConfirm({ id: t.id, name: t.name })} className="px-3 py-1.5 bg-red-100 text-red-400 rounded-lg text-sm hover:bg-red-200 flex items-center gap-1">
                        <Trash2 className="w-4 h-4" /> Purge
                      </button>
                    </>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-4 text-sm">
                <div className="bg-muted/50 rounded-lg p-3">
                  <p className="text-muted-foreground text-xs">Mailboxes</p>
                  <p className="text-lg font-bold">{t.total_mailboxes}</p>
                </div>
                <div className="bg-muted/50 rounded-lg p-3">
                  <p className="text-muted-foreground text-xs">OneDrives</p>
                  <p className="text-lg font-bold">{t.total_onedrives}</p>
                </div>
                <div className="bg-muted/50 rounded-lg p-3">
                  <p className="text-muted-foreground text-xs">SharePoint</p>
                  <p className="text-lg font-bold">{t.total_sites}</p>
                </div>
                <div className="bg-muted/50 rounded-lg p-3">
                  <p className="text-muted-foreground text-xs">Teams</p>
                  <p className="text-lg font-bold">{t.total_teams || 0}</p>
                </div>
                <div className="bg-muted/50 rounded-lg p-3">
                  <p className="text-muted-foreground text-xs">Entra ID</p>
                  <p className="text-lg font-bold">{t.total_entra_objects || 0}</p>
                </div>
                <div className="bg-muted/50 rounded-lg p-3">
                  <p className="text-muted-foreground text-xs">Last Discovery</p>
                  <p className="text-sm font-medium">{t.last_discovery_at?.slice(0, 16) || 'Never'}</p>
                </div>
              </div>
              {/* Permission Status */}
              <div className="mt-3">
                {t.ms_tenant_id?.startsWith('demo-') ? (
                  <span className="px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 inline-flex items-center gap-1">
                    Demo Tenant — permissions check requires real M365 connection
                  </span>
                ) : (
                <button
                  onClick={() => checkPerms(t.id)}
                  disabled={permsLoading && permsTenant === t.id}
                  className="px-3 py-1.5 border border-border text-muted-foreground rounded-lg text-xs font-medium hover:bg-muted/50 flex items-center gap-1"
                >
                  {permsLoading && permsTenant === t.id
                    ? <><Loader2 className="w-3 h-3 animate-spin" /> Checking...</>
                    : <><ShieldCheck className="w-3 h-3" /> {permsTenant === t.id && permsData ? 'Hide' : 'Check'} Permissions</>
                  }
                </button>
                )}

                {permsTenant === t.id && permsData && !permsData.error && (
                  <div className="mt-3 border rounded-lg overflow-hidden">
                    <div className={`px-4 py-2 text-sm font-medium flex items-center justify-between ${
                      permsData.all_backup_ready ? 'bg-green-500/10 text-green-400' : 'bg-orange-500/10 text-orange-700'
                    }`}>
                      <span className="flex items-center gap-1.5">
                        {permsData.all_backup_ready ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                        {permsData.all_backup_ready ? 'All backup permissions granted' : 'Some permissions missing'}
                      </span>
                      {!permsData.all_backup_ready && (
                        <a
                          href={`https://login.microsoftonline.com/${t.ms_tenant_id}/adminconsent?client_id=${t.client_id}&redirect_uri=${encodeURIComponent(window.location.origin + '/settings')}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-2.5 py-1 bg-orange-600 text-foreground rounded text-xs font-medium hover:bg-orange-700 flex items-center gap-1"
                        >
                          <ExternalLink className="w-3 h-3" /> Grant in Azure Portal
                        </a>
                      )}
                    </div>
                    <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="text-left px-4 py-2 font-medium text-muted-foreground">Workload</th>
                          <th className="text-center px-4 py-2 font-medium text-muted-foreground">Backup</th>
                          <th className="text-center px-4 py-2 font-medium text-muted-foreground">Restore</th>
                          <th className="text-left px-4 py-2 font-medium text-muted-foreground">Missing Permissions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {Object.entries(permsData.workloads).map(([wl, status]: [string, any]) => {
                          const allMissing = [...(status.missing_backup || []), ...(status.missing_restore || [])];
                          return (
                            <tr key={wl}>
                              <td className="px-4 py-2 font-medium capitalize">{wl.replace('_', ' ')}</td>
                              <td className="px-4 py-2 text-center">
                                {status.backup
                                  ? <CheckCircle className="w-4 h-4 text-green-500 mx-auto" />
                                  : <XCircle className="w-4 h-4 text-red-500 mx-auto" />}
                              </td>
                              <td className="px-4 py-2 text-center">
                                {status.restore === null ? <span className="text-muted-foreground">N/A</span>
                                  : status.restore
                                    ? <CheckCircle className="w-4 h-4 text-green-500 mx-auto" />
                                    : <XCircle className="w-4 h-4 text-red-500 mx-auto" />}
                              </td>
                              <td className="px-4 py-2">
                                {allMissing.length > 0 ? (
                                  <div className="space-y-1">
                                    {allMissing.map((perm: string) => (
                                      <code key={perm} className="inline-block bg-red-500/10 text-red-400 px-1.5 py-0.5 rounded text-[10px] font-mono mr-1">{perm}</code>
                                    ))}
                                  </div>
                                ) : <span className="text-green-600 text-xs font-medium">All granted</span>}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                      <tfoot>
                        <tr className="bg-muted/50 border-t">
                          <td colSpan={4} className="px-4 py-3">
                            <div className="flex items-center gap-3">
                              <a
                                href={`https://login.microsoftonline.com/${t.ms_tenant_id}/adminconsent?client_id=${t.client_id}&redirect_uri=${encodeURIComponent(window.location.origin + '/settings')}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="px-3 py-1.5 bg-orange-600 text-foreground rounded-lg text-xs font-medium hover:bg-orange-700 flex items-center gap-1"
                              >
                                <ExternalLink className="w-3 h-3" /> Grant All Permissions
                              </a>
                              <span className="text-[10px] text-muted-foreground">Opens Microsoft consent page to grant all configured permissions at once</span>
                            </div>
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                    </div>

                    {/* Instructions for fixing permissions */}
                    {!permsData.all_backup_ready && (
                      <div className="bg-blue-500/10 border-t border-blue-100 px-4 py-3">
                        <p className="text-xs font-semibold text-blue-400 mb-2">How to grant missing permissions:</p>
                        <ol className="text-xs text-blue-400 space-y-1.5 list-decimal list-inside">
                          <li>
                            <strong>One-time setup:</strong> Add redirect URI to your app registration in{' '}
                            <a href={`https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Authentication/appId/${t.client_id}`}
                              target="_blank" rel="noopener noreferrer" className="underline font-medium">Azure Portal → Authentication</a>
                            {' '}→ Add platform → Web → enter:
                            <code className="block mt-1 ml-4 bg-blue-100 px-2 py-1 rounded text-[11px] font-mono text-blue-900 select-all">
                              {window.location.origin}/settings
                            </code>
                          </li>
                          <li>
                            Add the missing permissions in{' '}
                            <a href={`https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/${t.client_id}`}
                              target="_blank" rel="noopener noreferrer" className="underline font-medium">Azure Portal → API Permissions</a>
                            {' '}→ Add a permission → Microsoft Graph → Application permissions:
                            <div className="mt-1 ml-4 space-y-0.5">
                              {Object.entries(permsData.workloads)
                                .flatMap(([, s]: [string, any]) => [...(s.missing_backup || []), ...(s.missing_restore || [])])
                                .filter((v, i, a) => a.indexOf(v) === i)
                                .map((perm: string) => (
                                  <code key={perm} className="block bg-blue-100 px-1.5 py-0.5 rounded text-[11px] font-mono text-blue-900 select-all">{perm}</code>
                                ))
                              }
                            </div>
                          </li>
                          <li>Click <strong>"Grant admin consent"</strong> in Azure Portal, or use the <strong>"Fix"</strong> buttons above (works after step 1)</li>
                          <li>Click <strong>"Check Permissions"</strong> here to verify</li>
                        </ol>
                      </div>
                    )}
                  </div>
                )}

                {permsTenant === t.id && permsData?.error && (
                  <div className="mt-3 bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-sm text-red-400">
                    {permsData.error}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        {isLoading && <p className="text-muted-foreground text-center py-8">Loading...</p>}
        {!isLoading && !tenants?.length && (
          <div className="text-center py-12 text-muted-foreground">
            <Building2 className="w-12 h-12 mx-auto mb-3 text-muted-foreground" />
            <p className="text-lg font-medium">No tenants configured</p>
            <p className="text-sm">Add your first SaaS platform to get started</p>
          </div>
        )}
      </div>
    </div>
  );
}
