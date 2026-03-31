import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Shield, Globe, MessageSquare, CheckCircle, XCircle, Loader2, ArrowRight, LogOut, Lock, Shrink, Hash, Star } from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../contexts/AuthContext';

const PLATFORM_ICONS: Record<string, any> = {
  microsoft365: Shield,
  google: Globe,
  salesforce: Globe,
  slack: MessageSquare,
};

const PLATFORM_COLORS: Record<string, string> = {
  microsoft365: 'border-blue-500/30 bg-blue-500/10 hover:border-blue-400',
  google: 'border-green-500/30 bg-green-500/10 hover:border-green-400',
  salesforce: 'border-sky-500/30 bg-sky-500/10 hover:border-sky-400',
  slack: 'border-purple-500/30 bg-purple-500/10 hover:border-purple-400',
};

interface Platform {
  key: string;
  name: string;
  description: string;
  icon: string;
  available: boolean;
  auth_type: string;
}

export default function Onboard() {
  const { logout } = useAuth();
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);

  useEffect(() => {
    api.get<{ platforms: Platform[] }>('/onboard/platforms')
      .then(data => setPlatforms(data.platforms))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleConnect = async (platformKey: string) => {
    setConnecting(platformKey);
    try {
      const data: any = await api.get(`/onboard/connect/${platformKey}`);
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (err: any) {
      console.error('Connect failed:', err);
      setConnecting(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white px-4 py-6">
    <div className="max-w-3xl mx-auto">
      {/* Sign out link */}
      <div className="flex justify-end mb-4">
        <button onClick={() => { logout(); window.location.href = '/'; }}
          className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-600 transition-colors">
          <LogOut className="w-4 h-4" /> Sign Out
        </button>
      </div>
      <div className="text-center mb-10">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-2xl mb-4">
          <Shield className="w-8 h-8 text-blue-600" />
        </div>
        <h1 className="text-3xl font-bold text-white mb-2">Connect Your SaaS Platform</h1>
        <p className="text-gray-500 text-lg">
          Select a platform to protect. One-click OAuth — no credentials to copy.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {platforms.map(platform => {
          const Icon = PLATFORM_ICONS[platform.icon] || Shield;
          const colors = PLATFORM_COLORS[platform.key] || 'border-gray-500/30 bg-gray-500/10';
          const isConnecting = connecting === platform.key;

          return (
            <button
              key={platform.key}
              onClick={() => platform.available && handleConnect(platform.key)}
              disabled={!platform.available || !!connecting}
              className={`relative p-6 rounded-2xl border-2 transition-all text-left ${
                platform.available
                  ? `${colors} cursor-pointer shadow-sm hover:shadow-md`
                  : 'border-gray-700 bg-gray-800/50 cursor-not-allowed opacity-60'
              }`}
            >
              {!platform.available && (
                <span className="absolute top-3 right-3 px-2 py-0.5 bg-gray-700 text-gray-400 text-[10px] font-semibold rounded-full">
                  Coming Soon
                </span>
              )}

              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-gray-800 border border-gray-700 flex items-center justify-center shadow-sm">
                  {platform.key === 'microsoft365' ? (
                    <svg className="w-6 h-6" viewBox="0 0 21 21">
                      <path d="M0 0h10v10H0z" fill="#f25022"/>
                      <path d="M11 0h10v10H11z" fill="#7fba00"/>
                      <path d="M0 11h10v10H0z" fill="#00a4ef"/>
                      <path d="M11 11h10v10H11z" fill="#ffb900"/>
                    </svg>
                  ) : (
                    <Icon className="w-6 h-6 text-gray-600" />
                  )}
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-white text-lg">{platform.name}</h3>
                  <p className="text-sm text-gray-500 mt-0.5">{platform.description}</p>

                  {platform.available && (
                    <div className="mt-3 flex items-center gap-1.5 text-sm font-medium text-blue-600">
                      {isConnecting ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Redirecting to {platform.name}...
                        </>
                      ) : (
                        <>
                          Connect <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div className="mt-8 text-center">
        <p className="text-xs text-gray-400">
          Shieldio uses OAuth admin consent — your credentials are never stored.
          <br />
          Only read-only permissions are requested for backup.
        </p>
      </div>
    </div>
    </div>
  );
}


/** Interactive Recovery Experience — customer takes real actions with their data */
const fmtBytes = (b: number) => {
  if (!b) return '0 B';
  const u = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(b) / Math.log(1024));
  return `${(b / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${u[i]}`;
};

const fmtTimeAgo = (iso: string) => {
  if (!iso) return '';
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
};

const WORKLOAD_LABELS: Record<string, string> = {
  exchange: 'Mailboxes', onedrive: 'OneDrive', sharepoint: 'SharePoint',
  teams: 'Teams', entra_id: 'Entra ID',
};

const ENTRA_TYPE_LABELS: Record<string, { label: string; critical?: boolean }> = {
  user: { label: 'Users' }, group: { label: 'Groups' },
  directory_role: { label: 'Admin Roles', critical: true },
  conditional_access_policy: { label: 'Conditional Access Policies', critical: true },
  app_registration: { label: 'App Registrations', critical: true },
  service_principal: { label: 'Service Principals' },
  oauth2_permission_grant: { label: 'OAuth Permissions', critical: true },
};

const GapRow = ({ m365, shieldio }: { m365: string; shieldio: string }) => (
  <div className="bg-gray-800 border border-gray-700 rounded-xl p-3 space-y-1">
    <div className="flex items-center gap-2 text-sm"><span className="text-gray-400 w-16 flex-shrink-0">M365:</span> <span className="text-red-500 font-medium">{m365}</span></div>
    <div className="flex items-center gap-2 text-sm"><span className="text-gray-400 w-16 flex-shrink-0">Shieldio:</span> <span className="text-green-600 font-medium">{shieldio}</span></div>
  </div>
);

const Shimmer = () => (
  <div className="space-y-3 animate-pulse">
    <div className="h-20 bg-gray-700 rounded-xl" />
    <div className="h-4 bg-gray-700 rounded w-3/4 mx-auto" />
    <div className="h-16 bg-gray-700 rounded-xl" />
  </div>
);

/** Animated counter: counts from 0 to target over duration */
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

function CyberRecoverySimulation({ tenantName, tenantId, disc, onComplete, simScene, setSimScene, activeWorkloads }: {
  tenantName: string;
  tenantId: number;
  disc: any;
  onComplete: () => void;
  simScene: number;
  setSimScene: (n: number) => void;
  activeWorkloads?: Set<string>;
}) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [sceneLoading, setSceneLoading] = useState(false);

  // Batch data (fetched on mount)
  const [summary, setSummary] = useState<any>(null);
  const [confidence, setConfidence] = useState<any>(null);
  const [entraSummary, setEntraSummary] = useState<any>(null);

  // Interactive state per scene
  const [engaged, setEngaged] = useState<Record<number, boolean>>({});
  const [attackPhase, setAttackPhase] = useState<'idle' | 'attacking' | 'detected' | 'resolved'>('idle');
  const [scoreRevealed, setScoreRevealed] = useState(false);
  const [recoveryPlan, setRecoveryPlan] = useState<any>(null);
  const [planVisible, setPlanVisible] = useState(0); // items revealed so far

  const markEngaged = (scene: number) => setEngaged(prev => ({ ...prev, [scene]: true }));

  // Batch-fetch on mount
  useEffect(() => {
    if (!tenantId) { setLoading(false); return; }
    Promise.allSettled([
      api.get(`/dashboard/summary?tenant_id=${tenantId}`),
      api.get(`/recovery/confidence?tenant_id=${tenantId}`),
      api.get(`/entra-id/summary?tenant_id=${tenantId}`),
    ]).then(([sumR, confR, entraR]) => {
      if (sumR.status === 'fulfilled') setSummary(sumR.value);
      if (confR.status === 'fulfilled') setConfidence(confR.value);
      if (entraR.status === 'fulfilled') setEntraSummary(entraR.value);
    }).finally(() => setLoading(false));
  }, [tenantId]);

  // Scene 0: auto-engage after mount animation
  useEffect(() => {
    if (simScene === 0 && !loading && !engaged[0]) {
      const t = setTimeout(() => markEngaged(0), 2000);
      return () => clearTimeout(t);
    }
  }, [simScene, loading]);

  // Scene 2: auto-reveal score animation
  useEffect(() => {
    if (simScene === 2 && !scoreRevealed && confidence) {
      const t = setTimeout(() => { setScoreRevealed(true); markEngaged(2); }, 2000);
      return () => clearTimeout(t);
    }
  }, [simScene, confidence]);

  // Derived data — filter to only selected workloads if provided
  const allWorkloads = summary?.workloads || {};
  const workloads = activeWorkloads
    ? Object.fromEntries(Object.entries(allWorkloads).filter(([k]) => activeWorkloads.has(k)))
    : allWorkloads;
  const totalItems = Object.values(workloads).reduce((s: number, w: any) => s + (w?.total || 0), 0);
  const totalStorage = summary?.storage?.total_bytes || 0;
  const snapshotCount = summary?.snapshots?.total || 0;
  const entra = entraSummary || {};
  const conf = confidence || {};
  const entraTotal = Object.values(entra.counts || {}).reduce((s: number, c: any) => s + (c as number), 0);

  // Scene 0 count-up values
  const countUpActive = simScene === 0 && !loading;
  const animItems = useCountUp(totalItems as number, countUpActive);
  const animSnaps = useCountUp(snapshotCount, countUpActive);
  // Scene 2 (confidence) count-up
  const animScore = useCountUp(conf.score || 0, scoreRevealed || simScene === 2);

  // Scene 1: attack simulation
  const runAttackSim = () => {
    setAttackPhase('attacking');
    setTimeout(() => setAttackPhase('detected'), 1500);
    setTimeout(() => { setAttackPhase('resolved'); markEngaged(1); }, 3000);
  };

  // Scene 4: generate plan on demand
  const generatePlan = () => {
    setSceneLoading(true);
    setPlanVisible(0);
    api.post<any>('/recovery/mass-restore', { tenant_id: tenantId, dry_run: true })
      .then(r => {
        setRecoveryPlan(r);
        // Stagger reveal items
        const items = r.plan || [];
        items.forEach((_: any, i: number) => {
          setTimeout(() => setPlanVisible(i + 1), (i + 1) * 200);
        });
        setTimeout(() => markEngaged(3), items.length * 200 + 500);
      })
      .catch(() => { setRecoveryPlan({ plan: [] }); markEngaged(3); })
      .finally(() => setSceneLoading(false));
  };

  const STEP_COUNT = 4;
  const isLastStep = simScene >= STEP_COUNT - 1;
  const canAdvance = engaged[simScene];

  // ────── Scene renderers ──────

  const renderScene0 = () => loading ? <Shimmer /> : (
    <div className="space-y-3">
      <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {Object.entries(workloads).map(([k, v]: [string, any], i) => (
            <div key={k} className="text-center transition-all duration-700" style={{ opacity: countUpActive ? 1 : 0, transitionDelay: `${i * 150}ms` }}>
              <div className="text-2xl font-bold text-green-700">{v?.total || 0}</div>
              <div className="text-xs text-green-600">{WORKLOAD_LABELS[k] || k}</div>
            </div>
          ))}
          {snapshotCount > 0 && (
            <div className="text-center transition-all duration-700" style={{ opacity: countUpActive ? 1 : 0, transitionDelay: `${Object.keys(workloads).length * 150}ms` }}>
              <div className="text-2xl font-bold text-green-700">{animSnaps}</div>
              <div className="text-xs text-green-600">Snapshots</div>
            </div>
          )}
          {totalStorage > 0 && (
            <div className="text-center transition-all duration-700" style={{ opacity: countUpActive ? 1 : 0, transitionDelay: `${(Object.keys(workloads).length + 1) * 150}ms` }}>
              <div className="text-2xl font-bold text-green-700">{fmtBytes(totalStorage)}</div>
              <div className="text-xs text-green-600">Protected</div>
            </div>
          )}
        </div>
        <div className="text-center mt-3 pt-3 border-t border-green-500/30">
          <span className="text-lg font-bold text-green-800">{animItems}</span>
          <span className="text-sm text-green-600 ml-1">total items backed up</span>
        </div>
      </div>
      <GapRow m365="93-day recycle bin. No point-in-time backup." shieldio={`${totalItems} items with unlimited point-in-time restore`} />
    </div>
  );

  const renderScene1 = () => loading ? <Shimmer /> : (
    <div className="space-y-3">
      {entra.protected ? (
        <>
          <div className="bg-purple-50 border border-purple-500/30 rounded-xl p-4">
            <p className="text-xs font-semibold text-purple-500 uppercase mb-2">Your Entra ID Backup</p>
            <div className="space-y-1.5">
              {Object.entries(entra.counts || {}).map(([type, count]: [string, any]) => {
                const meta = ENTRA_TYPE_LABELS[type] || { label: type };
                const isUnderAttack = attackPhase !== 'idle' && meta.critical;
                return (
                  <div key={type} className={`flex items-center justify-between text-sm px-2 py-1 rounded transition-all duration-500 ${
                    isUnderAttack && attackPhase === 'attacking' ? 'bg-red-100 ring-1 ring-red-400' :
                    isUnderAttack && attackPhase === 'resolved' ? 'bg-green-100 ring-1 ring-green-400' : ''
                  }`}>
                    <span className="text-purple-700">{meta.label}</span>
                    <span className="flex items-center gap-1.5">
                      <span className="font-bold text-purple-800">{count}</span>
                      {meta.critical && <span className="text-[10px] px-1.5 py-0.5 bg-red-100 text-red-700 rounded font-semibold">CRITICAL</span>}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          {/* Attack simulation */}
          {attackPhase === 'idle' && (
            <button onClick={runAttackSim}
              className="w-full py-2.5 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-700 transition-colors flex items-center justify-center gap-2 text-sm">
              Simulate Identity Attack
            </button>
          )}
          {attackPhase === 'attacking' && (
            <div className="bg-red-500/10 border border-red-300 rounded-xl p-3 animate-pulse">
              <p className="text-sm text-red-800 font-medium">An attacker disabled your MFA policy and granted themselves Global Admin...</p>
            </div>
          )}
          {(attackPhase === 'detected' || attackPhase === 'resolved') && (
            <div className="space-y-2">
              <div className="bg-red-500/10 border border-red-300 rounded-xl p-3">
                <p className="text-sm text-red-800 font-medium">Attack: MFA policy disabled + rogue Global Admin granted</p>
              </div>
              <div className={`bg-green-500/10 border border-green-300 rounded-xl p-3 transition-all duration-500 ${attackPhase === 'detected' ? 'opacity-0 scale-95' : 'opacity-100 scale-100'}`}>
                <p className="text-sm text-green-800 font-medium">Shieldio: Detected. One-click revert available{entra.last_backup ? ` from snapshot ${fmtTimeAgo(entra.last_backup)}` : ''}.</p>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4">
          <p className="text-sm text-amber-800 font-medium">Entra ID not yet backed up</p>
          <p className="text-xs text-amber-600 mt-1">{disc?.entra_objects ? `${disc.entra_objects} objects discovered` : 'Enable Entra ID workload'} — back it up to protect admin roles, MFA policies, and OAuth permissions.</p>
        </div>
      )}
      <GapRow m365="No Entra ID backup. No undo for disabled MFA or rogue admin grants."
        shieldio={entra.protected ? `${entraTotal} identity objects backed up with snapshot history` : 'Full Entra ID backup with point-in-time restore'} />
    </div>
  );

  const renderScene2 = () => loading ? <Shimmer /> : (
    <div className="space-y-3">
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
        <div className="flex items-center gap-5">
          <div className="relative w-20 h-20 flex-shrink-0">
            <svg viewBox="0 0 80 80" className="w-20 h-20 -rotate-90">
              <circle cx="40" cy="40" r="35" fill="none" stroke="#e5e7eb" strokeWidth="6" />
              <circle cx="40" cy="40" r="35" fill="none"
                stroke={conf.color === 'green' ? '#16a34a' : conf.color === 'blue' ? '#2563eb' : conf.color === 'amber' ? '#d97706' : '#dc2626'}
                strokeWidth="6" strokeLinecap="round"
                strokeDasharray={scoreRevealed ? `${(conf.score || 0) / 100 * 220} 220` : '0 220'}
                style={{ transition: 'stroke-dasharray 1.5s ease-out' }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-xl font-bold">{animScore}</span>
              <span className="text-[10px] text-gray-400">/ 100</span>
            </div>
          </div>
          <div className="flex-1">
            <div className={`flex items-center gap-2 mb-2 transition-opacity duration-1000 ${scoreRevealed ? 'opacity-100' : 'opacity-0'}`}>
              <span className={`text-lg font-bold ${conf.color === 'green' ? 'text-green-600' : conf.color === 'blue' ? 'text-blue-600' : conf.color === 'amber' ? 'text-amber-600' : 'text-red-600'}`}>
                Grade {conf.grade || '—'}
              </span>
              <span className="text-sm text-gray-500">{conf.label}</span>
            </div>
            {conf.factors && Object.entries(conf.factors).map(([key, f]: [string, any], i) => (
              <div key={key} className="mb-1">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-gray-500 capitalize">{key.replace('_', ' ')}</span>
                  <span className="font-medium">{Math.round(f.score)}%</span>
                </div>
                <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                  <div className="h-full rounded-full"
                    style={{
                      width: scoreRevealed ? `${f.score}%` : '0%',
                      background: f.score >= 80 ? '#16a34a' : f.score >= 50 ? '#d97706' : '#dc2626',
                      transition: `width 1s ease-out ${i * 300}ms`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
        {conf.recommendations?.length > 0 && scoreRevealed && (
          <div className="mt-3 px-3 py-2 bg-amber-500/10 border border-amber-500/30 rounded-lg animate-pulse">
            <p className="text-xs text-amber-800"><span className="font-semibold">Recommendation:</span> {conf.recommendations[0].action}</p>
          </div>
        )}
      </div>
      <GapRow m365="Zero recoverability metrics. No way to know if backups actually work."
        shieldio="Continuous confidence scoring across freshness, completeness, and validation" />
    </div>
  );

  const renderScene3 = () => (
    <div className="space-y-3">
      {!recoveryPlan ? (
        <div className="text-center py-6">
          <p className="text-sm text-gray-500 mb-4">Generate a full recovery plan from your backed-up data — no data is modified.</p>
          <button onClick={generatePlan} disabled={sceneLoading}
            className="px-6 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 disabled:opacity-50 transition-all flex items-center justify-center gap-2 mx-auto text-sm">
            {sceneLoading ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating...</> : 'Generate Recovery Plan'}
          </button>
        </div>
      ) : recoveryPlan.plan?.length > 0 ? (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-blue-500 uppercase">Recovery Plan Generated</p>
            <span className="text-xs text-blue-600 font-medium">
              {Math.min(planVisible, recoveryPlan.plan.length)} / {recoveryPlan.plan.length} objects
            </span>
          </div>
          {Object.entries(
            recoveryPlan.plan.slice(0, planVisible).reduce((acc: any, item: any) => {
              const wl = item.workload || 'unknown';
              if (!acc[wl]) acc[wl] = [];
              acc[wl].push(item);
              return acc;
            }, {} as Record<string, any[]>)
          ).map(([wl, items]: [string, any]) => (
            <div key={wl} className="mb-2">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold text-white ${
                  wl === 'entra_id' ? 'bg-red-500/100' : wl === 'exchange' ? 'bg-amber-500/100' : 'bg-blue-500/100'
                }`}>
                  {wl === 'entra_id' ? 'P1' : wl === 'exchange' ? 'P2' : 'P3'}
                </span>
                <span className="text-sm font-medium text-blue-800">{WORKLOAD_LABELS[wl] || wl}</span>
                <span className="text-xs text-blue-500">{items.length} objects</span>
              </div>
              {items.slice(0, 3).map((item: any) => (
                <div key={item.object_id} className="text-xs text-blue-600 ml-8 truncate">
                  {item.object_name} — {item.item_count} items {item.size_bytes ? `(${fmtBytes(item.size_bytes)})` : ''}
                </div>
              ))}
              {items.length > 3 && <div className="text-xs text-blue-400 ml-8">+{items.length - 3} more</div>}
            </div>
          ))}
          {planVisible >= recoveryPlan.plan.length && (
            <div className="mt-3 pt-3 border-t border-blue-500/30 text-center">
              <p className="text-sm font-semibold text-blue-800">
                Total: {recoveryPlan.plan.length} objects, {fmtBytes(recoveryPlan.plan.reduce((s: number, p: any) => s + (p.size_bytes || 0), 0))} recoverable
              </p>
              <button disabled className="mt-2 px-4 py-2 bg-gray-200 text-gray-500 rounded-lg text-xs cursor-not-allowed" title="Available from Recovery Dashboard">
                Execute Recovery (available in Recovery Dashboard)
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 text-center">
          <p className="text-sm text-blue-800 font-medium">No protected objects found for recovery plan</p>
        </div>
      )}
      <GapRow m365="Manually restore each mailbox, OneDrive, SharePoint site. Days to weeks."
        shieldio="One click. Priority-ordered. Identity first, then data. Minutes." />
    </div>
  );

  const scenes = [
    { key: 'overview', title: 'Your Backup at a Glance', subtitle: `${tenantName} — here's what Shieldio captured.`, problem: null as string | null, explore: { label: 'Explore backups', route: '/exchange' }, render: renderScene0 },
    { key: 'identity', title: 'Step 1: Secure Identity First', subtitle: 'Identity is the FIRST thing to restore in a cyber attack.', problem: 'If attackers have admin access, restoring data is pointless — they\'ll re-compromise everything.', explore: { label: 'Open Entra ID', route: '/entra-id' }, render: renderScene1 },
    { key: 'confidence', title: 'Step 2: Prove You Can Recover', subtitle: 'Know if you can actually recover — before you need to.', problem: null as string | null, explore: { label: 'Open Recovery Dashboard', route: '/recovery' }, render: renderScene2 },
    { key: 'mass_recovery', title: 'Step 3: One-Click Recovery', subtitle: 'Generate a full recovery plan from your real backups.', problem: 'Without Shieldio, recovery means restoring each mailbox, OneDrive, and site one by one. Days to weeks.', explore: { label: 'Open Recovery Dashboard', route: '/recovery' }, render: renderScene3 },
  ];

  const scene = scenes[simScene] || scenes[0];

  return (
    <div>
      <div className="text-center mb-4">
        <h2 className="text-xl font-bold text-white">Your Cyber Recovery Playbook</h2>
        <p className="text-gray-500 text-sm">Try each step with your real data</p>
      </div>

      {/* Step progress */}
      <div className="flex items-center justify-center gap-1.5 mb-5">
        {scenes.map((s, i) => (
          <button key={s.key} onClick={() => setSimScene(i)}
            className={`w-2.5 h-2.5 rounded-full transition-all ${
              i === simScene ? 'w-8 bg-blue-500/100' : engaged[i] ? 'bg-green-500/100' : i < simScene ? 'bg-blue-300' : 'bg-gray-200'
            }`} />
        ))}
      </div>

      {/* Step content */}
      <div className="bg-gray-800 rounded-2xl border border-gray-700 shadow-sm overflow-hidden">
        <div className="bg-gray-50 border-b border-gray-700 px-5 py-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-gray-400">Step {simScene + 1} of {STEP_COUNT}</span>
            {engaged[simScene] && <span className="text-xs font-semibold text-green-600 flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Done</span>}
          </div>
          <h3 className="text-lg font-bold text-white mt-1">{scene.title}</h3>
          <p className="text-sm text-gray-500">{scene.subtitle}</p>
        </div>

        {scene.problem && (
          <div className="px-5 py-3 bg-red-500/10 border-b border-red-100">
            <p className="text-sm text-red-800">{scene.problem}</p>
          </div>
        )}

        <div className="px-5 py-4">{scene.render()}</div>

        {/* Footer: Next + Explore link */}
        <div className="px-5 py-4 border-t border-gray-100 bg-gray-50">
          <div className="flex items-center justify-between">
            {!isLastStep ? (
              <button onClick={() => setSimScene(simScene + 1)} disabled={!canAdvance}
                className={`px-5 py-2.5 rounded-xl font-semibold text-sm flex items-center gap-1.5 transition-all ${
                  canAdvance ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                }`}>
                Next <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button onClick={onComplete} disabled={!canAdvance}
                className={`px-5 py-2.5 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all ${
                  canAdvance ? 'bg-green-600 text-white hover:bg-green-700' : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                }`}>
                Go to Dashboard <ArrowRight className="w-4 h-4" />
              </button>
            )}
            <button onClick={() => navigate(scene.explore.route)}
              className="text-xs text-blue-500 hover:text-blue-700 hover:underline">
              {scene.explore.label} →
            </button>
          </div>
          {!canAdvance && simScene === 1 && <p className="text-[11px] text-gray-400 mt-1.5">Click "Simulate Identity Attack" above to continue</p>}
          {!canAdvance && simScene === 3 && <p className="text-[11px] text-gray-400 mt-1.5">Click "Generate Recovery Plan" above to continue</p>}
        </div>
      </div>

      {/* Navigation + skip */}
      <div className="flex items-center justify-between mt-3">
        <button onClick={() => setSimScene(Math.max(0, simScene - 1))} disabled={simScene === 0}
          className="text-xs text-gray-400 hover:text-gray-600 disabled:opacity-30">← Back</button>
        <button onClick={onComplete} className="text-xs text-gray-400 hover:text-gray-600">Skip → Dashboard</button>
      </div>
    </div>
  );
}

/** Guided onboarding wizard — flows from OAuth callback through full setup */

const WIZARD_STEPS = [
  { key: 'connect', label: 'Connect', icon: Shield },
  { key: 'discover', label: 'Discover', icon: Globe },
  { key: 'protect', label: 'Protect', icon: Shield },
  { key: 'context', label: 'Intelligence', icon: Shield },
  { key: 'backup', label: 'Backup', icon: Shield },
  { key: 'recovery', label: 'Recovery', icon: Shield },
  { key: 'ready', label: 'Ready', icon: CheckCircle },
];

/**
 * Demo Onboard — starts at discovery (step 1), skipping OAuth.
 * Uses the first active tenant. For prospect demos where the tenant
 * is already connected but you want to show the full discovery → backup → recovery flow.
 */
export function DemoOnboard() {
  const [tenantId, setTenantId] = useState<number | null>(null);
  const [tenantName, setTenantName] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<any[]>('/tenants/')
      .then(tenants => {
        const active = tenants?.find((t: any) => t.status === 'active');
        if (active) {
          setTenantId(active.id);
          setTenantName(active.name);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!tenantId) {
    // No tenant — fall back to regular onboarding
    return <Onboard />;
  }

  // Render OnboardCallback with pre-set tenant data via URL params trick
  // We navigate to the callback with fake params that simulate a successful connection
  return <OnboardCallbackWithTenant tenantId={tenantId} tenantName={tenantName} />;
}

/** OnboardCallback variant that starts with an existing tenant (skips OAuth step 0) */
function OnboardCallbackWithTenant({ tenantId, tenantName }: { tenantId: number; tenantName: string }) {
  // Redirect to the callback URL with demo flag — OnboardCallback reads from searchParams
  useEffect(() => {
    window.location.replace(`/onboard/callback?demo=true&db_tenant_id=${tenantId}&tenant_name=${encodeURIComponent(tenantName)}`);
  }, [tenantId, tenantName]);
  return <div className="flex items-center justify-center min-h-[60vh]"><Loader2 className="w-8 h-8 animate-spin text-blue-500" /></div>;
}

// ── Session persistence helpers ──
const ONBOARD_STATE_KEY = 'shieldio_onboard_state';

function saveOnboardState(state: any) {
  try { sessionStorage.setItem(ONBOARD_STATE_KEY, JSON.stringify(state)); } catch {}
}

function loadOnboardState(): any | null {
  try {
    const raw = sessionStorage.getItem(ONBOARD_STATE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function clearOnboardState() {
  sessionStorage.removeItem(ONBOARD_STATE_KEY);
}

export function OnboardCallback() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Restore from sessionStorage or URL step param
  const saved = loadOnboardState();
  const urlStep = parseInt(searchParams.get('step') || '0');
  const initialStep = saved?.step ?? (urlStep || 0);

  const [step, _setStep] = useState(initialStep);
  const [simScene, setSimScene] = useState(saved?.simScene || 0);
  const [error, setError] = useState<string | null>(null);
  const [resultData, setResultData] = useState<any>(saved?.resultData || null);
  const [discoveryResults, setDiscoveryResults] = useState<any>(saved?.discoveryResults || null);
  const [slaPolicies, setSlaPolicies] = useState<any[]>(saved?.slaPolicies || []);
  const [selectedSla, setSelectedSla] = useState<number | null>(saved?.selectedSla || null);
  const [backupStatus, setBackupStatus] = useState<string>(saved?.backupStatus || 'pending');
  const [protecting, setProtecting] = useState(false);
  const [_backingUp, setBackingUp] = useState(false);

  // Workload toggles
  const [availableWorkloads, setAvailableWorkloads] = useState<any[]>(saved?.availableWorkloads || []);
  const [selectedWorkloads, setSelectedWorkloads] = useState<Set<string>>(
    saved?.selectedWorkloads ? new Set(saved.selectedWorkloads) : new Set(['exchange', 'entra_id', 'sharepoint'])
  );
  const [discovering, setDiscovering] = useState(false);
  const [backupWorkloads, setBackupWorkloads] = useState<Set<string>>(new Set());
  const [backupProgress, setBackupProgress] = useState<Record<string, string>>(saved?.backupProgress || {});

  // Wrap setStep to persist state + update URL
  const setStep = (newStep: number) => {
    _setStep(newStep);
    // Update URL without full navigation (allows browser back/forward)
    const params = new URLSearchParams(searchParams);
    params.set('step', String(newStep));
    setSearchParams(params, { replace: false });
  };

  // Persist state on every change
  useEffect(() => {
    saveOnboardState({
      step, simScene, resultData, discoveryResults, slaPolicies, selectedSla,
      backupStatus, backupProgress,
      availableWorkloads, selectedWorkloads: Array.from(selectedWorkloads),
    });
  }, [step, simScene, resultData, discoveryResults, slaPolicies, selectedSla, backupStatus, backupProgress, availableWorkloads, selectedWorkloads]);

  // Handle browser back/forward — sync URL step to state
  useEffect(() => {
    const urlStepNow = parseInt(searchParams.get('step') || '0');
    if (urlStepNow !== step && urlStepNow >= 0 && urlStepNow <= 6) {
      _setStep(urlStepNow);
    }
  }, [searchParams]);

  // Step 0: Process OAuth callback (or demo mode) — skip if state was restored
  useEffect(() => {
    // If we restored from sessionStorage with data already loaded, skip OAuth processing
    if (saved?.resultData && saved?.step > 0) {
      // Just reload workloads if needed
      if (availableWorkloads.length === 0) {
        api.get<any>('/onboard/workloads').then(data => setAvailableWorkloads(data.workloads || [])).catch(() => {});
      }
      if (slaPolicies.length === 0) {
        api.get<any>('/sla-policies/').then(p => { if (Array.isArray(p)) setSlaPolicies(p); }).catch(() => {});
      }
      return;
    }

    const isDemo = searchParams.get('demo') === 'true';
    const adminConsent = searchParams.get('admin_consent');
    const tenant = searchParams.get('tenant');
    const state = searchParams.get('state');
    const errParam = searchParams.get('error');

    if (errParam) {
      setError(searchParams.get('error_description') || errParam);
      return;
    }

    // Load workload metadata
    api.get<any>('/onboard/workloads').then(data => {
      setAvailableWorkloads(data.workloads || []);
      const recommended = (data.workloads || [])
        .filter((w: any) => w.recommended)
        .map((w: any) => w.key);
      setSelectedWorkloads(new Set(recommended));
    }).catch(() => {});

    // Demo mode: skip OAuth, use existing tenant
    if (isDemo) {
      const dbTenantId = parseInt(searchParams.get('db_tenant_id') || '0');
      const tenantName = searchParams.get('tenant_name') || 'Demo Tenant';
      if (dbTenantId) {
        setResultData({
          success: true, existing: true,
          db_tenant_id: dbTenantId,
          tenant_name: tenantName,
        });
        setStep(1); // Jump to discover
        api.get<any>('/sla-policies/').then(policies => {
          if (Array.isArray(policies)) setSlaPolicies(policies);
        }).catch(() => {});
      } else {
        setError('Demo mode: no tenant ID provided');
      }
      return;
    }

    if (adminConsent && tenant) {
      api.get<any>(`/onboard/callback?admin_consent=${adminConsent}&tenant=${tenant}&state=${state || ''}`)
        .then((data: any) => {
          if (data.success) {
            setResultData(data);
            if (data.discovery) setDiscoveryResults(data.discovery);
            setStep(1); // Move to discover
            api.get<any>('/sla-policies/').then(policies => {
              if (Array.isArray(policies)) setSlaPolicies(policies);
            }).catch(() => {});
          } else {
            setError(data.detail || data.error || 'Connection failed');
          }
        })
        .catch((e: any) => setError(e.message || 'Connection failed'));
    } else {
      setTimeout(() => setError('No authorization data received'), 3000);
    }
  }, []);

  // Run selective discovery
  const handleDiscoverSelected = async () => {
    if (!resultData?.db_tenant_id || selectedWorkloads.size === 0) return;
    setDiscovering(true);
    try {
      const data: any = await api.post('/onboard/discover', {
        tenant_id: resultData.db_tenant_id,
        workloads: Array.from(selectedWorkloads),
      });
      if (data.results) {
        setDiscoveryResults(data.results);
      }
    } catch (e: any) {
      setError(e.message || 'Discovery failed');
    } finally {
      setDiscovering(false);
    }
  };

  const toggleWorkload = (key: string) => {
    setSelectedWorkloads(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // toggleBackupWorkload removed — smart backup backs up all selected workloads

  // Step 2 → 3: Assign SLA and protect all
  const handleProtect = async () => {
    if (!selectedSla || !resultData?.db_tenant_id) return;
    setProtecting(true);
    try {
      await api.post('/onboard/complete', {
        tenant_id: resultData.db_tenant_id,
        sla_policy_id: selectedSla,
        protect_all: true,
      });
      setStep(3); // Move to intelligence/context step
    } catch (e: any) {
      setError(e.message || 'Protection failed');
    } finally {
      setProtecting(false);
    }
  };

  // Step 3 → 4: Run first backup (per-workload)
  const handleFirstBackup = async () => {
    const workloadsToBackup = backupWorkloads.size > 0 ? Array.from(backupWorkloads) : Array.from(selectedWorkloads);
    setBackingUp(true);
    setBackupStatus('running');

    const progress: Record<string, string> = {};
    workloadsToBackup.forEach(wl => { progress[wl] = 'pending'; });
    setBackupProgress({...progress});

    for (const wl of workloadsToBackup) {
      progress[wl] = 'running';
      setBackupProgress({...progress});
      try {
        if (wl === 'entra_id') {
          await api.post(`/entra-id/backup?tenant_id=${resultData.db_tenant_id}`);
        } else {
          await api.post(`/${wl}/backup-all?tenant_id=${resultData.db_tenant_id}`);
        }
        progress[wl] = 'done';
      } catch {
        progress[wl] = 'failed';
      }
      setBackupProgress({...progress});
    }

    setBackupStatus('complete');
    setStep(5); // Move to recovery sim
    setBackingUp(false);
  };

  // Get discovery data from result
  const disc = discoveryResults || resultData?.discovery?.results || resultData?.discovery;
  const tenantName = resultData?.tenant_name || searchParams.get('tenant_name') || 'Your Organization';
  const totalObjects = disc ? (disc.mailboxes || 0) + (disc.onedrives || 0) + (disc.sites || 0) + (disc.teams || 0) + (disc.entra_objects ? 1 : 0) : 0;

  // Error state
  if (error) {
    const isConfigError = error.includes('configuration') || error.includes('credentials');
    const isConsentError = error.includes('consent') || error.includes('Administrator');
    const isPropagation = error.includes('processing') || error.includes('wait');

    return (
      <div className="max-w-lg mx-auto text-center py-16">
        <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 ${
          isConfigError ? 'bg-amber-100' : 'bg-red-100'
        }`}>
          <XCircle className={`w-8 h-8 ${isConfigError ? 'text-amber-600' : 'text-red-600'}`} />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">
          {isPropagation ? 'Almost There' : isConfigError ? 'Setup Required' : 'Connection Failed'}
        </h2>
        <p className="text-gray-600 mb-2">{error}</p>
        {isPropagation && (
          <p className="text-sm text-gray-400 mb-6">Microsoft can take up to 60 seconds to process admin consent for new tenants.</p>
        )}
        {isConfigError && (
          <p className="text-sm text-gray-400 mb-6">This is a Shieldio platform issue, not a problem with your M365 tenant.</p>
        )}
        {isConsentError && (
          <p className="text-sm text-gray-400 mb-6">You need to sign in with a Global Administrator account to approve the connection.</p>
        )}
        <div className="flex items-center justify-center gap-3 mt-4">
          <button onClick={() => navigate('/onboard')} className="px-6 py-2.5 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700">
            {isPropagation ? 'Try Again (should work now)' : 'Try Again'}
          </button>
          <button onClick={() => navigate('/')} className="px-6 py-2.5 bg-gray-700 text-gray-300 rounded-xl font-medium hover:bg-gray-200">Dashboard</button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white px-4">
    <div className="max-w-2xl mx-auto py-8">
      {/* Progress bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          {WIZARD_STEPS.map((s, i) => (
            <div key={s.key} className="flex items-center gap-1.5">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                i < step ? 'bg-green-500/100 text-white' :
                i === step ? 'bg-blue-600 text-white ring-4 ring-blue-100' :
                'bg-gray-200 text-gray-500'
              }`}>
                {i < step ? <CheckCircle className="w-4 h-4" /> : i + 1}
              </div>
              <span className={`text-xs font-medium hidden sm:block ${i <= step ? 'text-white' : 'text-gray-400'}`}>{s.label}</span>
              {i < WIZARD_STEPS.length - 1 && <div className={`w-8 sm:w-16 h-0.5 mx-1 ${i < step ? 'bg-green-500/100' : 'bg-gray-200'}`} />}
            </div>
          ))}
        </div>
      </div>

      {/* Step 0: Connecting */}
      {step === 0 && (
        <div className="text-center py-12">
          <Loader2 className="w-12 h-12 animate-spin text-blue-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white">Connecting to Microsoft 365...</h2>
          <p className="text-gray-500 mt-2">Setting up secure access and discovering your workloads.</p>
        </div>
      )}

      {/* Step 1: Discovery — Workload Selection */}
      {step === 1 && (
        <div>
          <div className="text-center mb-6">
            <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <CheckCircle className="w-7 h-7 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-white">Connected to {tenantName}</h2>
            <p className="text-gray-500 mt-1">
              {discoveryResults
                ? `Found ${totalObjects} objects. Select workloads to discover or add more.`
                : 'Choose which workloads to discover. Fast workloads are pre-selected.'}
            </p>
          </div>

          {/* Workload toggle cards */}
          <div className="space-y-2 mb-4">
            {(availableWorkloads.length > 0 ? availableWorkloads : [
              { key: 'exchange', label: 'Exchange', description: 'Emails, calendar, contacts', speed: 'fast', est_seconds: 2, recommended: true },
              { key: 'entra_id', label: 'Entra ID', description: 'Users, groups, roles, policies', speed: 'fast', est_seconds: 2, recommended: true },
              { key: 'sharepoint', label: 'SharePoint', description: 'Sites, documents, lists', speed: 'medium', est_seconds: 5, recommended: true },
              { key: 'onedrive', label: 'OneDrive', description: 'Personal files and folders', speed: 'medium', est_seconds: 5, recommended: false },
              { key: 'teams', label: 'Teams', description: 'Channels, messages, chats', speed: 'slow', est_seconds: 10, recommended: false },
            ]).map((wl: any) => {
              const isSelected = selectedWorkloads.has(wl.key);
              const discCount = discoveryResults
                ? (wl.key === 'exchange' ? discoveryResults.mailboxes :
                   wl.key === 'onedrive' ? discoveryResults.onedrives :
                   wl.key === 'sharepoint' ? discoveryResults.sites :
                   wl.key === 'teams' ? discoveryResults.teams :
                   wl.key === 'entra_id' ? (discoveryResults.entra_objects ? 1 : 0) : 0)
                : null;

              return (
                <button
                  key={wl.key}
                  onClick={() => toggleWorkload(wl.key)}
                  disabled={discovering}
                  className={`w-full p-3 rounded-xl border-2 text-left transition-all flex items-center gap-3 ${
                    isSelected
                      ? 'border-blue-400 bg-blue-500/10/50'
                      : 'border-gray-700 hover:border-gray-300'
                  }`}
                >
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                    isSelected ? 'border-blue-500 bg-blue-500/100' : 'border-gray-300'
                  }`}>
                    {isSelected && <CheckCircle className="w-3.5 h-3.5 text-white" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white text-sm">{wl.label}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        wl.speed === 'fast' ? 'bg-green-100 text-green-700' :
                        wl.speed === 'medium' ? 'bg-amber-100 text-amber-700' :
                        'bg-gray-700 text-gray-600'
                      }`}>
                        {wl.speed === 'fast' ? '⚡ fast' : wl.speed === 'medium' ? '~5s' : '~10s'}
                      </span>
                      {wl.recommended && <span className="text-[10px] text-blue-500 font-medium">Recommended</span>}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{wl.description}</p>
                  </div>
                  {discCount !== null && discCount > 0 && (
                    <div className="text-right flex-shrink-0">
                      <div className="text-lg font-bold text-blue-600">{discCount}</div>
                      <div className="text-[10px] text-gray-400">found</div>
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          {/* Discover / Continue buttons */}
          <div className="flex gap-3">
            {!discoveryResults && (
              <button
                onClick={handleDiscoverSelected}
                disabled={discovering || selectedWorkloads.size === 0}
                className="flex-1 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {discovering ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Discovering {selectedWorkloads.size} workloads...</>
                ) : (
                  <>Discover Selected ({selectedWorkloads.size}) <ArrowRight className="w-4 h-4" /></>
                )}
              </button>
            )}
            {discoveryResults && (
              <>
                <button
                  onClick={handleDiscoverSelected}
                  disabled={discovering}
                  className="px-4 py-3 bg-gray-700 text-gray-300 rounded-xl font-medium hover:bg-gray-200 transition-colors flex items-center gap-2"
                >
                  {discovering ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  Re-discover
                </button>
                <button
                  onClick={() => { setBackupWorkloads(new Set(selectedWorkloads)); setStep(2); }}
                  className="flex-1 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
                >
                  Protect {totalObjects} Objects <ArrowRight className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Step 2: Choose SLA Policy */}
      {step === 2 && (
        <div>
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-white">Choose Protection Level</h2>
            <p className="text-gray-500 mt-1">How often should we back up your data?</p>
          </div>

          <div className="space-y-3 mb-6">
            {slaPolicies.length > 0 ? slaPolicies.map((sla: any) => (
              <button
                key={sla.id}
                onClick={() => setSelectedSla(sla.id)}
                className={`w-full p-4 rounded-xl border-2 text-left transition-all ${
                  selectedSla === sla.id
                    ? 'border-blue-500 bg-blue-500/10 ring-2 ring-blue-200'
                    : 'border-gray-700 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-bold text-white">{sla.name}</div>
                    <div className="text-sm text-gray-500">
                      Every {sla.backup_frequency_hours}h • {sla.retention_days} day retention
                      {sla.worm_enabled ? ' • WORM locked' : ''}
                    </div>
                  </div>
                  <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${
                    selectedSla === sla.id ? 'border-blue-500 bg-blue-500/100' : 'border-gray-300'
                  }`}>
                    {selectedSla === sla.id && <CheckCircle className="w-4 h-4 text-white" />}
                  </div>
                </div>
              </button>
            )) : (
              <div className="text-center py-4">
                <p className="text-gray-500 text-sm">No SLA policies found. We'll create a default daily backup policy.</p>
                <button
                  onClick={() => { setSelectedSla(-1); }}
                  className="mt-3 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
                >
                  Use Default (Daily, 30-day retention)
                </button>
              </div>
            )}
          </div>

          <button
            onClick={handleProtect}
            disabled={!selectedSla || protecting}
            className="w-full py-3 bg-green-600 text-white rounded-xl font-semibold hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {protecting ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Protecting...</>
            ) : (
              <>Protect All {totalObjects} Objects <ArrowRight className="w-4 h-4" /></>
            )}
          </button>
        </div>
      )}

      {/* Step 3: First Backup — per-workload selection + live progress */}
      {step === 3 && (
        <div>
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-white">Smart Backup Intelligence</h2>
            <p className="text-gray-500 mt-1">
              Shieldio auto-detects your organizational context to prioritize what matters most.
            </p>
          </div>
          <div className="space-y-3 mb-6">
            <div className="p-4 rounded-xl border border-blue-500/30 bg-blue-500/10/50">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold">1</div>
                <div className="font-semibold text-white">Org Context Detection</div>
              </div>
              <p className="text-sm text-gray-600 ml-11">Auto-discovers reporting hierarchy, department structure, VIP groups, and privileged roles from your Microsoft 365 tenant.</p>
            </div>
            <div className="p-4 rounded-xl border border-purple-500/30 bg-purple-500/10">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-full bg-purple-600 text-white flex items-center justify-center text-sm font-bold">2</div>
                <div className="font-semibold text-white">Criticality Scoring</div>
              </div>
              <p className="text-sm text-gray-600 ml-11">Each user and site gets a 4-factor criticality score: role weight, direct reports, sign-in recency, and VIP group membership. Critical assets are prioritized for faster RPO.</p>
            </div>
            <div className="p-4 rounded-xl border border-green-500/30 bg-green-500/10/50">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-full bg-green-600 text-white flex items-center justify-center text-sm font-bold">3</div>
                <div className="font-semibold text-white">MVB Recovery Plans</div>
              </div>
              <p className="text-sm text-gray-600 ml-11">Pre-computed 4-phase NIST-ordered recovery plans ensure your CEO, CFO, and critical infrastructure are restored first — automatically, not manually.</p>
            </div>
            <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10/50">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-full bg-amber-600 text-white flex items-center justify-center text-sm font-bold">4</div>
                <div className="font-semibold text-white">Confidence Scoring</div>
              </div>
              <p className="text-sm text-gray-600 ml-11">Criticality-weighted recovery confidence tells you not just "90% backed up" but "your most important 10 users have 100% coverage."</p>
            </div>
          </div>
          <div className="bg-gray-900 rounded-xl p-4 mb-6 text-center">
            <p className="text-gray-400 text-xs mb-1">What competitors require you to configure manually</p>
            <p className="text-white font-semibold">Shieldio detects automatically from your Microsoft Graph data</p>
          </div>
          <button
            onClick={() => setStep(4)}
            className="w-full py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
          >
            Continue to Backup <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {step === 4 && (
        <div>
          <div className="text-center mb-5">
            <h2 className="text-2xl font-bold text-white">Smart Backup Storyline</h2>
            <p className="text-gray-500 mt-1">Watch Shieldio discover, prioritize, and protect your data — live.</p>
          </div>

          {/* ── Phase 1: Discovery Storyline ── */}
          {backupStatus === 'pending' && (
            <div className="space-y-4">
              {/* Animated discovery cards — objects appearing */}
              <div className="bg-gray-800 rounded-xl border border-gray-700 p-4">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                  <span className="text-xs font-semibold text-green-400 uppercase tracking-wider">Discovered from {tenantName}</span>
                </div>

                <div className="space-y-2">
                  {[
                    { wl: 'exchange', count: disc?.mailboxes, label: 'Mailboxes', icon: '📧', color: 'text-blue-400 border-blue-500/30', detail: 'Emails, calendar events, contacts, attachments' },
                    { wl: 'onedrive', count: disc?.onedrives, label: 'OneDrive Accounts', icon: '📁', color: 'text-purple-400 border-purple-500/30', detail: 'Files, folders, version history' },
                    { wl: 'sharepoint', count: disc?.sites, label: 'SharePoint Sites', icon: '🌐', color: 'text-green-400 border-green-500/30', detail: 'Document libraries, lists, pages' },
                    { wl: 'teams', count: disc?.teams, label: 'Teams', icon: '💬', color: 'text-pink-400 border-pink-500/30', detail: 'Channel messages, files, chats' },
                    { wl: 'entra_id', count: disc?.entra_objects || 1, label: 'Entra ID Config', icon: '🔑', color: 'text-amber-400 border-amber-500/30', detail: 'Users, roles, CA policies, OAuth grants' },
                  ].filter(item => selectedWorkloads.has(item.wl) && item.count > 0).map((item, i) => (
                    <div key={item.wl}
                      className={`flex items-center gap-3 p-3 rounded-lg border bg-gray-900/50 ${item.color} transition-all duration-500`}
                      style={{ opacity: 1, transitionDelay: `${i * 150}ms` }}>
                      <span className="text-xl">{item.icon}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`text-sm font-bold ${item.color.split(' ')[0]}`}>{item.count}</span>
                          <span className="text-sm font-medium text-white">{item.label}</span>
                        </div>
                        <div className="text-[10px] text-gray-500">{item.detail}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Visual pipeline */}
              <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-4">
                <div className="text-xs font-medium text-gray-400 mb-3">Backup Pipeline — what happens to each object:</div>
                <div className="flex items-center justify-between gap-1">
                  {[
                    { icon: <Globe className="w-4 h-4" />, label: 'Read', color: 'bg-blue-500/20 text-blue-400', desc: 'Graph API' },
                    { icon: <Shrink className="w-4 h-4" />, label: 'Compress', color: 'bg-purple-500/20 text-purple-400', desc: '-60% size' },
                    { icon: <Hash className="w-4 h-4" />, label: 'Hash', color: 'bg-cyan-500/20 text-cyan-400', desc: 'SHA-256' },
                    { icon: <Lock className="w-4 h-4" />, label: 'Encrypt', color: 'bg-green-500/20 text-green-400', desc: 'AES-256' },
                    { icon: <Shield className="w-4 h-4" />, label: 'Store', color: 'bg-amber-500/20 text-amber-400', desc: 'Immutable' },
                  ].map((stage, i) => (
                    <div key={stage.label} className="flex items-center gap-1">
                      <div className={`flex flex-col items-center gap-1 ${stage.color} rounded-lg p-2 min-w-[52px]`}>
                        {stage.icon}
                        <span className="text-[9px] font-bold">{stage.label}</span>
                        <span className="text-[8px] opacity-60">{stage.desc}</span>
                      </div>
                      {i < 4 && <ArrowRight className="w-3 h-3 text-gray-600 shrink-0" />}
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={handleFirstBackup}
                disabled={selectedWorkloads.size === 0}
                className="w-full py-3 bg-green-600 text-white rounded-xl font-semibold hover:bg-green-500 transition-colors flex items-center justify-center gap-2"
              >
                <Shield className="w-5 h-5" />
                Protect {totalObjects} Objects Now
              </button>
            </div>
          )}

          {/* ── Phase 2: Live Backup Storyline ── */}
          {backupStatus === 'running' && (
            <div className="space-y-3">
              {/* Overall progress */}
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                  <span className="text-sm font-medium text-blue-300">Protecting {totalObjects} objects...</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div className="bg-blue-500 rounded-full h-2 transition-all duration-1000"
                    style={{ width: `${Math.round(Object.values(backupProgress).filter(s => s === 'done').length / Math.max(Object.keys(backupProgress).length, 1) * 100)}%` }} />
                </div>
              </div>

              {/* Per-workload live detail */}
              {Object.entries(backupProgress).map(([wl, status]) => {
                const objectCount = wl === 'exchange' ? disc?.mailboxes : wl === 'onedrive' ? disc?.onedrives : wl === 'sharepoint' ? disc?.sites : wl === 'teams' ? disc?.teams : wl === 'entra_id' ? 1 : 0;
                const pipelineStage = status === 'running' ? ['Reading', 'Compressing', 'Hashing', 'Encrypting', 'Storing'][Math.floor(Math.random() * 3)] : '';
                return (
                  <div key={wl} className={`rounded-xl border transition-all overflow-hidden ${
                    status === 'running' ? 'border-blue-500/50 bg-blue-500/5' :
                    status === 'done' ? 'border-green-500/30 bg-green-500/5' :
                    status === 'failed' ? 'border-red-500/30 bg-red-500/5' : 'border-gray-700 bg-gray-800/30'
                  }`}>
                    <div className="flex items-center gap-3 p-3">
                      {status === 'pending' && <div className="w-6 h-6 rounded-full border-2 border-gray-600 flex items-center justify-center text-[9px] text-gray-600">—</div>}
                      {status === 'running' && <Loader2 className="w-6 h-6 animate-spin text-blue-400" />}
                      {status === 'done' && <CheckCircle className="w-6 h-6 text-green-400" />}
                      {status === 'failed' && <XCircle className="w-6 h-6 text-red-400" />}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-sm text-white capitalize">{wl.replace('_', ' ')}</span>
                          <span className="text-[10px] text-gray-500">{objectCount} objects</span>
                        </div>
                        {status === 'running' && (
                          <div className="text-[10px] text-blue-300 mt-0.5 animate-pulse">{pipelineStage}...</div>
                        )}
                      </div>
                      <div className="text-right">
                        {status === 'done' && <span className="text-xs font-medium text-green-400">Protected ✓</span>}
                        {status === 'running' && <span className="text-xs font-medium text-blue-400">In progress</span>}
                        {status === 'pending' && <span className="text-xs text-gray-500">Next</span>}
                        {status === 'failed' && <span className="text-xs font-medium text-red-400">Failed</span>}
                      </div>
                    </div>
                    {/* Animated pipeline strip for running workload */}
                    {status === 'running' && (
                      <div className="flex h-1">
                        <div className="flex-1 bg-blue-500 animate-pulse" />
                        <div className="flex-1 bg-purple-500/50" />
                        <div className="flex-1 bg-cyan-500/30" />
                        <div className="flex-1 bg-green-500/20" />
                        <div className="flex-1 bg-amber-500/10" />
                      </div>
                    )}
                    {status === 'done' && <div className="h-1 bg-green-500" />}
                  </div>
                );
              })}
            </div>
          )}

          {/* ── Phase 3: Backup Complete — Protection Map ── */}
          {backupStatus === 'complete' && (
            <div className="space-y-4">
              {/* Success header */}
              <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-5 text-center">
                <div className="w-14 h-14 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-3">
                  <Shield className="w-7 h-7 text-green-400" />
                </div>
                <div className="text-xl font-bold text-white">{totalObjects} Objects Protected</div>
                <div className="text-xs text-green-300 mt-1">AES-256-GCM encrypted • Unique key per snapshot • Point-in-time restore ready</div>
              </div>

              {/* Protection map — visual summary of what's protected */}
              <div className="bg-gray-800 rounded-xl border border-gray-700 p-4">
                <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Protection Map</div>
                <div className="space-y-2">
                  {Object.entries(backupProgress).filter(([, s]) => s === 'done').map(([wl]) => {
                    const count = wl === 'exchange' ? disc?.mailboxes : wl === 'onedrive' ? disc?.onedrives : wl === 'sharepoint' ? disc?.sites : wl === 'teams' ? disc?.teams : 1;
                    return (
                      <div key={wl} className="flex items-center gap-3 p-2 rounded-lg bg-green-500/5 border border-green-500/20">
                        <Shield className="w-4 h-4 text-green-400 shrink-0" />
                        <div className="flex-1">
                          <span className="text-sm font-medium text-white capitalize">{wl.replace('_', ' ')}</span>
                          <span className="text-[10px] text-gray-500 ml-2">{count} {count === 1 ? 'object' : 'objects'}</span>
                        </div>
                        <span className="text-[10px] font-medium text-green-400">Encrypted ✓</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* What comes next — intelligence preview */}
              <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Star className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-semibold text-white">What happens next</span>
                </div>
                <div className="text-xs text-gray-400 space-y-1.5">
                  <div className="flex items-start gap-2">
                    <span className="text-blue-400 mt-0.5">1.</span>
                    <span>Shieldio analyzes your org to score each user by criticality</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-blue-400 mt-0.5">2.</span>
                    <span>A recovery plan is built: identity first, then CEO, then everyone else</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-blue-400 mt-0.5">3.</span>
                    <span>If ransomware hits, one click restores in priority order</span>
                  </div>
                </div>
              </div>

              <button onClick={() => setStep(5)} className="w-full py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-500 flex items-center justify-center gap-2">
                See Recovery Playbook <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {backupStatus !== 'complete' && (
            <button onClick={() => setStep(5)} className="mt-4 w-full text-sm text-gray-500 hover:text-gray-300 text-center">
              Skip — I'll run it later
            </button>
          )}
        </div>
      )}

      {/* Step 5: Cyber Recovery Simulation */}
      {step === 5 && (
        <CyberRecoverySimulation
          tenantName={tenantName}
          tenantId={resultData?.db_tenant_id}
          disc={disc}
          onComplete={() => setStep(6)}
          simScene={simScene}
          activeWorkloads={selectedWorkloads}
          setSimScene={setSimScene}
        />
      )}

      {/* Step 6: Ready! */}
      {step === 6 && (
        <div className="text-center">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4 animate-bounce">
            <CheckCircle className="w-10 h-10 text-green-600" />
          </div>
          <h2 className="text-3xl font-bold text-white mb-2">You're Protected! 🎉</h2>
          <p className="text-gray-500 mb-2">{tenantName} is now backed up with Shieldio.</p>

          <div className="bg-gray-50 rounded-xl p-4 mb-6 text-sm text-left max-w-md mx-auto">
            <div className="font-semibold text-white mb-2">What happens next:</div>
            <div className="space-y-2 text-gray-600">
              <div className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span>Automatic backups run on your chosen schedule</span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span>Smart Engine monitors for anomalies (ransomware detection)</span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span>Self-service restore available for your users</span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span>Recovery dashboard tracks your protection health</span>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => { sessionStorage.setItem('demo_onboard_complete', '1'); clearOnboardState(); navigate('/'); }}
              className="px-6 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              Go to Dashboard <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => navigate('/recovery')}
              className="px-6 py-3 bg-gray-700 text-gray-300 rounded-xl font-medium hover:bg-gray-200 transition-colors"
            >
              Recovery Dashboard
            </button>
          </div>
        </div>
      )}
    </div>
    </div>
  );
}
