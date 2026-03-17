import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Settings as SettingsIcon, Plus, CheckCircle, XCircle, RefreshCw, Trash2, Wifi } from 'lucide-react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import type { Tenant } from '../types';

export default function Settings() {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', ms_tenant_id: '', client_id: '', client_secret: '' });
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const qc = useQueryClient();

  const { data: tenants, isLoading } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => api.get<Tenant[]>('/tenants/'),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/tenants/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tenants'] });
      setShowForm(false);
      setForm({ name: '', ms_tenant_id: '', client_id: '', client_secret: '' });
    },
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
        <button onClick={() => setShowForm(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2">
          <Plus className="w-4 h-4" /> Add Tenant
        </button>
      </div>

      {showForm && (
        <div className="bg-white rounded-xl border shadow-sm p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">Onboard M365 Tenant</h3>
          <p className="text-sm text-gray-500 mb-4">
            Register your Azure AD App Registration credentials. Requires an app with Microsoft Graph API permissions for Exchange, OneDrive, and SharePoint.
          </p>
          <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(form); }} className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tenant Name</label>
              <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required placeholder="My Organization"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Azure AD Tenant ID</label>
              <input type="text" value={form.ms_tenant_id} onChange={e => setForm({ ...form, ms_tenant_id: e.target.value })} required placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Application (Client) ID</label>
              <input type="text" value={form.client_id} onChange={e => setForm({ ...form, client_id: e.target.value })} required placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Client Secret</label>
              <input type="password" value={form.client_secret} onChange={e => setForm({ ...form, client_secret: e.target.value })} required placeholder="Client secret value"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
            </div>
            <div className="col-span-2 flex gap-3">
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
                Add Tenant
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">
                Cancel
              </button>
            </div>
          </form>
        </div>
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
            <div className="grid grid-cols-4 gap-4 mt-4 text-sm">
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
