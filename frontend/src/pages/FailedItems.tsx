import { useState } from 'react';
import { getActivePlatformLabel } from '../config/platforms';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle2, RotateCcw, XCircle,
  ChevronDown, ChevronRight, ShieldAlert, Info, Eye, EyeOff,
  Mail, HardDrive, Globe, File, Folder, List, ListOrdered, Library,
  MessageSquare, KeyRound,
} from 'lucide-react';
import { api } from '../api/client';
import DataTable, { type Column, type FilterOption } from '../components/DataTable';
import { WORKLOAD_MAP } from '../config/workloads';
import type { FailedItemEntry, FailedItemsSummary, FailedItemCategory } from '../types';
import Breadcrumb from '../components/design-system/Breadcrumb';
import HeroSummaryBar, { type HeroStat } from '../components/design-system/HeroSummaryBar';

const CATEGORY_COLORS: Record<string, string> = {
  permission_denied: 'bg-red-100 text-red-400 border-red-500/20',
  not_found: 'bg-muted text-muted-foreground border-border',
  throttled: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  timeout: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  quota_exceeded: 'bg-orange-100 text-orange-800 border-orange-500/20',
  file_too_large: 'bg-purple-100 text-purple-800 border-purple-500/20',
  encryption_error: 'bg-red-100 text-red-400 border-red-500/20',
  storage_error: 'bg-red-100 text-red-400 border-red-500/20',
  invalid_data: 'bg-muted text-muted-foreground border-border',
  auth_expired: 'bg-red-100 text-red-400 border-red-500/20',
  server_error: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  network_error: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  unknown: 'bg-muted text-muted-foreground border-border',
};

const CATEGORY_LABELS: Record<string, string> = {
  permission_denied: 'Permission Denied',
  not_found: 'Not Found',
  throttled: 'Rate Limited',
  timeout: 'Timeout',
  quota_exceeded: 'Quota Exceeded',
  file_too_large: 'File Too Large',
  encryption_error: 'Encryption Error',
  storage_error: 'Storage Error',
  invalid_data: 'Invalid Data',
  auth_expired: 'Auth Expired',
  server_error: 'Server Error',
  network_error: 'Network Error',
  unknown: 'Unknown',
};

const ItemTypeIcon = ({ type }: { type: string | null }) => {
  switch (type) {
    case 'email': return <Mail className="w-3.5 h-3.5 text-blue-500" />;
    case 'file': return <File className="w-3.5 h-3.5 text-green-500" />;
    case 'folder': return <Folder className="w-3.5 h-3.5 text-yellow-500" />;
    case 'list': return <List className="w-3.5 h-3.5 text-purple-500" />;
    case 'list_item': return <ListOrdered className="w-3.5 h-3.5 text-purple-400" />;
    case 'document_library': return <Library className="w-3.5 h-3.5 text-teal-500" />;
    case 'calendar_event': return <Globe className="w-3.5 h-3.5 text-orange-500" />;
    case 'contact': return <HardDrive className="w-3.5 h-3.5 text-indigo-500" />;
    case 'channel_message': return <MessageSquare className="w-3.5 h-3.5 text-pink-500" />;
    case 'chat_message': return <MessageSquare className="w-3.5 h-3.5 text-pink-400" />;
    case 'user': return <KeyRound className="w-3.5 h-3.5 text-amber-500" />;
    default: return <File className="w-3.5 h-3.5 text-muted-foreground" />;
  }
};

const WorkloadIcon = ({ workload }: { workload: string }) => {
  const config = WORKLOAD_MAP[workload];
  if (!config) return <ShieldAlert className="w-5 h-5 text-muted-foreground" />;
  const Icon = config.icon;
  return <Icon className={`w-5 h-5 ${config.iconColor || 'text-muted-foreground'}`} />;
};

interface WorkloadFailureSummary {
  workload: string;
  total: number;
  unresolved: number;
  retriable: number;
  topCategory: string;
  topCategoryCount: number;
}

export default function FailedItems() {
  const [showResolved, setShowResolved] = useState(false);
  const [selectedWorkload, setSelectedWorkload] = useState<string | null>(null);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState('');
  const qc = useQueryClient();

  // Fetch summary
  const { data: summary } = useQuery({
    queryKey: ['failed-items-summary'],
    queryFn: () => api.get<FailedItemsSummary>('/failed-items/summary'),
    refetchInterval: 15000,
  });

  // Compute per-workload failure stats from summary
  const workloadStats: WorkloadFailureSummary[] = (() => {
    if (!summary?.by_workload) return [];
    return Object.entries(summary.by_workload as Record<string, any>).map(([wl, data]: [string, any]) => ({
      workload: wl,
      total: data.total || 0,
      unresolved: data.unresolved || 0,
      retriable: data.retriable || 0,
      topCategory: data.top_category || 'unknown',
      topCategoryCount: data.top_category_count || 0,
    })).sort((a, b) => b.unresolved - a.unresolved);
  })();

  // Mutations
  const resolveMutation = useMutation({
    mutationFn: (itemIds: number[]) => api.post('/failed-items/resolve', { item_ids: itemIds }),
    onSuccess: (data: any) => {
      setActionMsg(`Resolved ${data.resolved} items`);
      qc.invalidateQueries({ queryKey: ['failed-items'] });
      qc.invalidateQueries({ queryKey: ['failed-items-summary'] });
      setTimeout(() => setActionMsg(''), 4000);
    },
    onError: (err: any) => { setActionMsg(`Error: ${err.message}`); setTimeout(() => setActionMsg(''), 5000); },
  });

  const retryMutation = useMutation({
    mutationFn: (itemIds: number[]) =>
      api.post(`/failed-items/retry?${itemIds.map(id => `item_ids=${id}`).join('&')}`),
    onSuccess: (data: any) => {
      setActionMsg(`Retried ${data.total_items} items across ${data.objects_retried} objects`);
      qc.invalidateQueries({ queryKey: ['failed-items'] });
      qc.invalidateQueries({ queryKey: ['failed-items-summary'] });
      setTimeout(() => setActionMsg(''), 5000);
    },
    onError: (err: any) => { setActionMsg(`Error: ${err.message}`); setTimeout(() => setActionMsg(''), 5000); },
  });

  // Category filter options
  const categoryFilterOptions: { value: string; label: string }[] = (summary?.categories || []).map(
    (cat: FailedItemCategory) => ({
      value: cat.category,
      label: `${CATEGORY_LABELS[cat.category] || cat.category} (${cat.unresolved})`,
    })
  );

  // DataTable columns
  const columns: Column<FailedItemEntry>[] = [
    {
      key: 'item_name',
      label: 'Item',
      sortable: true,
      render: (row) => (
        <div className="flex items-center gap-2">
          <ItemTypeIcon type={row.item_type} />
          <span className="font-medium text-foreground max-w-[180px] truncate" title={row.item_name || undefined}>
            {row.item_name || 'Unknown'}
          </span>
        </div>
      ),
    },
    {
      key: 'error_category',
      label: 'Error',
      sortable: true,
      render: (row) => (
        <div>
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${CATEGORY_COLORS[row.error_category] || CATEGORY_COLORS.unknown}`}>
            {CATEGORY_LABELS[row.error_category] || row.error_category}
          </span>
          <p className="text-[11px] text-muted-foreground mt-0.5 max-w-[200px] truncate" title={row.error_message}>
            {row.error_message}
          </p>
        </div>
      ),
    },
    {
      key: 'item_path',
      label: 'Location',
      render: (row) => (
        <span className="text-muted-foreground text-xs max-w-[120px] truncate block" title={row.item_path || undefined}>
          {row.item_path || '—'}
        </span>
      ),
    },
    {
      key: 'retries_attempted',
      label: 'Retries',
      sortable: true,
      className: 'text-center',
      render: (row) => <span className="text-xs text-muted-foreground">{row.retries_attempted}</span>,
    },
    {
      key: 'is_resolved',
      label: 'Status',
      sortable: true,
      render: (row) => (
        row.is_resolved ? (
          <span className="inline-flex items-center gap-1 text-[11px] text-green-600 font-medium">
            <CheckCircle2 className="w-3 h-3" /> Resolved
          </span>
        ) : row.can_retry ? (
          <span className="inline-flex items-center gap-1 text-[11px] text-orange-600 font-medium">
            <RotateCcw className="w-3 h-3" /> Retriable
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground font-medium">
            <XCircle className="w-3 h-3" /> Permanent
          </span>
        )
      ),
    },
  ];

  const filters: FilterOption[] = [
    { key: 'error_category', label: 'All Categories', options: categoryFilterOptions },
  ];

  const heroStats: HeroStat[] = [
    {
      label: 'Total Failed',
      value: summary?.total_failed ?? 0,
      subtitle: 'Across all workloads',
      icon: XCircle,
      color: (summary?.total_failed ?? 0) > 0 ? 'red' : 'gray',
    },
    {
      label: 'Unresolved',
      value: summary?.total_unresolved ?? 0,
      subtitle: 'Needs attention',
      icon: ShieldAlert,
      color: (summary?.total_unresolved ?? 0) > 0 ? 'red' : 'green',
    },
    {
      label: 'Retriable',
      value: summary?.categories?.reduce((sum: number, c: FailedItemCategory) => sum + (c.retriable || 0), 0) ?? 0,
      subtitle: 'Ready to retry',
      icon: RotateCcw,
      color: 'amber',
    },
    {
      label: 'Error Types',
      value: summary?.categories?.length ?? 0,
      subtitle: 'Distinct categories',
      icon: Info,
      color: 'blue',
    },
  ];

  return (
    <div>
      {/* Breadcrumb + Search */}
      <Breadcrumb
        items={[
          { label: getActivePlatformLabel(), path: '/' },
          { label: 'Failed Items' },
        ]}
      />

      {/* Page Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-red-500/10">
            <ShieldAlert className="w-6 h-6 text-red-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Failed Items</h1>
            <p className="text-xs text-muted-foreground">Review failures by workload, understand root causes, take action</p>
          </div>
        </div>
        <button
          onClick={() => setShowResolved(!showResolved)}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
            showResolved ? 'bg-muted border-border text-muted-foreground' : 'bg-card border-border text-muted-foreground hover:bg-muted/50'
          }`}
        >
          {showResolved ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          {showResolved ? 'Showing Resolved' : 'Hide Resolved'}
        </button>
      </div>

      {actionMsg && (
        <div className={`rounded-lg p-3 mb-4 text-sm ${actionMsg.includes('Error') ? 'bg-red-500/10 border border-red-500/20 text-red-400' : 'bg-green-500/10 border border-green-500/20 text-green-400'}`}>
          {actionMsg}
        </div>
      )}

      {/* Hero Stats */}
      <HeroSummaryBar stats={heroStats} />

      {/* ═══ Workload Failure Cards ═══ */}
      {summary && workloadStats.length > 0 && (
        <div className="bg-card rounded-xl border shadow-sm mb-6">
          <div className="px-5 py-3 border-b flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-foreground">By Workload</h2>
              <p className="text-xs text-muted-foreground">Click a workload to filter the table below</p>
            </div>
            {selectedWorkload && (
              <button
                onClick={() => setSelectedWorkload(null)}
                className="text-xs text-blue-600 hover:underline font-medium"
              >
                Show all workloads
              </button>
            )}
          </div>
          <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
            {workloadStats.map(ws => {
              const config = WORKLOAD_MAP[ws.workload];
              const isSelected = selectedWorkload === ws.workload;
              const bgColor = config?.bgColor || 'bg-muted/50';
              const borderColor = isSelected ? 'border-blue-400 ring-2 ring-blue-200' : (config?.borderColor || 'border-border');

              return (
                <div
                  key={ws.workload}
                  onClick={() => setSelectedWorkload(isSelected ? null : ws.workload)}
                  className={`${bgColor} border ${borderColor} rounded-xl p-4 cursor-pointer hover:shadow-md transition-all`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <WorkloadIcon workload={ws.workload} />
                    <span className="text-sm font-semibold text-foreground">
                      {config?.label || ws.workload}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-red-600 font-bold">{ws.unresolved}</span>
                    <span className="text-muted-foreground">unresolved</span>
                    {ws.retriable > 0 && (
                      <span className="text-orange-500 font-medium">{ws.retriable} retriable</span>
                    )}
                  </div>
                  {ws.topCategory && ws.topCategoryCount > 0 && (
                    <div className="mt-2">
                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium border ${CATEGORY_COLORS[ws.topCategory] || CATEGORY_COLORS.unknown}`}>
                        {CATEGORY_LABELS[ws.topCategory]} ({ws.topCategoryCount})
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ═══ Error Categories (collapsible) ═══ */}
      {summary && summary.categories.length > 0 && !selectedWorkload && (
        <div className="bg-card rounded-xl border shadow-sm mb-6">
          <div className="px-5 py-3 border-b flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Error Categories</h2>
              <p className="text-xs text-muted-foreground">Click for resolution guidance</p>
            </div>
          </div>
          <div className="divide-y">
            {summary.categories.map((cat: FailedItemCategory) => {
              const isExpanded = expandedCategory === cat.category;
              return (
                <div key={cat.category}>
                  <div
                    className="flex items-center gap-3 px-5 py-2.5 cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => setExpandedCategory(isExpanded ? null : cat.category)}
                  >
                    {isExpanded ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" /> : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />}
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${CATEGORY_COLORS[cat.category] || CATEGORY_COLORS.unknown}`}>
                      {CATEGORY_LABELS[cat.category] || cat.category}
                    </span>
                    <span className="text-xs text-muted-foreground font-medium">{cat.count}</span>
                    {cat.unresolved > 0 && <span className="text-[10px] text-orange-600 bg-orange-500/10 px-1.5 py-0.5 rounded-full">{cat.unresolved} open</span>}
                    {cat.retriable > 0 && <span className="text-[10px] text-blue-600 bg-blue-500/10 px-1.5 py-0.5 rounded-full">{cat.retriable} retriable</span>}
                  </div>
                  {isExpanded && (
                    <div className="px-12 pb-3">
                      <div className="bg-blue-500/10 border border-blue-100 rounded-lg p-3">
                        <div className="flex items-start gap-2">
                          <Info className="w-3.5 h-3.5 text-blue-500 mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="text-xs font-semibold text-blue-900 mb-0.5">Resolution</p>
                            <p className="text-xs text-blue-400">{cat.resolution_hint}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ═══ Items DataTable (filtered by selected workload) ═══ */}
      <DataTable<FailedItemEntry>
        queryKey={`failed-items-${selectedWorkload || 'all'}-${showResolved}`}
        endpoint="/failed-items"
        columns={columns}
        extraParams={{
          ...(showResolved ? {} : { is_resolved: 'false' }),
          ...(selectedWorkload ? { workload_type: selectedWorkload } : {}),
        }}
        title={selectedWorkload ? `${WORKLOAD_MAP[selectedWorkload]?.label || selectedWorkload} Failures` : 'All Failed Items'}
        searchable
        searchPlaceholder="Search by item name or error..."
        filters={filters}
        exportable
        exportEndpoint="/export/csv?source=failed_items"
        defaultSortBy="created_at"
        defaultSortOrder="desc"
        defaultPageSize={25}
        emptyMessage={selectedWorkload ? `No failures for ${WORKLOAD_MAP[selectedWorkload]?.label || selectedWorkload}` : 'No failed items found'}
        rowKey="id"
        refetchInterval={10000}
        actions={(row) => (
          !row.is_resolved ? (
            <div className="flex items-center gap-2">
              {row.can_retry && (
                <button
                  onClick={() => retryMutation.mutate([row.id])}
                  disabled={retryMutation.isPending}
                  className="text-orange-600 hover:text-orange-800 text-xs font-medium"
                  title="Retry"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              )}
              <button
                onClick={() => resolveMutation.mutate([row.id])}
                disabled={resolveMutation.isPending}
                className="text-green-600 hover:text-green-400 text-xs font-medium"
                title="Resolve"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : null
        )}
      />
    </div>
  );
}
