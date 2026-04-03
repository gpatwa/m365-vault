import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, DollarSign, Users, Calendar, TrendingUp } from 'lucide-react';
import { api } from '../api/client';

interface BillingLineItem {
  tenant_id: number;
  tenant_name: string;
  user_count: number;
  storage_gb: number;
  unit_price: number;
  monthly_cost: number;
  status: string;
}

interface BillingData {
  month: string;
  total_tenants: number;
  total_users: number;
  unit_price: number;
  total_cost: number;
  wholesale_tier: string;
  line_items: BillingLineItem[];
  tiers: { min_users: number; max_users: number | null; price: number }[];
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-muted/500/10 text-muted-foreground',
  invoiced: 'bg-blue-500/100/10 text-blue-400',
  paid: 'bg-green-500/100/10 text-green-400',
};

export default function BillingPortal() {
  const now = new Date();
  const [month, setMonth] = useState(now.toISOString().slice(0, 7));

  const { data, isLoading } = useQuery({
    queryKey: ['msp-billing', month],
    queryFn: () => api.get<BillingData>(`/msp/billing?month=${month}`),
  });

  const handleExport = () => {
    const token = api.getToken();
    const base = (window as any).__RUNTIME_CONFIG__?.API_BASE
      ? `${(window as any).__RUNTIME_CONFIG__.API_BASE}/api`
      : import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';
    window.open(`${base}/msp/billing/export?month=${month}&token=${token}`, '_blank');
  };

  // Generate month options (last 12 months)
  const monthOptions: string[] = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    monthOptions.push(d.toISOString().slice(0, 7));
  }

  if (isLoading) {
    return <div className="flex items-center justify-center min-h-[50vh] text-muted-foreground animate-pulse">Loading billing...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Billing Portal</h1>
          <p className="text-sm text-muted-foreground">Per-tenant usage and cost breakdown</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={month}
            onChange={e => setMonth(e.target.value)}
            className="px-3 py-2 bg-card border border-border rounded-lg text-sm text-foreground focus:outline-none focus:border-ring"
          >
            {monthOptions.map(m => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500/100 transition-colors"
          >
            <Download className="w-4 h-4" /> Export CSV
          </button>
        </div>
      </div>

      {/* Summary cards */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-card rounded-xl p-4 border border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-green-500/100/10 flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-foreground">${data.total_cost.toFixed(2)}</div>
                <div className="text-xs text-muted-foreground">Total Cost</div>
              </div>
            </div>
          </div>
          <div className="bg-card rounded-xl p-4 border border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/100/10 flex items-center justify-center">
                <Users className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-foreground">{data.total_users}</div>
                <div className="text-xs text-muted-foreground">Total Users</div>
              </div>
            </div>
          </div>
          <div className="bg-card rounded-xl p-4 border border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/100/10 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-foreground">${data.unit_price.toFixed(2)}</div>
                <div className="text-xs text-muted-foreground">Per User Price</div>
              </div>
            </div>
          </div>
          <div className="bg-card rounded-xl p-4 border border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/100/10 flex items-center justify-center">
                <Calendar className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-foreground">{data.total_tenants}</div>
                <div className="text-xs text-muted-foreground">Active Tenants</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Wholesale tier info */}
      {data?.tiers && (
        <div className="bg-card/50 rounded-xl p-4 border border-border mb-6">
          <div className="text-xs font-medium text-muted-foreground mb-2">Wholesale Pricing Tiers</div>
          <div className="flex items-center gap-4">
            {data.tiers.map((tier, i) => (
              <div
                key={i}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium ${
                  data.unit_price === tier.price
                    ? 'bg-blue-500/100/20 text-blue-300 ring-1 ring-blue-500/50'
                    : 'bg-secondary/50 text-muted-foreground'
                }`}
              >
                {tier.max_users ? `${tier.min_users}-${tier.max_users}` : `${tier.min_users}+`} users: ${tier.price.toFixed(2)}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Billing table */}
      <div className="bg-card rounded-xl border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-card/50">
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">Tenant</th>
              <th className="text-right px-4 py-3 font-medium text-muted-foreground">Users</th>
              <th className="text-right px-4 py-3 font-medium text-muted-foreground">Storage</th>
              <th className="text-right px-4 py-3 font-medium text-muted-foreground">Unit Price</th>
              <th className="text-right px-4 py-3 font-medium text-muted-foreground">Monthly Cost</th>
              <th className="text-center px-4 py-3 font-medium text-muted-foreground">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {data?.line_items.map(item => (
              <tr key={item.tenant_id} className="hover:bg-secondary/30">
                <td className="px-4 py-3 text-foreground font-medium">{item.tenant_name}</td>
                <td className="px-4 py-3 text-right text-muted-foreground">{item.user_count}</td>
                <td className="px-4 py-3 text-right text-muted-foreground">{item.storage_gb} GB</td>
                <td className="px-4 py-3 text-right text-muted-foreground">${item.unit_price.toFixed(2)}</td>
                <td className="px-4 py-3 text-right text-foreground font-semibold">${item.monthly_cost.toFixed(2)}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-medium uppercase ${STATUS_COLORS[item.status] || STATUS_COLORS.draft}`}>
                    {item.status}
                  </span>
                </td>
              </tr>
            ))}
            {(!data?.line_items || data.line_items.length === 0) && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No billing data for this month</td></tr>
            )}
          </tbody>
          {data && data.line_items.length > 0 && (
            <tfoot>
              <tr className="border-t border-border bg-card/80">
                <td className="px-4 py-3 text-foreground font-semibold">Total</td>
                <td className="px-4 py-3 text-right text-foreground font-semibold">{data.total_users}</td>
                <td className="px-4 py-3 text-right text-muted-foreground">—</td>
                <td className="px-4 py-3 text-right text-muted-foreground">—</td>
                <td className="px-4 py-3 text-right text-green-400 font-bold text-base">${data.total_cost.toFixed(2)}</td>
                <td className="px-4 py-3"></td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  );
}
