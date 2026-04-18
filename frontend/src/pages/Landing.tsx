import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Shield, Mail, HardDrive, Globe, MessageSquare, KeyRound,
  AlertTriangle, ArrowRight, Check, X,
  Eye, Brain, ShieldCheck, ChevronRight, Scale, RotateCcw,
} from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { appUrl } from '../utils/appUrl';

// ── Scroll animation hook ──
function useInView(threshold = 0.05) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    // Check if already in viewport (e.g. anchor navigation)
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight + 100 && rect.bottom > -100) {
      setInView(true);
      return;
    }
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setInView(true); }, { threshold, rootMargin: '100px 0px' });
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, inView };
}

function FadeUp({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const { ref, inView } = useInView();
  return (
    <div ref={ref} className={`transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-90 translate-y-2'}`} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}

// Counter removed — hero metrics now use text labels instead of animated numbers

// ── Cyber Recovery Story — Cinematic 6-Phase Animation ──
function CyberRecoveryStory() {
  const { ref, inView } = useInView(0.05);
  const [phase, setPhase] = useState(0);
  const [autoPlay, setAutoPlay] = useState(true);

  // Continuous loop — cycles through all phases, pauses at end, restarts
  useEffect(() => {
    if (!inView || !autoPlay) return;
    const PHASE_DELAY = 2000; // ms per phase
    const PAUSE_AT_END = 3000; // pause before restart
    const TOTAL_CYCLE = 6 * PHASE_DELAY + PAUSE_AT_END;

    const runCycle = () => {
      setPhase(0);
      const timers = [
        setTimeout(() => setPhase(1), 600),
        setTimeout(() => setPhase(2), PHASE_DELAY * 1),
        setTimeout(() => setPhase(3), PHASE_DELAY * 2),
        setTimeout(() => setPhase(4), PHASE_DELAY * 3),
        setTimeout(() => setPhase(5), PHASE_DELAY * 4),
        setTimeout(() => setPhase(6), PHASE_DELAY * 5),
      ];
      return timers;
    };

    let timers = runCycle();
    const interval = setInterval(() => {
      timers.forEach(clearTimeout);
      timers = runCycle();
    }, TOTAL_CYCLE);

    return () => {
      timers.forEach(clearTimeout);
      clearInterval(interval);
    };
  }, [inView, autoPlay]);

  // Cohesive color palette: blue → indigo → rose → amber → blue → blue
  // Matches landing page blue/indigo brand colors, with rose for the crisis moment
  const PHASES = [
    { num: 1, label: 'PROTECT', emoji: '🛡️', color: 'from-blue-500 to-blue-600', border: 'border-blue-500/40', bg: 'bg-muted', glow: 'shadow-blue-500/10',
      title: 'Daily encrypted backups running',
      detail: 'AES-256-GCM • 5 workloads • WORM immutable',
      visual: '████████████████ 100%',
      items: ['📧 2,847 emails backed up', '📁 1,203 files secured', '💬 892 messages archived', '🔑 188 identity objects saved'] },
    { num: 2, label: 'MONITOR', emoji: '🧠', color: 'from-blue-400 to-indigo-500', border: 'border-indigo-500/40', bg: 'bg-muted', glow: 'shadow-indigo-500/10',
      title: 'AI learns your normal patterns',
      detail: 'Baselines • Z-score analysis • Trend detection',
      visual: '📊 ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁',
      items: ['Item count: 5,130 ± 42', 'Size: 26.5MB ± 1.2MB', 'Error rate: 1.2% ± 0.3%', 'Duration: 4.2min ± 0.8min'] },
    { num: 3, label: 'DETECT', emoji: '🚨', color: 'from-rose-500 to-red-600', border: 'border-rose-500/50', bg: 'bg-muted', glow: 'shadow-rose-500/20',
      title: '⚠️ ANOMALY: 1,847 files renamed to .encrypted',
      detail: 'Z-score: 8.4 • Severity: CRITICAL • Auto-alert sent',
      visual: '🔴 ▁▂▃▄▅▆▇████████████',
      items: ['OneDrive: 1,847 files changed', 'Extension: .docx → .encrypted', 'Time window: 14 minutes', 'Affected: 3 user accounts'] },
    { num: 4, label: 'RESPOND', emoji: '⚡', color: 'from-amber-400 to-amber-500', border: 'border-amber-500/40', bg: 'bg-muted', glow: 'shadow-amber-500/10',
      title: 'Auto-pause backups • Isolate clean point',
      detail: 'Circuit breaker active • Malware scan queued',
      visual: '🔒 Backup paused → Scanning...',
      items: ['✅ Last clean: 2h ago (#847)', '🔍 Scanning backup for malware', '🛑 Backups paused for 3 accounts', '📧 Alert sent to admin'] },
    { num: 5, label: 'RECOVER', emoji: '🔄', color: 'from-blue-400 to-blue-500', border: 'border-blue-500/40', bg: 'bg-muted', glow: 'shadow-blue-500/10',
      title: 'One-click restore from clean snapshot',
      detail: 'Snapshot #847 • 5,130 items • WORM-verified',
      visual: '████████████░░░░ 78%',
      items: ['📧 2,847 emails restored', '📁 1,203 files restored', '💬 892 messages restored', '⏱️ Estimated: 12 minutes'] },
    { num: 6, label: 'VERIFY', emoji: '✅', color: 'from-emerald-400 to-green-500', border: 'border-emerald-500/40', bg: 'bg-muted', glow: 'shadow-emerald-500/10',
      title: '100% recovery verified — checksums match',
      detail: 'All 5,130 items validated • Zero data loss',
      visual: '████████████████ 100% ✓',
      items: ['✅ 5,130/5,130 items verified', '✅ All SHA-256 checksums match', '✅ Backups resumed normally', '✅ Incident report generated'] },
  ];

  const current = PHASES[phase > 0 ? phase - 1 : 0];

  return (
    <div ref={ref} className="max-w-5xl mx-auto">
      {/* Phase selector — timeline bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-8 relative">
        {/* Timeline line */}
        <div className="absolute top-5 left-0 right-0 h-0.5 bg-card rounded">
          <div
            className="h-full rounded transition-all duration-1000 bg-gradient-to-r from-blue-500 via-rose-500 to-emerald-500"
            style={{ width: `${Math.max(((phase) / 6) * 100, 0)}%` }}
          />
        </div>
        {PHASES.map((p) => (
          <button
            key={p.num}
            onClick={() => { setPhase(p.num); setAutoPlay(false); }}
            className={`relative z-10 flex flex-col items-center gap-1.5 transition-all duration-500 ${phase >= p.num ? 'opacity-100 scale-100' : 'opacity-40 scale-90'}`}
          >
            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-lg transition-all duration-500 ${
              phase >= p.num
                ? `bg-gradient-to-br ${p.color} shadow-lg ${p.glow} ring-2 ring-offset-2 ring-offset-background ${p.border}`
                : 'bg-card border border-border'
            }`}>
              {phase >= p.num ? p.emoji : <span className="text-xs text-muted-foreground">{p.num}</span>}
            </div>
            <span className={`text-[10px] font-bold tracking-wider transition-colors ${phase >= p.num ? 'text-foreground' : 'text-muted-foreground'}`}>
              {p.label}
            </span>
          </button>
        ))}
      </div>

      {/* Active phase detail card */}
      {phase > 0 && (
        <div className={`relative rounded-2xl border overflow-hidden transition-all duration-700 ${current.border} ${current.bg} shadow-2xl ${current.glow}`}>
          {/* Pulsing background glow for DETECT phase */}
          {phase === 3 && (
            <div className="absolute inset-0 bg-red-500/5 animate-pulse" />
          )}

          <div className="relative p-8">
            {/* Header */}
            <div className="flex items-center gap-4 mb-6">
              <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${current.color} flex items-center justify-center text-2xl shadow-lg`}>
                {current.emoji}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-muted-foreground tracking-widest">PHASE {current.num}</span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold bg-gradient-to-r ${current.color} text-white`}>
                    {current.label}
                  </span>
                </div>
                <h3 className="text-xl font-bold text-foreground mt-1">{current.title}</h3>
                <p className="text-sm text-muted-foreground mt-0.5">{current.detail}</p>
              </div>
            </div>

            {/* Progress visualization */}
            <div className="bg-black/30 rounded-xl p-4 mb-6 font-mono text-sm">
              <div className="text-muted-foreground mb-1">$ kavachiq status</div>
              <div className={`transition-all duration-500 ${phase === 3 ? 'text-red-400' : phase >= 5 ? 'text-green-400' : 'text-blue-400'}`}>
                {current.visual}
              </div>
            </div>

            {/* Detail items grid */}
            <div className="grid grid-cols-2 gap-3">
              {current.items.map((item, idx) => (
                <div
                  key={idx}
                  className={`flex items-center gap-2 px-3 py-2.5 rounded-lg bg-card/5 border border-white/10 text-sm text-foreground transition-all duration-500`}
                  style={{ transitionDelay: `${idx * 150}ms`, opacity: phase >= current.num ? 1 : 0, transform: phase >= current.num ? 'translateX(0)' : 'translateX(-10px)' }}
                >
                  {item}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Pre-animation state */}
      {phase === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <div className="text-4xl mb-3 animate-pulse">🎬</div>
          <p className="text-sm">Scroll down to watch the story unfold...</p>
        </div>
      )}

      {/* Auto/Manual toggle */}
      <div className="flex justify-center mt-6 gap-4">
        {!autoPlay && (
          <button
            onClick={() => { setPhase(0); setAutoPlay(true); }}
            className="px-4 py-1.5 bg-card/10 text-muted-foreground text-xs rounded-lg hover:bg-card/20 hover:text-foreground transition-colors"
          >
            ▶ Replay
          </button>
        )}
      </div>
    </div>
  );
}

// ── Workload icons ──
const WORKLOADS = [
  { icon: Mail, label: 'Exchange', desc: 'Email, Calendar, Contacts', color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
  { icon: HardDrive, label: 'OneDrive', desc: 'Files & Folders', color: 'text-purple-400 bg-purple-500/10 border-purple-500/20' },
  { icon: Globe, label: 'SharePoint', desc: 'Sites, Lists, Documents', color: 'text-green-400 bg-green-500/10 border-green-500/20' },
  { icon: MessageSquare, label: 'Teams', desc: 'Chats, Channels, Files', color: 'text-pink-400 bg-pink-500/10 border-pink-500/20' },
  { icon: KeyRound, label: 'Entra ID', desc: '12 object types, Config drift', color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
];

// ── Competitor comparison (CISO-focused) ──
const COMPARE_FEATURES = [
  { feature: 'Context-aware recovery plans', us: true, them: false },
  { feature: 'Entra ID config backup + rollback', us: true, them: false },
  { feature: 'Criticality-based restore order', us: true, them: false },
  { feature: 'Recovery confidence score', us: true, them: false },
  { feature: 'Anomaly detection (built-in)', us: true, them: false },
  { feature: 'Self-service restore portal', us: true, them: false },
  { feature: 'eDiscovery + legal hold', us: true, them: false },
  { feature: 'Per-tenant alert configuration', us: true, them: false },
  { feature: 'WORM immutable storage', us: true, them: true },
  { feature: 'Intelligence surcharge', usVal: '$0', themVal: '$$$' },
  { feature: 'Starting price', usVal: '$1.50/user', themVal: '$2-10/user' },
];

// ── Pricing tiers (workload limits match TIER_WORKLOAD_LIMITS in backend) ──
const PRICING = [
  { name: 'Community', price: 'Free', period: 'forever', desc: '2 workloads, up to 25 objects', features: ['Choose any 2 workloads', 'Basic anomaly detection', '30-day retention', 'Self-service restore portal', 'Community support'], cta: 'Start Free', primary: false },
  { name: 'Professional', price: '$1.50', period: '/user/mo', desc: 'All 5 workloads, unlimited users', features: ['All 5 workloads + shared mailbox', 'Custom alert preferences', '90-day retention + SSO', 'Agent Shield + full Smart Engine', 'Self-service restore portal'], cta: 'Start Trial', primary: true },
  { name: 'Business', price: '$3.00', period: '/user/mo', desc: 'All 5 workloads, unlimited tenants', features: ['PST export + snapshot diff', 'Group membership restore', 'Org Context + MVB Plans', '1-year retention + priority support', 'MSP multi-tenant dashboard'], cta: 'Start Trial', primary: false },
  { name: 'Enterprise', price: '$5.00', period: '/user/mo', desc: '6 workloads, unlimited everything', features: ['6 workloads (+ Power Platform)', 'eDiscovery + legal hold', 'Agent Governance + WORM', 'Cleanroom recovery', 'Dedicated support + SLA'], cta: 'Contact Sales', primary: false },
];

// ═══════════════════════════════════════════════════════
// LANDING PAGE
// ═══════════════════════════════════════════════════════
export default function Landing() {
  const [heroReady, setHeroReady] = useState(false);
  useEffect(() => { setTimeout(() => setHeroReady(true), 100); }, []);

  return (
    <div className="min-h-screen bg-background">
      <Helmet>
        <title>KavachIQ — Microsoft 365 Backup & Ransomware Recovery</title>
        <meta name="description" content="Open-source M365 data protection with identity-first recovery. Back up Exchange, OneDrive, SharePoint, Teams & Entra ID. Free for 25 users." />
        <link rel="canonical" href="https://kavachiq.com/welcome" />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://kavachiq.com/welcome" />
        <meta property="og:title" content="KavachIQ — Microsoft 365 Backup & Ransomware Recovery" />
        <meta property="og:description" content="Open-source M365 data protection with identity-first recovery. Back up Exchange, OneDrive, SharePoint, Teams & Entra ID." />
        <meta property="og:image" content="https://kavachiq.com/og-welcome.jpg" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="KavachIQ — Microsoft 365 Backup & Ransomware Recovery" />
        <meta name="twitter:description" content="Open-source M365 data protection with identity-first recovery. Free for 25 users." />
        <meta name="twitter:image" content="https://kavachiq.com/og-welcome.jpg" />
        <script type="application/ld+json">{JSON.stringify({
          "@context": "https://schema.org",
          "@type": "SoftwareApplication",
          "name": "KavachIQ",
          "applicationCategory": "SecurityApplication",
          "operatingSystem": "Cloud",
          "description": "Open-source Microsoft 365 data protection platform with identity-first ransomware recovery.",
          "url": "https://kavachiq.com",
          "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD", "description": "Free for up to 25 users" },
          "publisher": {
            "@type": "Organization",
            "name": "KavachIQ",
            "url": "https://kavachiq.com",
            "logo": "https://kavachiq.com/favicon.svg"
          }
        })}</script>
      </Helmet>

      {/* ═══ NAV ═══ */}
      <nav className="fixed top-0 w-full z-50 bg-card/80 backdrop-blur-sm border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link to="/welcome" className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-teal-500" />
            <span className="font-bold text-foreground">KavachIQ</span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#how-it-works" className="hover:text-foreground">How It Works</a>
            <a href="#pricing" className="hover:text-foreground">Pricing</a>
            <Link to="/docs" className="hover:text-foreground">Docs</Link>
            <Link to="/about" className="hover:text-foreground">About</Link>
            <Link to="/contact" className="hover:text-foreground">Contact</Link>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link to="/tour" className="text-sm text-muted-foreground hover:text-foreground">Product Tour</Link>
            <a href={appUrl('/login')} className="text-sm text-muted-foreground hover:text-foreground">Sign In</a>
            <a href={appUrl('/login?register=true')} className="px-4 py-1.5 bg-gradient-to-r from-teal-500 to-cyan-500 text-white text-sm font-medium rounded-lg hover:from-teal-400 hover:to-cyan-400 transition-all shadow-lg shadow-teal-500/20">
              Start Free
            </a>
          </div>
        </div>
      </nav>

      {/* ═══ SECTION 1: HOOK — Emotional Trigger ═══ */}
      <section className="pt-24 pb-16 px-6">
        <div className="max-w-4xl mx-auto text-center">
          {/* Badge */}
          <div className={`inline-flex items-center gap-2 px-3 py-1 bg-red-500/10 text-red-400 rounded-full text-xs font-medium mb-6 transition-all duration-500 ${heroReady ? 'opacity-100' : 'opacity-0'}`}>
            <AlertTriangle className="w-3.5 h-3.5" />
            Microsoft doesn't back up your M365 data
          </div>

          {/* Headline */}
          <h1 className={`text-3xl md:text-5xl font-extrabold text-foreground leading-[1.1] tracking-tight transition-all duration-700 delay-200 ${heroReady ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}>
            Your emails. Your files.{' '}
            <br className="hidden md:block" />
            <span className="bg-gradient-to-r from-teal-500 to-cyan-500 bg-clip-text text-transparent">
              Your responsibility.
            </span>
          </h1>

          {/* Sub */}
          <p className={`mt-6 text-lg text-muted-foreground max-w-2xl mx-auto transition-all duration-700 delay-500 ${heroReady ? 'opacity-100' : 'opacity-0'}`}>
            Microsoft's 93-day recycle bin is not a recovery plan. When ransomware hits,
            KavachIQ already has a context-aware recovery plan — identity first, critical users next, then everyone else.
          </p>

          {/* CTAs */}
          <div className={`mt-8 flex items-center justify-center gap-4 transition-all duration-700 delay-700 ${heroReady ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
            <a href={appUrl('/login?register=true')} className="px-6 py-3 bg-teal-600 text-white font-semibold rounded-xl hover:bg-teal-700 transition-all hover:shadow-lg hover:shadow-teal-200/20 flex items-center gap-2">
              Start Free <ArrowRight className="w-4 h-4" />
            </a>
            <Link to="/tour" className="px-6 py-3 border border-teal-500/30 text-teal-400 font-medium rounded-xl hover:bg-teal-500/10 transition-colors flex items-center gap-2">
              <Eye className="w-4 h-4" /> See It In Action
            </Link>
          </div>

          {/* Stats — CISO-focused value props */}
          <div className={`mt-12 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto transition-all duration-700 delay-900 ${heroReady ? 'opacity-100' : 'opacity-0'}`}>
            <div className="text-center">
              <div className="text-xl font-bold text-teal-500">Context-Aware</div>
              <div className="text-xs text-muted-foreground mt-1">Recovery Plans</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-cyan-500">Pre-Computed</div>
              <div className="text-xs text-muted-foreground mt-1">Org Intelligence</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-green-600">$1.50/user</div>
              <div className="text-xs text-muted-foreground mt-1">All Included</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-foreground">SOC 2 + HIPAA</div>
              <div className="text-xs text-muted-foreground mt-1">+ GDPR + DORA</div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ SECTION 2: CYBER RECOVERY STORY — Cinematic Animation ═══ */}
      <section id="how-it-works" className="py-20 px-6 bg-gradient-to-b from-background via-background to-muted">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-red-500/10 text-red-400 rounded-full text-xs font-medium mb-4">
                <AlertTriangle className="w-3.5 h-3.5" /> Ransomware Scenario
              </div>
              <h2 className="text-3xl font-bold text-foreground">When ransomware hits at 2am, this is your playbook</h2>
              <p className="text-muted-foreground mt-2 max-w-xl mx-auto">Watch how KavachIQ detects an attack, identifies the blast radius, and recovers your critical users first — automatically</p>
            </div>
          </FadeUp>
          <CyberRecoveryStory />
        </div>
      </section>

      {/* ═══ SECTION 2.5: WHY NOT JUST USE MICROSOFT? ═══ */}
      <section className="py-20 px-6 bg-muted/50">
        <div className="max-w-4xl mx-auto">
          <FadeUp>
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-foreground">Why not just use Microsoft?</h2>
              <p className="text-muted-foreground mt-2">Microsoft 365 has built-in retention. Here's why it's not enough.</p>
            </div>
          </FadeUp>
          <FadeUp delay={200}>
            <div className="bg-card rounded-xl border border-border overflow-x-auto">
              <table className="w-full text-sm min-w-[480px]">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="text-left px-5 py-3 font-medium text-foreground">Capability</th>
                    <th className="text-center px-5 py-3 font-medium text-foreground">Microsoft 365</th>
                    <th className="text-center px-5 py-3 font-semibold text-teal-500">KavachIQ</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {[
                    { cap: 'Recovery model', m365: '93-day recycle bin', kavachiq: 'Unlimited point-in-time restore' },
                    { cap: 'Ransomware detection', m365: 'None', kavachiq: 'AI anomaly detection (Z-score baselines)' },
                    { cap: 'Recovery plan', m365: 'None — restore manually', kavachiq: 'Pre-computed 4-phase MVB plans' },
                    { cap: 'Entra ID rollback', m365: 'No undo for CA policies or roles', kavachiq: 'Full config snapshot + diff comparison' },
                    { cap: 'Recovery order', m365: 'Manual, one mailbox at a time', kavachiq: 'Criticality-ordered — CEO restored first' },
                    { cap: 'Recovery confidence', m365: 'Unknown until you try', kavachiq: 'Scored 0-100 with evidence' },
                  ].map(row => (
                    <tr key={row.cap} className="hover:bg-muted/50">
                      <td className="px-5 py-3 font-medium text-foreground">{row.cap}</td>
                      <td className="px-5 py-3 text-center text-foreground">{row.m365}</td>
                      <td className="px-5 py-3 text-center text-green-400 font-medium">{row.kavachiq}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </FadeUp>
        </div>
      </section>

      {/* ═══ SECTION 3: WORKLOADS — What You Protect ═══ */}
      <section id="workloads" className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-foreground">Every workload. One platform.</h2>
              <p className="text-muted-foreground mt-2">Five M365 workloads protected with unified backup, restore, and monitoring</p>
            </div>
          </FadeUp>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {WORKLOADS.map((wl, i) => (
              <FadeUp key={wl.label} delay={i * 100}>
                <div className={`border rounded-xl p-5 text-center hover:shadow-md transition-all cursor-default ${wl.color}`}>
                  <wl.icon className="w-8 h-8 mx-auto mb-3" />
                  <div className="font-semibold text-sm">{wl.label}</div>
                  <div className="text-[11px] mt-1 opacity-70">{wl.desc}</div>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ SECTION 4: INTELLIGENCE — AI-Powered Protection ═══ */}
      <section className="py-20 px-6 bg-gradient-to-b from-muted via-muted to-background text-foreground">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-500/10 text-amber-400 rounded-full text-xs font-medium mb-4">
                <Brain className="w-3.5 h-3.5" /> AI-Powered Intelligence
              </div>
              <h2 className="text-3xl font-bold">Recovery intelligence that no competitor has.</h2>
              <p className="text-muted-foreground mt-2 max-w-xl mx-auto">
                Other vendors back up your data. KavachIQ understands your organization and builds recovery plans automatically.
              </p>
            </div>
          </FadeUp>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { icon: Eye, title: 'Org Context', desc: 'Auto-discovers your reporting hierarchy, VIP groups, and privileged roles from Microsoft Graph. No manual user mapping.', color: 'from-teal-500 to-cyan-500' },
              { icon: Brain, title: 'Criticality Scoring', desc: '4-factor scoring: role weight, data sensitivity, activity level, business dependency. Your CEO scores 95. The intern scores 30.', color: 'from-amber-500 to-orange-500' },
              { icon: ShieldCheck, title: 'Recovery Plans', desc: 'Pre-computed 4-phase NIST-ordered plans: identity first, critical users next, then full recovery. Refreshed every 6 hours.', color: 'from-green-500 to-emerald-500' },
              { icon: AlertTriangle, title: 'Anomaly Detection', desc: 'Z-score baselines detect mass encryption, data exfiltration, and unusual deletions while backups are running.', color: 'from-rose-500 to-red-500' },
              { icon: RotateCcw, title: 'Self-Service Restore', desc: 'End users restore their own emails, files, and contacts without opening a support ticket. Role-based access, full audit trail.', color: 'from-blue-500 to-indigo-500' },
              { icon: Scale, title: 'eDiscovery + Legal Hold', desc: 'Cross-workload content search for litigation. Place custodian data under immutable legal hold to prevent deletion. Enterprise tier.', color: 'from-purple-500 to-violet-500' },
            ].map((f, i) => (
              <FadeUp key={f.title} delay={i * 150}>
                <div className="bg-card rounded-xl p-6 border border-border hover:border-teal-500/30 transition-all hover:shadow-lg hover:shadow-teal-500/5">
                  <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${f.color} flex items-center justify-center mb-4`}>
                    <f.icon className="w-5 h-5 text-white" />
                  </div>
                  <h3 className="font-semibold mb-2">{f.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ SECTION 5: TRUST — Security & Compliance ═══ */}
      <section id="security" className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-foreground">Enterprise-grade security</h2>
              <p className="text-muted-foreground mt-2">Your data is encrypted, immutable, and compliance-ready from day one</p>
            </div>
          </FadeUp>
          <div className="flex flex-wrap items-center justify-center gap-4 mb-8">
            {[
              { icon: '🔒', label: 'AES-256-GCM', desc: 'Encryption at Rest' },
              { icon: '🔑', label: 'Per-Tenant Keys', desc: 'Key Isolation' },
              { icon: '🛡️', label: 'WORM Storage', desc: 'Immutable Backups' },
              { icon: '✅', label: 'SOC 2', desc: '16 Controls Mapped' },
              { icon: '🇪🇺', label: 'GDPR', desc: '8 Articles Mapped' },
              { icon: '🏥', label: 'HIPAA', desc: '14 Safeguards Mapped' },
              { icon: '🔐', label: 'SSO + MFA', desc: 'Entra ID OIDC' },
              { icon: '📋', label: 'Audit Trail', desc: 'Full Logging' },
            ].map(b => (
              <FadeUp key={b.label}>
                <div className="flex items-center gap-2.5 px-4 py-3 bg-card/50 backdrop-blur-sm border border-border rounded-xl hover:border-blue-500/30 hover:shadow-lg hover:shadow-blue-500/5 transition-all">
                  <span className="text-lg">{b.icon}</span>
                  <div>
                    <div className="text-xs font-semibold text-foreground">{b.label}</div>
                    <div className="text-[10px] text-muted-foreground">{b.desc}</div>
                  </div>
                </div>
              </FadeUp>
            ))}
          </div>
          <div className="text-center">
            <Link to="/security" className="text-sm text-teal-500 hover:text-teal-400 font-medium">
              View full security posture <ChevronRight className="w-3.5 h-3.5 inline" />
            </Link>
          </div>
        </div>
      </section>

      {/* ═══ SECTION 6: COMPARE — Why Us ═══ */}
      <section className="py-20 px-6 bg-muted/50">
        <div className="max-w-3xl mx-auto">
          <FadeUp>
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-foreground">KavachIQ vs. Veeam, Rubrik, Druva</h2>
              <p className="text-muted-foreground mt-2">Recovery intelligence that competitors charge extra for — or don't offer at all</p>
            </div>
          </FadeUp>
          <FadeUp delay={200}>
            <div className="bg-card rounded-xl border border-border overflow-x-auto">
              <table className="w-full text-sm min-w-[480px]">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="text-left px-5 py-3 font-medium text-foreground">Feature</th>
                    <th className="text-center px-5 py-3 font-semibold text-teal-400">KavachIQ</th>
                    <th className="text-center px-5 py-3 font-medium text-foreground">Others</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {COMPARE_FEATURES.map(f => (
                    <tr key={f.feature} className="hover:bg-muted/50">
                      <td className="px-5 py-3 text-foreground">{f.feature}</td>
                      <td className="px-5 py-3 text-center">
                        {'usVal' in f ? <span className="font-semibold text-green-400">{f.usVal}</span>
                          : f.us ? <Check className="w-5 h-5 text-green-500 mx-auto" /> : <X className="w-5 h-5 text-red-400/60 mx-auto" />}
                      </td>
                      <td className="px-5 py-3 text-center">
                        {'themVal' in f ? <span className="text-foreground">{f.themVal}</span>
                          : f.them ? <Check className="w-5 h-5 text-muted-foreground mx-auto" /> : <X className="w-5 h-5 text-red-400/60 mx-auto" />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </FadeUp>
        </div>
      </section>

      {/* ═══ SECTION 7: PRICING ═══ */}
      <section id="pricing" className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-foreground">Simple, transparent pricing</h2>
              <p className="text-muted-foreground mt-2">No per-GB charges. No surprise overages. Intelligence included free.</p>
            </div>
          </FadeUp>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
            {PRICING.map((tier, i) => (
              <FadeUp key={tier.name} delay={i * 100}>
                <div className={`relative rounded-xl p-6 ${tier.primary ? 'bg-gradient-to-br from-teal-600 to-cyan-600 text-white ring-2 ring-teal-500/50 ring-offset-2 ring-offset-background shadow-xl shadow-teal-500/20' : 'bg-card border border-border text-foreground hover:border-teal-500/20 hover:shadow-lg hover:shadow-teal-500/5 transition-all'}`}>
                  {tier.primary && (
                    <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-gradient-to-r from-amber-400 to-orange-400 text-black text-[10px] font-bold rounded-full shadow-md">
                      Recommended
                    </span>
                  )}
                  <div className={`text-sm font-semibold ${tier.primary ? 'text-teal-200' : 'text-muted-foreground'}`}>{tier.name}</div>
                  <div className="flex items-baseline gap-1 mt-2">
                    <span className="text-3xl font-extrabold">{tier.price}</span>
                    <span className={`text-sm ${tier.primary ? 'text-teal-200' : 'text-muted-foreground'}`}>{tier.period}</span>
                  </div>
                  <p className={`text-sm mt-1 ${tier.primary ? 'text-teal-200' : 'text-muted-foreground'}`}>{tier.desc}</p>
                  <ul className="mt-5 space-y-2">
                    {tier.features.map(f => (
                      <li key={f} className="flex items-center gap-2 text-sm">
                        <Check className={`w-4 h-4 ${tier.primary ? 'text-teal-200' : 'text-green-500'}`} />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <a href={appUrl('/login')} className={`block mt-6 text-center py-2.5 rounded-lg font-medium text-sm transition-colors ${
                    tier.primary ? 'bg-white text-teal-600 hover:bg-teal-500/10' : 'bg-muted text-muted-foreground hover:bg-accent'
                  }`}>
                    {tier.cta}
                  </a>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ SECTION 8: SEE IT LIVE ═══ */}
      <section className="py-16 px-6 bg-muted text-foreground">
        <div className="max-w-3xl mx-auto text-center">
          <FadeUp>
            <h2 className="text-2xl font-bold mb-3">See it live with your data in 10 minutes</h2>
            <p className="text-muted-foreground text-sm mb-6">Connect your M365 tenant. Watch KavachIQ discover your org, score criticality, and build a recovery plan — in real time.</p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <a href={appUrl('/login?register=true')} className="px-6 py-3 bg-gradient-to-r from-teal-500 to-cyan-500 text-white font-semibold rounded-xl hover:from-teal-400 hover:to-cyan-400 transition-all shadow-lg shadow-teal-500/25 hover:shadow-teal-500/40 flex items-center gap-2">
                Start Free <ArrowRight className="w-4 h-4" />
              </a>
              <Link to="/contact" className="px-6 py-3 bg-card text-foreground font-medium rounded-xl hover:bg-secondary transition-colors border border-border">
                Book a Demo
              </Link>
            </div>
            <p className="text-muted-foreground text-xs mt-4">Free for up to 25 users. No credit card. SOC 2 + GDPR + HIPAA + DORA ready.</p>
          </FadeUp>
        </div>
      </section>

      {/* ═══ SECTION 9: FAQ ═══ */}
      <section className="py-20 px-6">
        <div className="max-w-3xl mx-auto">
          <FadeUp>
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-foreground">Frequently Asked Questions</h2>
            </div>
          </FadeUp>
          <div className="space-y-3">
            {[
              { q: 'How is KavachIQ different from Microsoft\'s built-in backup?', a: 'Microsoft 365 has a 93-day recycle bin — not a backup. KavachIQ provides unlimited point-in-time restore, criticality-ordered recovery plans, and anomaly detection that Microsoft doesn\'t offer.' },
              { q: 'Do you store my Microsoft credentials?', a: 'No. KavachIQ uses OAuth admin consent — your Global Admin approves read-only access via Microsoft\'s consent flow. We never see or store your password. Only a scoped API token is used.' },
              { q: 'What happens during a ransomware attack?', a: 'KavachIQ detects anomalies in real-time during backup (mass encryption, unusual deletions). It auto-pauses backups, isolates the clean snapshot, and provides a one-click recovery plan — identity first, then critical users, then everyone else.' },
              { q: 'How does criticality-ordered backup work?', a: 'KavachIQ reads your Microsoft Graph to discover org hierarchy, VIP groups, and privileged roles. Each user gets a 4-factor criticality score. Your CEO is backed up first, then VPs, then directors, then everyone else — automatically.' },
              { q: 'Can I choose which workloads to protect?', a: 'Yes. KavachIQ uses an opt-in model. You enable only the workloads you need (e.g., Exchange + Entra ID). Each workload gets its own consent URL with only the permissions it needs. Community tier includes 2 workloads; Professional includes all 5.' },
              { q: 'Can end users restore their own data?', a: 'Yes. The Self-Service Restore portal lets users search and recover their own emails, files, and contacts without opening a support ticket. Role-based access ensures they only see their own data.' },
              { q: 'Can I self-host KavachIQ?', a: 'Yes. KavachIQ is open source under Apache 2.0. Deploy to your own Azure subscription, AWS, or on-premises infrastructure. Your data never leaves your environment.' },
              { q: 'What\'s included in the free tier?', a: 'Up to 25 objects across 2 workloads of your choice. Basic Smart Engine, self-service restore, 30-day retention, and community support. No credit card required.' },
            ].map((faq, i) => (
              <FadeUp key={i} delay={i * 50}>
                <details className="group bg-card border border-border rounded-xl overflow-hidden hover:border-teal-500/20 transition-all">
                  <summary className="flex items-center justify-between px-5 py-4 cursor-pointer text-foreground font-medium text-sm">
                    {faq.q}
                    <ChevronRight className="w-4 h-4 text-muted-foreground transition-transform group-open:rotate-90" />
                  </summary>
                  <div className="px-5 pb-4 text-sm text-muted-foreground leading-relaxed">
                    {faq.a}
                  </div>
                </details>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ SECTION 10: FINAL CTA ═══ */}
      <section className="py-20 px-6 bg-gradient-to-br from-teal-600 to-cyan-700">
        <div className="max-w-3xl mx-auto text-center text-white">
          <FadeUp>
            <h2 className="text-3xl font-bold mb-4">Ready to prove you can recover?</h2>
            <p className="text-teal-100 mb-8">Most backup vendors prove you can back up. KavachIQ proves you can recover.</p>
            <a href={appUrl('/login?register=true')} className="inline-flex items-center gap-2 px-8 py-3.5 bg-white text-teal-700 font-semibold rounded-xl hover:bg-teal-500/10 transition-colors text-lg">
              Get Started Free <ArrowRight className="w-5 h-5" />
            </a>
          </FadeUp>
        </div>
      </section>

      {/* ═══ FOOTER ═══ */}
      <footer className="py-12 px-6 bg-muted text-muted-foreground">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Shield className="w-5 h-5 text-teal-400" />
                <span className="font-semibold text-foreground">KavachIQ</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                SaaS Data Protection Platform.<br />
                Open source. Self-hosted. Secure.
              </p>
            </div>
            <div>
              <div className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">Product</div>
              <div className="space-y-2 text-sm">
                <a href="#workloads" className="block hover:text-foreground">Workloads</a>
                <a href="#pricing" className="block hover:text-foreground">Pricing</a>
                <a href="#security" className="block hover:text-foreground">Security</a>
                <Link to="/docs" className="block hover:text-foreground">Documentation</Link>
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">Company</div>
              <div className="space-y-2 text-sm">
                <Link to="/about" className="block hover:text-foreground">About</Link>
                <Link to="/contact" className="block hover:text-foreground">Contact</Link>
                <a href="https://github.com/gpatwa/m365-vault" className="block hover:text-foreground">GitHub</a>
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">Legal</div>
              <div className="space-y-2 text-sm">
                <Link to="/legal?tab=tos" className="block hover:text-foreground">Terms of Service</Link>
                <Link to="/legal?tab=privacy" className="block hover:text-foreground">Privacy Policy</Link>
              </div>
            </div>
          </div>
          <div className="border-t border-border pt-6 text-center text-xs text-muted-foreground">
            &copy; {new Date().getFullYear()} KavachIQ. Open source under Apache 2.0 License.
          </div>
        </div>
      </footer>
    </div>
  );
}
