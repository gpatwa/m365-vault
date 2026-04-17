import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Shield, AlertTriangle, ArrowRight, CheckCircle, XCircle,
  Eye, Brain, ShieldCheck, RefreshCw,
} from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { appUrl } from '../utils/appUrl';

// ── Scroll animation ──
function useInView(threshold = 0.1) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight && rect.bottom > 0) { setInView(true); return; }
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setInView(true); }, { threshold, rootMargin: '50px' });
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, inView };
}

function FadeUp({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const { ref, inView } = useInView();
  return (
    <div ref={ref} className={`transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}

// ── Demo Data (static, no API calls) ──
const DEMO_USERS = [
  { name: 'Sarah Chen', role: 'CEO', score: 95, tier: 'critical', email: 'sarah@contoso.com', items: 2847 },
  { name: 'Marcus Johnson', role: 'CFO', score: 88, tier: 'critical', email: 'marcus@contoso.com', items: 1923 },
  { name: 'Emily Rodriguez', role: 'General Counsel', score: 82, tier: 'critical', email: 'emily@contoso.com', items: 3156 },
  { name: 'David Kim', role: 'VP Engineering', score: 75, tier: 'high', email: 'david@contoso.com', items: 1456 },
  { name: 'Lisa Thompson', role: 'HR Director', score: 68, tier: 'high', email: 'lisa@contoso.com', items: 987 },
  { name: 'James Wilson', role: 'Sales Manager', score: 45, tier: 'medium', email: 'james@contoso.com', items: 654 },
  { name: 'Priya Patel', role: 'Marketing', score: 35, tier: 'low', email: 'priya@contoso.com', items: 432 },
  { name: 'Alex Turner', role: 'Developer', score: 22, tier: 'low', email: 'alex@contoso.com', items: 289 },
];

const WORKLOADS = [
  { key: 'entra_id', label: 'Entra ID', icon: '🔑', objects: 188, size: '95 KB', status: 'protected' },
  { key: 'exchange', label: 'Exchange', icon: '📧', objects: 8, size: '2.1 GB', status: 'protected' },
  { key: 'onedrive', label: 'OneDrive', icon: '📁', objects: 8, size: '8.5 GB', status: 'protected' },
  { key: 'sharepoint', label: 'SharePoint', icon: '🌐', objects: 6, size: '5.2 GB', status: 'protected' },
  { key: 'teams', label: 'Teams', icon: '💬', objects: 3, size: '0.8 GB', status: 'protected' },
];

const RECOVERY_PHASES = [
  { phase: 1, name: 'Identity Controls', time: '5 min', items: 'Entra ID config, CA policies, roles', color: 'text-red-400', bg: 'bg-red-500/10' },
  { phase: 2, name: 'Critical Users (MVP)', time: '15 min', items: 'CEO, CFO, General Counsel', color: 'text-orange-400', bg: 'bg-orange-500/10' },
  { phase: 3, name: 'High Priority', time: '30 min', items: 'VP Eng, HR Director, Finance', color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  { phase: 4, name: 'Full Recovery', time: '120 min', items: 'All 26 objects across 5 workloads', color: 'text-green-400', bg: 'bg-green-500/10' },
];

// ── Scene Components ──

function SceneDashboard() {
  const [animStep, setAnimStep] = useState(0);
  const { ref, inView } = useInView();

  useEffect(() => {
    if (!inView) return;
    const timers = [300, 600, 900, 1200, 1500].map((d, i) => setTimeout(() => setAnimStep(i + 1), d));
    return () => timers.forEach(clearTimeout);
  }, [inView]);

  return (
    <div ref={ref} className="space-y-4">
      {/* Hero stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Protected', value: '26', sub: 'objects', color: 'text-teal-400' },
          { label: 'Success Rate', value: '95%', sub: 'last 7 days', color: 'text-green-400' },
          { label: 'Health Score', value: '87', sub: '/100', color: 'text-blue-400' },
          { label: 'Recovery Time', value: '170', sub: 'minutes', color: 'text-purple-400' },
        ].map((stat, i) => (
          <div key={stat.label} className={`bg-card border border-border rounded-xl p-4 transition-all duration-500 ${animStep > i ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
            <p className="text-xs text-muted-foreground">{stat.label}</p>
            <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}<span className="text-sm font-normal text-muted-foreground ml-1">{stat.sub}</span></p>
          </div>
        ))}
      </div>

      {/* Workload cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
        {WORKLOADS.map((wl, i) => (
          <div key={wl.key} className={`bg-card border border-border rounded-lg p-3 transition-all duration-500 ${animStep > 1 ? 'opacity-100' : 'opacity-0'}`} style={{ transitionDelay: `${i * 100}ms` }}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">{wl.icon}</span>
              <span className="text-xs font-semibold text-foreground">{wl.label}</span>
            </div>
            <p className="text-[10px] text-muted-foreground">{wl.objects} objects &middot; {wl.size}</p>
            <div className="mt-1.5 flex items-center gap-1">
              <CheckCircle className="w-3 h-3 text-green-500" />
              <span className="text-[10px] text-green-400">Protected</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SceneAttack() {
  const [phase, setPhase] = useState(0);
  const { ref, inView } = useInView();

  useEffect(() => {
    if (!inView) return;
    const timers = [500, 1500, 3000, 4500].map((d, i) => setTimeout(() => setPhase(i + 1), d));
    return () => timers.forEach(clearTimeout);
  }, [inView]);

  return (
    <div ref={ref} className="space-y-4">
      {/* Attack timeline */}
      <div className="bg-card border border-border rounded-xl p-5 space-y-3">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className={`w-5 h-5 transition-colors duration-300 ${phase >= 1 ? 'text-red-500 animate-pulse' : 'text-muted-foreground'}`} />
          <span className={`text-sm font-bold transition-colors ${phase >= 1 ? 'text-red-400' : 'text-muted-foreground'}`}>
            Ransomware Attack Detected
          </span>
          {phase >= 1 && <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-[10px] font-bold rounded-full">CRITICAL</span>}
        </div>

        {[
          { time: '09:14 AM', event: 'Suspicious login from unfamiliar IP (Kazakhstan)', icon: AlertTriangle, show: phase >= 1 },
          { time: '09:17 AM', event: '1,847 Exchange items renamed to .encrypted', icon: XCircle, show: phase >= 2 },
          { time: '09:18 AM', event: 'KavachIQ Smart Engine: Z-score 8.4 — anomaly flagged', icon: Brain, show: phase >= 3 },
          { time: '09:19 AM', event: 'Auto-snapshot triggered, recovery point secured', icon: Shield, show: phase >= 4 },
        ].map((evt, i) => (
          <div key={i} className={`flex items-start gap-3 px-3 py-2 rounded-lg transition-all duration-500 ${evt.show ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'} ${i <= 1 ? 'bg-red-500/5 border border-red-500/10' : i === 2 ? 'bg-amber-500/5 border border-amber-500/10' : 'bg-green-500/5 border border-green-500/10'}`}>
            <evt.icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${i <= 1 ? 'text-red-400' : i === 2 ? 'text-amber-400' : 'text-green-400'}`} />
            <div>
              <p className="text-xs font-mono text-muted-foreground">{evt.time}</p>
              <p className="text-sm text-foreground">{evt.event}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Recovery confidence */}
      {phase >= 4 && (
        <div className="bg-green-500/5 border border-green-500/20 rounded-xl p-4 flex items-center gap-3 animate-in fade-in duration-500">
          <ShieldCheck className="w-8 h-8 text-green-400" />
          <div>
            <p className="text-sm font-bold text-green-400">Recovery Available</p>
            <p className="text-xs text-green-400/70">Last clean backup: 09:13 AM (1 minute before attack). All 1,847 items recoverable.</p>
          </div>
        </div>
      )}
    </div>
  );
}

function SceneRecovery() {
  const [activePhase, setActivePhase] = useState(-1);
  const { ref, inView } = useInView();

  useEffect(() => {
    if (!inView) return;
    const timers = [500, 1500, 2500, 3500].map((d, i) => setTimeout(() => setActivePhase(i), d));
    return () => timers.forEach(clearTimeout);
  }, [inView]);

  return (
    <div ref={ref} className="space-y-4">
      {/* Criticality tiers */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h4 className="text-xs font-semibold text-teal-400 uppercase tracking-wider mb-3">Identity-First Recovery Order</h4>
        <div className="space-y-2">
          {RECOVERY_PHASES.map((p, i) => (
            <div key={p.phase}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-all duration-500 ${
                activePhase >= i
                  ? `${p.bg} border-current/20 opacity-100 translate-x-0`
                  : 'border-transparent opacity-40 translate-x-2'
              }`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${activePhase >= i ? p.bg : 'bg-muted'} ${p.color}`}>
                {activePhase > i ? <CheckCircle className="w-4 h-4" /> : p.phase}
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-semibold ${p.color}`}>{p.name}</p>
                <p className="text-xs text-muted-foreground truncate">{p.items}</p>
              </div>
              <div className="text-right shrink-0">
                <p className={`text-sm font-bold ${p.color}`}>{p.time}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Total recovery summary */}
      {activePhase >= 3 && (
        <div className="bg-teal-500/5 border border-teal-500/20 rounded-xl p-4 flex items-center justify-between animate-in fade-in duration-500">
          <div className="flex items-center gap-3">
            <RefreshCw className="w-6 h-6 text-teal-400" />
            <div>
              <p className="text-sm font-bold text-teal-400">Full Recovery Complete</p>
              <p className="text-xs text-teal-400/70">26 objects &middot; 747 items &middot; 445 MB &middot; 5 workloads</p>
            </div>
          </div>
          <p className="text-2xl font-bold text-teal-400">170 <span className="text-sm font-normal">min</span></p>
        </div>
      )}
    </div>
  );
}

function SceneCriticality() {
  const { ref, inView } = useInView();
  const tierColors: Record<string, string> = {
    critical: 'bg-red-500/10 text-red-400 border-red-500/20',
    high: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    low: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
  };

  return (
    <div ref={ref} className="space-y-2">
      {DEMO_USERS.map((user, i) => (
        <div key={user.name}
          className={`flex items-center gap-3 px-3 py-2 rounded-lg bg-card border border-border transition-all duration-500 ${inView ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'}`}
          style={{ transitionDelay: `${i * 80}ms` }}
        >
          <div className="w-8 h-8 rounded-full bg-teal-500/20 text-teal-400 flex items-center justify-center text-xs font-bold shrink-0">
            {user.name[0]}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-foreground truncate">{user.name}</p>
            <p className="text-[10px] text-muted-foreground">{user.role}</p>
          </div>
          <div className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${tierColors[user.tier]}`}>
            {user.tier.toUpperCase()}
          </div>
          <div className="text-right shrink-0 w-12">
            <p className="text-sm font-bold text-foreground">{user.score}</p>
            <p className="text-[10px] text-muted-foreground">score</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Main Tour Page ──

const SCENES = [
  {
    id: 'dashboard',
    badge: 'LIVE DASHBOARD',
    title: 'See Your Protection at a Glance',
    description: 'Real-time visibility across Exchange, OneDrive, SharePoint, Teams, and Entra ID. One dashboard, all workloads.',
    Component: SceneDashboard,
  },
  {
    id: 'criticality',
    badge: 'SMART ENGINE',
    title: 'AI-Powered Criticality Scoring',
    description: 'Automatically ranks users by business impact. CEO recovered first, interns last. No manual configuration needed.',
    Component: SceneCriticality,
  },
  {
    id: 'attack',
    badge: 'THREAT DETECTION',
    title: 'Ransomware Hits. KavachIQ Responds.',
    description: 'Smart Engine detects anomalies in real-time. Auto-snapshots secure your recovery point before damage spreads.',
    Component: SceneAttack,
  },
  {
    id: 'recovery',
    badge: 'ONE-CLICK RECOVERY',
    title: 'Identity-First, NIST-Ordered Recovery',
    description: 'Restore Entra ID first (roles, policies, MFA), then critical users, then everyone. Full recovery in 170 minutes.',
    Component: SceneRecovery,
  },
];

export default function Tour() {
  const [activeScene, setActiveScene] = useState(0);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Helmet>
        <title>Product Tour — KavachIQ M365 Backup in Action</title>
        <meta name="description" content="Interactive product tour: see how KavachIQ protects Microsoft 365 data and recovers from ransomware. Live dashboard, smart engine, threat detection, one-click recovery." />
        <link rel="canonical" href="https://kavachiq.com/tour" />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://kavachiq.com/tour" />
        <meta property="og:title" content="Product Tour — KavachIQ M365 Backup in Action" />
        <meta property="og:description" content="See how KavachIQ detects ransomware, scores user criticality, and recovers your Microsoft 365 data — identity first." />
        <meta property="og:image" content="https://kavachiq.com/og-image.jpg" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="Product Tour — KavachIQ M365 Backup in Action" />
        <meta name="twitter:description" content="See how KavachIQ detects ransomware and recovers your Microsoft 365 data — identity first." />
      </Helmet>
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-lg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link to="/welcome" className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-teal-500" />
            <span className="font-bold text-lg text-foreground">KavachIQ</span>
          </Link>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <a href={appUrl('/login')} className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Sign In
            </a>
            <a href={appUrl('/login?register=true')} className="px-4 py-2 bg-teal-600 text-white rounded-lg text-sm font-semibold hover:bg-teal-500 flex items-center gap-1.5">
              Start Free <ArrowRight className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-16 pb-12 text-center">
        <FadeUp>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-teal-500/10 border border-teal-500/20 rounded-full text-xs font-semibold text-teal-400 mb-6">
            <Eye className="w-3.5 h-3.5" /> Interactive Product Tour
          </div>
        </FadeUp>
        <FadeUp delay={100}>
          <h1 className="text-4xl md:text-5xl font-extrabold mb-4 bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text text-transparent">
            Cyber Recovery in Action
          </h1>
        </FadeUp>
        <FadeUp delay={200}>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
            See how KavachIQ protects Microsoft 365 data and recovers from ransomware attacks.
            No signup required. Scroll to explore.
          </p>
        </FadeUp>
        <FadeUp delay={300}>
          <div className="flex items-center justify-center gap-6 text-sm text-muted-foreground">
            {['4 interactive scenes', '~2 minutes', 'No signup needed'].map(t => (
              <span key={t} className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-teal-500" /> {t}
              </span>
            ))}
          </div>
        </FadeUp>
      </section>

      {/* Scene Navigation */}
      <div className="sticky top-14 z-40 bg-background/80 backdrop-blur-lg border-b border-border">
        <div className="max-w-4xl mx-auto px-6 flex gap-1 overflow-x-auto py-2">
          {SCENES.map((scene, i) => (
            <button
              key={scene.id}
              onClick={() => {
                setActiveScene(i);
                document.getElementById(`scene-${scene.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }}
              className={`px-4 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                activeScene === i
                  ? 'bg-teal-500/10 text-teal-400 border border-teal-500/20'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
              }`}
            >
              {i + 1}. {scene.badge}
            </button>
          ))}
        </div>
      </div>

      {/* Scenes */}
      <div className="max-w-4xl mx-auto px-6 py-12 space-y-24">
        {SCENES.map((scene, i) => (
          <section key={scene.id} id={`scene-${scene.id}`} className="scroll-mt-32">
            <FadeUp>
              <div className="mb-6">
                <span className="inline-block px-2.5 py-0.5 bg-teal-500/10 border border-teal-500/20 rounded-full text-[10px] font-bold text-teal-400 uppercase tracking-wider mb-3">
                  Scene {i + 1} &middot; {scene.badge}
                </span>
                <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-2">{scene.title}</h2>
                <p className="text-muted-foreground">{scene.description}</p>
              </div>
            </FadeUp>
            <FadeUp delay={200}>
              <div className="bg-background border border-border rounded-2xl p-6 shadow-lg shadow-black/5">
                <scene.Component />
              </div>
            </FadeUp>
          </section>
        ))}
      </div>

      {/* CTA Footer */}
      <section className="max-w-4xl mx-auto px-6 pb-24">
        <FadeUp>
          <div className="bg-gradient-to-r from-teal-500/10 to-cyan-500/10 border border-teal-500/20 rounded-2xl p-8 md:p-12 text-center">
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">
              Ready to Protect Your Data?
            </h2>
            <p className="text-muted-foreground mb-6 max-w-lg mx-auto">
              Free for up to 25 objects. No credit card required. Connect your Microsoft 365 in under 3 minutes.
            </p>
            <div className="flex items-center justify-center gap-4">
              <a href={appUrl('/login?register=true')} className="px-6 py-3 bg-teal-600 text-white rounded-xl text-sm font-bold hover:bg-teal-500 flex items-center gap-2 shadow-lg shadow-teal-500/20">
                Start Free <ArrowRight className="w-4 h-4" />
              </a>
              <Link to="/welcome" className="px-6 py-3 border border-border text-foreground rounded-xl text-sm font-semibold hover:bg-muted/50">
                Learn More
              </Link>
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              Free &middot; No credit card &middot; Setup in 3 minutes &middot; SOC 2 ready
            </p>
          </div>
        </FadeUp>
      </section>
    </div>
  );
}
