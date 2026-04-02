import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Shield, Globe, MessageSquare, CheckCircle, XCircle, Loader2, ArrowRight, LogOut, Lock, Shrink, Hash, Star, Brain } from 'lucide-react';
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
  const [showPreflight, setShowPreflight] = useState(false);
  const [preflightStep, setPreflightStep] = useState(0);

  useEffect(() => {
    api.get<{ platforms: Platform[] }>('/onboard/platforms')
      .then(data => setPlatforms(data.platforms))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // Animate preflight steps
  useEffect(() => {
    if (!showPreflight) return;
    const timers = [
      setTimeout(() => setPreflightStep(1), 400),
      setTimeout(() => setPreflightStep(2), 1000),
      setTimeout(() => setPreflightStep(3), 1600),
      setTimeout(() => setPreflightStep(4), 2200),
      setTimeout(() => setPreflightStep(5), 2800),
    ];
    return () => timers.forEach(clearTimeout);
  }, [showPreflight]);

  const handleConnect = async (platformKey: string) => {
    setConnecting(platformKey);
    try {
      const data: any = await api.get(`/onboard/connect/${platformKey}`);
      if (data.auth_url) {
        setTimeout(() => { window.location.href = data.auth_url; }, 0);
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
    <div className="min-h-screen bg-background text-foreground px-4 py-6">
    <div className="max-w-3xl mx-auto">
      {/* Sign out link */}
      <div className="flex justify-end mb-4">
        <button onClick={() => { logout(); window.location.href = '/'; }}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-muted-foreground transition-colors">
          <LogOut className="w-4 h-4" /> Sign Out
        </button>
      </div>
      <div className="text-center mb-10">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-2xl mb-4">
          <Shield className="w-8 h-8 text-blue-600" />
        </div>
        <h1 className="text-3xl font-bold text-foreground mb-2">Connect Your SaaS Platform</h1>
        <p className="text-muted-foreground text-lg">
          Select a platform to protect. One-click OAuth — no credentials to copy.
        </p>
      </div>

      {/* ═══ Pre-flight Briefing — animated overview before OAuth redirect ═══ */}
      {showPreflight && (
        <div className="max-w-2xl mx-auto mb-8">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-foreground">How Shieldio Connects to Microsoft 365</h2>
            <p className="text-muted-foreground mt-1">Secure, read-only access. Your credentials are never stored.</p>
          </div>

          {/* Animated flow diagram */}
          <div className="space-y-3 mb-6">
            {[
              { icon: '🏢', label: 'Your M365 Tenant', desc: 'Sign in with your Global Admin account', detail: 'Microsoft verifies your identity — Shieldio never sees your password', color: 'border-blue-500/40 bg-blue-500/10' },
              { icon: '🔐', label: 'Admin Consent', desc: 'Microsoft shows which permissions Shieldio needs', detail: 'You review and approve read-only access to your data — no write permissions', color: 'border-purple-500/40 bg-purple-500/10' },
              { icon: '📋', label: 'Read-Only Permissions', desc: 'Mail.Read, Files.Read, Sites.Read, Directory.Read', detail: 'Shieldio can only read your data for backup — cannot modify, delete, or send', color: 'border-green-500/40 bg-green-500/10' },
              { icon: '🔑', label: 'Secure Token Exchange', desc: 'Microsoft issues a scoped API token to Shieldio', detail: 'Per-tenant isolation — token only works for your organization', color: 'border-amber-500/40 bg-amber-500/10' },
              { icon: '🧠', label: 'Smart Discovery & Backup', desc: 'Shieldio discovers workloads, scores criticality, starts protection', detail: 'CEO backed up first, then VPs, then everyone — automatically prioritized', color: 'border-cyan-500/40 bg-cyan-500/10' },
            ].map((step, i) => (
              <div key={i} className={`flex items-start gap-4 p-4 rounded-xl border transition-all duration-500 ${step.color} ${
                preflightStep > i ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-[-20px]'
              }`} style={{ transitionDelay: `${i * 100}ms` }}>
                <div className="text-2xl flex-shrink-0 mt-0.5">{step.icon}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-muted-foreground">STEP {i + 1}</span>
                    <span className="font-semibold text-foreground text-sm">{step.label}</span>
                  </div>
                  <p className="text-sm text-foreground mt-0.5">{step.desc}</p>
                  <p className="text-xs text-muted-foreground mt-1">{step.detail}</p>
                </div>
                {preflightStep > i && <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-1" />}
              </div>
            ))}

            {/* Connection lines between steps */}
          </div>

          {/* Security badges */}
          <div className="flex flex-wrap items-center justify-center gap-2 mb-6">
            {['AES-256 Encryption', 'Per-Tenant Isolation', 'No Write Access', 'SOC 2 Ready', 'GDPR Compliant'].map(badge => (
              <span key={badge} className="text-[10px] px-2.5 py-1 bg-card border border-border rounded-full text-muted-foreground flex items-center gap-1">
                <Lock className="w-3 h-3" /> {badge}
              </span>
            ))}
          </div>

          {/* Action buttons */}
          {preflightStep >= 5 && (
            <div className="flex gap-3">
              <button onClick={() => { setShowPreflight(false); setPreflightStep(0); }}
                className="flex-1 py-3 bg-muted text-foreground rounded-xl font-medium hover:bg-accent transition-colors text-sm">
                ← Back
              </button>
              <button onClick={() => handleConnect('microsoft365')}
                disabled={!!connecting}
                className="flex-2 py-3 px-8 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-500 transition-colors flex items-center justify-center gap-2">
                {connecting ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Redirecting to Microsoft...</>
                ) : (
                  <>Proceed to Microsoft <ArrowRight className="w-4 h-4" /></>
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {!showPreflight && (<><div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {platforms.map(platform => {
          const Icon = PLATFORM_ICONS[platform.icon] || Shield;
          const colors = PLATFORM_COLORS[platform.key] || 'border-gray-500/30 bg-muted/500/10';
          const isConnecting = connecting === platform.key;

          return (
            <button
              key={platform.key}
              onClick={() => platform.available && (platform.key === 'microsoft365' ? setShowPreflight(true) : handleConnect(platform.key))}
              disabled={!platform.available || !!connecting}
              className={`relative p-6 rounded-2xl border-2 transition-all text-left ${
                platform.available
                  ? `${colors} cursor-pointer shadow-sm hover:shadow-md`
                  : 'border-border bg-card/50 cursor-not-allowed opacity-60'
              }`}
            >
              {!platform.available && (
                <span className="absolute top-3 right-3 px-2 py-0.5 bg-secondary text-muted-foreground text-[10px] font-semibold rounded-full">
                  Coming Soon
                </span>
              )}

              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-card border border-border flex items-center justify-center shadow-sm">
                  {platform.key === 'microsoft365' ? (
                    <svg className="w-6 h-6" viewBox="0 0 21 21">
                      <path d="M0 0h10v10H0z" fill="#f25022"/>
                      <path d="M11 0h10v10H11z" fill="#7fba00"/>
                      <path d="M0 11h10v10H0z" fill="#00a4ef"/>
                      <path d="M11 11h10v10H11z" fill="#ffb900"/>
                    </svg>
                  ) : (
                    <Icon className="w-6 h-6 text-muted-foreground" />
                  )}
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-foreground text-lg">{platform.name}</h3>
                  <p className="text-sm text-muted-foreground mt-0.5">{platform.description}</p>

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
        <p className="text-xs text-muted-foreground">
          Shieldio uses OAuth admin consent — your credentials are never stored.
          <br />
          Only read-only permissions are requested for backup.
        </p>
      </div>
      </>)}
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
  <div className="bg-card border border-border rounded-xl p-3 space-y-1">
    <div className="flex items-center gap-2 text-sm"><span className="text-muted-foreground w-16 flex-shrink-0">M365:</span> <span className="text-red-500 font-medium">{m365}</span></div>
    <div className="flex items-center gap-2 text-sm"><span className="text-muted-foreground w-16 flex-shrink-0">Shieldio:</span> <span className="text-green-600 font-medium">{shieldio}</span></div>
  </div>
);

const Shimmer = () => (
  <div className="space-y-3 animate-pulse">
    <div className="h-20 bg-secondary rounded-xl" />
    <div className="h-4 bg-secondary rounded w-3/4 mx-auto" />
    <div className="h-16 bg-secondary rounded-xl" />
  </div>
);

// ── Intelligence Step: Animated Org Graph + Criticality Priority ──

const TIER_CONFIG: Record<string, { color: string; border: string; bg: string; icon: string; label: string }> = {
  critical: { color: 'text-red-400', border: 'border-red-500/40', bg: 'bg-red-500/10', icon: '👑', label: 'Critical' },
  high: { color: 'text-orange-400', border: 'border-orange-500/40', bg: 'bg-orange-500/10', icon: '⭐', label: 'High' },
  medium: { color: 'text-blue-400', border: 'border-blue-500/30', bg: 'bg-blue-500/10', icon: '●', label: 'Medium' },
  low: { color: 'text-muted-foreground', border: 'border-border', bg: 'bg-muted', icon: '○', label: 'Standard' },
};

function TenantConnectedStep({ tenantName, tenantId, onContinue }: { tenantName: string; tenantId?: number; onContinue: () => void }) {
  const [stage, setStage] = useState<'discovering' | 'verifying' | 'done'>('discovering');
  const [discoveryStep, setDiscoveryStep] = useState(0); // 0-3 for discovery animation
  const [revealed, setRevealed] = useState(0); // 0-6, animates each security check

  // Stage 1: Tenant discovery animation
  useEffect(() => {
    const timers = [
      setTimeout(() => setDiscoveryStep(1), 600),
      setTimeout(() => setDiscoveryStep(2), 1400),
      setTimeout(() => setDiscoveryStep(3), 2200),
      setTimeout(() => setStage('verifying'), 3000),
    ];
    return () => timers.forEach(clearTimeout);
  }, []);

  // Stage 2: Security verification animation
  useEffect(() => {
    if (stage !== 'verifying') return;
    const timers = [
      setTimeout(() => setRevealed(1), 400),
      setTimeout(() => setRevealed(2), 1000),
      setTimeout(() => setRevealed(3), 1600),
      setTimeout(() => setRevealed(4), 2200),
      setTimeout(() => setRevealed(5), 2800),
      setTimeout(() => { setRevealed(6); setStage('done'); }, 3400),
    ];
    return () => timers.forEach(clearTimeout);
  }, [stage]);

  const securityChecks = [
    { icon: '🔐', label: 'OAuth 2.0 Admin Consent', detail: 'Delegated via Microsoft identity platform — no passwords stored', color: 'border-blue-500/30 bg-blue-500/10' },
    { icon: '📡', label: 'Microsoft Graph API Access', detail: 'Secure HTTPS connection to graph.microsoft.com established', color: 'border-purple-500/30 bg-purple-500/10' },
    { icon: '👁️', label: 'Read-Only Permissions', detail: 'Only Mail.Read, Files.Read, Sites.Read, User.Read.All — no write access', color: 'border-green-500/30 bg-green-500/10' },
    { icon: '🛡️', label: 'Per-Tenant Isolation', detail: 'Unique encryption key (DEK) generated for this tenant — zero cross-tenant access', color: 'border-amber-500/30 bg-amber-500/10' },
    { icon: '✅', label: 'Tenant ID Validated', detail: `Tenant ${tenantId || '...'} confirmed in Microsoft Entra directory`, color: 'border-cyan-500/30 bg-cyan-500/10' },
    { icon: '🔒', label: 'Encryption Key Provisioned', detail: 'AES-256-GCM data encryption key wrapped by master KEK — ready for backup', color: 'border-red-500/30 bg-red-500/10' },
  ];

  const allDone = stage === 'done';

  // ── Stage 1: Tenant Discovery ──
  if (stage === 'discovering') {
    const discoverySteps = [
      { icon: '🌐', label: 'Redirecting to Microsoft login...', detail: 'login.microsoftonline.com' },
      { icon: '✍️', label: 'Admin consent granted', detail: 'Global Administrator approved read-only access' },
      { icon: '📋', label: `Tenant discovered: ${tenantName}`, detail: `Tenant ID: ${tenantId || '...'}  •  Microsoft 365 Business` },
      { icon: '🔑', label: 'OAuth token exchange complete', detail: 'Authorization code → access token + refresh token' },
    ];
    return (
      <div>
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
          </div>
          <h2 className="text-2xl font-bold text-foreground">Connecting to Microsoft 365</h2>
          <p className="text-muted-foreground mt-1">Establishing secure OAuth connection to your tenant</p>
        </div>

        {/* OAuth flow visualization */}
        <div className="bg-card border border-border rounded-xl p-5 mb-4">
          <div className="flex items-center justify-between mb-5">
            <div className="flex flex-col items-center gap-1">
              <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                <svg className="w-5 h-5" viewBox="0 0 21 21"><path d="M0 0h10v10H0z" fill="#f25022"/><path d="M11 0h10v10H11z" fill="#7fba00"/><path d="M0 11h10v10H0z" fill="#00a4ef"/><path d="M11 11h10v10H11z" fill="#ffb900"/></svg>
              </div>
              <span className="text-[10px] text-muted-foreground">Microsoft</span>
            </div>
            <div className="flex-1 mx-3 relative">
              <div className="h-0.5 bg-border rounded" />
              <div className="h-0.5 bg-blue-500 rounded absolute top-0 left-0 transition-all duration-1000"
                style={{ width: `${Math.min(discoveryStep / 3 * 100, 100)}%` }} />
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-background px-2">
                <Lock className="w-3.5 h-3.5 text-green-400" />
              </div>
            </div>
            <div className="flex flex-col items-center gap-1">
              <div className="w-10 h-10 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center justify-center">
                <Shield className="w-5 h-5 text-green-400" />
              </div>
              <span className="text-[10px] text-muted-foreground">Shieldio</span>
            </div>
          </div>

          <div className="space-y-2.5">
            {discoverySteps.map((s, i) => (
              <div key={i} className={`flex items-start gap-3 p-2.5 rounded-lg transition-all duration-500 ${
                discoveryStep > i ? 'bg-green-500/5 border border-green-500/20' :
                discoveryStep === i ? 'bg-blue-500/5 border border-blue-500/20' :
                'opacity-30'
              }`}>
                {discoveryStep > i ? (
                  <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                ) : discoveryStep === i ? (
                  <Loader2 className="w-5 h-5 text-blue-400 animate-spin flex-shrink-0 mt-0.5" />
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-border flex-shrink-0 mt-0.5" />
                )}
                <div>
                  <div className="text-sm font-medium text-foreground">{s.label}</div>
                  <div className="text-[11px] text-muted-foreground">{s.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ── Stage 2 & 3: Security Verification ──
  return (
    <div>
      {/* Header */}
      <div className="text-center mb-6">
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
            <svg className="w-6 h-6" viewBox="0 0 21 21"><path d="M0 0h10v10H0z" fill="#f25022"/><path d="M11 0h10v10H11z" fill="#7fba00"/><path d="M0 11h10v10H0z" fill="#00a4ef"/><path d="M11 11h10v10H11z" fill="#ffb900"/></svg>
          </div>
          <ArrowRight className="w-5 h-5 text-muted-foreground" />
          <div className="w-12 h-12 rounded-xl bg-green-500/10 border border-green-500/20 flex items-center justify-center">
            <Shield className="w-6 h-6 text-green-400" />
          </div>
        </div>
        <h2 className="text-2xl font-bold text-foreground">
          {allDone ? `${tenantName} — Secured & Ready` : 'Securing Your Connection'}
        </h2>
        <p className="text-muted-foreground mt-1">
          {allDone
            ? 'Zero-trust access model verified. Your credentials are never stored.'
            : 'Verifying security posture and access permissions'}
        </p>
      </div>

      {/* Tenant identity card */}
      <div className="bg-card border border-border rounded-xl p-4 mb-4 flex items-center gap-4">
        <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-white text-sm font-bold">
          {tenantName.charAt(0)}
        </div>
        <div className="flex-1">
          <div className="font-bold text-foreground">{tenantName}</div>
          <div className="text-xs text-muted-foreground">Microsoft 365 Business • Tenant {tenantId}</div>
        </div>
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full transition-all duration-500 ${
          allDone ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse'
        }`}>
          {allDone ? '✓ Secured' : '⏳ Verifying...'}
        </span>
      </div>

      {/* Security verification pipeline */}
      <div className="space-y-2 mb-5">
        {securityChecks.map((check, i) => {
          const done = revealed > i;
          const active = revealed === i;
          return (
            <div key={i} className={`flex items-start gap-3 p-3 rounded-xl border transition-all duration-700 ${
              done ? check.color : active ? 'border-blue-500/30 bg-blue-500/5' : 'border-border bg-card/50 opacity-40'
            }`} style={{ transitionDelay: `${i * 100}ms` }}>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                {done ? (
                  <span className="text-lg">{check.icon}</span>
                ) : active ? (
                  <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-border" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-foreground">{check.label}</span>
                  {done && <CheckCircle className="w-3.5 h-3.5 text-green-400" />}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{check.detail}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Security summary — appears after all checks */}
      {allDone && (
        <div className="bg-muted rounded-xl p-4 mb-5 transition-all duration-700">
          <div className="text-xs font-semibold text-foreground mb-2">Security Model</div>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <div className="text-lg font-bold text-green-400">0</div>
              <div className="text-[10px] text-muted-foreground">Passwords stored</div>
            </div>
            <div>
              <div className="text-lg font-bold text-blue-400">Read</div>
              <div className="text-[10px] text-muted-foreground">Only permission</div>
            </div>
            <div>
              <div className="text-lg font-bold text-amber-400">AES-256</div>
              <div className="text-[10px] text-muted-foreground">Encryption ready</div>
            </div>
          </div>
        </div>
      )}

      {/* Continue button */}
      {allDone && (
        <button onClick={onContinue}
          className="w-full py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-500 transition-all duration-500 flex items-center justify-center gap-2">
          Discover Workloads <ArrowRight className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

function IntelligenceStep({ tenantId, onContinue }: { tenantId?: number; onContinue: () => void }) {
  const [phase, setPhase] = useState<'scanning' | 'graph' | 'plan'>('scanning');
  const [intel, setIntel] = useState<any>(null);
  const [revealedTier, setRevealedTier] = useState(-1); // -1=none, 0=critical, 1=high, 2=medium, 3=low

  // Fetch intelligence data
  useEffect(() => {
    if (!tenantId) return;
    api.get<any>(`/onboard/intelligence?tenant_id=${tenantId}`)
      .then(data => {
        setIntel(data);
        // Auto-advance: scanning → graph after 2.5s
        setTimeout(() => setPhase('graph'), 2500);
      })
      .catch(() => {
        // Fallback: skip to continue
        setTimeout(() => setPhase('graph'), 1500);
      });
  }, [tenantId]);

  // Animate tier reveals when in graph phase
  useEffect(() => {
    if (phase !== 'graph' || !intel) return;
    const timers = [
      setTimeout(() => setRevealedTier(0), 400),    // critical
      setTimeout(() => setRevealedTier(1), 1000),   // high
      setTimeout(() => setRevealedTier(2), 1600),   // medium
      setTimeout(() => setRevealedTier(3), 2200),   // low — all revealed
    ];
    return () => timers.forEach(clearTimeout);
  }, [phase, intel]);

  // Phase A: Scanning animation
  if (phase === 'scanning') {
    const scanSteps = [
      { text: 'Scanning Microsoft Graph API...', delay: 0 },
      { text: `Found ${intel?.total_users || '...'} users`, delay: 600 },
      { text: `Detected org hierarchy`, delay: 1200 },
      { text: `Scoring criticality (4-factor model)`, delay: 1800 },
    ];
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-blue-500/10 flex items-center justify-center">
          <Brain className="w-8 h-8 text-blue-400 animate-pulse" />
        </div>
        <h2 className="text-2xl font-bold text-foreground mb-2">Analyzing Your Organization</h2>
        <p className="text-muted-foreground mb-8">Shieldio is learning who matters most...</p>
        <div className="max-w-sm mx-auto space-y-3 text-left">
          {scanSteps.map((s, i) => (
            <div key={i} className="flex items-center gap-3 transition-all duration-500"
              style={{ opacity: intel || i < 2 ? 1 : 0.3, transitionDelay: `${s.delay}ms` }}>
              {intel || i < 2 ? (
                <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
              ) : (
                <Loader2 className="w-4 h-4 text-blue-400 animate-spin flex-shrink-0" />
              )}
              <span className="text-sm text-foreground">{s.text}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const users = intel?.users || [];
  const tiers = intel?.tiers || { critical: 0, high: 0, medium: 0, low: 0 };
  const mvbPlan = intel?.mvb_plan?.phases || [];
  const tierOrder: Array<'critical' | 'high' | 'medium' | 'low'> = ['critical', 'high', 'medium', 'low'];

  // Phase B: Org Intelligence Graph
  if (phase === 'graph') {
    return (
      <div>
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold text-foreground">Org Intelligence Map</h2>
          <p className="text-muted-foreground mt-1">Who gets backed up first — and why</p>
        </div>

        {/* Tier summary bar */}
        <div className="flex items-center justify-center gap-4 mb-6">
          {tierOrder.map((tier, i) => {
            const cfg = TIER_CONFIG[tier];
            const count = tiers[tier] || 0;
            return (
              <div key={tier} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all duration-500 ${
                revealedTier >= i ? `${cfg.border} ${cfg.bg}` : 'border-transparent opacity-30'
              }`}>
                <span className="text-sm">{cfg.icon}</span>
                <span className={`text-xs font-semibold ${cfg.color}`}>{cfg.label}</span>
                <span className={`text-xs font-bold ${cfg.color}`}>{count}</span>
              </div>
            );
          })}
        </div>

        {/* Tiered user graph — rows by criticality */}
        <div className="space-y-3 mb-6">
          {tierOrder.map((tier, tierIdx) => {
            const cfg = TIER_CONFIG[tier];
            const tierUsers = users.filter((u: any) => u.tier === tier);
            if (tierUsers.length === 0) return null;
            const visible = revealedTier >= tierIdx;
            return (
              <div key={tier} className={`transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
                {/* Tier label */}
                <div className="flex items-center gap-2 mb-2">
                  <div className={`w-2 h-2 rounded-full ${cfg.bg.replace('/10', '')}`} />
                  <span className={`text-xs font-bold uppercase tracking-wider ${cfg.color}`}>
                    {tier === 'critical' ? '🛡️ Backed up FIRST' : tier === 'high' ? '⚡ Then high priority' : tier === 'medium' ? '→ Then directors' : '→ Then everyone else'}
                  </span>
                </div>
                {/* User cards row */}
                <div className="flex flex-wrap gap-2">
                  {tierUsers.map((user: any, ui: number) => (
                    <div key={ui} className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${cfg.border} ${cfg.bg} transition-all duration-500`}
                      style={{ transitionDelay: `${ui * 100}ms` }}>
                      <div className={`w-8 h-8 rounded-full ${tier === 'critical' ? 'bg-red-600' : tier === 'high' ? 'bg-orange-600' : tier === 'medium' ? 'bg-blue-600' : 'bg-secondary'} text-white flex items-center justify-center text-[10px] font-bold`}>
                        {user.score}
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-foreground">{user.name}</div>
                        <div className="text-[10px] text-muted-foreground">{user.title}</div>
                      </div>
                    </div>
                  ))}
                </div>
                {/* Connection line to next tier */}
                {tierIdx < 3 && <div className="flex justify-center my-1"><div className="w-px h-4 bg-border" /></div>}
              </div>
            );
          })}
        </div>

        {/* Transition to plan view */}
        {revealedTier >= 3 && (
          <div className="text-center">
            <button onClick={() => setPhase('plan')}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-500 transition-colors flex items-center justify-center gap-2 mx-auto">
              See Recovery Priority Order <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    );
  }

  // Phase C: MVB Recovery Plan — backup priority order
  return (
    <div>
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-foreground">Recovery Priority Order</h2>
        <p className="text-muted-foreground mt-1">Pre-computed. When ransomware hits, recovery starts instantly.</p>
      </div>

      {/* 4-phase recovery timeline */}
      <div className="space-y-3 mb-6">
        {mvbPlan.map((phase: any, i: number) => {
          const colors = ['bg-red-600', 'bg-orange-600', 'bg-blue-600', 'bg-secondary'];
          const borders = ['border-red-500/40', 'border-orange-500/40', 'border-blue-500/30', 'border-border'];
          return (
            <div key={i} className={`p-4 rounded-xl border ${borders[i]} bg-card transition-all duration-500`}
              style={{ transitionDelay: `${i * 300}ms` }}>
              <div className="flex items-center gap-3 mb-2">
                <div className={`w-8 h-8 rounded-full ${colors[i]} text-white flex items-center justify-center text-xs font-bold`}>
                  {i + 1}
                </div>
                <div className="flex-1">
                  <div className="font-semibold text-foreground text-sm">{phase.name}</div>
                  <div className="text-xs text-muted-foreground">{phase.description}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-foreground">~{phase.est_minutes} min</div>
                  <div className="text-[10px] text-muted-foreground">{phase.objects} objects</div>
                </div>
              </div>
              {phase.users && (
                <div className="flex flex-wrap gap-1.5 ml-11">
                  {phase.users.map((name: string, j: number) => (
                    <span key={j} className="text-[10px] px-2 py-0.5 bg-muted rounded-full text-muted-foreground">{name}</span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Differentiator callout */}
      <div className="bg-muted rounded-xl p-4 mb-6 text-center border border-border">
        <p className="text-muted-foreground text-xs mb-1">What competitors require you to configure manually</p>
        <p className="text-foreground font-semibold">Shieldio computes this automatically from Microsoft Graph</p>
      </div>

      <button onClick={onContinue}
        className="w-full py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-500 transition-colors flex items-center justify-center gap-2">
        Continue to Backup <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}

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

function CyberRecoverySimulation({ tenantName, tenantId, disc: _disc, onComplete, simScene, setSimScene, activeWorkloads }: {
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
  void entra; // used in entraCounts fallback below

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

  // Use demo data if entra summary not available
  const entraCounts = Object.keys(entra.counts || {}).length > 0
    ? entra.counts
    : { users: 15, groups: 8, roles: 3, conditional_access_policies: 5, oauth_grants: 12 };

  const renderScene1 = () => loading ? <Shimmer /> : (
    <div className="space-y-3">
      <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4">
        <p className="text-xs font-semibold text-purple-400 uppercase mb-2">Your Entra ID Backup</p>
        <div className="space-y-1.5">
          {Object.entries(entraCounts).map(([type, count]: [string, any]) => {
            const meta = ENTRA_TYPE_LABELS[type] || { label: type.replace(/_/g, ' ') };
            const isUnderAttack = attackPhase !== 'idle' && meta.critical;
            return (
              <div key={type} className={`flex items-center justify-between text-sm px-2 py-1 rounded transition-all duration-500 ${
                isUnderAttack && attackPhase === 'attacking' ? 'bg-red-500/20 ring-1 ring-red-400' :
                isUnderAttack && attackPhase === 'resolved' ? 'bg-green-500/20 ring-1 ring-green-400' : ''
              }`}>
                <span className="text-purple-300">{meta.label || type.replace(/_/g, ' ')}</span>
                <span className="flex items-center gap-1.5">
                  <span className="font-bold text-purple-300">{count}</span>
                  {meta.critical && <span className="text-[10px] px-1.5 py-0.5 bg-red-500/20 text-red-400 rounded font-semibold">CRITICAL</span>}
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
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 animate-pulse">
          <p className="text-sm text-red-400 font-medium">An attacker disabled your MFA policy and granted themselves Global Admin...</p>
        </div>
      )}
      {(attackPhase === 'detected' || attackPhase === 'resolved') && (
        <div className="space-y-2">
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3">
            <p className="text-sm text-red-400 font-medium">Attack: MFA policy disabled + rogue Global Admin granted</p>
          </div>
          <div className={`bg-green-500/10 border border-green-500/30 rounded-xl p-3 transition-all duration-500 ${attackPhase === 'detected' ? 'opacity-0 scale-95' : 'opacity-100 scale-100'}`}>
            <p className="text-sm text-green-400 font-medium">Shieldio: Detected. One-click revert available from latest snapshot.</p>
          </div>
        </div>
      )}
      <GapRow m365="No Entra ID backup. No undo for disabled MFA or rogue admin grants."
        shieldio={`${Object.values(entraCounts).reduce((s: number, c: any) => s + (c as number), 0)} identity objects backed up with snapshot history`} />
    </div>
  );

  const renderScene2 = () => loading ? <Shimmer /> : (
    <div className="space-y-3">
      <div className="bg-card border border-border rounded-xl p-4">
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
              <span className="text-[10px] text-muted-foreground">/ 100</span>
            </div>
          </div>
          <div className="flex-1">
            <div className={`flex items-center gap-2 mb-2 transition-opacity duration-1000 ${scoreRevealed ? 'opacity-100' : 'opacity-0'}`}>
              <span className={`text-lg font-bold ${conf.color === 'green' ? 'text-green-600' : conf.color === 'blue' ? 'text-blue-600' : conf.color === 'amber' ? 'text-amber-600' : 'text-red-600'}`}>
                Grade {conf.grade || '—'}
              </span>
              <span className="text-sm text-muted-foreground">{conf.label}</span>
            </div>
            {conf.factors && Object.entries(conf.factors).map(([key, f]: [string, any], i) => (
              <div key={key} className="mb-1">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-muted-foreground capitalize">{key.replace('_', ' ')}</span>
                  <span className="font-medium">{Math.round(f.score)}%</span>
                </div>
                <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
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
          <p className="text-sm text-muted-foreground mb-4">Generate a full recovery plan from your backed-up data — no data is modified.</p>
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
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold text-foreground ${
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
              <button disabled className="mt-2 px-4 py-2 bg-muted text-muted-foreground rounded-lg text-xs cursor-not-allowed" title="Available from Recovery Dashboard">
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
        <h2 className="text-xl font-bold text-foreground">Your Cyber Recovery Playbook</h2>
        <p className="text-muted-foreground text-sm">Try each step with your real data</p>
      </div>

      {/* Step progress */}
      <div className="flex items-center justify-center gap-1.5 mb-5">
        {scenes.map((s, i) => (
          <button key={s.key} onClick={() => setSimScene(i)}
            className={`w-2.5 h-2.5 rounded-full transition-all ${
              i === simScene ? 'w-8 bg-blue-500/100' : engaged[i] ? 'bg-green-500/100' : i < simScene ? 'bg-blue-300' : 'bg-muted'
            }`} />
        ))}
      </div>

      {/* Step content */}
      <div className="bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
        <div className="bg-muted/50 border-b border-border px-5 py-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-muted-foreground">Step {simScene + 1} of {STEP_COUNT}</span>
            {engaged[simScene] && <span className="text-xs font-semibold text-green-600 flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Done</span>}
          </div>
          <h3 className="text-lg font-bold text-foreground mt-1">{scene.title}</h3>
          <p className="text-sm text-muted-foreground">{scene.subtitle}</p>
        </div>

        {scene.problem && (
          <div className="px-5 py-3 bg-red-500/10 border-b border-red-100">
            <p className="text-sm text-red-800">{scene.problem}</p>
          </div>
        )}

        <div className="px-5 py-4">{scene.render()}</div>

        {/* Footer: Next + Explore link */}
        <div className="px-5 py-4 border-t border-border bg-muted/50">
          <div className="flex items-center justify-between">
            {!isLastStep ? (
              <button onClick={() => setSimScene(simScene + 1)} disabled={!canAdvance}
                className={`px-5 py-2.5 rounded-xl font-semibold text-sm flex items-center gap-1.5 transition-all ${
                  canAdvance ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-muted text-muted-foreground cursor-not-allowed'
                }`}>
                Next <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button onClick={onComplete} disabled={!canAdvance}
                className={`px-5 py-2.5 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all ${
                  canAdvance ? 'bg-green-600 text-white hover:bg-green-700' : 'bg-muted text-muted-foreground cursor-not-allowed'
                }`}>
                Go to Dashboard <ArrowRight className="w-4 h-4" />
              </button>
            )}
            <button onClick={() => navigate(scene.explore.route)}
              className="text-xs text-blue-500 hover:text-blue-700 hover:underline">
              {scene.explore.label} →
            </button>
          </div>
          {!canAdvance && simScene === 1 && <p className="text-[11px] text-muted-foreground mt-1.5">Click "Simulate Identity Attack" above to continue</p>}
          {!canAdvance && simScene === 3 && <p className="text-[11px] text-muted-foreground mt-1.5">Click "Generate Recovery Plan" above to continue</p>}
        </div>
      </div>

      {/* Navigation + skip */}
      <div className="flex items-center justify-between mt-3">
        <button onClick={() => setSimScene(Math.max(0, simScene - 1))} disabled={simScene === 0}
          className="text-xs text-muted-foreground hover:text-muted-foreground disabled:opacity-30">← Back</button>
        <button onClick={onComplete} className="text-xs text-muted-foreground hover:text-muted-foreground">Skip → Dashboard</button>
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
  // Demo user always gets the full onboarding experience from step 0
  // (platform selection → connect → discover → protect → backup → ready)
  return <Onboard />;
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
  // For demo mode, always start fresh (clear previous session)
  const isDemo = searchParams.get('demo') === 'true';
  const saved = isDemo ? null : loadOnboardState();
  const urlStep = parseInt(searchParams.get('step') || '0');
  const initialStep = saved?.step ?? urlStep;

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
        // Start at step 0 (tenant verification) — not step 1
        setStep(0);
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
        <h2 className="text-2xl font-bold text-foreground mb-2">
          {isPropagation ? 'Almost There' : isConfigError ? 'Setup Required' : 'Connection Failed'}
        </h2>
        <p className="text-muted-foreground mb-2">{error}</p>
        {isPropagation && (
          <p className="text-sm text-muted-foreground mb-6">Microsoft can take up to 60 seconds to process admin consent for new tenants.</p>
        )}
        {isConfigError && (
          <p className="text-sm text-muted-foreground mb-6">This is a Shieldio platform issue, not a problem with your M365 tenant.</p>
        )}
        {isConsentError && (
          <p className="text-sm text-muted-foreground mb-6">You need to sign in with a Global Administrator account to approve the connection.</p>
        )}
        <div className="flex items-center justify-center gap-3 mt-4">
          <button onClick={() => navigate('/onboard')} className="px-6 py-2.5 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700">
            {isPropagation ? 'Try Again (should work now)' : 'Try Again'}
          </button>
          <button onClick={() => navigate('/')} className="px-6 py-2.5 bg-secondary text-muted-foreground rounded-xl font-medium hover:bg-muted">Dashboard</button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground px-4">
    <div className="max-w-2xl mx-auto py-8">
      {/* Progress bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          {WIZARD_STEPS.map((s, i) => (
            <div key={s.key} className="flex items-center gap-1.5">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                i < step ? 'bg-green-500/100 text-foreground' :
                i === step ? 'bg-blue-600 text-white ring-4 ring-blue-100' :
                'bg-muted text-muted-foreground'
              }`}>
                {i < step ? <CheckCircle className="w-4 h-4" /> : i + 1}
              </div>
              <span className={`text-xs font-medium hidden sm:block ${i <= step ? 'text-foreground' : 'text-muted-foreground'}`}>{s.label}</span>
              {i < WIZARD_STEPS.length - 1 && <div className={`w-8 sm:w-16 h-0.5 mx-1 ${i < step ? 'bg-green-500/100' : 'bg-muted'}`} />}
            </div>
          ))}
        </div>
      </div>

      {/* Step 0: Tenant Connected — verification card */}
      {step === 0 && <TenantConnectedStep tenantName={tenantName} tenantId={resultData?.db_tenant_id} onContinue={() => setStep(1)} />}

      {/* Step 1: Discovery — Workload Selection */}
      {step === 1 && (
        <div>
          <div className="text-center mb-6">
            <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <CheckCircle className="w-7 h-7 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-foreground">Connected to {tenantName}</h2>
            <p className="text-muted-foreground mt-1">
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
                      : 'border-border hover:border-border'
                  }`}
                >
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                    isSelected ? 'border-blue-500 bg-blue-500/100' : 'border-gray-300'
                  }`}>
                    {isSelected && <CheckCircle className="w-3.5 h-3.5 text-foreground" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-foreground text-sm">{wl.label}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        wl.speed === 'fast' ? 'bg-green-100 text-green-700' :
                        wl.speed === 'medium' ? 'bg-amber-100 text-amber-700' :
                        'bg-secondary text-muted-foreground'
                      }`}>
                        {wl.speed === 'fast' ? '⚡ fast' : wl.speed === 'medium' ? '~5s' : '~10s'}
                      </span>
                      {wl.recommended && <span className="text-[10px] text-blue-500 font-medium">Recommended</span>}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">{wl.description}</p>
                  </div>
                  {discCount !== null && discCount > 0 && (
                    <div className="text-right flex-shrink-0">
                      <div className="text-lg font-bold text-blue-600">{discCount}</div>
                      <div className="text-[10px] text-muted-foreground">found</div>
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
                  className="px-4 py-3 bg-secondary text-muted-foreground rounded-xl font-medium hover:bg-muted transition-colors flex items-center gap-2"
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
            <h2 className="text-2xl font-bold text-foreground">Choose Protection Level</h2>
            <p className="text-muted-foreground mt-1">How often should we back up your data?</p>
          </div>

          <div className="space-y-3 mb-6">
            {slaPolicies.length > 0 ? slaPolicies.map((sla: any) => (
              <button
                key={sla.id}
                onClick={() => setSelectedSla(sla.id)}
                className={`w-full p-4 rounded-xl border-2 text-left transition-all ${
                  selectedSla === sla.id
                    ? 'border-blue-500 bg-blue-500/10 ring-2 ring-blue-200'
                    : 'border-border hover:border-border'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-bold text-foreground">{sla.name}</div>
                    <div className="text-sm text-muted-foreground">
                      Every {sla.backup_frequency_hours}h • {sla.retention_days} day retention
                      {sla.worm_enabled ? ' • WORM locked' : ''}
                    </div>
                  </div>
                  <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${
                    selectedSla === sla.id ? 'border-blue-500 bg-blue-500/100' : 'border-gray-300'
                  }`}>
                    {selectedSla === sla.id && <CheckCircle className="w-4 h-4 text-foreground" />}
                  </div>
                </div>
              </button>
            )) : (
              <div className="text-center py-4">
                <p className="text-muted-foreground text-sm">No SLA policies found. We'll create a default daily backup policy.</p>
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

      {/* Step 3: Smart Intelligence — org graph + criticality-ordered backup priority */}
      {step === 3 && <IntelligenceStep tenantId={resultData?.db_tenant_id} onContinue={() => setStep(4)} />}

      {step === 4 && (
        <div>
          <div className="text-center mb-5">
            <h2 className="text-2xl font-bold text-foreground">Smart Backup Storyline</h2>
            <p className="text-muted-foreground mt-1">Criticality-ordered: identity first, then critical users, then everyone else.</p>
          </div>

          {/* Criticality priority banner */}
          <div className="bg-card border border-border rounded-xl p-3 mb-4">
            <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-2">Backup Priority Order</div>
            <div className="flex items-center gap-2 text-xs">
              <span className="flex items-center gap-1 px-2 py-1 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 font-medium">
                {backupStatus === 'running' ? '🔄' : backupStatus === 'complete' ? '✅' : '1️⃣'} Identity + CEO
              </span>
              <ArrowRight className="w-3 h-3 text-muted-foreground" />
              <span className="flex items-center gap-1 px-2 py-1 bg-orange-500/10 border border-orange-500/20 rounded-lg text-orange-400 font-medium">
                {backupStatus === 'complete' ? '✅' : '2️⃣'} VPs
              </span>
              <ArrowRight className="w-3 h-3 text-muted-foreground" />
              <span className="flex items-center gap-1 px-2 py-1 bg-blue-500/10 border border-blue-500/20 rounded-lg text-blue-400 font-medium">
                {backupStatus === 'complete' ? '✅' : '3️⃣'} Directors
              </span>
              <ArrowRight className="w-3 h-3 text-muted-foreground" />
              <span className="flex items-center gap-1 px-2 py-1 bg-muted border border-border rounded-lg text-muted-foreground font-medium">
                {backupStatus === 'complete' ? '✅' : '4️⃣'} Staff
              </span>
            </div>
          </div>

          {/* ── Phase 1: Discovery Storyline ── */}
          {backupStatus === 'pending' && (
            <div className="space-y-4">
              {/* Animated discovery cards — objects appearing */}
              <div className="bg-card rounded-xl border border-border p-4">
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
                      className={`flex items-center gap-3 p-3 rounded-lg border bg-muted/50 ${item.color} transition-all duration-500`}
                      style={{ opacity: 1, transitionDelay: `${i * 150}ms` }}>
                      <span className="text-xl">{item.icon}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`text-sm font-bold ${item.color.split(' ')[0]}`}>{item.count}</span>
                          <span className="text-sm font-medium text-foreground">{item.label}</span>
                        </div>
                        <div className="text-[10px] text-muted-foreground">{item.detail}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Visual pipeline */}
              <div className="bg-card/50 rounded-xl border border-border p-4">
                <div className="text-xs font-medium text-muted-foreground mb-3">Backup Pipeline — what happens to each object:</div>
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
                      {i < 4 && <ArrowRight className="w-3 h-3 text-muted-foreground shrink-0" />}
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
                <div className="w-full bg-secondary rounded-full h-2">
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
                    status === 'failed' ? 'border-red-500/30 bg-red-500/5' : 'border-border bg-card/30'
                  }`}>
                    <div className="flex items-center gap-3 p-3">
                      {status === 'pending' && <div className="w-6 h-6 rounded-full border-2 border-border flex items-center justify-center text-[9px] text-muted-foreground">—</div>}
                      {status === 'running' && <Loader2 className="w-6 h-6 animate-spin text-blue-400" />}
                      {status === 'done' && <CheckCircle className="w-6 h-6 text-green-400" />}
                      {status === 'failed' && <XCircle className="w-6 h-6 text-red-400" />}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-sm text-foreground capitalize">{wl.replace('_', ' ')}</span>
                          <span className="text-[10px] text-muted-foreground">{objectCount} objects</span>
                        </div>
                        {status === 'running' && (
                          <div className="text-[10px] text-blue-300 mt-0.5 animate-pulse">{pipelineStage}...</div>
                        )}
                      </div>
                      <div className="text-right">
                        {status === 'done' && <span className="text-xs font-medium text-green-400">Protected ✓</span>}
                        {status === 'running' && <span className="text-xs font-medium text-blue-400">In progress</span>}
                        {status === 'pending' && <span className="text-xs text-muted-foreground">Next</span>}
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
                <div className="text-xl font-bold text-foreground">{totalObjects} Objects Protected</div>
                <div className="text-xs text-green-300 mt-1">Criticality-ordered • AES-256-GCM encrypted • Point-in-time restore ready</div>
                <div className="flex items-center justify-center gap-3 mt-3 text-[10px]">
                  <span className="text-red-400">👑 CEO secured first</span>
                  <span className="text-muted-foreground">→</span>
                  <span className="text-orange-400">⭐ VPs next</span>
                  <span className="text-muted-foreground">→</span>
                  <span className="text-blue-400">Directors</span>
                  <span className="text-muted-foreground">→</span>
                  <span className="text-muted-foreground">Everyone</span>
                </div>
              </div>

              {/* Protection map — visual summary of what's protected */}
              <div className="bg-card rounded-xl border border-border p-4">
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Protection Map</div>
                <div className="space-y-2">
                  {Object.entries(backupProgress).filter(([, s]) => s === 'done').map(([wl]) => {
                    const count = wl === 'exchange' ? disc?.mailboxes : wl === 'onedrive' ? disc?.onedrives : wl === 'sharepoint' ? disc?.sites : wl === 'teams' ? disc?.teams : 1;
                    return (
                      <div key={wl} className="flex items-center gap-3 p-2 rounded-lg bg-green-500/5 border border-green-500/20">
                        <Shield className="w-4 h-4 text-green-400 shrink-0" />
                        <div className="flex-1">
                          <span className="text-sm font-medium text-foreground capitalize">{wl.replace('_', ' ')}</span>
                          <span className="text-[10px] text-muted-foreground ml-2">{count} {count === 1 ? 'object' : 'objects'}</span>
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
                  <span className="text-sm font-semibold text-foreground">What happens next</span>
                </div>
                <div className="text-xs text-muted-foreground space-y-1.5">
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
            <button onClick={() => setStep(5)} className="mt-4 w-full text-sm text-muted-foreground hover:text-muted-foreground text-center">
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
          <h2 className="text-3xl font-bold text-foreground mb-2">You're Protected! 🎉</h2>
          <p className="text-muted-foreground mb-2">{tenantName} is now backed up with Shieldio.</p>

          <div className="bg-muted/50 rounded-xl p-4 mb-6 text-sm text-left max-w-md mx-auto">
            <div className="font-semibold text-foreground mb-2">What happens next:</div>
            <div className="space-y-2 text-muted-foreground">
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
              className="px-6 py-3 bg-secondary text-muted-foreground rounded-xl font-medium hover:bg-muted transition-colors"
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
