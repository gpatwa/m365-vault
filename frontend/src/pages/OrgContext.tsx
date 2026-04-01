import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Users, Globe, Shield, RefreshCw, Loader2, ShieldAlert, Crown } from 'lucide-react';
import { api } from '../api/client';
import CriticalityBadge from '../components/CriticalityBadge';

const TABS = ['Users', 'Sites', 'VIP Groups'] as const;

export default function OrgContext() {
  const [tab, setTab] = useState<typeof TABS[number]>('Users');
  const [userPage, setUserPage] = useState(1);
  const [sitePage, setSitePage] = useState(1);
  const [tierFilter, setTierFilter] = useState('');
  const [search, setSearch] = useState('');
  const queryClient = useQueryClient();

  // Get first tenant (simplified — would be tenant selector in multi-tenant)
  const { data: tenants } = useQuery({ queryKey: ['tenants'], queryFn: () => api.get<any[]>('/tenants/') });
  const tenantId = tenants?.[0]?.id;

  const { data: summary } = useQuery({
    queryKey: ['org-context-summary', tenantId],
    queryFn: () => api.get<any>(`/org-context/summary?tenant_id=${tenantId}`),
    enabled: !!tenantId,
  });

  const { data: usersData, isLoading: loadingUsers } = useQuery({
    queryKey: ['org-context-users', tenantId, tierFilter, search, userPage],
    queryFn: () => api.get<any>(`/org-context/users?tenant_id=${tenantId}&page=${userPage}&page_size=25${tierFilter ? `&tier=${tierFilter}` : ''}${search ? `&search=${encodeURIComponent(search)}` : ''}`),
    enabled: !!tenantId && tab === 'Users',
  });

  const { data: sitesData, isLoading: loadingSites } = useQuery({
    queryKey: ['org-context-sites', tenantId, tierFilter, search, sitePage],
    queryFn: () => api.get<any>(`/org-context/sites?tenant_id=${tenantId}&page=${sitePage}&page_size=25${tierFilter ? `&tier=${tierFilter}` : ''}${search ? `&search=${encodeURIComponent(search)}` : ''}`),
    enabled: !!tenantId && tab === 'Sites',
  });

  const { data: vipData } = useQuery({
    queryKey: ['org-context-vip-groups', tenantId],
    queryFn: () => api.get<any>(`/org-context/vip-groups?tenant_id=${tenantId}`),
    enabled: !!tenantId && tab === 'VIP Groups',
  });

  const syncMutation = useMutation({
    mutationFn: () => api.post(`/org-context/sync?tenant_id=${tenantId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-context-summary'] });
      queryClient.invalidateQueries({ queryKey: ['org-context-users'] });
      queryClient.invalidateQueries({ queryKey: ['org-context-sites'] });
    },
  });

  const tiers = summary?.by_tier || { critical: 0, high: 0, medium: 0, low: 0 };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Shield className="w-6 h-6 text-blue-600" />
            Organizational Context
          </h1>
          <p className="text-sm text-gray-500 mt-1">Auto-detected criticality scores from Microsoft Graph signals</p>
        </div>
        <button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending || !tenantId}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          {syncMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {syncMutation.isPending ? 'Syncing...' : 'Sync Now'}
        </button>
      </div>

      {/* Sync result toast */}
      {syncMutation.isSuccess && (
        <div className="mb-4 px-4 py-3 bg-green-50 border border-green-200 rounded-xl text-sm text-green-800">
          Sync complete: {(syncMutation.data as any)?.users_scored} users and {(syncMutation.data as any)?.sites_scored} sites scored
          {(syncMutation.data as any)?.tiers?.critical > 0 && ` — ${(syncMutation.data as any).tiers.critical} critical users detected`}
        </div>
      )}

      {/* Hero stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-red-700">{tiers.critical}</div>
          <div className="text-xs text-red-600 font-medium">Critical</div>
        </div>
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-orange-700">{tiers.high}</div>
          <div className="text-xs text-orange-600 font-medium">High</div>
        </div>
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-blue-700">{summary?.total_users || 0}</div>
          <div className="text-xs text-blue-600 font-medium">Total Scored</div>
        </div>
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-gray-700">{summary?.vip_groups_count || 0}</div>
          <div className="text-xs text-gray-500 font-medium">VIP Groups</div>
        </div>
      </div>

      {/* Top critical users */}
      {summary?.top_critical_users?.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
            <Crown className="w-4 h-4 text-amber-500" /> Most Critical Users
          </h3>
          <div className="flex flex-wrap gap-3">
            {summary.top_critical_users.map((u: any, i: number) => (
              <div key={i} className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2">
                <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center text-red-700 text-xs font-bold">
                  {u.criticality_score}
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-900">{u.display_name}</div>
                  <div className="text-[11px] text-gray-500">{u.top_signal}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-4">
        {TABS.map(t => (
          <button key={t} onClick={() => { setTab(t); setTierFilter(''); setSearch(''); }}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}>
            {t === 'Users' && <Users className="w-4 h-4 inline mr-1.5" />}
            {t === 'Sites' && <Globe className="w-4 h-4 inline mr-1.5" />}
            {t === 'VIP Groups' && <ShieldAlert className="w-4 h-4 inline mr-1.5" />}
            {t}
          </button>
        ))}
      </div>

      {/* Filters */}
      {(tab === 'Users' || tab === 'Sites') && (
        <div className="flex items-center gap-3 mb-4">
          <input type="text" value={search} onChange={e => { setSearch(e.target.value); setUserPage(1); setSitePage(1); }}
            placeholder={`Search ${tab.toLowerCase()}...`}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm w-64 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <select value={tierFilter} onChange={e => { setTierFilter(e.target.value); setUserPage(1); setSitePage(1); }}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option value="">All Tiers</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      )}

      {/* Users tab */}
      {tab === 'Users' && (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">User</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Department</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Title</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Score</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Tier</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Roles</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Reports</th>
              </tr>
            </thead>
            <tbody>
              {loadingUsers ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-400">Loading...</td></tr>
              ) : usersData?.items?.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-400">
                  {summary?.total_users === 0 ? 'No users scored yet. Click "Sync Now" to collect org context.' : 'No users match your filters.'}
                </td></tr>
              ) : usersData?.items?.map((u: any) => (
                <tr key={u.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="text-sm font-medium text-gray-900">{u.display_name}</div>
                    <div className="text-xs text-gray-500">{u.email}</div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{u.department || '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{u.job_title || '—'}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1.5">
                      <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{
                          width: `${u.criticality_score}%`,
                          background: u.criticality_score >= 80 ? '#dc2626' : u.criticality_score >= 60 ? '#ea580c' : u.criticality_score >= 40 ? '#2563eb' : '#6b7280',
                        }} />
                      </div>
                      <span className="text-xs font-medium text-gray-700 w-6">{u.criticality_score}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center"><CriticalityBadge tier={u.criticality_tier} /></td>
                  <td className="px-4 py-3 text-center">
                    {u.is_global_admin ? (
                      <span className="text-[10px] px-1.5 py-0.5 bg-red-100 text-red-700 rounded font-semibold">Global Admin</span>
                    ) : u.has_privileged_role ? (
                      <span className="text-[10px] px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded font-semibold">Privileged</span>
                    ) : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-center text-sm text-gray-600">{u.direct_reports_count || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {/* Pagination */}
          {usersData && usersData.total > 25 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
              <span className="text-xs text-gray-500">{usersData.total} users</span>
              <div className="flex gap-1">
                <button onClick={() => setUserPage(p => Math.max(1, p - 1))} disabled={userPage === 1}
                  className="px-3 py-1 text-xs border border-gray-300 rounded disabled:opacity-30">Prev</button>
                <button onClick={() => setUserPage(p => p + 1)} disabled={userPage * 25 >= usersData.total}
                  className="px-3 py-1 text-xs border border-gray-300 rounded disabled:opacity-30">Next</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Sites tab */}
      {tab === 'Sites' && (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Site</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Score</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Tier</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Files</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Visitors</th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Sharing</th>
              </tr>
            </thead>
            <tbody>
              {loadingSites ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">Loading...</td></tr>
              ) : sitesData?.items?.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">No sites scored yet.</td></tr>
              ) : sitesData?.items?.map((s: any) => (
                <tr key={s.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="text-sm font-medium text-gray-900">{s.site_name}</div>
                    <div className="text-xs text-gray-500 truncate max-w-xs">{s.site_url}</div>
                  </td>
                  <td className="px-4 py-3 text-center text-sm font-medium">{s.criticality_score}</td>
                  <td className="px-4 py-3 text-center"><CriticalityBadge tier={s.criticality_tier} /></td>
                  <td className="px-4 py-3 text-center text-sm text-gray-600">{s.file_count}</td>
                  <td className="px-4 py-3 text-center text-sm text-gray-600">{s.unique_visitors}</td>
                  <td className="px-4 py-3 text-center">
                    {s.external_sharing_enabled ? (
                      <span className="text-[10px] px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded font-semibold">External</span>
                    ) : <span className="text-gray-300">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* VIP Groups tab */}
      {tab === 'VIP Groups' && (
        <div className="space-y-4">
          {vipData?.groups?.length === 0 && (
            <div className="bg-white border border-gray-200 rounded-xl p-8 text-center">
              <ShieldAlert className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-500">No VIP groups defined yet.</p>
              <p className="text-xs text-gray-400 mt-1">VIP groups boost criticality scores for important users.</p>
            </div>
          )}
          {vipData?.groups?.map((g: any) => (
            <div key={g.id} className="bg-white border border-gray-200 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900">{g.name}</h3>
                  {g.description && <p className="text-xs text-gray-500 mt-0.5">{g.description}</p>}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500">{g.member_count} members</span>
                  <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded font-medium">+{g.criticality_boost} boost</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
