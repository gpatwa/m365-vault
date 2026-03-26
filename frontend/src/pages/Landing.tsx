import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield, Mail, HardDrive, Globe, MessageSquare, KeyRound,
  AlertTriangle, ArrowRight, Lock, Server, Check, X,
  Zap, Eye, Brain, ShieldCheck, ChevronRight,
} from 'lucide-react';

// ── Scroll animation hook ──
function useInView(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setInView(true); }, { threshold });
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, inView };
}

function FadeUp({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const { ref, inView } = useInView();
  return (
    <div ref={ref} className={`transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}

function Counter({ target, suffix = '' }: { target: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  const { ref, inView } = useInView();
  useEffect(() => {
    if (!inView) return;
    let frame: number;
    const start = performance.now();
    const animate = (now: number) => {
      const p = Math.min((now - start) / 1500, 1);
      setCount(Math.round(target * p));
      if (p < 1) frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [inView, target]);
  return <span ref={ref}>{count}{suffix}</span>;
}

// ── Animated Data Flow ──
function AnimatedFlow() {
  const { ref, inView } = useInView(0.3);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const timers = [
      setTimeout(() => setStep(1), 500),
      setTimeout(() => setStep(2), 1500),
      setTimeout(() => setStep(3), 2500),
    ];
    return () => timers.forEach(clearTimeout);
  }, [inView]);

  return (
    <div ref={ref} className="max-w-4xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative">
        {/* Connecting lines (desktop) */}
        <div className="hidden md:block absolute top-1/2 left-[33%] w-[34%] h-0.5 -translate-y-1/2">
          <div className={`h-full bg-gradient-to-r from-blue-400 to-green-400 transition-all duration-1000 ${step >= 2 ? 'w-full' : 'w-0'}`} />
        </div>
        <div className="hidden md:block absolute top-1/2 left-[67%] w-[33%] h-0.5 -translate-y-1/2">
          <div className={`h-full bg-gradient-to-r from-green-400 to-emerald-400 transition-all duration-1000 ${step >= 3 ? 'w-full' : 'w-0'}`} />
        </div>

        {/* Step 1: Your M365 Data */}
        <div className={`relative bg-white rounded-2xl border-2 p-6 transition-all duration-700 ${step >= 1 ? 'border-blue-300 shadow-lg shadow-blue-100 opacity-100 translate-y-0' : 'border-gray-200 opacity-40 translate-y-4'}`}>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center text-sm font-bold text-blue-600">1</div>
            <span className="font-semibold text-gray-900">Connect</span>
          </div>
          <p className="text-sm text-gray-500 mb-4">Your M365 tenant connects in 60 seconds</p>
          <div className="flex flex-wrap gap-2">
            {[
              { icon: Mail, label: 'Emails', color: 'bg-blue-50 text-blue-600' },
              { icon: HardDrive, label: 'Files', color: 'bg-purple-50 text-purple-600' },
              { icon: Globe, label: 'Sites', color: 'bg-green-50 text-green-600' },
              { icon: MessageSquare, label: 'Chats', color: 'bg-pink-50 text-pink-600' },
              { icon: KeyRound, label: 'Identity', color: 'bg-amber-50 text-amber-600' },
            ].map(item => (
              <div key={item.label} className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium ${item.color}`}>
                <item.icon className="w-3.5 h-3.5" /> {item.label}
              </div>
            ))}
          </div>
          {/* Animated particles */}
          {step >= 1 && (
            <div className="absolute -right-3 top-1/2 -translate-y-1/2 hidden md:flex flex-col gap-1">
              {[0, 1, 2].map(i => (
                <div key={i} className="w-2 h-2 bg-blue-400 rounded-full animate-ping" style={{ animationDelay: `${i * 300}ms`, animationDuration: '1.5s' }} />
              ))}
            </div>
          )}
        </div>

        {/* Step 2: Shieldio Engine */}
        <div className={`relative bg-white rounded-2xl border-2 p-6 transition-all duration-700 delay-500 ${step >= 2 ? 'border-green-300 shadow-lg shadow-green-100 opacity-100 translate-y-0' : 'border-gray-200 opacity-40 translate-y-4'}`}>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center text-sm font-bold text-green-600">2</div>
            <span className="font-semibold text-gray-900">Protect</span>
          </div>
          <p className="text-sm text-gray-500 mb-4">Shieldio encrypts, compresses, deduplicates</p>
          <div className="space-y-2">
            {[
              { icon: Lock, label: 'AES-256-GCM encrypt', active: step >= 2 },
              { icon: Zap, label: 'zstd compress (2.9x)', active: step >= 2 },
              { icon: Eye, label: 'SHA-256 verify', active: step >= 2 },
              { icon: Brain, label: 'Anomaly baseline', active: step >= 2 },
            ].map((item, i) => (
              <div key={item.label} className={`flex items-center gap-2 text-xs transition-all duration-500 ${item.active ? 'text-gray-700 opacity-100' : 'text-gray-300 opacity-50'}`} style={{ transitionDelay: `${i * 200 + 500}ms` }}>
                <item.icon className="w-3.5 h-3.5 text-green-500" />
                {item.label}
              </div>
            ))}
          </div>
          {step >= 2 && (
            <div className="absolute -right-3 top-1/2 -translate-y-1/2 hidden md:flex flex-col gap-1">
              {[0, 1, 2].map(i => (
                <div key={i} className="w-2 h-2 bg-green-400 rounded-full animate-ping" style={{ animationDelay: `${i * 300}ms`, animationDuration: '1.5s' }} />
              ))}
            </div>
          )}
        </div>

        {/* Step 3: Protected */}
        <div className={`bg-white rounded-2xl border-2 p-6 transition-all duration-700 delay-1000 ${step >= 3 ? 'border-emerald-300 shadow-lg shadow-emerald-100 opacity-100 translate-y-0' : 'border-gray-200 opacity-40 translate-y-4'}`}>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center text-sm font-bold text-emerald-600">3</div>
            <span className="font-semibold text-gray-900">Secure</span>
          </div>
          <p className="text-sm text-gray-500 mb-4">Sleep well — your data is protected</p>
          <div className="space-y-2">
            {[
              { icon: ShieldCheck, label: 'WORM immutable', color: 'text-emerald-500' },
              { icon: Brain, label: 'AI-monitored 24/7', color: 'text-emerald-500' },
              { icon: Zap, label: 'Self-healing retry', color: 'text-emerald-500' },
              { icon: AlertTriangle, label: 'Anomaly alerts', color: 'text-emerald-500' },
            ].map((item, i) => (
              <div key={item.label} className={`flex items-center gap-2 text-xs transition-all duration-500 ${step >= 3 ? 'text-gray-700 opacity-100' : 'text-gray-300 opacity-50'}`} style={{ transitionDelay: `${i * 200 + 1000}ms` }}>
                <item.icon className={`w-3.5 h-3.5 ${item.color}`} />
                {item.label}
              </div>
            ))}
          </div>
          {step >= 3 && (
            <div className="absolute top-3 right-3">
              <div className="w-6 h-6 bg-emerald-500 rounded-full flex items-center justify-center animate-bounce">
                <Check className="w-4 h-4 text-white" />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Workload icons ──
const WORKLOADS = [
  { icon: Mail, label: 'Exchange', desc: 'Email, Calendar, Contacts', color: 'text-blue-600 bg-blue-50 border-blue-200' },
  { icon: HardDrive, label: 'OneDrive', desc: 'Files & Folders', color: 'text-purple-600 bg-purple-50 border-purple-200' },
  { icon: Globe, label: 'SharePoint', desc: 'Sites, Lists, Documents', color: 'text-green-600 bg-green-50 border-green-200' },
  { icon: MessageSquare, label: 'Teams', desc: 'Chats, Channels, Files', color: 'text-pink-600 bg-pink-50 border-pink-200' },
  { icon: KeyRound, label: 'Entra ID', desc: '12 object types, Config drift', color: 'text-amber-600 bg-amber-50 border-amber-200' },
];

// ── Competitor comparison ──
const COMPARE_FEATURES = [
  { feature: 'Open source', us: true, them: false },
  { feature: 'Self-hosted option', us: true, them: false },
  { feature: 'Per-tenant encryption keys', us: true, them: true },
  { feature: 'AI anomaly detection', us: true, them: true },
  { feature: 'AI intelligence included free', us: true, them: false },
  { feature: 'WORM immutable storage', us: true, them: true },
  { feature: 'Teams chat backup', us: true, them: true },
  { feature: 'Entra ID config backup', us: true, them: false },
  { feature: 'Starting price', usVal: 'Free', themVal: '$2.50/user/mo' },
];

// ── Pricing tiers ──
const PRICING = [
  { name: 'Community', price: 'Free', period: 'forever', desc: 'Up to 25 users', features: ['3 workloads', 'Basic Smart Engine', 'Community support'], cta: 'Start Free', primary: false },
  { name: 'Professional', price: '$1.50', period: '/user/mo', desc: 'Unlimited users', features: ['5 workloads + Teams', 'Full Smart Engine', 'SSO + MFA', 'Email support'], cta: 'Start Trial', primary: true },
  { name: 'Enterprise', price: '$3.00', period: '/user/mo', desc: 'Unlimited everything', features: ['All workloads', 'Custom rules', 'MSP console', 'Priority support'], cta: 'Contact Sales', primary: false },
];

// ═══════════════════════════════════════════════════════
// LANDING PAGE
// ═══════════════════════════════════════════════════════
export default function Landing() {
  const [heroReady, setHeroReady] = useState(false);
  useEffect(() => { setTimeout(() => setHeroReady(true), 100); }, []);

  return (
    <div className="min-h-screen bg-white">

      {/* ═══ NAV ═══ */}
      <nav className="fixed top-0 w-full z-50 bg-white/80 backdrop-blur-sm border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link to="/welcome" className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-blue-600" />
            <span className="font-bold text-gray-900">Shieldio</span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm text-gray-600">
            <a href="#how-it-works" className="hover:text-gray-900">How It Works</a>
            <a href="#workloads" className="hover:text-gray-900">Workloads</a>
            <a href="#pricing" className="hover:text-gray-900">Pricing</a>
            <a href="#security" className="hover:text-gray-900">Security</a>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm text-gray-600 hover:text-gray-900">Sign In</Link>
            <Link to="/login" className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
              Start Free
            </Link>
          </div>
        </div>
      </nav>

      {/* ═══ SECTION 1: HOOK — Emotional Trigger ═══ */}
      <section className="pt-24 pb-16 px-6">
        <div className="max-w-4xl mx-auto text-center">
          {/* Badge */}
          <div className={`inline-flex items-center gap-2 px-3 py-1 bg-red-50 text-red-700 rounded-full text-xs font-medium mb-6 transition-all duration-500 ${heroReady ? 'opacity-100' : 'opacity-0'}`}>
            <AlertTriangle className="w-3.5 h-3.5" />
            Microsoft doesn't back up your M365 data
          </div>

          {/* Headline */}
          <h1 className={`text-4xl md:text-6xl font-extrabold text-gray-900 leading-[1.1] tracking-tight transition-all duration-700 delay-200 ${heroReady ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}>
            Your emails. Your files.{' '}
            <br className="hidden md:block" />
            <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              Your responsibility.
            </span>
          </h1>

          {/* Sub */}
          <p className={`mt-6 text-lg text-gray-500 max-w-2xl mx-auto transition-all duration-700 delay-500 ${heroReady ? 'opacity-100' : 'opacity-0'}`}>
            96% of ransomware attacks target backups. Microsoft 365 retention policies are not backup.
            Shieldio gives you independent, encrypted, immutable protection for your SaaS data.
          </p>

          {/* CTAs */}
          <div className={`mt-8 flex items-center justify-center gap-4 transition-all duration-700 delay-700 ${heroReady ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
            <Link to="/login" className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-all hover:shadow-lg hover:shadow-blue-200 flex items-center gap-2">
              Start Free <ArrowRight className="w-4 h-4" />
            </Link>
            <a href="https://github.com/gpatwa/m365-vault" target="_blank" rel="noopener noreferrer"
              className="px-6 py-3 bg-gray-100 text-gray-700 font-medium rounded-xl hover:bg-gray-200 transition-colors flex items-center gap-2">
              <Server className="w-4 h-4" /> View Source
            </a>
          </div>

          {/* Stats */}
          <div className={`mt-12 flex items-center justify-center gap-12 text-center transition-all duration-700 delay-900 ${heroReady ? 'opacity-100' : 'opacity-0'}`}>
            <div><div className="text-2xl font-bold text-gray-900"><Counter target={5} /></div><div className="text-xs text-gray-500">M365 Workloads</div></div>
            <div><div className="text-2xl font-bold text-gray-900"><Counter target={10} suffix="min" /></div><div className="text-xs text-gray-500">Recovery Time</div></div>
            <div><div className="text-2xl font-bold text-gray-900"><Counter target={4} /></div><div className="text-xs text-gray-500">Compliance Frameworks</div></div>
            <div><div className="text-2xl font-bold text-gray-900"><Counter target={99} suffix="%" /></div><div className="text-xs text-gray-500">Backup Success Rate</div></div>
          </div>
        </div>
      </section>

      {/* ═══ SECTION 2: HOW IT WORKS — Animated Flow ═══ */}
      <section id="how-it-works" className="py-20 px-6 bg-gray-50">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900">Protected in 3 steps</h2>
              <p className="text-gray-500 mt-2">Watch your data flow from vulnerable to vault-secured</p>
            </div>
          </FadeUp>
          <AnimatedFlow />
        </div>
      </section>

      {/* ═══ SECTION 3: WORKLOADS — What You Protect ═══ */}
      <section id="workloads" className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900">Every workload. One platform.</h2>
              <p className="text-gray-500 mt-2">Five M365 workloads protected with unified backup, restore, and monitoring</p>
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
      <section className="py-20 px-6 bg-gray-900 text-white">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-500/10 text-amber-400 rounded-full text-xs font-medium mb-4">
                <Brain className="w-3.5 h-3.5" /> AI-Powered Intelligence
              </div>
              <h2 className="text-3xl font-bold">Smart protection. Zero token cost.</h2>
              <p className="text-gray-400 mt-2 max-w-xl mx-auto">
                Anomaly detection, health scoring, self-healing, and sensitive data discovery — built on statistical ML, not expensive LLM APIs.
              </p>
            </div>
          </FadeUp>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { icon: Brain, title: 'Anomaly Detection', desc: 'Z-score baselines learn normal patterns. Flags mass deletions, encryption spikes, unusual changes.', color: 'from-amber-500 to-orange-500' },
              { icon: ShieldCheck, title: 'Self-Healing', desc: 'Failed backups auto-retry with exponential backoff. Circuit breaker pauses on API outages.', color: 'from-green-500 to-emerald-500' },
              { icon: Eye, title: 'Sensitive Data Scanner', desc: 'Regex PII/PHI/PCI detection on backup data. Finds sensitive data deleted from production.', color: 'from-blue-500 to-indigo-500' },
            ].map((f, i) => (
              <FadeUp key={f.title} delay={i * 150}>
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-gray-600 transition-colors">
                  <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${f.color} flex items-center justify-center mb-4`}>
                    <f.icon className="w-5 h-5 text-white" />
                  </div>
                  <h3 className="font-semibold mb-2">{f.title}</h3>
                  <p className="text-sm text-gray-400 leading-relaxed">{f.desc}</p>
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
              <h2 className="text-3xl font-bold text-gray-900">Enterprise-grade security</h2>
              <p className="text-gray-500 mt-2">Your data is encrypted, immutable, and compliance-ready from day one</p>
            </div>
          </FadeUp>
          <div className="flex flex-wrap items-center justify-center gap-4 mb-8">
            {[
              { icon: '🔒', label: 'AES-256-GCM', desc: 'Encryption at Rest' },
              { icon: '🔑', label: 'Per-Tenant Keys', desc: 'Key Isolation' },
              { icon: '🛡️', label: 'WORM Storage', desc: 'Immutable Backups' },
              { icon: '✅', label: 'SOC 2 Ready', desc: '16 Controls' },
              { icon: '🇪🇺', label: 'GDPR Ready', desc: '8 Articles' },
              { icon: '🏥', label: 'HIPAA Ready', desc: '14 Safeguards' },
              { icon: '🔐', label: 'SSO + MFA', desc: 'Entra ID OIDC' },
              { icon: '📋', label: 'Audit Trail', desc: 'Full Logging' },
            ].map(b => (
              <FadeUp key={b.label}>
                <div className="flex items-center gap-2.5 px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl hover:border-gray-300 hover:shadow-sm transition-all">
                  <span className="text-lg">{b.icon}</span>
                  <div>
                    <div className="text-xs font-semibold text-gray-800">{b.label}</div>
                    <div className="text-[10px] text-gray-500">{b.desc}</div>
                  </div>
                </div>
              </FadeUp>
            ))}
          </div>
          <div className="text-center">
            <Link to="/security" className="text-sm text-blue-600 hover:text-blue-800 font-medium">
              View full security posture <ChevronRight className="w-3.5 h-3.5 inline" />
            </Link>
          </div>
        </div>
      </section>

      {/* ═══ SECTION 6: COMPARE — Why Us ═══ */}
      <section className="py-20 px-6 bg-gray-50">
        <div className="max-w-3xl mx-auto">
          <FadeUp>
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-gray-900">How we compare</h2>
              <p className="text-gray-500 mt-2">Shieldio vs. traditional backup vendors</p>
            </div>
          </FadeUp>
          <FadeUp delay={200}>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="text-left px-5 py-3 font-medium text-gray-600">Feature</th>
                    <th className="text-center px-5 py-3 font-semibold text-blue-600">Shieldio</th>
                    <th className="text-center px-5 py-3 font-medium text-gray-400">Others</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {COMPARE_FEATURES.map(f => (
                    <tr key={f.feature} className="hover:bg-gray-50">
                      <td className="px-5 py-3 text-gray-700">{f.feature}</td>
                      <td className="px-5 py-3 text-center">
                        {'usVal' in f ? <span className="font-semibold text-green-600">{f.usVal}</span>
                          : f.us ? <Check className="w-5 h-5 text-green-500 mx-auto" /> : <X className="w-5 h-5 text-gray-300 mx-auto" />}
                      </td>
                      <td className="px-5 py-3 text-center">
                        {'themVal' in f ? <span className="text-gray-400">{f.themVal}</span>
                          : f.them ? <Check className="w-5 h-5 text-gray-400 mx-auto" /> : <X className="w-5 h-5 text-gray-300 mx-auto" />}
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
              <h2 className="text-3xl font-bold text-gray-900">Simple, transparent pricing</h2>
              <p className="text-gray-500 mt-2">No per-GB charges. No surprise overages. Intelligence included free.</p>
            </div>
          </FadeUp>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {PRICING.map((tier, i) => (
              <FadeUp key={tier.name} delay={i * 100}>
                <div className={`rounded-xl p-6 ${tier.primary ? 'bg-blue-600 text-white ring-2 ring-blue-600 ring-offset-2' : 'bg-white border border-gray-200'}`}>
                  <div className={`text-sm font-semibold ${tier.primary ? 'text-blue-200' : 'text-gray-500'}`}>{tier.name}</div>
                  <div className="flex items-baseline gap-1 mt-2">
                    <span className="text-3xl font-extrabold">{tier.price}</span>
                    <span className={`text-sm ${tier.primary ? 'text-blue-200' : 'text-gray-400'}`}>{tier.period}</span>
                  </div>
                  <p className={`text-sm mt-1 ${tier.primary ? 'text-blue-200' : 'text-gray-500'}`}>{tier.desc}</p>
                  <ul className="mt-5 space-y-2">
                    {tier.features.map(f => (
                      <li key={f} className="flex items-center gap-2 text-sm">
                        <Check className={`w-4 h-4 ${tier.primary ? 'text-blue-200' : 'text-green-500'}`} />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Link to="/login" className={`block mt-6 text-center py-2.5 rounded-lg font-medium text-sm transition-colors ${
                    tier.primary ? 'bg-white text-blue-600 hover:bg-blue-50' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}>
                    {tier.cta}
                  </Link>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ SECTION 8: DEPLOY ═══ */}
      <section className="py-16 px-6 bg-gray-900 text-white">
        <div className="max-w-3xl mx-auto text-center">
          <FadeUp>
            <h2 className="text-2xl font-bold mb-3">Deploy in 5 minutes</h2>
            <p className="text-gray-400 text-sm mb-6">Self-hosted on your infrastructure. Your data never leaves your control.</p>
            <div className="bg-gray-800 rounded-xl p-4 text-left font-mono text-sm border border-gray-700">
              <div className="text-gray-500"># Clone and start</div>
              <div className="text-green-400">$ git clone https://github.com/gpatwa/m365-vault</div>
              <div className="text-green-400">$ cd m365-vault && make dev</div>
              <div className="text-gray-500 mt-2"># Or deploy to Azure</div>
              <div className="text-green-400">$ make acr-push && make tf-apply</div>
            </div>
          </FadeUp>
        </div>
      </section>

      {/* ═══ SECTION 9: FINAL CTA ═══ */}
      <section className="py-20 px-6 bg-gradient-to-br from-blue-600 to-indigo-700">
        <div className="max-w-3xl mx-auto text-center text-white">
          <FadeUp>
            <h2 className="text-3xl font-bold mb-4">Ready to protect your SaaS data?</h2>
            <p className="text-blue-100 mb-8">Free for up to 25 users. No credit card required.</p>
            <Link to="/login" className="inline-flex items-center gap-2 px-8 py-3.5 bg-white text-blue-700 font-semibold rounded-xl hover:bg-blue-50 transition-colors text-lg">
              Get Started Free <ArrowRight className="w-5 h-5" />
            </Link>
          </FadeUp>
        </div>
      </section>

      {/* ═══ FOOTER ═══ */}
      <footer className="py-12 px-6 bg-gray-900 text-gray-400">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Shield className="w-5 h-5 text-blue-400" />
                <span className="font-semibold text-white">Shieldio</span>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed">
                SaaS Data Protection Platform.<br />
                Open source. Self-hosted. Secure.
              </p>
            </div>
            <div>
              <div className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-3">Product</div>
              <div className="space-y-2 text-sm">
                <a href="#workloads" className="block hover:text-white">Workloads</a>
                <a href="#pricing" className="block hover:text-white">Pricing</a>
                <a href="#security" className="block hover:text-white">Security</a>
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-3">Resources</div>
              <div className="space-y-2 text-sm">
                <a href="https://github.com/gpatwa/m365-vault" className="block hover:text-white">GitHub</a>
                <Link to="/login" className="block hover:text-white">Documentation</Link>
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-3">Legal</div>
              <div className="space-y-2 text-sm">
                <Link to="/legal?tab=tos" className="block hover:text-white">Terms of Service</Link>
                <Link to="/legal?tab=privacy" className="block hover:text-white">Privacy Policy</Link>
              </div>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-6 text-center text-xs text-gray-500">
            &copy; {new Date().getFullYear()} Shieldio. Open source under Apache 2.0 License.
          </div>
        </div>
      </footer>
    </div>
  );
}
