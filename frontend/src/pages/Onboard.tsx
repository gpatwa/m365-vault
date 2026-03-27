import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Shield, Globe, MessageSquare, CheckCircle, XCircle, Loader2, ArrowRight } from 'lucide-react';
import { api } from '../api/client';

const PLATFORM_ICONS: Record<string, any> = {
  microsoft365: Shield,
  google: Globe,
  salesforce: Globe,
  slack: MessageSquare,
};

const PLATFORM_COLORS: Record<string, string> = {
  microsoft365: 'border-blue-200 bg-blue-50 hover:border-blue-400',
  google: 'border-green-200 bg-green-50 hover:border-green-400',
  salesforce: 'border-sky-200 bg-sky-50 hover:border-sky-400',
  slack: 'border-purple-200 bg-purple-50 hover:border-purple-400',
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
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-10">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-2xl mb-4">
          <Shield className="w-8 h-8 text-blue-600" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Connect Your SaaS Platform</h1>
        <p className="text-gray-500 text-lg">
          Select a platform to protect. One-click OAuth — no credentials to copy.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {platforms.map(platform => {
          const Icon = PLATFORM_ICONS[platform.icon] || Shield;
          const colors = PLATFORM_COLORS[platform.key] || 'border-gray-200 bg-gray-50';
          const isConnecting = connecting === platform.key;

          return (
            <button
              key={platform.key}
              onClick={() => platform.available && handleConnect(platform.key)}
              disabled={!platform.available || !!connecting}
              className={`relative p-6 rounded-2xl border-2 transition-all text-left ${
                platform.available
                  ? `${colors} cursor-pointer shadow-sm hover:shadow-md`
                  : 'border-gray-100 bg-gray-50 cursor-not-allowed opacity-60'
              }`}
            >
              {!platform.available && (
                <span className="absolute top-3 right-3 px-2 py-0.5 bg-gray-200 text-gray-500 text-[10px] font-semibold rounded-full">
                  Coming Soon
                </span>
              )}

              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-white border border-gray-100 flex items-center justify-center shadow-sm">
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
                  <h3 className="font-bold text-gray-900 text-lg">{platform.name}</h3>
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
  );
}


/** Guided onboarding wizard — flows from OAuth callback through full setup */

const WIZARD_STEPS = [
  { key: 'connect', label: 'Connect', icon: Shield },
  { key: 'discover', label: 'Discover', icon: Globe },
  { key: 'protect', label: 'Protect', icon: Shield },
  { key: 'backup', label: 'First Backup', icon: Shield },
  { key: 'ready', label: 'Ready', icon: CheckCircle },
];

export function OnboardCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [step, setStep] = useState(0); // 0=connecting, 1=discover, 2=protect, 3=backup, 4=ready
  const [error, setError] = useState<string | null>(null);
  const [resultData, setResultData] = useState<any>(null);
  const [discoveryResults, setDiscoveryResults] = useState<any>(null);
  const [slaPolicies, setSlaPolicies] = useState<any[]>([]);
  const [selectedSla, setSelectedSla] = useState<number | null>(null);
  const [backupStatus, setBackupStatus] = useState<string>('pending');
  const [protecting, setProtecting] = useState(false);
  const [_backingUp, setBackingUp] = useState(false);

  // Workload toggles
  const [availableWorkloads, setAvailableWorkloads] = useState<any[]>([]);
  const [selectedWorkloads, setSelectedWorkloads] = useState<Set<string>>(new Set(['exchange', 'entra_id', 'sharepoint']));
  const [discovering, setDiscovering] = useState(false);
  const [backupWorkloads, setBackupWorkloads] = useState<Set<string>>(new Set());
  const [backupProgress, setBackupProgress] = useState<Record<string, string>>({});

  // Step 0: Process OAuth callback
  useEffect(() => {
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
      // Pre-select recommended workloads
      const recommended = (data.workloads || [])
        .filter((w: any) => w.recommended)
        .map((w: any) => w.key);
      setSelectedWorkloads(new Set(recommended));
    }).catch(() => {});

    if (adminConsent && tenant) {
      api.get<any>(`/onboard/callback?admin_consent=${adminConsent}&tenant=${tenant}&state=${state || ''}`)
        .then((data: any) => {
          if (data.success) {
            setResultData(data);
            if (data.discovery) setDiscoveryResults(data.discovery);
            setStep(1); // Move to discover
            // Load SLA policies
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

  const toggleBackupWorkload = (key: string) => {
    setBackupWorkloads(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

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
      setStep(3); // Move to first backup
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
    setStep(4);
    setBackingUp(false);
  };

  // Get discovery data from result
  const disc = discoveryResults || resultData?.discovery?.results || resultData?.discovery;
  const tenantName = resultData?.tenant_name || searchParams.get('tenant_name') || 'Your Organization';
  const totalObjects = disc ? (disc.mailboxes || 0) + (disc.onedrives || 0) + (disc.sites || 0) + (disc.teams || 0) + (disc.entra_objects ? 1 : 0) : 0;

  // Error state
  if (error) {
    return (
      <div className="max-w-lg mx-auto text-center py-16">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <XCircle className="w-8 h-8 text-red-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Connection Failed</h2>
        <p className="text-red-600 mb-6">{error}</p>
        <div className="flex items-center justify-center gap-3">
          <button onClick={() => navigate('/onboard')} className="px-6 py-2.5 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700">Try Again</button>
          <button onClick={() => navigate('/')} className="px-6 py-2.5 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200">Dashboard</button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-8">
      {/* Progress bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          {WIZARD_STEPS.map((s, i) => (
            <div key={s.key} className="flex items-center gap-1.5">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                i < step ? 'bg-green-500 text-white' :
                i === step ? 'bg-blue-600 text-white ring-4 ring-blue-100' :
                'bg-gray-200 text-gray-500'
              }`}>
                {i < step ? <CheckCircle className="w-4 h-4" /> : i + 1}
              </div>
              <span className={`text-xs font-medium hidden sm:block ${i <= step ? 'text-gray-900' : 'text-gray-400'}`}>{s.label}</span>
              {i < WIZARD_STEPS.length - 1 && <div className={`w-8 sm:w-16 h-0.5 mx-1 ${i < step ? 'bg-green-500' : 'bg-gray-200'}`} />}
            </div>
          ))}
        </div>
      </div>

      {/* Step 0: Connecting */}
      {step === 0 && (
        <div className="text-center py-12">
          <Loader2 className="w-12 h-12 animate-spin text-blue-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900">Connecting to Microsoft 365...</h2>
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
            <h2 className="text-2xl font-bold text-gray-900">Connected to {tenantName}</h2>
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
                      ? 'border-blue-400 bg-blue-50/50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                    isSelected ? 'border-blue-500 bg-blue-500' : 'border-gray-300'
                  }`}>
                    {isSelected && <CheckCircle className="w-3.5 h-3.5 text-white" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-900 text-sm">{wl.label}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        wl.speed === 'fast' ? 'bg-green-100 text-green-700' :
                        wl.speed === 'medium' ? 'bg-amber-100 text-amber-700' :
                        'bg-gray-100 text-gray-600'
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
                  className="px-4 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition-colors flex items-center gap-2"
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
            <h2 className="text-2xl font-bold text-gray-900">Choose Protection Level</h2>
            <p className="text-gray-500 mt-1">How often should we back up your data?</p>
          </div>

          <div className="space-y-3 mb-6">
            {slaPolicies.length > 0 ? slaPolicies.map((sla: any) => (
              <button
                key={sla.id}
                onClick={() => setSelectedSla(sla.id)}
                className={`w-full p-4 rounded-xl border-2 text-left transition-all ${
                  selectedSla === sla.id
                    ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-bold text-gray-900">{sla.name}</div>
                    <div className="text-sm text-gray-500">
                      Every {sla.backup_frequency_hours}h • {sla.retention_days} day retention
                      {sla.worm_enabled ? ' • WORM locked' : ''}
                    </div>
                  </div>
                  <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${
                    selectedSla === sla.id ? 'border-blue-500 bg-blue-500' : 'border-gray-300'
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
            <h2 className="text-2xl font-bold text-gray-900">Run Your First Backup</h2>
            <p className="text-gray-500 mt-1">Select workloads to back up now. Exchange is fastest for a quick verify.</p>
          </div>

          {backupStatus === 'pending' && (
            <>
              <div className="space-y-2 mb-4">
                {Array.from(selectedWorkloads).map(wlKey => {
                  const wl = availableWorkloads.find((w: any) => w.key === wlKey) || { key: wlKey, label: wlKey, speed: '?' };
                  const isChecked = backupWorkloads.has(wlKey);
                  return (
                    <button
                      key={wlKey}
                      onClick={() => toggleBackupWorkload(wlKey)}
                      className={`w-full p-3 rounded-xl border-2 text-left transition-all flex items-center gap-3 ${
                        isChecked ? 'border-green-400 bg-green-50/50' : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                        isChecked ? 'border-green-500 bg-green-500' : 'border-gray-300'
                      }`}>
                        {isChecked && <CheckCircle className="w-3.5 h-3.5 text-white" />}
                      </div>
                      <span className="font-medium text-sm text-gray-900">{wl.label}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ml-auto ${
                        wl.speed === 'fast' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                      }`}>
                        ~{wl.est_seconds || '?'}s
                      </span>
                    </button>
                  );
                })}
              </div>
              <button
                onClick={handleFirstBackup}
                disabled={backupWorkloads.size === 0 && selectedWorkloads.size === 0}
                className="w-full py-3 bg-green-600 text-white rounded-xl font-semibold hover:bg-green-700 transition-colors flex items-center justify-center gap-2"
              >
                <Shield className="w-5 h-5" />
                Backup {backupWorkloads.size > 0 ? backupWorkloads.size : selectedWorkloads.size} Workload(s) Now
              </button>
            </>
          )}

          {backupStatus === 'running' && (
            <div className="space-y-2">
              {Object.entries(backupProgress).map(([wl, status]) => (
                <div key={wl} className="flex items-center gap-3 p-3 rounded-xl border border-gray-200">
                  {status === 'pending' && <div className="w-5 h-5 rounded-full border-2 border-gray-300" />}
                  {status === 'running' && <Loader2 className="w-5 h-5 animate-spin text-blue-500" />}
                  {status === 'done' && <CheckCircle className="w-5 h-5 text-green-500" />}
                  {status === 'failed' && <XCircle className="w-5 h-5 text-red-500" />}
                  <span className="font-medium text-sm capitalize">{wl.replace('_', ' ')}</span>
                  <span className={`ml-auto text-xs font-medium ${
                    status === 'done' ? 'text-green-600' :
                    status === 'running' ? 'text-blue-600' :
                    status === 'failed' ? 'text-red-600' : 'text-gray-400'
                  }`}>
                    {status === 'done' ? 'Complete ✓' : status === 'running' ? 'Backing up...' : status === 'failed' ? 'Failed' : 'Waiting'}
                  </span>
                </div>
              ))}
            </div>
          )}

          <button
            onClick={() => setStep(4)}
            className="mt-4 w-full text-sm text-gray-400 hover:text-gray-600 text-center"
          >
            Skip — I'll run it later
          </button>
        </div>
      )}

      {/* Step 4: Ready! */}
      {step === 4 && (
        <div className="text-center">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4 animate-bounce">
            <CheckCircle className="w-10 h-10 text-green-600" />
          </div>
          <h2 className="text-3xl font-bold text-gray-900 mb-2">You're Protected! 🎉</h2>
          <p className="text-gray-500 mb-2">{tenantName} is now backed up with Shieldio.</p>

          <div className="bg-gray-50 rounded-xl p-4 mb-6 text-sm text-left max-w-md mx-auto">
            <div className="font-semibold text-gray-900 mb-2">What happens next:</div>
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
              onClick={() => navigate('/')}
              className="px-6 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              Go to Dashboard <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => navigate('/recovery')}
              className="px-6 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition-colors"
            >
              Recovery Dashboard
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
