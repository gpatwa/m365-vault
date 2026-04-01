import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ChevronRight, Clock, FileText, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import { WORKLOAD_MAP } from '../config/workloads';
import { formatSize, timeAgo } from '../utils/format';

interface Snapshot {
  id: number;
  snapshot_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  item_count: number;
  size_bytes: number;
  items_failed: number;
}

interface SnapshotItem {
  id: number;
  item_type: string;
  ms_item_id: string;
  name: string;
  path: string;
  size_bytes: number;
  metadata: any;
}

export default function ObjectDetail() {
  const { workload, objectId } = useParams<{ workload: string; objectId: string }>();
  const navigate = useNavigate();
  const wlConfig = WORKLOAD_MAP[workload || ''];
  const Icon = wlConfig?.icon;

  // Fetch object info
  const { data: object } = useQuery({
    queryKey: ['object-detail', objectId],
    queryFn: async () => {
      // Use the appropriate workload API
      const endpoint = getObjectEndpoint(workload!, objectId!);
      return api.get<any>(endpoint);
    },
    enabled: !!objectId && !!workload,
  });

  // Fetch snapshot history
  const { data: snapshots, isLoading: loadingSnapshots } = useQuery({
    queryKey: ['object-snapshots', objectId],
    queryFn: () => api.get<any>(`/jobs/snapshots?protected_object_id=${objectId}&page_size=20`),
    enabled: !!objectId,
  });

  // Selected snapshot for item browsing
  const latestSnapshotId = snapshots?.items?.[0]?.id;

  const { data: items, isLoading: loadingItems } = useQuery({
    queryKey: ['snapshot-items', latestSnapshotId],
    queryFn: () => {
      const endpoint = getItemsEndpoint(workload!, latestSnapshotId!);
      return api.get<any>(endpoint);
    },
    enabled: !!latestSnapshotId,
  });

  const workloadLabel = wlConfig?.label || workload || 'Unknown';
  const objectName = object?.display_name || object?.name || `Object #${objectId}`;

  return (
    <div>
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-sm text-gray-500 mb-4">
        <button onClick={() => navigate('/')} className="hover:text-gray-700">Dashboard</button>
        <ChevronRight className="w-3.5 h-3.5" />
        <button onClick={() => navigate(`/${workload?.replace('_', '-')}`)} className="hover:text-gray-700">
          {workloadLabel}
        </button>
        <ChevronRight className="w-3.5 h-3.5" />
        <span className="text-gray-900 font-medium truncate max-w-[200px]">{objectName}</span>
      </nav>

      {/* Object Summary Bar */}
      <div className={`rounded-xl border ${wlConfig?.borderColor || 'border-gray-200'} ${wlConfig?.bgColor || 'bg-gray-50'} p-5 mb-6`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {Icon && (
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center bg-white border ${wlConfig?.borderColor || 'border-gray-200'}`}>
                <Icon className={`w-5 h-5 ${wlConfig?.iconColor || 'text-gray-500'}`} />
              </div>
            )}
            <div>
              <h1 className="text-lg font-bold text-gray-900">{objectName}</h1>
              <div className="flex items-center gap-3 mt-0.5">
                {object?.status && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    object.status === 'protected' ? 'bg-green-100 text-green-700' :
                    object.status === 'error' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {object.status}
                  </span>
                )}
                {object?.email && <span className="text-xs text-gray-500">{object.email}</span>}
                {object?.site_url && <span className="text-xs text-gray-500 truncate max-w-[300px]">{object.site_url}</span>}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-6 text-center">
            <div>
              <p className="text-xl font-bold text-gray-900">{object?.total_items_backed_up || 0}</p>
              <p className="text-[10px] text-gray-500 uppercase">Items</p>
            </div>
            <div>
              <p className="text-xl font-bold text-gray-900">{formatSize(object?.total_size_bytes || 0)}</p>
              <p className="text-[10px] text-gray-500 uppercase">Size</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-700">{object?.last_backup_at ? timeAgo(object.last_backup_at) : 'Never'}</p>
              <p className="text-[10px] text-gray-500 uppercase">Last Backup</p>
            </div>
          </div>
        </div>
      </div>

      {/* Two columns: Snapshot History + Item Catalog */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Snapshot History */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-gray-400" />
                <h3 className="text-sm font-semibold text-gray-800">Backup History</h3>
              </div>
              <span className="text-[10px] text-gray-400">{snapshots?.total || 0} snapshots</span>
            </div>
            <div className="divide-y divide-gray-50 max-h-[500px] overflow-y-auto">
              {loadingSnapshots ? (
                <div className="p-4 text-center"><Loader2 className="w-5 h-5 animate-spin text-gray-300 mx-auto" /></div>
              ) : (snapshots?.items || []).length === 0 ? (
                <div className="p-6 text-center text-sm text-gray-400">No backups yet</div>
              ) : (
                (snapshots?.items || []).map((snap: Snapshot) => (
                  <div
                    key={snap.id}
                    className={`px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors ${
                      snap.id === latestSnapshotId ? 'bg-blue-50/50 border-l-2 border-blue-400' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${
                          snap.status === 'completed' ? 'bg-green-400' :
                          snap.status === 'failed' ? 'bg-red-400' :
                          snap.status === 'in_progress' ? 'bg-blue-400 animate-pulse' :
                          'bg-gray-300'
                        }`} />
                        <span className="text-xs font-medium text-gray-700">
                          #{snap.id}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 rounded text-gray-500">
                          {snap.snapshot_type}
                        </span>
                      </div>
                      <span className="text-[10px] text-gray-400">
                        {snap.completed_at ? timeAgo(snap.completed_at) : 'Running'}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-[10px] text-gray-500">
                      <span>{snap.item_count} items</span>
                      <span>{formatSize(snap.size_bytes)}</span>
                      {snap.items_failed > 0 && (
                        <span className="text-red-500">{snap.items_failed} failed</span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right: Item Catalog */}
        <div className="lg:col-span-2">
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-gray-400" />
                <h3 className="text-sm font-semibold text-gray-800">
                  Backed-up Items
                  {latestSnapshotId && <span className="text-gray-400 font-normal ml-1">(Snapshot #{latestSnapshotId})</span>}
                </h3>
              </div>
              <span className="text-[10px] text-gray-400">{items?.total || 0} items</span>
            </div>
            <div className="max-h-[500px] overflow-y-auto">
              {loadingItems ? (
                <div className="p-8 text-center"><Loader2 className="w-5 h-5 animate-spin text-gray-300 mx-auto" /></div>
              ) : (items?.items || []).length === 0 ? (
                <div className="p-8 text-center text-sm text-gray-400">
                  {latestSnapshotId ? 'No items in this snapshot' : 'Run a backup to see items here'}
                </div>
              ) : (
                <table className="w-full">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="text-left px-4 py-2 text-[10px] font-semibold text-gray-500 uppercase">Name</th>
                      <th className="text-left px-4 py-2 text-[10px] font-semibold text-gray-500 uppercase">Type</th>
                      <th className="text-left px-4 py-2 text-[10px] font-semibold text-gray-500 uppercase">Path</th>
                      <th className="text-right px-4 py-2 text-[10px] font-semibold text-gray-500 uppercase">Size</th>
                      <th className="text-right px-4 py-2 text-[10px] font-semibold text-gray-500 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {(items?.items || []).map((item: SnapshotItem) => (
                      <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-2.5">
                          <p className="text-sm text-gray-800 font-medium truncate max-w-[250px]">{item.name}</p>
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 rounded text-gray-500">
                            {item.item_type.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-xs text-gray-500 truncate max-w-[150px]">{item.path || '-'}</td>
                        <td className="px-4 py-2.5 text-xs text-gray-500 text-right">{formatSize(item.size_bytes)}</td>
                        <td className="px-4 py-2.5 text-right">
                          <button className="text-[10px] px-2 py-1 bg-blue-50 text-blue-600 rounded hover:bg-blue-100 font-medium transition-colors">
                            Restore
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Helper: Map workload to correct API endpoints ──

function getObjectEndpoint(_workload: string, objectId: string): string {
  return `/dashboard/object/${objectId}`;
}

function getItemsEndpoint(workload: string, snapshotId: number): string {
  switch (workload) {
    case 'exchange': return `/exchange/snapshot/${snapshotId}/items?page_size=50`;
    case 'onedrive': return `/onedrive/snapshot/${snapshotId}/items?page_size=50`;
    case 'sharepoint': return `/sharepoint/snapshot/${snapshotId}/items?page_size=50`;
    case 'teams': return `/teams/snapshot/${snapshotId}/items?page_size=50`;
    case 'entra_id': return `/entra-id/snapshot/${snapshotId}/items?page_size=50`;
    default: return `/exchange/snapshot/${snapshotId}/items?page_size=50`;
  }
}
