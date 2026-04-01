import { useState, useEffect } from 'react';
import { Mail, HardDrive, Globe, KeyRound, MessageSquare, Shield, CheckCircle, XCircle, Loader2, ChevronRight, ChevronDown, ExternalLink, Zap, Clock, Calendar, ShieldCheck } from 'lucide-react';
import { api } from '../api/client';

interface OnboardingWizardProps {
  onComplete: () => void;
  onCancel: () => void;
}

interface DiscoveryResult {
  mailboxes: number;
  onedrives: number;
  sites: number;
  teams: number;
  entra_objects: number;
  removed: number;
  errors: string[];
}

interface PermissionStatus {
  all_backup_ready: boolean;
  consent_url: string;
  workloads: Record<string, { backup: boolean; restore: boolean | null; missing_backup: string[]; missing_restore: string[] }>;
}

const WORKLOADS = [
  { key: 'exchange', label: 'Exchange', desc: 'Mailboxes, calendars, contacts', icon: Mail, color: 'blue' },
  { key: 'onedrive', label: 'OneDrive', desc: 'Files and folders', icon: HardDrive, color: 'purple' },
  { key: 'sharepoint', label: 'SharePoint', desc: 'Sites, lists, documents', icon: Globe, color: 'green' },
  { key: 'teams', label: 'Teams', desc: 'Channels, messages, files', icon: MessageSquare, color: 'pink' },
  { key: 'entra_id', label: 'Entra ID', desc: 'Users, groups, policies', icon: KeyRound, color: 'amber' },
] as const;

const FREQUENCIES = [
  { hours: 24, label: 'Daily', desc: 'Recommended for most workloads', icon: Calendar },
  { hours: 4, label: 'Every 4 hours', desc: 'For critical data', icon: Zap },
  { hours: 12, label: 'Every 12 hours', desc: 'Balanced frequency', icon: Clock },
];

const RETENTION_OPTIONS = [30, 60, 90, 180, 365];

export default function OnboardingWizard({ onComplete, onCancel }: OnboardingWizardProps) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ name: '', ms_tenant_id: '', client_id: '', client_secret: '' });
  const [tenantId, setTenantId] = useState<number | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [discovering, setDiscovering] = useState(false);
  const [discovery, setDiscovery] = useState<DiscoveryResult | null>(null);
  const [selectedWorkloads, setSelectedWorkloads] = useState<Set<string>>(new Set(['exchange', 'onedrive', 'sharepoint', 'teams', 'entra_id']));
  const [frequency, setFrequency] = useState(24);
  const [retention, setRetention] = useState(30);
  const [autoBackup, setAutoBackup] = useState(true);
  const [protecting, setProtecting] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const [permissions, setPermissions] = useState<PermissionStatus | null>(null);
  const [checkingPerms, setCheckingPerms] = useState(false);
  const [error, setError] = useState('');

  // Step 2: Auto-discover when entering step 2
  useEffect(() => {
    if (step === 2 && tenantId && !discovery && !discovering) {
      runSetup();
    }
  }, [step, tenantId]);

  const runSetup = async () => {
    if (!tenantId) return;
    setDiscovering(true);
    setError('');
    try {
      const result: any = await api.post(`/tenants/${tenantId}/setup`);
      if (result.test && !result.test.success) {
        setError(`Connection failed: ${result.test.message}`);
        setStep(1);
        setTestResult({ success: false, message: result.test.message });
      } else if (result.discovery) {
        setDiscovery(result.discovery);
        // Check permissions after discovery
        checkPermissions();
      }
    } catch (err: any) {
      setError(`Setup failed: ${err.message}`);
    } finally {
      setDiscovering(false);
    }
  };

  const checkPermissions = async () => {
    if (!tenantId) return;
    setCheckingPerms(true);
    try {
      const result: any = await api.get(`/tenants/${tenantId}/permissions`);
      if (!result.error) {
        setPermissions(result);
      }
    } catch {
      // Permission check is optional — don't block onboarding
    } finally {
      setCheckingPerms(false);
    }
  };

  const handleStep1Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setConnecting(true);
    setError('');
    setTestResult(null);

    try {
      // Create tenant
      const tenant: any = await api.post('/tenants/', form);
      setTenantId(tenant.id);

      // Test connection
      const test: any = await api.post(`/tenants/${tenant.id}/test`);
      setTestResult(test);

      if (test.success) {
        setTimeout(() => setStep(2), 600);
      } else {
        setError(`Connection failed: ${test.message}`);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create tenant');
    } finally {
      setConnecting(false);
    }
  };

  const handleProtect = async () => {
    if (!tenantId) return;
    setProtecting(true);
    setError('');

    try {
      await api.post('/sla-policies/quick-protect', {
        tenant_id: tenantId,
        workload_types: Array.from(selectedWorkloads),
        frequency_hours: frequency,
        retention_days: retention,
      });
      onComplete();
    } catch (err: any) {
      setError(`Protection failed: ${err.message}`);
    } finally {
      setProtecting(false);
    }
  };

  const toggleWorkload = (key: string) => {
    setSelectedWorkloads(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const getWorkloadCount = (key: string) => {
    if (!discovery) return 0;
    switch (key) {
      case 'exchange': return discovery.mailboxes;
      case 'onedrive': return discovery.onedrives;
      case 'sharepoint': return discovery.sites;
      case 'teams': return discovery.teams || 0;
      case 'entra_id': return discovery.entra_objects;
      default: return 0;
    }
  };

  const totalProtected = WORKLOADS
    .filter(w => selectedWorkloads.has(w.key))
    .reduce((sum, w) => sum + getWorkloadCount(w.key), 0);

  const colorMap: Record<string, { bg: string; border: string; text: string; ring: string }> = {
    blue: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', ring: 'ring-blue-400' },
    purple: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', ring: 'ring-purple-400' },
    green: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', ring: 'ring-green-400' },
    pink: { bg: 'bg-pink-50', border: 'border-pink-200', text: 'text-pink-700', ring: 'ring-pink-400' },
    amber: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', ring: 'ring-amber-400' },
  };

  return (
    <div className="bg-card rounded-xl border shadow-lg overflow-hidden mb-6">
      {/* Progress Header */}
      <div className="bg-muted/50 border-b px-6 py-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-foreground">Connect SaaS Platform</h2>
          <span className="text-sm text-muted-foreground">Step {step} of 3</span>
        </div>
        <div className="flex gap-1">
          {[1, 2, 3].map(s => (
            <div key={s} className={`h-1.5 flex-1 rounded-full transition-all ${
              s <= step ? 'bg-blue-600' : 'bg-gray-200'
            }`} />
          ))}
        </div>
        <div className="flex justify-between mt-2 text-xs text-muted-foreground">
          <span className={step >= 1 ? 'text-blue-600 font-medium' : ''}>Connect</span>
          <span className={step >= 2 ? 'text-blue-600 font-medium' : ''}>Discover</span>
          <span className={step >= 3 ? 'text-blue-600 font-medium' : ''}>Protect</span>
        </div>
      </div>

      <div className="p-6">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 mb-4 text-sm flex items-center gap-2">
            <XCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* ── STEP 1: Connect ── */}
        {step === 1 && (
          <div>
            <p className="text-muted-foreground text-sm mb-4">
              Enter your Azure AD App Registration credentials to connect your SaaS platform.
            </p>

            {/* Setup Guide */}
            <button
              onClick={() => setShowGuide(!showGuide)}
              className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700 mb-4"
            >
              {showGuide ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              How to create an Azure AD App Registration
            </button>

            {showGuide && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 text-sm text-blue-800 space-y-2">
                <p className="font-medium">Quick Setup Guide:</p>
                <ol className="list-decimal list-inside space-y-1.5 text-blue-700">
                  <li>Go to <a href="https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade" target="_blank" rel="noopener noreferrer" className="underline inline-flex items-center gap-1">Azure Portal &gt; App Registrations <ExternalLink className="w-3 h-3" /></a></li>
                  <li>Click "New registration" &gt; Name it "Shieldio Backup" &gt; Register</li>
                  <li>Go to "API permissions" &gt; Add: <code className="bg-blue-100 px-1 rounded">Mail.Read</code>, <code className="bg-blue-100 px-1 rounded">Files.Read.All</code>, <code className="bg-blue-100 px-1 rounded">Sites.Read.All</code>, <code className="bg-blue-100 px-1 rounded">User.Read.All</code>, <code className="bg-blue-100 px-1 rounded">Directory.Read.All</code></li>
                  <li>Click "Grant admin consent"</li>
                  <li>Go to "Certificates & secrets" &gt; New client secret &gt; Copy the value</li>
                  <li>Copy the Application (Client) ID from the Overview page</li>
                </ol>
              </div>
            )}

            <form onSubmit={handleStep1Submit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-1">Organization Name</label>
                  <input
                    type="text" required value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                    placeholder="Contoso Inc."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-ring focus:border-ring"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-1">Azure AD Tenant ID</label>
                  <input
                    type="text" required value={form.ms_tenant_id}
                    onChange={e => setForm({ ...form, ms_tenant_id: e.target.value })}
                    placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-ring focus:border-ring font-mono text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-1">Application (Client) ID</label>
                  <input
                    type="text" required value={form.client_id}
                    onChange={e => setForm({ ...form, client_id: e.target.value })}
                    placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-ring focus:border-ring font-mono text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-1">Client Secret</label>
                  <input
                    type="password" required value={form.client_secret}
                    onChange={e => setForm({ ...form, client_secret: e.target.value })}
                    placeholder="Client secret value"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-ring focus:border-ring"
                  />
                </div>
              </div>

              {testResult && (
                <div className={`flex items-center gap-2 text-sm p-3 rounded-lg ${
                  testResult.success
                    ? 'bg-green-50 border border-green-200 text-green-700'
                    : 'bg-red-50 border border-red-200 text-red-700'
                }`}>
                  {testResult.success ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                  {testResult.message}
                </div>
              )}

              <div className="flex justify-between pt-2">
                <button type="button" onClick={onCancel} className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground">
                  Cancel
                </button>
                <button
                  type="submit" disabled={connecting}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {connecting ? <><Loader2 className="w-4 h-4 animate-spin" /> Connecting...</> : <>Connect & Verify <ChevronRight className="w-4 h-4" /></>}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* ── STEP 2: Discover ── */}
        {step === 2 && (
          <div>
            {discovering ? (
              <div className="text-center py-12">
                <Loader2 className="w-10 h-10 animate-spin text-blue-600 mx-auto mb-4" />
                <p className="text-lg font-medium text-muted-foreground">Discovering workloads...</p>
                <p className="text-sm text-muted-foreground mt-1">Scanning mailboxes, drives, sites, and directory objects</p>
              </div>
            ) : discovery ? (
              <div>
                <p className="text-muted-foreground text-sm mb-4">
                  Select which workloads to protect. All discovered workloads are enabled by default.
                </p>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  {WORKLOADS.map(w => {
                    const count = getWorkloadCount(w.key);
                    const selected = selectedWorkloads.has(w.key);
                    const c = colorMap[w.color];
                    const Icon = w.icon;
                    return (
                      <button
                        key={w.key}
                        onClick={() => toggleWorkload(w.key)}
                        disabled={count === 0}
                        className={`relative p-4 rounded-xl border-2 text-left transition-all ${
                          count === 0
                            ? 'border-border bg-muted/50 opacity-50 cursor-not-allowed'
                            : selected
                              ? `${c.border} ${c.bg} ring-2 ${c.ring}`
                              : 'border-border bg-card hover:border-border'
                        }`}
                      >
                        {count > 0 && (
                          <div className={`absolute top-2 right-2 w-5 h-5 rounded-full flex items-center justify-center ${
                            selected ? 'bg-green-500' : 'bg-gray-200'
                          }`}>
                            {selected && <CheckCircle className="w-4 h-4 text-foreground" />}
                          </div>
                        )}
                        <Icon className={`w-6 h-6 mb-2 ${count > 0 ? c.text : 'text-muted-foreground'}`} />
                        <p className={`text-2xl font-bold ${count > 0 ? 'text-foreground' : 'text-muted-foreground'}`}>{count}</p>
                        <p className="text-sm font-medium text-muted-foreground">{w.label}</p>
                        <p className="text-xs text-muted-foreground">{w.desc}</p>
                      </button>
                    );
                  })}
                </div>

                {discovery.errors?.length > 0 && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4 text-sm text-yellow-800">
                    <p className="font-medium mb-1">Warnings:</p>
                    {discovery.errors.map((err, i) => <p key={i}>{err}</p>)}
                  </div>
                )}

                {/* Permission Status */}
                {permissions && !permissions.all_backup_ready && (
                  <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 mb-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <ShieldCheck className="w-5 h-5 text-orange-600" />
                        <p className="text-sm font-semibold text-orange-800">Missing Permissions</p>
                      </div>
                      <a
                        href={permissions.consent_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1.5 bg-orange-600 text-foreground rounded-lg text-xs font-medium hover:bg-orange-700 flex items-center gap-1"
                      >
                        <ExternalLink className="w-3 h-3" /> Grant Permissions
                      </a>
                    </div>
                    <div className="space-y-1">
                      {Object.entries(permissions.workloads).map(([wl, status]) => {
                        if (status.backup) return null;
                        return (
                          <div key={wl} className="flex items-center gap-2 text-xs text-orange-700">
                            <XCircle className="w-3 h-3" />
                            <span className="font-medium capitalize">{wl.replace('_', ' ')}</span>
                            <span>— missing: {status.missing_backup.join(', ')}</span>
                          </div>
                        );
                      })}
                    </div>
                    <button
                      onClick={checkPermissions}
                      disabled={checkingPerms}
                      className="mt-2 text-xs text-orange-600 hover:text-orange-800 underline"
                    >
                      {checkingPerms ? 'Checking...' : 'Re-check permissions'}
                    </button>
                  </div>
                )}

                {permissions && permissions.all_backup_ready && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <p className="text-sm text-green-700 font-medium">All backup permissions granted</p>
                  </div>
                )}

                <div className="flex justify-between pt-2">
                  <button onClick={() => { setStep(1); setDiscovery(null); }} className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground">
                    Back
                  </button>
                  <button
                    onClick={() => setStep(3)}
                    disabled={selectedWorkloads.size === 0}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                  >
                    Configure Protection <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center py-12">
                <XCircle className="w-10 h-10 text-red-400 mx-auto mb-4" />
                <p className="text-muted-foreground">Discovery failed. Please go back and check your credentials.</p>
                <button onClick={() => setStep(1)} className="mt-4 px-4 py-2 bg-muted rounded-lg text-sm hover:bg-accent">
                  Back to Credentials
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── STEP 3: Protect ── */}
        {step === 3 && (
          <div>
            <p className="text-muted-foreground text-sm mb-4">
              Choose a backup schedule and start protecting your data.
            </p>

            {/* Frequency Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-muted-foreground mb-2">Backup Frequency</label>
              <div className="grid grid-cols-3 gap-3">
                {FREQUENCIES.map(f => {
                  const Icon = f.icon;
                  return (
                    <button
                      key={f.hours}
                      onClick={() => setFrequency(f.hours)}
                      className={`p-3 rounded-lg border-2 text-left transition-all ${
                        frequency === f.hours
                          ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                          : 'border-border hover:border-border'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Icon className="w-4 h-4 text-blue-600" />
                        <span className="text-sm font-medium">{f.label}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">{f.desc}</p>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Retention */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-muted-foreground mb-2">Retention Period</label>
              <div className="flex gap-2">
                {RETENTION_OPTIONS.map(days => (
                  <button
                    key={days}
                    onClick={() => setRetention(days)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      retention === days
                        ? 'bg-blue-600 text-white'
                        : 'bg-muted text-muted-foreground hover:bg-accent'
                    }`}
                  >
                    {days} days
                  </button>
                ))}
              </div>
            </div>

            {/* Auto-backup */}
            <label className="flex items-center gap-3 mb-6 cursor-pointer">
              <input
                type="checkbox" checked={autoBackup}
                onChange={e => setAutoBackup(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-ring"
              />
              <span className="text-sm text-muted-foreground">Start first backup immediately after setup</span>
            </label>

            {/* Summary */}
            <div className="bg-muted/50 rounded-lg border p-4 mb-6">
              <p className="text-sm font-medium text-muted-foreground mb-2">Protection Summary</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                {WORKLOADS.filter(w => selectedWorkloads.has(w.key)).map(w => {
                  const Icon = w.icon;
                  const c = colorMap[w.color];
                  return (
                    <div key={w.key} className={`flex items-center gap-2 ${c.text}`}>
                      <Icon className="w-4 h-4" />
                      <span>{getWorkloadCount(w.key)} {w.label}</span>
                    </div>
                  );
                })}
              </div>
              <div className="mt-3 pt-3 border-t border-border flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Total objects: <strong>{totalProtected}</strong></span>
                <span className="text-muted-foreground">Schedule: <strong>Every {frequency}h</strong> &bull; Retain: <strong>{retention} days</strong></span>
              </div>
            </div>

            <div className="flex justify-between">
              <button onClick={() => setStep(2)} className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground">
                Back
              </button>
              <button
                onClick={handleProtect} disabled={protecting || totalProtected === 0}
                className="px-6 py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
              >
                {protecting ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Activating Protection...</>
                ) : (
                  <><Shield className="w-4 h-4" /> Start Protection</>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
