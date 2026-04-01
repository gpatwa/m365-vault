import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Check, X, Lock, Unlock } from 'lucide-react';
import { api } from '../api/client';

interface FeatureData {
  tier: string;
  categories: Record<string, Record<string, boolean>>;
  limits: Record<string, any>;
}

interface TierComparison {
  current_tier: string;
  comparison: Record<string, Record<string, boolean>>;
}

const CATEGORY_LABELS: Record<string, { label: string; icon: string; color: string }> = {
  workloads: { label: 'Workloads', icon: '📦', color: 'border-blue-500/30 bg-blue-500/5' },
  intelligence: { label: 'Intelligence', icon: '🧠', color: 'border-purple-500/30 bg-purple-500/5' },
  recovery: { label: 'Recovery', icon: '🔄', color: 'border-green-500/30 bg-green-500/5' },
  compliance: { label: 'Compliance', icon: '📋', color: 'border-amber-500/30 bg-amber-500/5' },
  operations: { label: 'Operations (MSP)', icon: '🏢', color: 'border-cyan-500/30 bg-cyan-500/5' },
  platform: { label: 'Platform', icon: '⚙️', color: 'border-gray-500/30 bg-gray-800/500/5' },
};

const TIER_LABELS: Record<string, { label: string; color: string }> = {
  community: { label: 'Community', color: 'text-gray-400' },
  professional: { label: 'Professional', color: 'text-blue-400' },
  business: { label: 'Business', color: 'text-purple-400' },
  enterprise: { label: 'Enterprise', color: 'text-amber-400' },
};

export default function FeatureFlags() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'current' | 'comparison'>('current');

  const { data: features } = useQuery({
    queryKey: ['feature-categories'],
    queryFn: () => api.get<FeatureData>('/features/categories'),
  });

  const { data: tiers } = useQuery({
    queryKey: ['feature-tiers'],
    queryFn: () => api.get<TierComparison>('/features/tiers'),
    enabled: tab === 'comparison',
  });

  const overrideMutation = useMutation({
    mutationFn: ({ feature, enabled }: { feature: string; enabled: boolean }) =>
      api.put('/features/override', { feature, enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['feature-categories'] }),
  });

  // removeMutation available via: api.del(`/features/override/${feature}`)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Feature Configuration</h1>
          <p className="text-sm text-gray-400">
            Tier: <span className={TIER_LABELS[features?.tier || 'community']?.color || 'text-gray-400'}>
              {TIER_LABELS[features?.tier || 'community']?.label || features?.tier}
            </span>
            {features?.limits && (
              <span className="text-gray-600 ml-2">
                | {features.limits.max_objects || '∞'} objects | {features.limits.max_tenants || '∞'} tenants | {features.limits.retention_days}d retention
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setTab('current')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium ${tab === 'current' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}`}>
            Current Tier
          </button>
          <button onClick={() => setTab('comparison')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium ${tab === 'comparison' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}`}>
            Tier Comparison
          </button>
        </div>
      </div>

      {tab === 'current' && features && (
        <div className="space-y-4">
          {Object.entries(features.categories || {}).map(([category, featureMap]) => {
            const meta = CATEGORY_LABELS[category] || { label: category, icon: '📦', color: 'border-gray-700' };
            return (
              <div key={category} className={`rounded-xl border p-4 ${meta.color}`}>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-lg">{meta.icon}</span>
                  <h3 className="text-sm font-semibold text-white">{meta.label}</h3>
                  <span className="text-[10px] text-gray-500 ml-auto">
                    {Object.values(featureMap).filter(Boolean).length}/{Object.keys(featureMap).length} enabled
                  </span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {Object.entries(featureMap).map(([feature, enabled]) => (
                    <div key={feature}
                      className={`flex items-center justify-between px-3 py-2 rounded-lg border text-xs ${
                        enabled ? 'border-green-500/20 bg-green-500/5' : 'border-gray-700 bg-gray-800/50'
                      }`}>
                      <div className="flex items-center gap-2">
                        {enabled ?
                          <Check className="w-3.5 h-3.5 text-green-400" /> :
                          <Lock className="w-3.5 h-3.5 text-gray-500" />
                        }
                        <span className={enabled ? 'text-white' : 'text-gray-500'}>{feature.replace(/_/g, ' ')}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        {!enabled && (
                          <button onClick={() => overrideMutation.mutate({ feature, enabled: true })}
                            className="p-1 text-gray-600 hover:text-green-400" title="Force enable">
                            <Unlock className="w-3 h-3" />
                          </button>
                        )}
                        {enabled && (
                          <button onClick={() => overrideMutation.mutate({ feature, enabled: false })}
                            className="p-1 text-gray-600 hover:text-red-400" title="Force disable">
                            <Lock className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {tab === 'comparison' && tiers && (
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-700 bg-gray-800/50">
                <th className="text-left px-4 py-3 text-gray-400 font-medium">Feature</th>
                {Object.keys(TIER_LABELS).map(tier => (
                  <th key={tier} className={`text-center px-3 py-3 font-medium ${
                    tier === tiers.current_tier ? 'text-blue-400' : 'text-gray-500'
                  }`}>
                    {TIER_LABELS[tier]?.label}
                    {tier === tiers.current_tier && <div className="text-[9px] text-blue-300">(current)</div>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/50">
              {Object.entries(tiers.comparison || {}).map(([feature, tierMap]) => (
                <tr key={feature} className="hover:bg-gray-700/30">
                  <td className="px-4 py-2 text-gray-300 capitalize">{feature.replace(/_/g, ' ')}</td>
                  {Object.keys(TIER_LABELS).map(tier => (
                    <td key={tier} className="text-center px-3 py-2">
                      {(tierMap as Record<string, boolean>)[tier] ?
                        <Check className="w-4 h-4 text-green-400 mx-auto" /> :
                        <X className="w-4 h-4 text-gray-600 mx-auto" />
                      }
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
