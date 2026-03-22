import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Settings as SettingsIcon, Plus, CheckCircle, XCircle, RefreshCw, Trash2, Wifi, Pause, Play, KeyRound, AlertTriangle } from 'lucide-react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import OnboardingWizard from '../components/OnboardingWizard';
import type { Tenant } from '../types';

export default function Settings() {
  const [showWizard, setShowWizard] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [purgeConfirm, setPurgeConfirm] = useState<{ id: number; name: string } | null>(null);
  const [purgeInput, setPurgeInput] = useState('');
  const [credentialsEdit, setCredentialsEdit] = useState<{ id: number } | null>(null);
  const [credForm, setCredForm] = useState({ client_id: '', client_secret: '' });
  const [actionMsg, setActionMsg] = useState('');
  const qc = useQueryClient();

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
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-500">Manage M365 tenant connections</p>
        </div>
        {!showWizard && (
          <button onClick={() => setShowWizard(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2">
            <Plus className="w-4 h-4" /> Add Tenant
          </button>
        )}
      </div>

      {showWizard && (
        <OnboardingWizard
          onComplete={() => {
            setShowWizard(false);
            qc.invalidateQueries({ queryKey: ['tenants'] });
            qc.invalidateQueries({ queryKey: ['dashboard'] });
          }}
          onCancel={() => setShowWizard(false)}
        />
      )}

      {/* Action messages */}
      {(testResult || actionMsg) && (
        <div className={`rounded-lg p-4 mb-4 flex items-center gap-3 ${
          testResult ? (testResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200')
            : 'bg-blue-50 border border-blue-200'
        }`}>
          {testResult ? (
            <>
              {testResult.success ? <CheckCircle className="w-5 h-5 text-green-600" /> : <XCircle className="w-5 h-5 text-red-600" />}
              <span className={testResult.success ? 'text-green-800' : 'text-red-800'}>{testResult.message}</span>
            </>
          ) : (
            <>
              <CheckCircle className="w-5 h-5 text-blue-600" />
              <span className="text-blue-800">{actionMsg}</span>
            </>
          )}
          <button onClick={() => { setTestResult(null); setActionMsg(''); }} className="ml-auto text-gray-400 hover:text-gray-600">&times;</button>
        </div>
      )}

      {/* Purge Confirmation Modal */}
      {purgeConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">Purge Tenant</h3>
                <p className="text-sm text-gray-500">This action is irreversible</p>
              </div>
            </div>
            <p className="text-sm text-gray-700 mb-4">
              This will permanently delete <strong>{purgeConfirm.name}</strong> and ALL associated data including backups, snapshots, jobs, and storage blobs.
            </p>
            <p className="text-sm text-gray-700 mb-2">
              Type <strong className="font-mono bg-gray-100 px-1 rounded">{purgeConfirm.name}</strong> to confirm:
            </p>
            <input
              type="text" value={purgeInput}
              onChange={e => setPurgeInput(e.target.value)}
              placeholder="Type tenant name to confirm"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4 focus:ring-2 focus:ring-red-500 focus:border-red-500 font-mono text-sm"
              autoFocus
            />
            <div className="flex gap-3 justify-end">
              <button onClick={() => { setPurgeConfirm(null); setPurgeInput(''); }} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
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
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Update Credentials</h3>
            <p className="text-sm text-gray-500 mb-4">Update your Azure AD App Registration credentials. Leave blank to keep current value.</p>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Application (Client) ID</label>
                <input
                  type="text" value={credForm.client_id}
                  onChange={e => setCredForm({ ...credForm, client_id: e.target.value })}
                  placeholder="Leave blank to keep current"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Client Secret</label>
                <input
                  type="password" value={credForm.client_secret}
                  onChange={e => setCredForm({ ...credForm, client_secret: e.target.value })}
                  placeholder="Leave blank to keep current"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex gap-3 justify-end mt-4">
              <button onClick={() => { setCredentialsEdit(null); setCredForm({ client_id: '', client_secret: '' }); }} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
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
            <div key={t.id} className={`bg-white rounded-xl border shadow-sm p-5 ${isInactive ? 'opacity-75' : ''}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${isInactive ? 'bg-gray-100' : 'bg-blue-50'}`}>
                    <SettingsIcon className={`w-6 h-6 ${isInactive ? 'text-gray-400' : 'text-blue-600'}`} />
                  </div>
                  <div>
                    <h3 className="font-semibold">{t.name}</h3>
                    <p className="text-sm text-gray-500 font-mono">{t.ms_tenant_id}</p>
                  </div>
                  <StatusBadge status={t.status} />
                </div>
                <div className="flex items-center gap-2">
                  {/* Common actions */}
                  <button onClick={() => testMutation.mutate(t.id)} className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200 flex items-center gap-1">
                    <Wifi className="w-4 h-4" /> Test
                  </button>
                  <button onClick={() => setCredentialsEdit({ id: t.id })} className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200 flex items-center gap-1">
                    <KeyRound className="w-4 h-4" />
                  </button>

                  {/* Active tenant actions */}
                  {isActive && (
                    <>
                      <button onClick={() => discoverMutation.mutate(t.id)} className="px-3 py-1.5 bg-blue-100 text-blue-700 rounded-lg text-sm hover:bg-blue-200 flex items-center gap-1">
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
                      <button onClick={() => reactivateMutation.mutate(t.id)} className="px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-sm hover:bg-green-200 flex items-center gap-1">
                        <Play className="w-4 h-4" /> Reactivate
                      </button>
                      <button onClick={() => setPurgeConfirm({ id: t.id, name: t.name })} className="px-3 py-1.5 bg-red-100 text-red-700 rounded-lg text-sm hover:bg-red-200 flex items-center gap-1">
                        <Trash2 className="w-4 h-4" /> Purge
                      </button>
                    </>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-5 gap-4 mt-4 text-sm">
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-gray-500">Mailboxes</p>
                  <p className="text-lg font-bold">{t.total_mailboxes}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-gray-500">OneDrives</p>
                  <p className="text-lg font-bold">{t.total_onedrives}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-gray-500">SharePoint Sites</p>
                  <p className="text-lg font-bold">{t.total_sites}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-gray-500">Entra ID Objects</p>
                  <p className="text-lg font-bold">{t.total_entra_objects || 0}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-gray-500">Last Discovery</p>
                  <p className="text-sm font-medium">{t.last_discovery_at?.slice(0, 16) || 'Never'}</p>
                </div>
              </div>
            </div>
          );
        })}
        {isLoading && <p className="text-gray-400 text-center py-8">Loading...</p>}
        {!isLoading && !tenants?.length && (
          <div className="text-center py-12 text-gray-400">
            <SettingsIcon className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-lg font-medium">No tenants configured</p>
            <p className="text-sm">Add your first M365 tenant to get started</p>
          </div>
        )}
      </div>
    </div>
  );
}
