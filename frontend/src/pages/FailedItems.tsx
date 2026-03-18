import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle, CheckCircle2, RotateCcw, XCircle, Loader2,
  ChevronDown, ChevronRight, ShieldAlert, Info, Eye, EyeOff,
  Mail, HardDrive, Globe, File, Folder, List, ListOrdered, Library,
} from 'lucide-react';
import { api } from '../api/client';
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
  const [categoryFilter, setCategoryFilter] = useState('');
  const [showResolved, setShowResolved] = useState(false);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const [selectedItems, setSelectedItems] = useState<Set<number>>(new Set());
  const [page, setPage] = useState(1);
  const [actionMsg, setActionMsg] = useState('');
  const qc = useQueryClient();

  // Fetch summary
  const { data: summary } = useQuery({
    queryKey: ['failed-items-summary'],
    queryFn: () => api.get<FailedItemsSummary>('/failed-items/summary'),
    refetchInterval: 15000,
  });

  // Fetch items list
  const { data: itemsData, isLoading: loadingItems } = useQuery({
    queryKey: ['failed-items', categoryFilter, showResolved, page],
    queryFn: () => {
      const params = new URLSearchParams();
      if (categoryFilter) params.set('error_category', categoryFilter);
      if (!showResolved) params.set('is_resolved', 'false');
      params.set('page', String(page));
      params.set('page_size', '50');
      return api.get<{ total: number; page: number; page_size: number; items: FailedItemEntry[] }>(
        `/failed-items?${params.toString()}`
      );
    },
    refetchInterval: 10000,
  });

  // Mutations
  const resolveMutation = useMutation({
    mutationFn: (itemIds: number[]) => api.post('/failed-items/resolve', { item_ids: itemIds }),
    onSuccess: (data: any) => {
      setActionMsg(`Resolved ${data.resolved} items`);
      setSelectedItems(new Set());
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
      setSelectedItems(new Set());
      qc.invalidateQueries({ queryKey: ['failed-items'] });
      qc.invalidateQueries({ queryKey: ['failed-items-summary'] });
      setTimeout(() => setActionMsg(''), 5000);
    },
    onError: (err: any) => { setActionMsg(`Error: ${err.message}`); setTimeout(() => setActionMsg(''), 5000); },
  });

  const toggleSelect = (id: number) => {
    const next = new Set(selectedItems);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelectedItems(next);
  };

  const selectAll = () => {
    if (!itemsData?.items) return;
    const unresolved = itemsData.items.filter(i => !i.is_resolved);
    if (selectedItems.size === unresolved.length) {
      setSelectedItems(new Set());
    } else {
      setSelectedItems(new Set(unresolved.map(i => i.id)));
    }
  };

  const totalPages = itemsData ? Math.ceil(itemsData.total / itemsData.page_size) : 0;

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
            <p className="text-sm text-gray-500">Click a category to filter items and see resolution guidance</p>
          </div>
          <div className="divide-y">
            {summary.categories.map((cat: FailedItemCategory) => {
              const isExpanded = expandedCategory === cat.category;
              const isFiltered = categoryFilter === cat.category;
              return (
                <div key={cat.category}>
                  <div
                    className={`flex items-center gap-4 px-5 py-3.5 cursor-pointer hover:bg-gray-50 transition-colors ${isFiltered ? 'bg-blue-50' : ''}`}
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
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setCategoryFilter(isFiltered ? '' : cat.category);
                        setPage(1);
                      }}
                      className={`text-xs font-medium px-3 py-1.5 rounded-lg transition-colors ${
                        isFiltered ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {isFiltered ? 'Clear Filter' : 'Filter'}
                    </button>
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

      {/* Bulk actions */}
      {selectedItems.size > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4 flex items-center gap-4">
          <span className="text-sm font-medium text-blue-800">{selectedItems.size} items selected</span>
          <div className="flex gap-2">
            <button
              onClick={() => resolveMutation.mutate(Array.from(selectedItems))}
              disabled={resolveMutation.isPending}
              className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-700 flex items-center gap-1.5 disabled:opacity-50"
            >
              {resolveMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
              Resolve
            </button>
            <button
              onClick={() => retryMutation.mutate(Array.from(selectedItems))}
              disabled={retryMutation.isPending}
              className="px-3 py-1.5 bg-orange-600 text-white rounded-lg text-xs font-medium hover:bg-orange-700 flex items-center gap-1.5 disabled:opacity-50"
            >
              {retryMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <RotateCcw className="w-3 h-3" />}
              Retry Selected
            </button>
            <button
              onClick={() => setSelectedItems(new Set())}
              className="px-3 py-1.5 bg-white border border-gray-300 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Items table */}
      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left w-8">
                <input
                  type="checkbox"
                  checked={itemsData?.items && itemsData.items.filter(i => !i.is_resolved).length > 0 && selectedItems.size === itemsData.items.filter(i => !i.is_resolved).length}
                  onChange={selectAll}
                  className="rounded border-gray-300"
                />
              </th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Item</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Type</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Path</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Error</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Category</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Retries</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {itemsData?.items?.map((item: FailedItemEntry) => (
              <tr key={item.id} className={`hover:bg-gray-50 ${item.is_resolved ? 'opacity-60' : ''}`}>
                <td className="px-4 py-3">
                  {!item.is_resolved && (
                    <input
                      type="checkbox"
                      checked={selectedItems.has(item.id)}
                      onChange={() => toggleSelect(item.id)}
                      className="rounded border-gray-300"
                    />
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <ItemTypeIcon type={item.item_type} />
                    <span className="font-medium text-gray-900 max-w-[200px] truncate" title={item.item_name || undefined}>
                      {item.item_name || 'Unknown'}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 capitalize text-gray-600 text-xs">
                  {(item.item_type || 'unknown').replace(/_/g, ' ')}
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs max-w-[150px] truncate" title={item.item_path || undefined}>
                  {item.item_path || '—'}
                </td>
                <td className="px-4 py-3">
                  <div className="max-w-[250px]">
                    <p className="text-xs text-red-600 truncate" title={item.error_message}>
                      {item.error_message}
                    </p>
                    {item.error_code && (
                      <p className="text-xs text-gray-400 mt-0.5">{item.error_code}</p>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${CATEGORY_COLORS[item.error_category] || CATEGORY_COLORS.unknown}`}>
                    {CATEGORY_ICONS[item.error_category] || item.error_category}
                  </span>
                </td>
                <td className="px-4 py-3 text-center text-xs text-gray-500">
                  {item.retries_attempted}
                </td>
                <td className="px-4 py-3">
                  {item.is_resolved ? (
                    <span className="inline-flex items-center gap-1 text-xs text-green-600 font-medium">
                      <CheckCircle2 className="w-3 h-3" /> Resolved
                    </span>
                  ) : item.can_retry ? (
                    <span className="inline-flex items-center gap-1 text-xs text-orange-600 font-medium">
                      <RotateCcw className="w-3 h-3" /> Retriable
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs text-gray-500 font-medium">
                      <XCircle className="w-3 h-3" /> Permanent
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {!item.is_resolved && (
                    <div className="flex items-center gap-2">
                      {item.can_retry && (
                        <button
                          onClick={() => retryMutation.mutate([item.id])}
                          disabled={retryMutation.isPending}
                          className="text-orange-600 hover:text-orange-800 text-xs font-medium flex items-center gap-1"
                          title="Retry this item"
                        >
                          <RotateCcw className="w-3 h-3" />
                        </button>
                      )}
                      <button
                        onClick={() => resolveMutation.mutate([item.id])}
                        disabled={resolveMutation.isPending}
                        className="text-green-600 hover:text-green-800 text-xs font-medium flex items-center gap-1"
                        title="Mark as resolved"
                      >
                        <CheckCircle2 className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {loadingItems && (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400"><Loader2 className="w-5 h-5 animate-spin inline mr-2" />Loading...</td></tr>
            )}
            {!loadingItems && (!itemsData?.items || itemsData.items.length === 0) && (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">
                {categoryFilter ? 'No failed items in this category' : 'No failed items found'}
              </td></tr>
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
            <p className="text-sm text-gray-500">
              Showing {((page - 1) * 50) + 1}–{Math.min(page * 50, itemsData?.total || 0)} of {itemsData?.total || 0}
            </p>
            <div className="flex gap-1">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 rounded-lg text-sm border bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                Prev
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1.5 rounded-lg text-sm border bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
