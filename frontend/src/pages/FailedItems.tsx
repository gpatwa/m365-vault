import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle, CheckCircle2, RotateCcw, XCircle,
  ChevronDown, ChevronRight, ShieldAlert, Info, Eye, EyeOff,
  Mail, HardDrive, Globe, File, Folder, List, ListOrdered, Library,
} from 'lucide-react';
import { api } from '../api/client';
import DataTable, { type Column, type FilterOption } from '../components/DataTable';
import type { FailedItemEntry, FailedItemsSummary, FailedItemCategory } from '../types';

const CATEGORY_COLORS: Record<string, string> = {
  permission_denied: 'bg-red-100 text-red-800 border-red-200',
  not_found: 'bg-gray-100 text-gray-700 border-gray-200',
  throttled: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  timeout: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  quota_exceeded: 'bg-orange-100 text-orange-800 border-orange-200',
  file_too_large: 'bg-purple-100 text-purple-800 border-purple-200',
  encryption_error: 'bg-red-100 text-red-800 border-red-200',
  storage_error: 'bg-red-100 text-red-800 border-red-200',
  invalid_data: 'bg-gray-100 text-gray-700 border-gray-200',
  auth_expired: 'bg-red-100 text-red-800 border-red-200',
  server_error: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  network_error: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  unknown: 'bg-gray-100 text-gray-600 border-gray-200',
};

const CATEGORY_ICONS: Record<string, string> = {
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
    case 'email': return <Mail className="w-4 h-4 text-blue-500" />;
    case 'file': return <File className="w-4 h-4 text-green-500" />;
    case 'folder': return <Folder className="w-4 h-4 text-yellow-500" />;
    case 'list': return <List className="w-4 h-4 text-purple-500" />;
    case 'list_item': return <ListOrdered className="w-4 h-4 text-purple-400" />;
    case 'document_library': return <Library className="w-4 h-4 text-teal-500" />;
    case 'calendar_event': return <Globe className="w-4 h-4 text-orange-500" />;
    case 'contact': return <HardDrive className="w-4 h-4 text-indigo-500" />;
    default: return <File className="w-4 h-4 text-gray-400" />;
  }
};

export default function FailedItems() {
  const [showResolved, setShowResolved] = useState(false);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState('');
  const qc = useQueryClient();

  // Fetch summary
  const { data: summary } = useQuery({
    queryKey: ['failed-items-summary'],
    queryFn: () => api.get<FailedItemsSummary>('/failed-items/summary'),
    refetchInterval: 15000,
  });

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

  // Build category filter options from summary
  const categoryFilterOptions: { value: string; label: string }[] = (summary?.categories || []).map(
    (cat: FailedItemCategory) => ({
      value: cat.category,
      label: `${CATEGORY_ICONS[cat.category] || cat.category} (${cat.unresolved})`,
    })
  );

  const columns: Column<FailedItemEntry>[] = [
    {
      key: 'item_name',
      label: 'Item',
      sortable: true,
      render: (row) => (
        <div className="flex items-center gap-2">
          <ItemTypeIcon type={row.item_type} />
          <span className="font-medium text-gray-900 max-w-[200px] truncate" title={row.item_name || undefined}>
            {row.item_name || 'Unknown'}
          </span>
        </div>
      ),
    },
    {
      key: 'item_type',
      label: 'Type',
      sortable: true,
      render: (row) => (
        <span className="capitalize text-gray-600 text-xs">
          {(row.item_type || 'unknown').replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'item_path',
      label: 'Path',
      render: (row) => (
        <span className="text-gray-500 text-xs max-w-[150px] truncate block" title={row.item_path || undefined}>
          {row.item_path || '—'}
        </span>
      ),
    },
    {
      key: 'error_message',
      label: 'Error',
      render: (row) => (
        <div className="max-w-[250px]">
          <p className="text-xs text-red-600 truncate" title={row.error_message}>
            {row.error_message}
          </p>
          {row.error_code && (
            <p className="text-xs text-gray-400 mt-0.5">{row.error_code}</p>
          )}
        </div>
      ),
    },
    {
      key: 'error_category',
      label: 'Category',
      sortable: true,
      render: (row) => (
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${CATEGORY_COLORS[row.error_category] || CATEGORY_COLORS.unknown}`}>
          {CATEGORY_ICONS[row.error_category] || row.error_category}
        </span>
      ),
    },
    {
      key: 'retries_attempted',
      label: 'Retries',
      sortable: true,
      render: (row) => <span className="text-center text-xs text-gray-500">{row.retries_attempted}</span>,
    },
    {
      key: 'is_resolved',
      label: 'Status',
      sortable: true,
      render: (row) => (
        row.is_resolved ? (
          <span className="inline-flex items-center gap-1 text-xs text-green-600 font-medium">
            <CheckCircle2 className="w-3 h-3" /> Resolved
          </span>
        ) : row.can_retry ? (
          <span className="inline-flex items-center gap-1 text-xs text-orange-600 font-medium">
            <RotateCcw className="w-3 h-3" /> Retriable
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs text-gray-500 font-medium">
            <XCircle className="w-3 h-3" /> Permanent
          </span>
        )
      ),
    },
  ];

  const filters: FilterOption[] = [
    {
      key: 'error_category',
      label: 'All Categories',
      options: categoryFilterOptions,
    },
  ];

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <ShieldAlert className="w-7 h-7 text-red-500" />
            Failed Items
          </h1>
          <p className="text-gray-500">Review skipped items, understand failures, and take action</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowResolved(!showResolved)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
              showResolved ? 'bg-gray-100 border-gray-300 text-gray-700' : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'
            }`}
          >
            {showResolved ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            {showResolved ? 'Showing Resolved' : 'Hide Resolved'}
          </button>
        </div>
      </div>

      {/* Action message */}
      {actionMsg && (
        <div className={`rounded-lg p-3 mb-4 text-sm ${actionMsg.includes('Error') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-green-50 border border-green-200 text-green-700'}`}>
          {actionMsg}
        </div>
      )}

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl border shadow-sm p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-lg">
                <XCircle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Failed</p>
                <p className="text-2xl font-bold text-gray-900">{summary.total_failed}</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border shadow-sm p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-100 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Unresolved</p>
                <p className="text-2xl font-bold text-gray-900">{summary.total_unresolved}</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border shadow-sm p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Info className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Error Categories</p>
                <p className="text-2xl font-bold text-gray-900">{summary.categories.length}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error category breakdown */}
      {summary && summary.categories.length > 0 && (
        <div className="bg-white rounded-xl border shadow-sm mb-6">
          <div className="px-5 py-4 border-b">
            <h2 className="text-lg font-semibold text-gray-900">Error Categories</h2>
            <p className="text-sm text-gray-500">Click a category to see resolution guidance</p>
          </div>
          <div className="divide-y">
            {summary.categories.map((cat: FailedItemCategory) => {
              const isExpanded = expandedCategory === cat.category;
              return (
                <div key={cat.category}>
                  <div
                    className="flex items-center gap-4 px-5 py-3.5 cursor-pointer hover:bg-gray-50 transition-colors"
                    onClick={() => setExpandedCategory(isExpanded ? null : cat.category)}
                  >
                    {isExpanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${CATEGORY_COLORS[cat.category] || CATEGORY_COLORS.unknown}`}>
                      {CATEGORY_ICONS[cat.category] || cat.category}
                    </span>
                    <div className="flex-1 flex items-center gap-6">
                      <span className="text-sm font-medium text-gray-900">{cat.count} total</span>
                      {cat.unresolved > 0 && (
                        <span className="text-xs font-medium text-orange-600 bg-orange-50 px-2 py-0.5 rounded-full">
                          {cat.unresolved} unresolved
                        </span>
                      )}
                      {cat.resolved > 0 && (
                        <span className="text-xs font-medium text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
                          {cat.resolved} resolved
                        </span>
                      )}
                      {cat.retriable > 0 && (
                        <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
                          {cat.retriable} retriable
                        </span>
                      )}
                    </div>
                  </div>
                  {isExpanded && (
                    <div className="px-14 pb-4">
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <div className="flex items-start gap-2">
                          <Info className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="text-sm font-medium text-blue-900 mb-1">How to Fix</p>
                            <p className="text-sm text-blue-800">{cat.resolution_hint}</p>
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

      {/* Failed items table — DataTable */}
      <DataTable<FailedItemEntry>
        queryKey="failed-items"
        endpoint="/failed-items"
        columns={columns}
        extraParams={showResolved ? {} : { is_resolved: 'false' }}
        searchable
        searchPlaceholder="Search by item name or error..."
        filters={filters}
        exportable
        exportEndpoint="/export/csv?source=failed_items"
        defaultSortBy="created_at"
        defaultSortOrder="desc"
        defaultPageSize={50}
        emptyMessage="No failed items found"
        rowKey="id"
        refetchInterval={10000}
        actions={(row) => (
          !row.is_resolved ? (
            <div className="flex items-center gap-2">
              {row.can_retry && (
                <button
                  onClick={() => retryMutation.mutate([row.id])}
                  disabled={retryMutation.isPending}
                  className="text-orange-600 hover:text-orange-800 text-xs font-medium flex items-center gap-1"
                  title="Retry this item"
                >
                  <RotateCcw className="w-3 h-3" />
                </button>
              )}
              <button
                onClick={() => resolveMutation.mutate([row.id])}
                disabled={resolveMutation.isPending}
                className="text-green-600 hover:text-green-800 text-xs font-medium flex items-center gap-1"
                title="Mark as resolved"
              >
                <CheckCircle2 className="w-3 h-3" />
              </button>
            </div>
          ) : null
        )}
      />
    </div>
  );
}
