/**
 * eDiscovery — Enterprise tier legal search & hold.
 *
 * Tier-gated: if not Enterprise, shows locked card with upgrade CTA.
 * When available: cross-workload content search + legal hold creation.
 *
 * APIs:
 * - GET /api/ediscovery/status → availability check
 * - POST /api/ediscovery/search → content search across snapshots
 * - POST /api/ediscovery/hold → create legal hold on custodian data
 */
import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Search, Loader2, Lock, ArrowRight, ChevronDown,
  Scale, Shield, FileText, Calendar, User, Filter,
} from 'lucide-react';
import { api } from '../api/client';
import { useTenantSwitcher } from '../hooks/useTenant';
import { useToast } from '../components/Toast';
import { WORKLOADS, WORKLOAD_MAP } from '../config/workloads';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';

// ── Types ────────────────────────────────────────────

interface EDiscoveryStatus {
  available: boolean;
  tier_required: string;
  features: string[];
}

interface SearchResultItem {
  item_id: number;
  snapshot_id: number;
  object_name: string;
  object_email?: string;
  workload: string;
  item_type: string;
  name: string;
  subject?: string;
  sender?: string;
  path?: string;
  received_at?: string;
  size_bytes: number;
}

interface SearchResponse {
  query: string;
  total_results: number;
  items: SearchResultItem[];
}

interface LegalHoldResponse {
  name: string;
  status: string;
  policies_held: number;
  custodians: string[];
  created_by: string;
}

// ── Helpers ──────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function formatDate(iso: string | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

const INITIAL_SHOW = 5;

// ── Component ────────────────────────────────────────

export default function EDiscovery() {
  const { selectedTenant } = useTenantSwitcher();
  const tenantId = selectedTenant?.id;
  const toast = useToast();

  // Search state
  const [searchInput, setSearchInput] = useState('');
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const [workloadFilters, setWorkloadFilters] = useState<string[]>([]);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [custodians, setCustodians] = useState('');
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});

  // Legal hold dialog
  const [holdOpen, setHoldOpen] = useState(false);
  const [holdName, setHoldName] = useState('');
  const [holdDescription, setHoldDescription] = useState('');
  const [holdCustodians, setHoldCustodians] = useState('');
  const [holdWorkloads, setHoldWorkloads] = useState<string[]>([]);
  const [holdKeywords, setHoldKeywords] = useState('');

  // Tier gate check
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['ediscovery-status'],
    queryFn: () => api.get<EDiscoveryStatus>('/ediscovery/status'),
  });

  // Search mutation (POST — user-triggered action)
  const searchMutation = useMutation({
    mutationFn: () =>
      api.post<SearchResponse>('/ediscovery/search', {
        query: searchInput,
        tenant_id: tenantId,
        workloads: workloadFilters.length > 0 ? workloadFilters : undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        custodians: custodians || undefined,
        max_results: 200,
      }),
    onError: (err: any) => toast.error('Search failed', err.message),
  });

  // Legal hold mutation
  const holdMutation = useMutation({
    mutationFn: () =>
      api.post<LegalHoldResponse>('/ediscovery/hold', {
        tenant_id: tenantId,
        name: holdName,
        description: holdDescription || undefined,
        custodians: holdCustodians
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        workloads: holdWorkloads.length > 0 ? holdWorkloads : undefined,
        keywords: holdKeywords || undefined,
      }),
    onSuccess: (data: any) => {
      toast.success('Legal hold created', `${data.name}: ${data.policies_held} policies held`);
      setHoldOpen(false);
      resetHoldForm();
    },
    onError: (err: any) => toast.error('Failed to create hold', err.message),
  });

  // ── Handlers ────────────────────────────────────────

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) searchMutation.mutate();
  };

  const resetHoldForm = () => {
    setHoldName('');
    setHoldDescription('');
    setHoldCustodians('');
    setHoldWorkloads([]);
    setHoldKeywords('');
  };

  const toggleWorkloadFilter = (key: string) => {
    setWorkloadFilters((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const toggleHoldWorkload = (key: string) => {
    setHoldWorkloads((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  // Group results by workload
  const results = searchMutation.data;
  const groupedResults: Record<string, SearchResultItem[]> = {};
  results?.items?.forEach((item) => {
    if (!groupedResults[item.workload]) groupedResults[item.workload] = [];
    groupedResults[item.workload].push(item);
  });

  // ── Loading state ───────────────────────────────────

  if (statusLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  // ── Tier gate — Enterprise required ─────────────────

  if (status && !status.available) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Scale className="w-7 h-7 text-blue-600" /> eDiscovery
          </h1>
          <p className="text-muted-foreground">Legal search and hold across all protected data</p>
        </div>
        <div className="bg-card border border-border rounded-xl p-8 text-center">
          <Lock className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h2 className="text-lg font-bold text-foreground mb-2">
            eDiscovery requires {status.tier_required || 'Enterprise'} tier
          </h2>
          <p className="text-muted-foreground text-sm mb-6 max-w-md mx-auto">
            Cross-workload legal search, custodian holds, compliance exports, and full audit trail for litigation support.
          </p>
          <div className="flex flex-wrap gap-2 justify-center mb-6">
            {['Legal Hold', 'Content Search', 'Export', 'Audit Trail'].map((f) => (
              <span key={f} className="px-2.5 py-1 bg-muted rounded-full text-xs text-muted-foreground">
                {f}
              </span>
            ))}
          </div>
          <a
            href="/billing"
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            View Plans <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </div>
    );
  }

  // ── Main eDiscovery UI ──────────────────────────────

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Scale className="w-7 h-7 text-blue-600" /> eDiscovery
          </h1>
          <p className="text-muted-foreground">Search across all backup snapshots and manage legal holds</p>
        </div>
      </div>

      {/* Search Panel */}
      <div className="bg-card border border-border rounded-xl p-6 mb-6">
        <form onSubmit={handleSearch}>
          {/* Search Input */}
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search across all backups... (emails, files, messages)"
              className="w-full pl-11 pr-4 py-3 border border-border rounded-xl bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-transparent text-sm"
            />
          </div>

          {/* Filters Toggle */}
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => setFiltersExpanded(!filtersExpanded)}
              className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <Filter className="w-3.5 h-3.5" />
              Filters
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${filtersExpanded ? 'rotate-180' : ''}`} />
            </button>
            <button
              type="submit"
              disabled={!searchInput.trim() || searchMutation.isPending}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 transition-colors"
            >
              {searchMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              Search
            </button>
          </div>

          {/* Expanded Filters */}
          {filtersExpanded && (
            <div className="mt-4 pt-4 border-t border-border space-y-4">
              {/* Workload pill toggles */}
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-2">Workloads</label>
                <div className="flex flex-wrap gap-2">
                  {WORKLOADS.map((wl) => {
                    const active = workloadFilters.includes(wl.key);
                    return (
                      <button
                        key={wl.key}
                        type="button"
                        onClick={() => toggleWorkloadFilter(wl.key)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                          active
                            ? `${wl.bgColor} ${wl.textColor} border ${wl.borderColor}`
                            : 'bg-muted text-muted-foreground border border-transparent hover:border-border'
                        }`}
                      >
                        <wl.icon className="w-3 h-3" />
                        {wl.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Date range + Custodians */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">From Date</label>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">To Date</label>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">Custodians</label>
                  <input
                    type="text"
                    value={custodians}
                    onChange={(e) => setCustodians(e.target.value)}
                    placeholder="user@company.com, ..."
                    className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm placeholder:text-muted-foreground"
                  />
                </div>
              </div>
            </div>
          )}
        </form>
      </div>

      {/* Results Count */}
      {results && (
        <div className="mb-4 text-sm text-muted-foreground">
          Found <strong className="text-foreground">{results.total_results}</strong> items
          {Object.keys(groupedResults).length > 0 && (
            <>
              {' '}across{' '}
              <strong className="text-foreground">{Object.keys(groupedResults).length}</strong> workloads
            </>
          )}
        </div>
      )}

      {/* Search Results — grouped by workload */}
      {results && Object.keys(groupedResults).length > 0 && (
        <div className="space-y-4 mb-6">
          {Object.entries(groupedResults).map(([workload, items]) => {
            const wl = WORKLOAD_MAP[workload];
            const Icon = wl?.icon || FileText;
            const showAll = expandedGroups[workload];
            const displayItems = showAll ? items : items.slice(0, INITIAL_SHOW);
            const remaining = items.length - INITIAL_SHOW;

            return (
              <div key={workload} className="bg-card border border-border rounded-xl overflow-hidden">
                {/* Group Header */}
                <div className={`flex items-center gap-3 px-5 py-3 border-b border-border ${wl?.bgColor || 'bg-muted'}`}>
                  <Icon className={`w-4.5 h-4.5 ${wl?.textColor || 'text-muted-foreground'}`} />
                  <span className="font-semibold text-foreground text-sm">{wl?.label || workload}</span>
                  <span className="text-xs text-muted-foreground">({items.length} items)</span>
                </div>

                {/* Items */}
                <div className="divide-y divide-border">
                  {displayItems.map((item) => (
                    <div key={item.item_id} className="px-5 py-3 flex items-center gap-3 hover:bg-accent/30 transition-colors">
                      <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">
                          {item.subject || item.name}
                        </p>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                          {item.sender && (
                            <span className="flex items-center gap-1">
                              <User className="w-3 h-3" /> {item.sender}
                            </span>
                          )}
                          {item.path && (
                            <span className="truncate max-w-[200px]">{item.path}</span>
                          )}
                          {item.received_at && (
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" /> {formatDate(item.received_at)}
                            </span>
                          )}
                        </div>
                      </div>
                      <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded shrink-0">
                        {formatBytes(item.size_bytes)}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Show More */}
                {remaining > 0 && !showAll && (
                  <button
                    onClick={() => setExpandedGroups((prev) => ({ ...prev, [workload]: true }))}
                    className="w-full px-5 py-2 text-sm text-blue-400 hover:text-blue-300 hover:bg-accent/30 transition-colors border-t border-border"
                  >
                    Show {remaining} more
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Empty Results */}
      {results && results.total_results === 0 && (
        <div className="bg-card border border-border rounded-xl p-8 text-center mb-6">
          <Search className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">
            No results found for "{results.query}". Try different keywords or adjust filters.
          </p>
        </div>
      )}

      {/* Legal Hold Section */}
      <div className="bg-card border border-border rounded-xl p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-foreground flex items-center gap-2">
              <Shield className="w-5 h-5 text-amber-400" /> Legal Hold
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Place custodian data under legal hold to prevent deletion during litigation
            </p>
          </div>
          <button
            onClick={() => setHoldOpen(true)}
            className="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 transition-colors flex items-center gap-2"
          >
            <Lock className="w-4 h-4" /> Create Legal Hold
          </button>
        </div>
      </div>

      {/* Legal Hold Dialog */}
      <Dialog open={holdOpen} onOpenChange={setHoldOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-amber-400" /> Create Legal Hold
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Hold Name <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={holdName}
                onChange={(e) => setHoldName(e.target.value)}
                placeholder="e.g., Case #2025-001"
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Description</label>
              <textarea
                value={holdDescription}
                onChange={(e) => setHoldDescription(e.target.value)}
                placeholder="Reason for the legal hold..."
                rows={2}
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm resize-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Custodian Emails <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={holdCustodians}
                onChange={(e) => setHoldCustodians(e.target.value)}
                placeholder="user@company.com, legal@company.com"
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm"
              />
              <p className="text-xs text-muted-foreground mt-1">Comma-separated email addresses</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Workloads</label>
              <div className="flex flex-wrap gap-2">
                {WORKLOADS.map((wl) => {
                  const active = holdWorkloads.includes(wl.key);
                  return (
                    <button
                      key={wl.key}
                      type="button"
                      onClick={() => toggleHoldWorkload(wl.key)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                        active
                          ? `${wl.bgColor} ${wl.textColor} border ${wl.borderColor}`
                          : 'bg-muted text-muted-foreground border border-transparent hover:border-border'
                      }`}
                    >
                      <wl.icon className="w-3 h-3" />
                      {wl.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Keywords (optional)</label>
              <input
                type="text"
                value={holdKeywords}
                onChange={(e) => setHoldKeywords(e.target.value)}
                placeholder="invoice, contract, confidential"
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm"
              />
            </div>
          </div>

          <DialogFooter>
            <button
              onClick={() => setHoldOpen(false)}
              className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => holdMutation.mutate()}
              disabled={!holdName.trim() || !holdCustodians.trim() || holdMutation.isPending}
              className="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 disabled:opacity-50 flex items-center gap-2 transition-colors"
            >
              {holdMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Lock className="w-4 h-4" />
              )}
              Create Hold
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
