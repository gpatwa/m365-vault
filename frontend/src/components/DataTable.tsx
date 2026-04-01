/**
 * DataTable — Shared server-side paginated, sortable, filterable table.
 *
 * Designed for scale: handles 1 to 500K+ rows via server-side operations.
 * All filtering, sorting, and pagination happens on the backend.
 *
 * Features:
 * - Server-side pagination (page/page_size)
 * - Server-side sorting (sort_by/sort_order)
 * - Server-side search (debounced 300ms)
 * - URL-synced state (filters persist in browser URL)
 * - CSV export button
 * - Loading skeletons
 * - Empty state
 * - Responsive
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight,
  Search, Download, RefreshCw, Filter, X,
} from 'lucide-react';
import { api } from '../api/client';

// ── Types ──

export interface Column<T = any> {
  key: string;
  label: string;
  sortable?: boolean;
  width?: string;           // e.g., 'w-48', 'min-w-[200px]'
  render?: (row: T) => React.ReactNode;
  className?: string;       // Additional cell classes
}

export interface FilterOption {
  key: string;
  label: string;
  options: { value: string; label: string }[];
}

interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

interface DataTableProps<T> {
  // Data
  queryKey: string;           // React Query key prefix
  endpoint: string;           // API endpoint (e.g., '/exchange/mailboxes')
  columns: Column<T>[];       // Column definitions
  extraParams?: Record<string, string | number>; // Extra query params (e.g., tenant_id)

  // Features
  searchable?: boolean;       // Enable search bar
  searchPlaceholder?: string;
  filters?: FilterOption[];   // Dropdown filters
  exportable?: boolean;       // Show CSV export button
  exportEndpoint?: string;    // Custom export endpoint

  // Display
  title?: string;
  subtitle?: string;
  emptyMessage?: string;
  defaultPageSize?: number;
  defaultSortBy?: string;
  defaultSortOrder?: 'asc' | 'desc';
  rowKey?: string | ((row: T) => string); // Unique key for each row

  // Actions
  onRowClick?: (row: T) => void;
  actions?: (row: T) => React.ReactNode; // Row action buttons
  headerActions?: React.ReactNode;       // Buttons next to title

  // Query control
  enabled?: boolean;          // Disable fetching until ready (e.g., tenant_id resolved)

  // Refresh
  refetchInterval?: number;   // Auto-refresh interval in ms
}

// ── Debounce Hook ──

function useDebounce(value: string, delay: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debounced;
}

// ── Component ──

export default function DataTable<T extends Record<string, any>>({
  queryKey,
  endpoint,
  columns,
  extraParams = {},
  searchable = false,
  searchPlaceholder = 'Search...',
  filters = [],
  exportable = false,
  exportEndpoint,
  title,
  subtitle,
  emptyMessage = 'No data found',
  defaultPageSize = 25,
  defaultSortBy,
  defaultSortOrder = 'desc',
  rowKey = 'id',
  onRowClick,
  actions,
  headerActions,
  refetchInterval,
  enabled = true,
}: DataTableProps<T>) {
  const [searchParams, setSearchParams] = useSearchParams();

  // State from URL params (synced)
  const page = parseInt(searchParams.get('page') || '1');
  const pageSize = parseInt(searchParams.get('page_size') || String(defaultPageSize));
  const sortBy = searchParams.get('sort_by') || defaultSortBy || '';
  const sortOrder = (searchParams.get('sort_order') || defaultSortOrder) as 'asc' | 'desc';
  const searchQuery = searchParams.get('q') || '';

  // Local search input (debounced)
  const [searchInput, setSearchInput] = useState(searchQuery);
  const debouncedSearch = useDebounce(searchInput, 300);

  // Filter state
  const [activeFilters, setActiveFilters] = useState<Record<string, string>>(() => {
    const f: Record<string, string> = {};
    filters.forEach(filter => {
      const v = searchParams.get(filter.key);
      if (v) f[filter.key] = v;
    });
    return f;
  });

  // Sync debounced search to URL
  useEffect(() => {
    const params = new URLSearchParams(searchParams);
    if (debouncedSearch) params.set('q', debouncedSearch);
    else params.delete('q');
    params.set('page', '1'); // Reset to page 1 on search
    setSearchParams(params, { replace: true });
  }, [debouncedSearch]);

  // Build API query params
  const apiParams = useMemo(() => {
    const params: Record<string, string | number> = {
      ...extraParams,
      page,
      page_size: pageSize,
    };
    if (sortBy) {
      params.sort_by = sortBy;
      params.sort_order = sortOrder;
    }
    if (debouncedSearch) params.search = debouncedSearch;
    Object.entries(activeFilters).forEach(([k, v]) => {
      if (v) params[k] = v;
    });
    return params;
  }, [page, pageSize, sortBy, sortOrder, debouncedSearch, activeFilters, extraParams]);

  // Build query string
  const queryString = Object.entries(apiParams)
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join('&');

  // Fetch data
  const { data, isLoading, isRefetching, refetch } = useQuery({
    queryKey: [queryKey, queryString],
    queryFn: () => api.get<PaginatedResponse<T>>(`${endpoint}?${queryString}`),
    refetchInterval,
    enabled,
  });

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  // ── Handlers ──

  const updateParam = useCallback((key: string, value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) params.set(key, value);
    else params.delete(key);
    setSearchParams(params, { replace: true });
  }, [searchParams, setSearchParams]);

  const handleSort = (key: string) => {
    const params = new URLSearchParams(searchParams);
    if (sortBy === key) {
      params.set('sort_order', sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      params.set('sort_by', key);
      params.set('sort_order', 'desc');
    }
    params.set('page', '1');
    setSearchParams(params, { replace: true });
  };

  const handlePageChange = (newPage: number) => {
    updateParam('page', String(newPage));
  };

  const handleFilter = (key: string, value: string) => {
    const newFilters = { ...activeFilters, [key]: value };
    if (!value) delete newFilters[key];
    setActiveFilters(newFilters);
    const params = new URLSearchParams(searchParams);
    if (value) params.set(key, value);
    else params.delete(key);
    params.set('page', '1');
    setSearchParams(params, { replace: true });
  };

  const clearFilters = () => {
    setActiveFilters({});
    setSearchInput('');
    const params = new URLSearchParams();
    setSearchParams(params, { replace: true });
  };

  const handleExport = async () => {
    const ep = exportEndpoint || `${endpoint}/export`;
    // Build export URL relative to API
    const base = (window as any).__RUNTIME_CONFIG__?.API_BASE || import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';
    const separator = ep.includes('?') ? '&' : '?';
    window.open(`${base}${ep}${separator}${queryString}&format=csv`, '_blank');
  };

  const getRowKey = (row: T, index: number): string => {
    if (typeof rowKey === 'function') return rowKey(row);
    return String(row[rowKey] ?? index);
  };

  const hasActiveFilters = Object.values(activeFilters).some(v => v) || debouncedSearch;

  // ── Render ──

  return (
    <div className="space-y-4">
      {/* Header */}
      {(title || headerActions || exportable) && (
        <div className="flex items-center justify-between">
          <div>
            {title && <h2 className="text-lg font-semibold text-foreground">{title}</h2>}
            {subtitle && <p className="text-sm text-muted-foreground mt-0.5">{subtitle}</p>}
          </div>
          <div className="flex items-center gap-2">
            {headerActions}
            <button
              onClick={() => refetch()}
              disabled={isRefetching}
              className="p-2 text-muted-foreground hover:text-muted-foreground hover:bg-muted rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${isRefetching ? 'animate-spin' : ''}`} />
            </button>
            {exportable && (
              <button
                onClick={handleExport}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-muted-foreground bg-card border border-border rounded-lg hover:bg-muted/50 transition-colors"
              >
                <Download className="w-3.5 h-3.5" /> Export
              </button>
            )}
          </div>
        </div>
      )}

      {/* Search + Filters */}
      {(searchable || filters.length > 0) && (
        <div className="flex items-center gap-3 flex-wrap">
          {searchable && (
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                value={searchInput}
                onChange={e => setSearchInput(e.target.value)}
                placeholder={searchPlaceholder}
                className="w-full pl-9 pr-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-ring focus:border-ring"
              />
              {searchInput && (
                <button
                  onClick={() => setSearchInput('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-muted-foreground hover:text-muted-foreground"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          )}

          {filters.map(filter => (
            <select
              key={filter.key}
              value={activeFilters[filter.key] || ''}
              onChange={e => handleFilter(filter.key, e.target.value)}
              className="px-3 py-2 text-sm border border-border rounded-lg bg-card focus:ring-2 focus:ring-ring"
            >
              <option value="">{filter.label}</option>
              {filter.options.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          ))}

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 px-2 py-1.5 text-xs text-muted-foreground hover:text-foreground/80 hover:bg-muted rounded-md transition-colors"
            >
              <X className="w-3 h-3" /> Clear filters
            </button>
          )}

          {/* Result count */}
          {data && (
            <span className="text-xs text-muted-foreground ml-auto">
              {data.total.toLocaleString()} result{data.total !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}

      {/* Table */}
      <div className="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                {columns.map(col => (
                  <th
                    key={col.key}
                    className={`text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider ${col.width || ''} ${
                      col.sortable ? 'cursor-pointer select-none hover:text-foreground/80 hover:bg-muted transition-colors' : ''
                    } ${col.className || ''}`}
                    onClick={col.sortable ? () => handleSort(col.key) : undefined}
                  >
                    <div className="flex items-center gap-1">
                      {col.label}
                      {col.sortable && (
                        <span className="ml-0.5">
                          {sortBy === col.key ? (
                            sortOrder === 'asc' ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronsUpDown className="w-3.5 h-3.5 text-muted-foreground/50" />
                          )}
                        </span>
                      )}
                    </div>
                  </th>
                ))}
                {actions && <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase w-24">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {isLoading ? (
                // Loading skeleton
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={`skeleton-${i}`}>
                    {columns.map(col => (
                      <td key={col.key} className="px-4 py-3">
                        <div className="h-4 bg-muted rounded animate-pulse" style={{ width: `${60 + Math.random() * 40}%` }} />
                      </td>
                    ))}
                    {actions && <td className="px-4 py-3"><div className="h-4 bg-muted rounded animate-pulse w-12 ml-auto" /></td>}
                  </tr>
                ))
              ) : data?.items?.length ? (
                data.items.map((row, idx) => (
                  <tr
                    key={getRowKey(row, idx)}
                    className={`transition-colors ${
                      onRowClick ? 'cursor-pointer hover:bg-primary/5' : 'hover:bg-muted/50'
                    }`}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                  >
                    {columns.map(col => (
                      <td key={col.key} className={`px-4 py-3 text-sm text-foreground/80 ${col.className || ''}`}>
                        {col.render ? col.render(row) : (row[col.key] ?? '—')}
                      </td>
                    ))}
                    {actions && (
                      <td className="px-4 py-3 text-right" onClick={e => e.stopPropagation()}>
                        {actions(row)}
                      </td>
                    )}
                  </tr>
                ))
              ) : (
                // Empty state
                <tr>
                  <td colSpan={columns.length + (actions ? 1 : 0)} className="px-4 py-12 text-center">
                    <div className="text-muted-foreground">
                      <Filter className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm font-medium">{emptyMessage}</p>
                      {hasActiveFilters && (
                        <button onClick={clearFilters} className="mt-2 text-xs text-blue-500 hover:underline">
                          Clear filters and try again
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.total > pageSize && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border bg-muted/50">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>Rows per page:</span>
              <select
                value={pageSize}
                onChange={e => { updateParam('page_size', e.target.value); updateParam('page', '1'); }}
                className="px-1.5 py-1 border border-border rounded text-xs bg-card"
              >
                {[10, 25, 50, 100].map(n => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
              <span className="ml-2">
                {((page - 1) * pageSize + 1).toLocaleString()}-{Math.min(page * pageSize, data.total).toLocaleString()} of {data.total.toLocaleString()}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1}
                className="p-1.5 rounded-md hover:bg-accent disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              {/* Page numbers */}
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                let pageNum: number;
                if (totalPages <= 5) pageNum = i + 1;
                else if (page <= 3) pageNum = i + 1;
                else if (page >= totalPages - 2) pageNum = totalPages - 4 + i;
                else pageNum = page - 2 + i;
                return (
                  <button
                    key={pageNum}
                    onClick={() => handlePageChange(pageNum)}
                    className={`w-8 h-8 rounded-md text-xs font-medium transition-colors ${
                      page === pageNum
                        ? 'bg-blue-600 text-white'
                        : 'text-muted-foreground hover:bg-accent'
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= totalPages}
                className="p-1.5 rounded-md hover:bg-accent disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
