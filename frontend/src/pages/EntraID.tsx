import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Shield, Search, Users, KeyRound, ShieldCheck, AppWindow, MapPin, UserCog } from 'lucide-react';
import { api } from '../api/client';
import { formatSize, timeAgo } from '../utils/format';

interface EntraSummary {
  protected: boolean;
  object_id?: number;
  status?: string;
  last_backup?: string;
  snapshot_id?: number;
  item_count?: number;
  size_bytes?: number;
  counts?: Record<string, number>;
  message?: string;
}

interface SnapshotItem {
  id: number;
  item_type: string;
  ms_item_id: string;
  name: string;
  path: string;
  size_bytes: number;
  metadata: Record<string, any> | null;
}

const ITEM_TYPE_CONFIG: Record<string, { label: string; icon: typeof Users; color: string }> = {
  user: { label: 'Users', icon: Users, color: 'text-blue-600' },
  group: { label: 'Groups', icon: Users, color: 'text-purple-600' },
  directory_role: { label: 'Directory Roles', icon: UserCog, color: 'text-amber-600' },
  role_assignment: { label: 'Role Assignments', icon: KeyRound, color: 'text-orange-600' },
  conditional_access_policy: { label: 'Conditional Access', icon: ShieldCheck, color: 'text-red-600' },
  app_registration: { label: 'App Registrations', icon: AppWindow, color: 'text-green-600' },
  named_location: { label: 'Named Locations', icon: MapPin, color: 'text-indigo-600' },
};

export default function EntraID() {
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const tenantId = 1;

  const { data: summary, isLoading } = useQuery({
    queryKey: ['entra-summary', tenantId],
    queryFn: () => api.get<EntraSummary>(`/entra-id/summary?tenant_id=${tenantId}`),
  });

  const { data: items, isLoading: loadingItems } = useQuery({
    queryKey: ['entra-items', summary?.snapshot_id, selectedType, search],
    queryFn: () => api.get<{ total: number; items: SnapshotItem[] }>(
      `/entra-id/snapshot/${summary!.snapshot_id}/items?page_size=100${selectedType ? `&item_type=${selectedType}` : ''}${search ? `&search=${search}` : ''}`
    ),
    enabled: !!summary?.snapshot_id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-600" />
      </div>
    );
  }

  if (!summary?.protected) {
    return (
      <div className="text-center py-16">
        <Shield className="w-16 h-16 mx-auto mb-4 text-gray-300" />
        <h2 className="text-xl font-semibold text-gray-700 mb-2">Entra ID Not Discovered</h2>
        <p className="text-gray-500">Run discovery on your tenant from the Settings page to enable Entra ID backup.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-50 rounded-lg">
            <Shield className="w-6 h-6 text-amber-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Entra ID</h1>
            <p className="text-sm text-gray-500">
              {summary.last_backup ? `Last backup ${timeAgo(summary.last_backup)}` : 'No backups yet'}
              {summary.item_count ? ` • ${summary.item_count} objects • ${formatSize(summary.size_bytes || 0)}` : ''}
            </p>
          </div>
        </div>
      </div>

      {/* Object Type Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {Object.entries(ITEM_TYPE_CONFIG).map(([type, config]) => {
          const count = summary.counts?.[type] || 0;
          const Icon = config.icon;
          const isSelected = selectedType === type;
          return (
            <button
              key={type}
              onClick={() => setSelectedType(isSelected ? null : type)}
              className={`p-3 rounded-lg border text-left transition-all ${
                isSelected
                  ? 'border-amber-400 bg-amber-50 ring-2 ring-amber-200'
                  : 'border-gray-200 bg-white hover:border-amber-200 hover:bg-amber-50/50'
              }`}
            >
              <Icon className={`w-5 h-5 mb-1 ${config.color}`} />
              <p className="text-lg font-bold">{count}</p>
              <p className="text-xs text-gray-500 truncate">{config.label}</p>
            </button>
          );
        })}
      </div>

      {/* Search */}
      {summary.snapshot_id && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search backed-up objects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
          />
        </div>
      )}

      {/* Items Table */}
      {summary.snapshot_id && (
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Type</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Details</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Size</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loadingItems ? (
                <tr><td colSpan={4} className="text-center py-8 text-gray-400">Loading...</td></tr>
              ) : items?.items?.length ? (
                items.items.map((item) => {
                  const config = ITEM_TYPE_CONFIG[item.item_type];
                  const Icon = config?.icon || Shield;
                  return (
                    <tr key={item.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${config?.color || 'text-gray-600'}`}>
                          <Icon className="w-3.5 h-3.5" />
                          {config?.label || item.item_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-900">{item.name}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {item.metadata && Object.entries(item.metadata)
                          .filter(([, v]) => v !== null && v !== undefined && v !== '')
                          .slice(0, 3)
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(' • ')}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-500">{formatSize(item.size_bytes)}</td>
                    </tr>
                  );
                })
              ) : (
                <tr><td colSpan={4} className="text-center py-8 text-gray-400">
                  {selectedType ? 'No items of this type' : 'No backed-up objects yet'}
                </td></tr>
              )}
            </tbody>
          </table>
          {items?.total ? (
            <div className="px-4 py-2 bg-gray-50 border-t text-xs text-gray-500">
              Showing {items.items.length} of {items.total} objects
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
