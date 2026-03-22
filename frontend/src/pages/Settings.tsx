import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Settings as SettingsIcon, Plus, CheckCircle, XCircle, RefreshCw, Trash2, Wifi } from 'lucide-react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import OnboardingWizard from '../components/OnboardingWizard';
import type { Tenant } from '../types';

export default function Settings() {
  const [showWizard, setShowWizard] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const qc = useQueryClient();

  const { data: tenants, isLoading } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => api.get<Tenant[]>('/tenants/'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.del(`/tenants/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenants'] }),
  });

  const testMutation = useMutation({
    mutationFn: (id: number) => api.post<{ success: boolean; message: string }>(`/tenants/${id}/test`),
    onSuccess: (data) => setTestResult(data),
  });

  const discoverMutation = useMutation({
    mutationFn: (id: number) => api.post(`/tenants/${id}/discover`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenants'] }),
  });

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

      {testResult && (
        <div className={`rounded-lg p-4 mb-4 flex items-center gap-3 ${testResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
          {testResult.success ? <CheckCircle className="w-5 h-5 text-green-600" /> : <XCircle className="w-5 h-5 text-red-600" />}
          <span className={testResult.success ? 'text-green-800' : 'text-red-800'}>{testResult.message}</span>
          <button onClick={() => setTestResult(null)} className="ml-auto text-gray-400 hover:text-gray-600">&times;</button>
        </div>
      )}

      <div className="space-y-4">
        {tenants?.map(t => (
          <div key={t.id} className="bg-white rounded-xl border shadow-sm p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-50 rounded-lg">
                  <SettingsIcon className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold">{t.name}</h3>
                  <p className="text-sm text-gray-500 font-mono">{t.ms_tenant_id}</p>
                </div>
                <StatusBadge status={t.status} />
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => testMutation.mutate(t.id)} className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200 flex items-center gap-1">
                  <Wifi className="w-4 h-4" /> Test
                </button>
                <button onClick={() => discoverMutation.mutate(t.id)} className="px-3 py-1.5 bg-blue-100 text-blue-700 rounded-lg text-sm hover:bg-blue-200 flex items-center gap-1">
                  <RefreshCw className="w-4 h-4" /> Discover
                </button>
                <button onClick={() => { if (confirm('Delete?')) deleteMutation.mutate(t.id); }} className="px-3 py-1.5 bg-red-100 text-red-700 rounded-lg text-sm hover:bg-red-200 flex items-center gap-1">
                  <Trash2 className="w-4 h-4" />
                </button>
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
        ))}
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
