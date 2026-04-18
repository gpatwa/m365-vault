import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Shield, Mail, HardDrive, Globe, MessageSquare, KeyRound,
  AlertTriangle, ArrowRight, Check,
  Eye, Brain, ShieldCheck, ChevronRight, Scale,
  Users, Server, FileSearch, GitBranch, CheckCircle2,
} from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { appUrl } from '../utils/appUrl';

// ── Scroll animation hook ──
// IntersectionObserver handles both initial (already-in-view) and scroll-triggered
// visibility. The observer fires on the first animation frame after observe(), so
// elements already in the viewport animate in within ~16ms.
function useInView(threshold = 0.05) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
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

// ── Cyber Recovery Story — Cinematic 6-Phase Animation ──
function CyberRecoveryStory() {
  const { ref, inView } = useInView(0.05);
  const [phase, setPhase] = useState(0);
  const [autoPlay, setAutoPlay] = useState(true);

  useEffect(() => {
    if (!inView || !autoPlay) return;
    const PHASE_DELAY = 2000;
    const PAUSE_AT_END = 3000;
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

  const PHASES = [
    { num: 1, label: 'PROTECT', emoji: '🛡️', color: 'from-blue-500 to-blue-600', border: 'border-blue-500/40', bg: 'bg-muted', glow: 'shadow-blue-500/10',
      title: 'Snapshot identity and workload state',
      detail: 'Entra ID config · Exchange · OneDrive · SharePoint · Teams',
      visual: '████████████████ 100%',
      items: ['🔑 188 Entra ID objects captured', '📧 2,847 mailboxes snapshotted', '📁 1,203 sites protected', '🛡️ WORM lock: 30 days'] },
    { num: 2, label: 'MONITOR', emoji: '🧠', color: 'from-blue-400 to-indigo-500', border: 'border-indigo-500/40', bg: 'bg-muted', glow: 'shadow-indigo-500/10',
      title: 'Learn baselines for your tenant',
      detail: 'Change rate · group membership · conditional access drift',
      visual: '📊 ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁',
      items: ['Item count: 5,130 ± 42', 'CA policies: 24 (stable)', 'Privileged roles: 8 (stable)', 'Error rate: 1.2% ± 0.3%'] },
    { num: 3, label: 'DETECT', emoji: '🚨', color: 'from-rose-500 to-red-600', border: 'border-rose-500/50', bg: 'bg-muted', glow: 'shadow-rose-500/20',
      title: 'Anomaly: mass rename across OneDrive',
      detail: 'Z-score 8.4 · severity CRITICAL · identity changes flagged',
      visual: '🔴 ▁▂▃▄▅▆▇████████████',
      items: ['OneDrive: 1,847 files changed', 'Global Admin count: +2 (alert)', 'MFA disabled on 3 users', 'Affected: 3 user accounts'] },
    { num: 4, label: 'ASSESS', emoji: '🔍', color: 'from-amber-400 to-amber-500', border: 'border-amber-500/40', bg: 'bg-muted', glow: 'shadow-amber-500/10',
      title: 'Blast radius identified',
      detail: 'Affected identities · policies · data · priority order',
      visual: '🔒 Clean snapshot #847 selected',
      items: ['✅ Last clean: 2h ago (#847)', '🔐 3 policies reverted', '👥 MVB users scored', '📋 Recovery plan generated'] },
    { num: 5, label: 'RECOVER', emoji: '🔄', color: 'from-blue-400 to-blue-500', border: 'border-blue-500/40', bg: 'bg-muted', glow: 'shadow-blue-500/10',
      title: 'Guided restore in recovery order',
      detail: 'Identity first · critical users next · business data after',
      visual: '████████████░░░░ 78%',
      items: ['🔑 Entra ID restored (5 min)', '👔 MVB users online (15 min)', '📁 Business data restoring', '✅ Recovery verified'] },
    { num: 6, label: 'VERIFY', emoji: '✅', color: 'from-emerald-400 to-green-500', border: 'border-emerald-500/40', bg: 'bg-muted', glow: 'shadow-emerald-500/10',
      title: 'Recovery confidence verified',
      detail: 'Checksums match · policies active · users can sign in',
      visual: '████████████████ 100% ✓',
      items: ['✅ 5,130 items verified', '✅ Entra ID policies active', '✅ MFA re-enforced on all users', '✅ Incident report generated'] },
  ];

  const current = PHASES[phase > 0 ? phase - 1 : 0];

  return (
    <div ref={ref} className="max-w-5xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-8 relative">
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

      {phase > 0 && (
        <div className={`relative rounded-2xl border overflow-hidden transition-all duration-700 ${current.border} ${current.bg} shadow-2xl ${current.glow}`}>
          {phase === 3 && (
            <div className="absolute inset-0 bg-red-500/5 animate-pulse" />
          )}
          <div className="relative p-8">
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
            <div className="bg-black/30 rounded-xl p-4 mb-6 font-mono text-sm">
              <div className="text-muted-foreground mb-1">$ kavachiq status</div>
              <div className={`transition-all duration-500 ${phase === 3 ? 'text-red-400' : phase >= 5 ? 'text-green-400' : 'text-blue-400'}`}>
                {current.visual}
              </div>
            </div>
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

      {phase === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <div className="text-4xl mb-3 animate-pulse">🎬</div>
          <p className="text-sm">Scroll to watch a recovery scenario.</p>
        </div>
      )}

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

// ── Workloads protected ──
const WORKLOADS = [
  { icon: KeyRound, label: 'Microsoft Entra', desc: '12 identity object types, policy drift, role changes', color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
  { icon: Mail, label: 'Exchange Online', desc: 'Mailboxes, calendars, contacts', color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
  { icon: HardDrive, label: 'OneDrive', desc: 'User files and folders', color: 'text-purple-400 bg-purple-500/10 border-purple-500/20' },
  { icon: Globe, label: 'SharePoint', desc: 'Sites, lists, documents', color: 'text-green-400 bg-green-500/10 border-green-500/20' },
  { icon: MessageSquare, label: 'Teams', desc: 'Chats, channels, files', color: 'text-pink-400 bg-pink-500/10 border-pink-500/20' },
];

// ── What breaks in a real M365 incident ──
const PROBLEMS = [
  { icon: KeyRound, title: 'Compromised identities', desc: 'Attackers disable MFA, grant themselves Global Admin, or add service principals with elevated rights.' },
  { icon: Shield, title: 'Policy and role drift', desc: 'Conditional access, administrative units, and role assignments are quietly modified and hard to revert.' },
  { icon: AlertTriangle, title: 'Destructive deletions', desc: 'Mailboxes, SharePoint sites, Teams, or entire groups deleted. Recycle bins fill up. Some items are unrecoverable after 30 or 93 days.' },
  { icon: HardDrive, title: 'Ransomware and encryption', desc: 'Files renamed in bulk across OneDrive and SharePoint. Versioning alone rarely gets the business back to a usable state.' },
  { icon: Users, title: 'Group membership changes', desc: 'Security group and license group membership shifts silently, breaking access for real users.' },
  { icon: MessageSquare, title: 'Blast radius unknown', desc: 'Who was affected, what changed, and what to restore first is the hardest part of any incident.' },
];

// ── Product capability pillars ──
const PILLARS = [
  { icon: KeyRound, title: 'Entra Recovery', desc: 'Snapshot and restore 12 Entra ID object types: users, groups, roles, conditional access, OAuth grants, service principals, and more.', color: 'from-amber-500 to-orange-500' },
  { icon: Brain, title: 'Criticality-Based Recovery', desc: 'Score every user and workload by role weight, data sensitivity, activity, and business dependency. Recover what matters first.', color: 'from-teal-500 to-cyan-500' },
  { icon: FileSearch, title: 'Blast Radius Analysis', desc: 'See exactly what changed, who was affected, and which systems are at risk. Diff identity and data state across snapshots.', color: 'from-rose-500 to-red-500' },
  { icon: GitBranch, title: 'Guided Recovery Plans', desc: 'Pre-computed NIST-aligned plans: identity first, critical users next, business data after. Refreshed on a schedule, ready when you need them.', color: 'from-green-500 to-emerald-500' },
  { icon: HardDrive, title: 'Microsoft 365 Data Recovery', desc: 'Unlimited point-in-time restore across Exchange, OneDrive, SharePoint, and Teams. Granular per-item and workload-wide restore.', color: 'from-blue-500 to-indigo-500' },
  { icon: CheckCircle2, title: 'Recovery Verification', desc: 'Recovery confidence scored with evidence. Checksum validation, policy-active checks, and sign-in tests confirm you are actually back online.', color: 'from-purple-500 to-violet-500' },
];

// ── Category comparison (not vendor-by-vendor) ──
type CellVal = boolean | 'partial';
interface CompareRow { feature: string; kavachiq: CellVal; native: CellVal; backup: CellVal; manual: CellVal; suite: CellVal; }
const CATEGORY_COMPARE: CompareRow[] = [
  { feature: 'Identity-first recovery sequencing', kavachiq: true, native: false, backup: false, manual: false, suite: 'partial' },
  { feature: 'Entra ID config snapshot and diff', kavachiq: true, native: 'partial', backup: 'partial', manual: false, suite: 'partial' },
  { feature: 'Criticality-based restore order', kavachiq: true, native: false, backup: false, manual: false, suite: false },
  { feature: 'Blast radius analysis', kavachiq: true, native: false, backup: false, manual: false, suite: 'partial' },
  { feature: 'Pre-computed recovery plans', kavachiq: true, native: false, backup: false, manual: false, suite: 'partial' },
  { feature: 'Unified M365 data recovery', kavachiq: true, native: 'partial', backup: true, manual: false, suite: true },
  { feature: 'Recovery verification with evidence', kavachiq: true, native: false, backup: 'partial', manual: false, suite: 'partial' },
];

function Cell({ v }: { v: boolean | 'partial' }) {
  if (v === true) return <Check className="w-5 h-5 text-green-500 mx-auto" />;
  if (v === 'partial') return <span className="text-xs text-amber-400 font-medium">partial</span>;
  return <span className="text-xs text-muted-foreground">—</span>;
}

// ═══════════════════════════════════════════════════════
// LANDING PAGE
// ═══════════════════════════════════════════════════════
export default function Landing() {
  const [heroReady, setHeroReady] = useState(false);
  useEffect(() => { setTimeout(() => setHeroReady(true), 100); }, []);

  return (
    <div className="min-h-screen bg-background">
      <Helmet>
        <title>KavachIQ — Identity-First Cyber Recovery for Microsoft 365</title>
        <meta name="description" content="KavachIQ is the identity-first cyber recovery platform for Microsoft Entra and Microsoft 365. Assess blast radius, restore identity first, recover critical users next, verify business recovery." />
        <link rel="canonical" href="https://kavachiq.com/welcome" />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://kavachiq.com/welcome" />
        <meta property="og:title" content="KavachIQ — Identity-First Cyber Recovery for Microsoft 365" />
        <meta property="og:description" content="Recover Microsoft 365 safely, starting with identity. Assess blast radius, restore Entra controls first, recover critical users next." />
        <meta property="og:image" content="https://kavachiq.com/og-welcome.jpg" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="KavachIQ — Identity-First Cyber Recovery for Microsoft 365" />
        <meta name="twitter:description" content="Recover Microsoft 365 safely, starting with identity. Assess blast radius, restore Entra controls first, recover critical users next." />
        <meta name="twitter:image" content="https://kavachiq.com/og-welcome.jpg" />
        <script type="application/ld+json">{JSON.stringify({
          "@context": "https://schema.org",
          "@type": "SoftwareApplication",
          "name": "KavachIQ",
          "applicationCategory": "SecurityApplication",
          "applicationSubCategory": "Cyber Recovery for Microsoft 365",
          "operatingSystem": "Cloud",
          "description": "Identity-first cyber recovery platform for Microsoft Entra and Microsoft 365. Helps teams assess blast radius, restore identity controls first, recover critical users next, and verify business recovery.",
          "url": "https://kavachiq.com",
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
            <a href="#platform" className="hover:text-foreground">Platform</a>
            <a href="#how-it-works" className="hover:text-foreground">How It Works</a>
            <Link to="/tour" className="hover:text-foreground">Product Tour</Link>
            <Link to="/security" className="hover:text-foreground">Security</Link>
            <Link to="/about" className="hover:text-foreground">About</Link>
            <Link to="/contact" className="hover:text-foreground">Contact</Link>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <a href={appUrl('/login')} className="hidden sm:inline text-sm text-muted-foreground hover:text-foreground">Sign In</a>
            <Link to="/contact" className="px-4 py-1.5 bg-gradient-to-r from-teal-500 to-cyan-500 text-white text-sm font-medium rounded-lg hover:from-teal-400 hover:to-cyan-400 transition-all shadow-lg shadow-teal-500/20">
              Request a Demo
            </Link>
          </div>
        </div>
      </nav>

      {/* ═══ 1. HERO ═══ */}
      <section className="pt-28 pb-16 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className={`inline-flex items-center gap-2 px-3 py-1 bg-teal-500/10 text-teal-400 rounded-full text-xs font-medium mb-6 transition-all duration-500 ${heroReady ? 'opacity-100' : 'opacity-0'}`}>
            <Shield className="w-3.5 h-3.5" />
            Identity-first cyber recovery for Microsoft Entra and Microsoft 365
          </div>

          <h1 className={`text-3xl md:text-5xl font-extrabold text-foreground leading-[1.1] tracking-tight transition-all duration-700 delay-200 ${heroReady ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}>
            Recover Microsoft 365 safely,{' '}
            <br className="hidden md:block" />
            <span className="bg-gradient-to-r from-teal-500 to-cyan-500 bg-clip-text text-transparent">
              starting with identity.
            </span>
          </h1>

          <p className={`mt-6 text-lg text-muted-foreground max-w-2xl mx-auto transition-all duration-700 delay-500 ${heroReady ? 'opacity-100' : 'opacity-0'}`}>
            KavachIQ helps Microsoft 365 teams assess blast radius, restore Microsoft Entra controls first, recover critical users next, and bring business data back online with confidence.
          </p>

          <div className={`mt-8 flex flex-col sm:flex-row items-center justify-center gap-4 transition-all duration-700 delay-700 ${heroReady ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
            <Link to="/contact" className="px-6 py-3 bg-teal-600 text-white font-semibold rounded-xl hover:bg-teal-700 transition-all hover:shadow-lg hover:shadow-teal-200/20 flex items-center gap-2">
              Request a Demo <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/tour" className="px-6 py-3 border border-teal-500/30 text-teal-400 font-medium rounded-xl hover:bg-teal-500/10 transition-colors flex items-center gap-2">
              <Eye className="w-4 h-4" /> See the Product Tour
            </Link>
          </div>

          <div className={`mt-12 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto transition-all duration-700 delay-900 ${heroReady ? 'opacity-100' : 'opacity-0'}`}>
            <div className="text-center">
              <div className="text-xl font-bold text-teal-500">Entra First</div>
              <div className="text-xs text-muted-foreground mt-1">Restore identity before data</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-cyan-500">Blast Radius</div>
              <div className="text-xs text-muted-foreground mt-1">See what changed, who is affected</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-green-500">Guided Recovery</div>
              <div className="text-xs text-muted-foreground mt-1">Pre-computed, business-safe order</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-foreground">Microsoft-Native</div>
              <div className="text-xs text-muted-foreground mt-1">Built on Microsoft Graph</div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ 2. PROBLEM — What breaks in M365 incidents ═══ */}
      <section className="py-20 px-6 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-foreground">What actually breaks in a Microsoft 365 incident</h2>
              <p className="text-muted-foreground mt-2 max-w-2xl mx-auto">Real incidents rarely look like a clean data-loss event. They involve identity changes, destructive admin actions, and a tangle of affected users and systems.</p>
            </div>
          </FadeUp>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {PROBLEMS.map((p, i) => (
              <FadeUp key={p.title} delay={i * 80}>
                <div className="bg-card border border-border rounded-xl p-5 h-full">
                  <div className="w-9 h-9 rounded-lg bg-rose-500/10 flex items-center justify-center mb-3">
                    <p.icon className="w-5 h-5 text-rose-400" />
                  </div>
                  <h3 className="font-semibold text-foreground mb-1.5">{p.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{p.desc}</p>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ 3. WHY BACKUP ALONE IS NOT ENOUGH ═══ */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <FadeUp>
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-foreground">Why backup alone is not enough</h2>
              <p className="text-muted-foreground mt-2 max-w-2xl mx-auto">Backup preserves data. Recovery is a different problem.</p>
            </div>
          </FadeUp>
          <FadeUp delay={150}>
            <div className="bg-card border border-border rounded-xl p-7 space-y-5 text-sm text-muted-foreground leading-relaxed">
              <p>
                Microsoft 365 and third-party backup products do the first job well: they keep copies of mailboxes, sites, files, and increasingly identity configuration. That matters.
              </p>
              <p>
                Recovery is where most teams struggle. When an incident happens, the question is not "do I have a backup?" It is "what changed, who is affected, what do I restore first, and how do I know we are actually back online?"
              </p>
              <p className="text-foreground font-medium">
                KavachIQ focuses on the recovery problem: understanding blast radius, restoring identity controls first, sequencing critical users and systems, and verifying business recovery with evidence.
              </p>
            </div>
          </FadeUp>
        </div>
      </section>

      {/* ═══ 4. WHAT KAVACHIQ DOES ═══ */}
      <section id="platform" className="py-20 px-6 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-foreground">A six-phase recovery workflow for Microsoft 365</h2>
              <p className="text-muted-foreground mt-2 max-w-2xl mx-auto">Protect, Monitor, Detect, Assess, Recover, Verify. Each phase is purpose-built for identity-first Microsoft 365 recovery.</p>
            </div>
          </FadeUp>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { step: '01', title: 'Protect', desc: 'Capture protected identity and workload state across Microsoft Entra and Microsoft 365. Snapshot policies, roles, groups, OAuth grants, and data.' },
              { step: '02', title: 'Monitor', desc: 'Track ongoing workload and identity activity. Baselines for change rate, privileged role counts, and conditional access drift.' },
              { step: '03', title: 'Detect', desc: 'Flag destructive changes, ransomware-like activity, and suspicious identity drift with evidence.' },
              { step: '04', title: 'Assess', desc: 'Compute blast radius. Diff state across snapshots. Identify affected users, identities, policies, and workloads.' },
              { step: '05', title: 'Recover', desc: 'Execute identity-first restore and rollback in the safest business order. Guided by pre-computed recovery plans.' },
              { step: '06', title: 'Verify', desc: 'Confirm business recovery with checksum validation, policy-active checks, and sign-in validation.' },
            ].map((s, i) => (
              <FadeUp key={s.title} delay={i * 100}>
                <div className="bg-card border border-border rounded-xl p-5 h-full">
                  <div className="text-xs font-bold text-teal-500 tracking-wider mb-2">STEP {s.step}</div>
                  <h3 className="font-semibold text-foreground text-lg mb-1.5">{s.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{s.desc}</p>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ 5. WHY IDENTITY-FIRST MATTERS ═══ */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-foreground">Why identity-first recovery matters</h2>
              <p className="text-muted-foreground mt-2 max-w-2xl mx-auto">Data recovery without identity recovery is incomplete.</p>
            </div>
          </FadeUp>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FadeUp delay={100}>
              <div className="bg-card border border-border rounded-xl p-6 h-full">
                <h3 className="font-semibold text-foreground mb-3">Identity controls the blast radius</h3>
                <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                  Admins, privileged roles, conditional access policies, OAuth grants, and group membership decide who has access to what.
                </p>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li className="flex items-start gap-2"><Check className="w-4 h-4 text-teal-500 mt-0.5 shrink-0" /> Global Admin and privileged role assignments</li>
                  <li className="flex items-start gap-2"><Check className="w-4 h-4 text-teal-500 mt-0.5 shrink-0" /> Conditional access policies and MFA enforcement</li>
                  <li className="flex items-start gap-2"><Check className="w-4 h-4 text-teal-500 mt-0.5 shrink-0" /> Service principals, OAuth grants, app consent</li>
                  <li className="flex items-start gap-2"><Check className="w-4 h-4 text-teal-500 mt-0.5 shrink-0" /> Security group and license group membership</li>
                </ul>
              </div>
            </FadeUp>
            <FadeUp delay={200}>
              <div className="bg-card border border-border rounded-xl p-6 h-full">
                <h3 className="font-semibold text-foreground mb-3">Restore in the right order</h3>
                <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                  Recovering mailboxes before restoring identity controls is unsafe. Attackers and broken policies stay in place until identity is corrected.
                </p>
                <ol className="space-y-2 text-sm text-muted-foreground">
                  <li className="flex items-start gap-2"><span className="text-xs font-bold text-teal-500 w-5 shrink-0">01</span><span>Identity controls: roles, policies, OAuth grants</span></li>
                  <li className="flex items-start gap-2"><span className="text-xs font-bold text-teal-500 w-5 shrink-0">02</span><span>Critical users: executives, admins, compliance owners</span></li>
                  <li className="flex items-start gap-2"><span className="text-xs font-bold text-teal-500 w-5 shrink-0">03</span><span>High-priority departments and sites</span></li>
                  <li className="flex items-start gap-2"><span className="text-xs font-bold text-teal-500 w-5 shrink-0">04</span><span>Full business data, verified end-to-end</span></li>
                </ol>
              </div>
            </FadeUp>
          </div>
        </div>
      </section>

      {/* ═══ 6. PRODUCT CAPABILITIES / PILLARS ═══ */}
      <section className="py-20 px-6 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-foreground">Purpose-built for Microsoft 365 recovery</h2>
              <p className="text-muted-foreground mt-2 max-w-2xl mx-auto">Six capabilities that work together to get you back online.</p>
            </div>
          </FadeUp>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {PILLARS.map((f, i) => (
              <FadeUp key={f.title} delay={i * 100}>
                <div className="bg-card rounded-xl p-6 border border-border hover:border-teal-500/30 transition-all hover:shadow-lg hover:shadow-teal-500/5 h-full">
                  <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${f.color} flex items-center justify-center mb-4`}>
                    <f.icon className="w-5 h-5 text-white" />
                  </div>
                  <h3 className="font-semibold mb-2 text-foreground">{f.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
                </div>
              </FadeUp>
            ))}
          </div>

          {/* Workload strip */}
          <FadeUp delay={400}>
            <div className="mt-12">
              <div className="text-center text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Protected workloads</div>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {WORKLOADS.map((wl) => (
                  <div key={wl.label} className={`border rounded-xl p-4 text-center ${wl.color}`}>
                    <wl.icon className="w-6 h-6 mx-auto mb-2" />
                    <div className="font-semibold text-sm">{wl.label}</div>
                    <div className="text-[11px] mt-1 opacity-70">{wl.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          </FadeUp>
        </div>
      </section>

      {/* ═══ 7. HOW IT WORKS — Cinematic Animation ═══ */}
      <section id="how-it-works" className="py-20 px-6 bg-gradient-to-b from-background via-background to-muted">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-teal-500/10 text-teal-400 rounded-full text-xs font-medium mb-4">
                <Eye className="w-3.5 h-3.5" /> Recovery scenario
              </div>
              <h2 className="text-3xl font-bold text-foreground">How a recovery actually unfolds</h2>
              <p className="text-muted-foreground mt-2 max-w-xl mx-auto">KavachIQ moves through six phases: protect, monitor, detect, assess, recover, verify.</p>
            </div>
          </FadeUp>
          <CyberRecoveryStory />
        </div>
      </section>

      {/* ═══ 8. WHY KAVACHIQ — Category comparison ═══ */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-foreground">Why KavachIQ</h2>
              <p className="text-muted-foreground mt-2 max-w-2xl mx-auto">Recovery is a specialized problem. Compare how different approaches handle it.</p>
            </div>
          </FadeUp>
          <FadeUp delay={200}>
            <div className="bg-card rounded-xl border border-border overflow-x-auto">
              <table className="w-full text-sm min-w-[720px]">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="text-left px-5 py-3 font-medium text-foreground">Capability</th>
                    <th className="text-center px-5 py-3 font-semibold text-teal-500">KavachIQ</th>
                    <th className="text-center px-5 py-3 font-medium text-foreground">Native M365 tools</th>
                    <th className="text-center px-5 py-3 font-medium text-foreground">Generic backup</th>
                    <th className="text-center px-5 py-3 font-medium text-foreground">Manual restore</th>
                    <th className="text-center px-5 py-3 font-medium text-foreground">Broad cyber suites</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {CATEGORY_COMPARE.map(row => (
                    <tr key={row.feature} className="hover:bg-muted/50">
                      <td className="px-5 py-3 text-foreground">{row.feature}</td>
                      <td className="px-5 py-3 text-center"><Cell v={row.kavachiq} /></td>
                      <td className="px-5 py-3 text-center"><Cell v={row.native} /></td>
                      <td className="px-5 py-3 text-center"><Cell v={row.backup} /></td>
                      <td className="px-5 py-3 text-center"><Cell v={row.manual} /></td>
                      <td className="px-5 py-3 text-center"><Cell v={row.suite} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </FadeUp>
          <FadeUp delay={300}>
            <p className="text-xs text-muted-foreground text-center mt-4 max-w-2xl mx-auto">
              KavachIQ is purpose-built for identity-first Microsoft 365 recovery. Other categories solve adjacent problems.
            </p>
          </FadeUp>
        </div>
      </section>

      {/* ═══ 9. BUYER RELEVANCE ═══ */}
      <section className="py-20 px-6 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-foreground">Built for the people who actually run recovery</h2>
              <p className="text-muted-foreground mt-2 max-w-2xl mx-auto">Operator-grade workflows. Enterprise-ready trust.</p>
            </div>
          </FadeUp>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { icon: Server, title: 'Microsoft 365 and Entra admins', desc: 'A practical recovery workflow for the people inside Microsoft 365 every day. Built on Microsoft Graph with tenant-scoped access.', bullets: ['Identity and data in one workflow', 'Granular, per-item restore', 'Minimal setup, tenant-scoped'] },
              { icon: ShieldCheck, title: 'IT and security leaders', desc: 'Know your recovery time, recovery order, and recovery confidence before an incident happens. Close the gap between backup and business recovery.', bullets: ['Pre-computed recovery plans', 'Recovery verification with evidence', 'Aligned to NIST SP 800-184'] },
              { icon: Scale, title: 'Procurement and risk', desc: 'Enterprise controls on day one. Per-tenant keys, audit trail, and compliance-mapped safeguards for SOC 2, GDPR, HIPAA, and DORA reviews.', bullets: ['AES-256-GCM, per-tenant keys', 'Full audit trail', 'Compliance-mapped evidence'] },
            ].map((p, i) => (
              <FadeUp key={p.title} delay={i * 150}>
                <div className="bg-card border border-border rounded-xl p-6 h-full">
                  <div className="w-10 h-10 rounded-lg bg-teal-500/10 flex items-center justify-center mb-4">
                    <p.icon className="w-5 h-5 text-teal-400" />
                  </div>
                  <h3 className="font-semibold text-foreground mb-2">{p.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed mb-3">{p.desc}</p>
                  <ul className="space-y-1.5 text-sm text-muted-foreground">
                    {p.bullets.map(b => (
                      <li key={b} className="flex items-start gap-2"><Check className="w-4 h-4 text-teal-500 mt-0.5 shrink-0" /> {b}</li>
                    ))}
                  </ul>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ SECURITY STRIP ═══ */}
      <section id="security" className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-foreground">Enterprise-grade security</h2>
              <p className="text-muted-foreground mt-2">Encryption, immutability, and compliance controls on day one.</p>
            </div>
          </FadeUp>
          <div className="flex flex-wrap items-center justify-center gap-3">
            {[
              { icon: '🔒', label: 'AES-256-GCM', desc: 'Encryption at Rest' },
              { icon: '🔑', label: 'Per-Tenant Keys', desc: 'Key Isolation' },
              { icon: '🛡️', label: 'WORM Storage', desc: 'Immutable Backups' },
              { icon: '✅', label: 'SOC 2', desc: '16 controls mapped' },
              { icon: '🇪🇺', label: 'GDPR', desc: '8 articles mapped' },
              { icon: '🏥', label: 'HIPAA', desc: '14 safeguards mapped' },
              { icon: '🔐', label: 'SSO + MFA', desc: 'Entra ID OIDC' },
              { icon: '📋', label: 'Audit Trail', desc: 'Full logging' },
            ].map(b => (
              <div key={b.label} className="flex items-center gap-2.5 px-4 py-2.5 bg-card/50 backdrop-blur-sm border border-border rounded-xl">
                <span className="text-lg">{b.icon}</span>
                <div>
                  <div className="text-xs font-semibold text-foreground">{b.label}</div>
                  <div className="text-[10px] text-muted-foreground">{b.desc}</div>
                </div>
              </div>
            ))}
          </div>
          <div className="text-center mt-6">
            <Link to="/security" className="text-sm text-teal-500 hover:text-teal-400 font-medium">
              View full security posture <ChevronRight className="w-3.5 h-3.5 inline" />
            </Link>
          </div>
        </div>
      </section>

      {/* ═══ 10. FINAL CTA ═══ */}
      <section className="py-20 px-6 bg-gradient-to-br from-teal-600 to-cyan-700">
        <div className="max-w-3xl mx-auto text-center text-white">
          <FadeUp>
            <h2 className="text-3xl font-bold mb-4">See KavachIQ in your Microsoft 365 environment</h2>
            <p className="text-teal-100 mb-8 max-w-xl mx-auto">Request a walkthrough with a recovery engineer. Bring your questions about Entra, ransomware, or a specific incident scenario.</p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link to="/contact" className="inline-flex items-center gap-2 px-8 py-3.5 bg-white text-teal-700 font-semibold rounded-xl hover:bg-teal-500/10 transition-colors text-lg">
                Request a Demo <ArrowRight className="w-5 h-5" />
              </Link>
              <Link to="/tour" className="inline-flex items-center gap-2 px-8 py-3.5 border border-white/30 text-white font-medium rounded-xl hover:bg-white/10 transition-colors text-lg">
                See the Product Tour
              </Link>
            </div>
            <p className="mt-6 text-sm text-teal-100">
              Or read a recovery scenario:{' '}
              <Link to="/scenarios/compromised-global-admin" className="underline underline-offset-2 hover:text-white">
                compromised Global Admin
              </Link>
              {' '}&middot;{' '}
              <Link to="/scenarios/destructive-sharepoint-onedrive-deletion" className="underline underline-offset-2 hover:text-white">
                destructive deletion
              </Link>
            </p>
          </FadeUp>
        </div>
      </section>

      {/* ═══ FOOTER ═══ */}
      <footer className="py-12 px-6 bg-muted text-muted-foreground">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-8">
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-2 mb-4">
                <Shield className="w-5 h-5 text-teal-400" />
                <span className="font-semibold text-foreground">KavachIQ</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Identity-first cyber recovery<br />
                for Microsoft Entra and<br />
                Microsoft 365.
              </p>
            </div>
            <div>
              <div className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">Product</div>
              <div className="space-y-2 text-sm">
                <a href="#platform" className="block hover:text-foreground">Platform</a>
                <a href="#how-it-works" className="block hover:text-foreground">How It Works</a>
                <Link to="/tour" className="block hover:text-foreground">Product Tour</Link>
                <Link to="/security" className="block hover:text-foreground">Security</Link>
                <Link to="/docs" className="block hover:text-foreground">Documentation</Link>
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">Recovery Scenarios</div>
              <div className="space-y-2 text-sm">
                <Link to="/scenarios/compromised-global-admin" className="block hover:text-foreground">Compromised Global Admin</Link>
                <Link to="/scenarios/destructive-sharepoint-onedrive-deletion" className="block hover:text-foreground">Destructive Deletion</Link>
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">Company</div>
              <div className="space-y-2 text-sm">
                <Link to="/about" className="block hover:text-foreground">About</Link>
                <Link to="/contact" className="block hover:text-foreground">Contact</Link>
                <Link to="/contact" className="block hover:text-foreground">Request a Demo</Link>
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
            &copy; {new Date().getFullYear()} KavachIQ. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
