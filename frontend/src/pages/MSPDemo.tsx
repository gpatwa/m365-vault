import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Shield, Building2, Users, Palette, Activity, ShieldAlert,
  FileText, DollarSign, LogOut, ArrowRight, ArrowLeft, CheckCircle,
  Loader2, Play, Sparkles,
} from 'lucide-react';
import { api } from '../api/client';

// ── Scene definitions ──
const SCENES = [
  { key: 'overview', label: 'MSP Console', icon: Building2, color: 'from-blue-500 to-blue-600' },
  { key: 'onboard', label: 'Onboard', icon: Users, color: 'from-green-500 to-green-600' },
  { key: 'branding', label: 'Brand', icon: Palette, color: 'from-purple-500 to-purple-600' },
  { key: 'monitor', label: 'Monitor', icon: Activity, color: 'from-cyan-500 to-cyan-600' },
  { key: 'incident', label: 'Incident', icon: ShieldAlert, color: 'from-red-500 to-red-600' },
  { key: 'compliance', label: 'Compliance', icon: FileText, color: 'from-amber-500 to-amber-600' },
  { key: 'billing', label: 'Billing', icon: DollarSign, color: 'from-emerald-500 to-emerald-600' },
  { key: 'complete', label: 'Complete', icon: CheckCircle, color: 'from-blue-500 to-indigo-600' },
];

// ── Animated counter hook ──
function useCountUp(target: number, active: boolean, duration = 1500) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!active || target <= 0) { setValue(target); return; }
    setValue(0);
    const start = Date.now();
    const tick = () => {
      const elapsed = Date.now() - start;
      if (elapsed >= duration) { setValue(target); return; }
      setValue(Math.round((elapsed / duration) * target));
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [target, active, duration]);
  return value;
}

export default function MSPDemo() {
  const navigate = useNavigate();
  const [scene, setScene] = useState(0);
  const [engaged, setEngaged] = useState<Record<number, boolean>>({});
  const [seeding, setSeeding] = useState(false);
  const [seeded, setSeeded] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<any>(null);
  const [offboarded, setOffboarded] = useState(false);
  const [complianceViews, setComplianceViews] = useState(0);

  const markEngaged = (s: number) => setEngaged(prev => ({ ...prev, [s]: true }));

  // Seed demo data on mount
  useEffect(() => {
    setSeeding(true);
    api.post('/msp/demo-seed')
      .then(() => setSeeded(true))
      .catch(() => setSeeded(true))
      .finally(() => setSeeding(false));
  }, []);

  // Fetch MSP overview
  const { data: overview, refetch: refetchOverview } = useQuery({
    queryKey: ['msp-demo-overview'],
    queryFn: () => api.get<any>('/msp/overview'),
    enabled: seeded,
    refetchInterval: false,
  });

  // Fetch billing
  const { data: billing } = useQuery({
    queryKey: ['msp-demo-billing'],
    queryFn: () => api.get<any>('/msp/billing'),
    enabled: seeded && scene >= 6,
  });

  // Bulk onboard mutation
  const onboardMutation = useMutation({
    mutationFn: () => api.post<any>('/msp/onboard-bulk', {
      tenants: [
        { name: 'Riverside Clinic', ms_tenant_id: 'demo-riverside', client_id: 'demo-cid-r', client_secret: 'demo-secret-r' },
        { name: 'Metro Law Partners', ms_tenant_id: 'demo-metro-law', client_id: 'demo-cid-m', client_secret: 'demo-secret-m' },
      ],
    }),
    onSuccess: () => { markEngaged(1); refetchOverview(); },
  });

  // Offboard mutation
  const offboardMutation = useMutation({
    mutationFn: (tenantId: number) => api.post<any>(`/msp/offboard/${tenantId}`),
    onSuccess: () => { setOffboarded(true); refetchOverview(); },
  });

  const canAdvance = engaged[scene] || scene === 0;
  const tenants = overview?.tenants || [];
  const summary = overview?.summary || {};

  // Auto-engage scenes with no interaction required
  useEffect(() => {
    if (scene === 0 && seeded && !engaged[0]) {
      const t = setTimeout(() => markEngaged(0), 2500);
      return () => clearTimeout(t);
    }
    if (scene === 6 && !engaged[6]) {
      const t = setTimeout(() => markEngaged(6), 3000);
      return () => clearTimeout(t);
    }
  }, [scene, seeded]);

  // ── Scene renderers ──

  const renderScene0 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white">Welcome to the MSP Console</h2>
        <p className="text-gray-400 mt-1">Your single pane of glass across every client tenant</p>
      </div>
      {seeding ? (
        <div className="text-center py-8"><Loader2 className="w-8 h-8 animate-spin text-blue-400 mx-auto" /><p className="text-gray-500 mt-2">Setting up demo tenants...</p></div>
      ) : (
        <>
          <div className="grid grid-cols-4 gap-4">
            <StatBox label="Client Tenants" value={useCountUp(summary.total_tenants || 0, scene === 0)} color="text-blue-400" />
            <StatBox label="Protected Users" value={useCountUp(summary.total_protected_users || 0, scene === 0)} color="text-green-400" />
            <StatBox label="Overall Health" value={useCountUp(summary.overall_health || 0, scene === 0)} color="text-emerald-400" suffix="/100" />
            <StatBox label="Active Alerts" value={summary.total_alerts || 0} color={summary.total_alerts > 0 ? 'text-amber-400' : 'text-green-400'} />
          </div>
          <div className="space-y-2">
            {tenants.slice(0, 5).map((t: any) => (
              <div key={t.id} className="flex items-center gap-4 bg-gray-800 rounded-xl p-3 border border-gray-700">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold border-2 ${
                  t.health_score >= 90 ? 'text-green-400 border-green-500/30 bg-green-500/10' :
                  t.health_score >= 70 ? 'text-amber-400 border-amber-500/30 bg-amber-500/10' :
                  'text-red-400 border-red-500/30 bg-red-500/10'
                }`}>{t.health_score}</div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-white">{t.name}</div>
                  <div className="text-xs text-gray-500">{t.protected_objects} objects | {t.workload_count} workloads</div>
                </div>
                <div className="text-xs text-gray-400">{t.protection_pct}% protected</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );

  const renderScene1 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white">Onboard New Clients in 60 Seconds</h2>
        <p className="text-gray-400 mt-1">CSV upload or manual entry. Credentials encrypted with AES-256-GCM.</p>
      </div>
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-gray-700 bg-gray-800/50">
            <th className="text-left px-4 py-2 text-gray-400">Tenant</th>
            <th className="text-left px-4 py-2 text-gray-400">Segment</th>
            <th className="text-center px-4 py-2 text-gray-400">Status</th>
          </tr></thead>
          <tbody className="divide-y divide-gray-700/50">
            <tr><td className="px-4 py-3 text-white">Riverside Clinic</td><td className="px-4 py-3 text-gray-400">Healthcare</td>
              <td className="px-4 py-3 text-center">{onboardMutation.isSuccess ? <CheckCircle className="w-4 h-4 text-green-400 mx-auto" /> : <span className="text-gray-500">Ready</span>}</td></tr>
            <tr><td className="px-4 py-3 text-white">Metro Law Partners</td><td className="px-4 py-3 text-gray-400">Legal</td>
              <td className="px-4 py-3 text-center">{onboardMutation.isSuccess ? <CheckCircle className="w-4 h-4 text-green-400 mx-auto" /> : <span className="text-gray-500">Ready</span>}</td></tr>
          </tbody>
        </table>
      </div>
      {!onboardMutation.isSuccess ? (
        <button onClick={() => onboardMutation.mutate()} disabled={onboardMutation.isPending}
          className="w-full py-3 bg-green-600 text-white rounded-xl font-semibold hover:bg-green-500 disabled:opacity-50 flex items-center justify-center gap-2">
          {onboardMutation.isPending ? <><Loader2 className="w-4 h-4 animate-spin" /> Onboarding...</> : <><Play className="w-4 h-4" /> Onboard 2 Clients Now</>}
        </button>
      ) : (
        <div className="text-center text-green-400 font-medium py-2">2 clients onboarded successfully. Credentials encrypted. Keys isolated.</div>
      )}
    </div>
  );

  const renderScene2 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white">Your Brand, Your Platform</h2>
        <p className="text-gray-400 mt-1">Clients see YOUR company — not ours. Custom logo, colors, and name.</p>
      </div>
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 space-y-4">
          <div className="text-sm font-medium text-gray-300">Preview: Your Sidebar</div>
          <div className="bg-slate-900 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-7 h-7 rounded bg-blue-500 flex items-center justify-center"><Shield className="w-4 h-4 text-white" /></div>
              <div><div className="text-sm font-bold text-white">Acme Cyber Solutions</div><div className="text-[9px] text-gray-500">Managed Security</div></div>
            </div>
            {['Dashboard', 'Exchange', 'OneDrive', 'Recovery'].map(item => (
              <div key={item} className="flex items-center gap-2 px-3 py-1.5 text-xs text-gray-400">{item}</div>
            ))}
          </div>
        </div>
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 space-y-4">
          <div className="text-sm font-medium text-gray-300">What You Can Customize</div>
          {[
            { label: 'Company Name', example: 'Acme Cyber Solutions' },
            { label: 'Logo', example: 'Upload your logo (SVG/PNG)' },
            { label: 'Primary Color', example: '#3b82f6 (or any hex)' },
            { label: 'Tagline', example: 'Managed Security Services' },
          ].map(item => (
            <div key={item.label} className="flex items-center justify-between text-xs">
              <span className="text-gray-400">{item.label}</span>
              <span className="text-gray-300 font-mono text-[10px]">{item.example}</span>
            </div>
          ))}
          <button onClick={() => markEngaged(2)} className="w-full py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-500">
            {engaged[2] ? 'Branding Applied' : 'Apply Demo Branding'}
          </button>
        </div>
      </div>
    </div>
  );

  const renderScene3 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white">Monitor Every Client from One Console</h2>
        <p className="text-gray-400 mt-1">Click a tenant to drill down into their protection details</p>
      </div>
      <div className="space-y-2">
        {tenants.filter((t: any) => t.status === 'active').slice(0, 5).map((t: any) => (
          <button key={t.id} onClick={() => { setSelectedTenant(t); markEngaged(3); }}
            className={`w-full flex items-center gap-4 bg-gray-800 rounded-xl p-4 border transition-all text-left ${
              selectedTenant?.id === t.id ? 'border-blue-500 ring-1 ring-blue-500/30' : 'border-gray-700 hover:border-gray-600'
            }`}>
            <div className={`w-12 h-12 rounded-full flex items-center justify-center text-sm font-bold border-2 ${
              t.health_score >= 90 ? 'text-green-400 border-green-500/30 bg-green-500/10' : 'text-amber-400 border-amber-500/30 bg-amber-500/10'
            }`}>{t.health_score}</div>
            <div className="flex-1">
              <div className="font-medium text-white">{t.name}</div>
              <div className="text-xs text-gray-500">{t.protected_objects}/{t.total_objects} objects | {t.workload_count} workloads | Last backup: {t.last_backup ? 'Recent' : 'Pending'}</div>
            </div>
            <div className="text-right">
              <div className="text-lg font-bold text-white">{t.protection_pct}%</div>
              <div className="text-[10px] text-gray-500">Protected</div>
            </div>
          </button>
        ))}
      </div>
      {selectedTenant && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 text-center text-sm text-blue-300">
          Selected: <strong>{selectedTenant.name}</strong> — {selectedTenant.protected_objects} objects across {selectedTenant.workload_count} workloads including Entra ID
        </div>
      )}
    </div>
  );

  const renderScene4 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white">When Ransomware Hits Your Client</h2>
        <p className="text-gray-400 mt-1">Shieldio detects the attack, builds a recovery plan, and restores critical users first</p>
      </div>
      <div className="space-y-3">
        {[
          { phase: 1, title: 'Detect', desc: 'AI anomaly detection flags 1,847 files renamed to .encrypted', color: 'border-red-500/40 bg-red-500/5', icon: '🚨' },
          { phase: 2, title: 'Isolate', desc: 'Circuit breaker pauses backups. Clean restore point identified (2h ago)', color: 'border-amber-500/40 bg-amber-500/5', icon: '🔒' },
          { phase: 3, title: 'Plan', desc: 'MVB recovery plan: Identity first → CEO/CFO → Critical staff → Everyone', color: 'border-blue-500/40 bg-blue-500/5', icon: '📋' },
          { phase: 4, title: 'Recover', desc: 'One-click mass recovery. 125 users restored in priority order. Zero data loss.', color: 'border-green-500/40 bg-green-500/5', icon: '✅' },
        ].map((p, i) => (
          <div key={p.phase} className={`border rounded-xl p-4 ${p.color} transition-all duration-500`}
            style={{ opacity: 1, transitionDelay: `${i * 200}ms` }}>
            <div className="flex items-center gap-3">
              <span className="text-2xl">{p.icon}</span>
              <div>
                <div className="text-sm font-semibold text-white">Phase {p.phase}: {p.title}</div>
                <div className="text-xs text-gray-400 mt-0.5">{p.desc}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
      <button onClick={() => markEngaged(4)} className="w-full py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-500 flex items-center justify-center gap-2">
        {engaged[4] ? <><CheckCircle className="w-4 h-4" /> Recovery Complete</> : <><Play className="w-4 h-4" /> Simulate Recovery</>}
      </button>
      {engaged[4] && <div className="text-center text-green-400 text-sm font-medium">All 125 users restored. Identity controls verified. Client back online.</div>}
    </div>
  );

  const renderScene5 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white">Audit-Ready in One Click</h2>
        <p className="text-gray-400 mt-1">Generate compliance evidence for every client, for every framework</p>
      </div>
      <div className="grid grid-cols-2 gap-4">
        {[
          { type: 'HIPAA', safeguards: 6, desc: 'Healthcare — technical safeguards 164.312' },
          { type: 'SOC 2', safeguards: 6, desc: 'Trust Services Criteria CC6-CC8, A1' },
          { type: 'GDPR', safeguards: 6, desc: 'EU Data Protection Art. 5-33' },
          { type: 'DORA', safeguards: 6, desc: 'Financial Services Art. 6-13' },
        ].map(f => (
          <button key={f.type} onClick={() => { setComplianceViews(prev => prev + 1); if (complianceViews >= 1) markEngaged(5); }}
            className="bg-gray-800 rounded-xl p-4 border border-gray-700 hover:border-blue-500 transition-all text-left">
            <div className="text-lg font-bold text-white">{f.type}</div>
            <div className="text-xs text-gray-500 mt-1">{f.desc}</div>
            <div className="flex items-center gap-1 mt-3 text-xs text-green-400">
              <CheckCircle className="w-3 h-3" /> {f.safeguards} controls mapped
            </div>
          </button>
        ))}
      </div>
      <div className="bg-gray-800/50 rounded-xl p-4 text-center">
        <p className="text-xs text-gray-400">Each report includes: backup coverage, encryption status, audit trail summary, SLA compliance, retention policies</p>
        <p className="text-xs text-gray-500 mt-1">Export as PDF for your client's auditor. No consultant needed.</p>
      </div>
    </div>
  );

  const renderScene6 = () => {
    const totalUsers = billing?.total_users || 125;
    const unitPrice = billing?.unit_price || 1.50;
    const totalCost = billing?.total_cost || totalUsers * unitPrice;
    const sellAt = 6.00;
    const revenue = totalUsers * sellAt;
    const margin = revenue - totalCost;
    const marginPct = Math.round((margin / revenue) * 100);

    return (
      <div className="space-y-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white">Your Margin, Your Business</h2>
          <p className="text-gray-400 mt-1">Wholesale pricing that makes your managed services profitable</p>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 text-center">
            <div className="text-sm text-gray-500">You Pay</div>
            <div className="text-3xl font-bold text-white mt-1">${unitPrice.toFixed(2)}</div>
            <div className="text-xs text-gray-500">per user/mo</div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 text-center">
            <div className="text-sm text-gray-500">You Sell At</div>
            <div className="text-3xl font-bold text-blue-400 mt-1">${sellAt.toFixed(2)}</div>
            <div className="text-xs text-gray-500">per user/mo</div>
          </div>
          <div className="bg-green-500/10 rounded-xl p-4 border border-green-500/30 text-center">
            <div className="text-sm text-green-300">Your Margin</div>
            <div className="text-3xl font-bold text-green-400 mt-1">{marginPct}%</div>
            <div className="text-xs text-green-300">${margin.toFixed(0)}/mo profit</div>
          </div>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="text-xs text-gray-400 mb-2">With 15 clients averaging 100 users each:</div>
          <div className="text-lg text-white font-bold">$2,250/mo cost → $9,000/mo revenue → <span className="text-green-400">$6,750/mo profit</span></div>
        </div>
      </div>
    );
  };

  const renderScene7 = () => {
    const lastTenant = tenants.find((t: any) => t.name === 'Pacific Finance') || tenants[tenants.length - 1];
    return (
      <div className="space-y-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white">The Complete MSP Lifecycle</h2>
          <p className="text-gray-400 mt-1">Onboard, protect, monitor, recover, report, bill, offboard — one console</p>
        </div>
        {!offboarded && lastTenant ? (
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 text-center space-y-4">
            <LogOut className="w-10 h-10 text-amber-400 mx-auto" />
            <div>
              <div className="text-white font-semibold">Offboard: {lastTenant.name}</div>
              <div className="text-xs text-gray-500 mt-1">Tenant will be deactivated. Backups retained per SLA retention policy.</div>
            </div>
            <button onClick={() => offboardMutation.mutate(lastTenant.id)} disabled={offboardMutation.isPending}
              className="px-6 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-500 disabled:opacity-50">
              {offboardMutation.isPending ? 'Offboarding...' : 'Confirm Offboard'}
            </button>
          </div>
        ) : (
          <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-center text-green-300 text-sm">
            Client offboarded. Backups retained per SLA policy. Data is safe.
          </div>
        )}
        <div className="bg-gradient-to-br from-blue-600/20 to-indigo-600/20 border border-blue-500/30 rounded-xl p-6 text-center space-y-4">
          <Sparkles className="w-10 h-10 text-blue-400 mx-auto" />
          <h3 className="text-xl font-bold text-white">You Just Completed the Full MSP Lifecycle</h3>
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Clients Managed', value: String(summary.total_tenants || 5) },
              { label: 'Users Protected', value: String(summary.total_protected_users || 125) + '+' },
              { label: 'Compliance Frameworks', value: '4' },
              { label: 'Monthly Revenue', value: '$' + ((summary.total_protected_users || 125) * 6).toFixed(0) },
            ].map(s => (
              <div key={s.label} className="text-center">
                <div className="text-xl font-bold text-white">{s.value}</div>
                <div className="text-[10px] text-gray-400">{s.label}</div>
              </div>
            ))}
          </div>
          <button onClick={() => navigate('/login')}
            className="px-8 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-500 text-lg inline-flex items-center gap-2">
            Start Your MSP Pilot — 3 Months Free <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    );
  };

  const sceneRenderers = [renderScene0, renderScene1, renderScene2, renderScene3, renderScene4, renderScene5, renderScene6, renderScene7];

  return (
    <div className="max-w-3xl mx-auto py-4">
      {/* Progress bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          {SCENES.map((s, i) => (
            <div key={s.key} className="flex items-center gap-1">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                i < scene ? 'bg-green-500 text-white' :
                i === scene ? `bg-gradient-to-br ${s.color} text-white ring-2 ring-offset-2 ring-offset-gray-900 ring-blue-500/50` :
                'bg-gray-800 text-gray-500 border border-gray-700'
              }`}>
                {i < scene ? <CheckCircle className="w-4 h-4" /> : <s.icon className="w-3.5 h-3.5" />}
              </div>
              {i < SCENES.length - 1 && <div className={`w-4 sm:w-8 h-0.5 ${i < scene ? 'bg-green-500' : 'bg-gray-700'}`} />}
            </div>
          ))}
        </div>
        <div className="text-center">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider">Scene {scene + 1} of {SCENES.length}: </span>
          <span className="text-xs text-gray-300 font-medium">{SCENES[scene].label}</span>
        </div>
      </div>

      {/* Scene content */}
      <div className="min-h-[400px]">
        {sceneRenderers[scene]()}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between mt-8 pt-4 border-t border-gray-700">
        <button onClick={() => setScene(Math.max(0, scene - 1))} disabled={scene === 0}
          className="flex items-center gap-2 px-4 py-2 text-gray-400 hover:text-white disabled:opacity-30 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <div className="text-xs text-gray-600">{scene + 1} / {SCENES.length}</div>
        {scene < SCENES.length - 1 ? (
          <button onClick={() => setScene(scene + 1)} disabled={!canAdvance}
            className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-30 transition-all">
            Next <ArrowRight className="w-4 h-4" />
          </button>
        ) : (
          <div />
        )}
      </div>
    </div>
  );
}

function StatBox({ label, value, color, suffix = '' }: { label: string; value: number; color: string; suffix?: string }) {
  return (
    <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 text-center">
      <div className={`text-2xl font-bold ${color}`}>{value}{suffix}</div>
      <div className="text-[10px] text-gray-500 mt-1">{label}</div>
    </div>
  );
}
