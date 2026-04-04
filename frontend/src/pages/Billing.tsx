import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CreditCard, Check, Loader2, ExternalLink } from 'lucide-react';
import { api } from '../api/client';
import { useTenantId } from '../hooks/useTenant';
import Breadcrumb from '../components/design-system/Breadcrumb';

const TIERS = [
  { key: 'professional', name: 'Professional', price: '$1.50', period: '/user/mo', features: ['5 workloads', 'Shared + archive mailbox', 'Mail rules backup', '90-day retention'] },
  { key: 'business', name: 'Business', price: '$3.00', period: '/user/mo', features: ['PST export', 'Group membership restore', 'Snapshot diff', '1-year retention'], popular: true },
  { key: 'enterprise', name: 'Enterprise', price: '$5.00', period: '/user/mo', features: ['PIM backup', 'Agent Governance', 'WORM + eDiscovery', 'Dedicated support'] },
];

export default function Billing() {
  const tenantId = useTenantId();
  const [loading, setLoading] = useState<string | null>(null);

  const { data: config } = useQuery({
    queryKey: ['billing-config'],
    queryFn: () => api.get<any>('/billing/config'),
  });

  const { data: sub } = useQuery({
    queryKey: ['billing-subscription', tenantId],
    queryFn: () => api.get<any>(`/billing/subscription?tenant_id=${tenantId}`),
    enabled: !!tenantId,
  });

  const handleCheckout = async (priceId: string) => {
    if (!tenantId || !priceId) return;
    setLoading(priceId);
    try {
      const res = await api.post<any>('/billing/checkout', {
        tenant_id: tenantId,
        price_id: priceId,
        quantity: 1,
      });
      if (res.checkout_url) window.location.href = res.checkout_url;
    } catch (err) {
      console.error('Checkout failed:', err);
    } finally {
      setLoading(null);
    }
  };

  const handlePortal = async () => {
    if (!tenantId) return;
    setLoading('portal');
    try {
      const res = await api.post<any>('/billing/portal', { tenant_id: tenantId });
      if (res.portal_url) window.location.href = res.portal_url;
    } catch (err) {
      console.error('Portal failed:', err);
    } finally {
      setLoading(null);
    }
  };

  const currentTier = sub?.subscription_tier || 'community';
  const status = sub?.subscription_status || 'free';
  const isActive = ['active', 'trialing'].includes(status);

  return (
    <div>
      <Breadcrumb items={[{ label: 'Administration', path: '/settings' }, { label: 'Billing' }]} />

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-teal-500/10 rounded-xl flex items-center justify-center">
            <CreditCard className="w-5 h-5 text-teal-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Billing & Subscription</h1>
            <p className="text-xs text-muted-foreground">Manage your plan, payment method, and invoices</p>
          </div>
        </div>
        {sub?.stripe_customer_id && (
          <button onClick={handlePortal} disabled={loading === 'portal'}
            className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg text-sm font-medium hover:bg-muted transition-colors">
            {loading === 'portal' ? <Loader2 className="w-4 h-4 animate-spin" /> : <ExternalLink className="w-4 h-4" />}
            Manage Subscription
          </button>
        )}
      </div>

      {/* Current Plan */}
      <div className="bg-card border border-border rounded-xl p-5 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Current Plan</div>
            <div className="text-xl font-bold text-foreground mt-1 capitalize">{currentTier}</div>
            <div className="flex items-center gap-2 mt-1">
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                status === 'active' ? 'bg-green-500/10 text-green-400 border border-green-500/20' :
                status === 'trialing' ? 'bg-teal-500/10 text-teal-400 border border-teal-500/20' :
                status === 'past_due' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                'bg-muted text-muted-foreground border border-border'
              }`}>
                {status === 'trialing' ? 'Trial' : status === 'active' ? 'Active' : status === 'past_due' ? 'Past Due' : status === 'canceled' ? 'Canceled' : 'Free'}
              </span>
              {sub?.trial_ends_at && status === 'trialing' && (
                <span className="text-xs text-muted-foreground">
                  Trial ends {new Date(sub.trial_ends_at).toLocaleDateString()}
                </span>
              )}
              {sub?.current_period_end && isActive && (
                <span className="text-xs text-muted-foreground">
                  Next billing: {new Date(sub.current_period_end).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Pricing Tiers */}
      <h2 className="text-lg font-semibold text-foreground mb-4">
        {isActive ? 'Change Plan' : 'Choose a Plan'}
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {TIERS.map(tier => {
          const priceId = config?.prices?.[tier.key];
          const isCurrent = currentTier === tier.key;

          return (
            <div key={tier.key} className={`relative bg-card border rounded-xl p-5 ${
              tier.popular ? 'border-teal-500/50 ring-1 ring-teal-500/20' : 'border-border'
            }`}>
              {tier.popular && (
                <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-gradient-to-r from-teal-500 to-cyan-500 text-white text-[10px] font-bold rounded-full">
                  Most Popular
                </span>
              )}
              <div className="text-sm font-semibold text-muted-foreground">{tier.name}</div>
              <div className="flex items-baseline gap-1 mt-2">
                <span className="text-2xl font-extrabold text-foreground">{tier.price}</span>
                <span className="text-sm text-muted-foreground">{tier.period}</span>
              </div>
              <ul className="mt-4 space-y-2">
                {tier.features.map(f => (
                  <li key={f} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Check className="w-4 h-4 text-teal-500 shrink-0" /> {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => priceId && handleCheckout(priceId)}
                disabled={isCurrent || !priceId || loading === priceId}
                className={`w-full mt-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isCurrent ? 'bg-muted text-muted-foreground cursor-default' :
                  tier.popular ? 'bg-teal-600 text-white hover:bg-teal-700' :
                  'bg-muted text-foreground hover:bg-accent'
                } disabled:opacity-50`}
              >
                {loading === priceId ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> :
                 isCurrent ? 'Current Plan' : 'Start 14-Day Trial'}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
