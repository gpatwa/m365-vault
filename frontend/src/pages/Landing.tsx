import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield, Mail, Globe, MessageSquare,
  AlertTriangle,
  CheckCircle, ArrowRight, Zap, Server, ChevronRight, Eye, Clock,
  ShieldCheck, Database, Fingerprint, Activity,
  X, Check,
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

// ── Animated counter ──
function Counter({ target, suffix = '', duration = 2000 }: { target: number; suffix?: string; duration?: number }) {
  const [count, setCount] = useState(0);
  const { ref, inView } = useInView();
  useEffect(() => {
    if (!inView) return;
    const start = Date.now();
    const timer = setInterval(() => {
      const progress = Math.min((Date.now() - start) / duration, 1);
      setCount(Math.floor(progress * target));
      if (progress >= 1) clearInterval(timer);
    }, 16);
    return () => clearInterval(timer);
  }, [inView, target, duration]);
  return <span ref={ref}>{count}{suffix}</span>;
}

// ── Fade-up wrapper ──
function FadeUp({ children, delay = 0, className = '' }: { children: React.ReactNode; delay?: number; className?: string }) {
  const { ref, inView } = useInView();
  return (
    <div
      ref={ref}
      className={`transition-all duration-700 ${inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

const SAAS_APPS = [
  { icon: Mail, label: 'Microsoft 365', items: 'Exchange, OneDrive, SharePoint, Teams, Entra ID', color: 'text-blue-600 bg-blue-50 border-blue-200', available: true },
  { icon: Globe, label: 'Google Workspace', items: 'Gmail, Drive, Calendar, Chat', color: 'text-red-600 bg-red-50 border-red-200', available: false },
  { icon: Database, label: 'Salesforce', items: 'Accounts, Contacts, Opportunities', color: 'text-sky-600 bg-sky-50 border-sky-200', available: false },
  { icon: MessageSquare, label: 'Slack', items: 'Messages, Channels, Files', color: 'text-purple-600 bg-purple-50 border-purple-200', available: false },
  { icon: Activity, label: 'Atlassian', items: 'Jira Issues, Confluence Wikis', color: 'text-blue-600 bg-blue-50 border-blue-200', available: false },
];

const STEPS = [
  {
    num: '01',
    title: 'Connect',
    desc: 'Paste your tenant ID. Shieldio auto-configures permissions via Microsoft admin consent. One click.',
    detail: 'Guided 3-step wizard handles app registration, Graph API permissions, and initial discovery automatically.',
    icon: Fingerprint,
    color: 'from-blue-500 to-blue-600',
  },
  {
    num: '02',
    title: 'Protect',
    desc: 'Choose workloads and frequency. Exchange daily? OneDrive every 6 hours? Teams hourly? You decide.',
    detail: 'SLA policies with automated scheduling, retention rules, WORM immutability, and legal hold.',
    icon: ShieldCheck,
    color: 'from-green-500 to-green-600',
  },
  {
    num: '03',
    title: 'Sleep',
    desc: 'Automated backups run silently. AI detects anomalies. Self-healing retries failures automatically.',
    detail: 'Intelligent anomaly detection, predictive health scoring, email/webhook alerts. You only hear when something needs attention.',
    icon: Eye,
    color: 'from-purple-500 to-purple-600',
  },
];

const COMPETITORS = [
  { name: 'Shieldio', price: '$1.50', storage: 'Unlimited', ai: 'Included (all tiers)', openSource: true, selfHosted: true, workloads: '5+', highlight: true },
  { name: 'Veeam', price: '$2.63–3.50', storage: 'Unlimited', ai: 'None', openSource: false, selfHosted: false, workloads: '5' },
  { name: 'Druva', price: '$2.50–10', storage: 'Tiered', ai: 'Premium tier only', openSource: false, selfHosted: false, workloads: '5' },
  { name: 'Commvault', price: '$1.70–4.50', storage: '5-50 GB cap', ai: 'Premium tier only', openSource: false, selfHosted: false, workloads: '4' },
  { name: 'Microsoft', price: '$0.15/GB', storage: 'Pay-as-you-go', ai: 'None', openSource: false, selfHosted: false, workloads: '3' },
];

export default function Landing() {
  // Hero text animation
  const [heroReady, setHeroReady] = useState(false);
  useEffect(() => { setTimeout(() => setHeroReady(true), 100); }, []);

  return (
    <div className="min-h-screen bg-white overflow-hidden">
      {/* ═══ Navbar ═══ */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-blue-600" />
            <span className="text-lg font-bold text-gray-900">Shieldio</span>
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-500">
            <a href="#problem" className="hover:text-gray-900 transition-colors">Why</a>
            <a href="#how" className="hover:text-gray-900 transition-colors">How It Works</a>
            <a href="#compare" className="hover:text-gray-900 transition-colors">Compare</a>
            <a href="#pricing" className="hover:text-gray-900 transition-colors">Pricing</a>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm font-medium text-gray-600 hover:text-gray-900">Sign In</Link>
            <Link to="/login" className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
              Start Free
            </Link>
          </div>
        </div>
      </nav>

      {/* ═══ SECTION 1: Hero ═══ */}
      <section className="relative pt-16 pb-20 px-6 overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50/50 via-white to-indigo-50/30 -z-10" />

        <div className="max-w-5xl mx-auto text-center">
          <div className={`inline-flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium mb-6 transition-all duration-500 ${heroReady ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-4'}`}>
            <Zap className="w-3 h-3" /> SaaS Data Protection Platform
          </div>

          <h1 className={`text-5xl md:text-7xl font-extrabold text-gray-900 leading-[1.1] tracking-tight transition-all duration-700 delay-200 ${heroReady ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}>
            Your SaaS vendor<br />
            <span className="bg-gradient-to-r from-red-500 to-orange-500 bg-clip-text text-transparent">
              won't save your data.
            </span>
            <br />
            <span className={`bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent transition-all duration-700 delay-500 ${heroReady ? 'opacity-100' : 'opacity-0'}`}>
              We will.
            </span>
          </h1>

          <p className={`mt-6 text-lg md:text-xl text-gray-500 max-w-2xl mx-auto leading-relaxed transition-all duration-700 delay-700 ${heroReady ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
            AI-powered backup for Microsoft 365, Google Workspace, and Salesforce.
            Intelligent protection with built-in anomaly detection. Self-hosted. Open source.
          </p>

          <div className={`mt-8 flex items-center justify-center gap-4 transition-all duration-700 delay-900 ${heroReady ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
            <Link to="/login" className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-all hover:shadow-lg hover:shadow-blue-200 flex items-center gap-2">
              Start Free <ArrowRight className="w-4 h-4" />
            </Link>
            <a href="https://github.com/gpatwa/m365-vault" target="_blank" rel="noopener noreferrer"
              className="px-6 py-3 bg-gray-100 text-gray-700 font-medium rounded-xl hover:bg-gray-200 transition-colors flex items-center gap-2">
              <Server className="w-4 h-4" /> GitHub
            </a>
          </div>

          {/* Stats */}
          <div className={`mt-12 flex items-center justify-center gap-8 md:gap-16 text-center transition-all duration-700 delay-1000 ${heroReady ? 'opacity-100' : 'opacity-0'}`}>
            <div>
              <p className="text-3xl font-bold text-gray-900"><Counter target={5} /></p>
              <p className="text-xs text-gray-400 mt-1">Workloads</p>
            </div>
            <div className="w-px h-8 bg-gray-200" />
            <div>
              <p className="text-3xl font-bold text-gray-900"><Counter target={102} suffix="+" /></p>
              <p className="text-xs text-gray-400 mt-1">API Routes</p>
            </div>
            <div className="w-px h-8 bg-gray-200" />
            <div>
              <p className="text-3xl font-bold text-blue-600">AI</p>
              <p className="text-xs text-gray-400 mt-1">Built-in Intelligence</p>
            </div>
            <div className="w-px h-8 bg-gray-200" />
            <div>
              <p className="text-3xl font-bold text-gray-900"><Counter target={256} /></p>
              <p className="text-xs text-gray-400 mt-1">-bit Encryption</p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ SECTION 2: The Problem ═══ */}
      <section id="problem" className="py-20 px-6 bg-gray-900 text-white">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-red-500/10 text-red-400 rounded-full text-xs font-medium mb-4">
                <AlertTriangle className="w-3 h-3" /> The Problem
              </div>
              <h2 className="text-3xl md:text-4xl font-bold">
                SaaS vendors provide <span className="text-red-400">retention</span>, not <span className="text-green-400">backup</span>.
              </h2>
              <p className="mt-4 text-gray-400 max-w-2xl mx-auto">
                If your data is deleted, corrupted, or encrypted by ransomware — your SaaS vendor cannot recover it.
                Microsoft, Google, and Salesforce all say the same thing: <em className="text-white">"Backing up your data is your responsibility."</em>
              </p>
            </div>
          </FadeUp>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
            {[
              { stat: '96%', label: 'of ransomware attacks target backup data first', icon: AlertTriangle, color: 'text-red-400' },
              { stat: '600M', label: 'attacks daily on Microsoft 365 infrastructure', icon: Shield, color: 'text-orange-400' },
              { stat: '15%', label: 'of businesses regularly test their backup recovery', icon: Clock, color: 'text-yellow-400' },
            ].map((item, i) => (
              <FadeUp key={item.stat} delay={i * 150}>
                <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 text-center">
                  <item.icon className={`w-6 h-6 ${item.color} mx-auto mb-3`} />
                  <p className={`text-4xl font-extrabold ${item.color}`}>{item.stat}</p>
                  <p className="text-sm text-gray-400 mt-2">{item.label}</p>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ SECTION 3: What You Protect ═══ */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900">One platform. Every SaaS app.</h2>
              <p className="mt-3 text-gray-500">Start with Microsoft 365 today. Expand as we add more platforms.</p>
            </div>
          </FadeUp>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {SAAS_APPS.map((app, i) => (
              <FadeUp key={app.label} delay={i * 100}>
                <div className={`rounded-xl border p-5 text-center transition-all hover:shadow-lg ${
                  app.available ? `${app.color} hover:-translate-y-1` : 'bg-gray-50 border-gray-200 opacity-60'
                }`}>
                  <app.icon className={`w-8 h-8 mx-auto mb-3 ${app.available ? '' : 'text-gray-400'}`} />
                  <h3 className={`font-semibold text-sm ${app.available ? 'text-gray-900' : 'text-gray-500'}`}>{app.label}</h3>
                  <p className="text-[11px] text-gray-500 mt-1">{app.items}</p>
                  {app.available ? (
                    <span className="inline-flex items-center gap-1 mt-3 text-[10px] font-semibold text-green-700 bg-green-100 px-2 py-0.5 rounded-full">
                      <CheckCircle className="w-2.5 h-2.5" /> Available
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 mt-3 text-[10px] font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                      Coming Soon
                    </span>
                  )}
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ SECTION 4: How It Works ═══ */}
      <section id="how" className="py-20 px-6 bg-gray-50">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900">Protected in 3 steps</h2>
              <p className="mt-3 text-gray-500">From zero to fully protected in under 5 minutes.</p>
            </div>
          </FadeUp>

          <div className="space-y-8">
            {STEPS.map((step, i) => (
              <FadeUp key={step.num} delay={i * 200}>
                <div className="bg-white rounded-2xl border border-gray-200 p-8 flex flex-col md:flex-row items-start gap-6 hover:shadow-lg transition-shadow">
                  <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${step.color} flex items-center justify-center flex-shrink-0`}>
                    <step.icon className="w-7 h-7 text-white" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-xs font-mono text-gray-400">{step.num}</span>
                      <h3 className="text-xl font-bold text-gray-900">{step.title}</h3>
                    </div>
                    <p className="text-gray-600 mb-2">{step.desc}</p>
                    <p className="text-sm text-gray-400">{step.detail}</p>
                  </div>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ SECTION 5: What Makes Us Different ═══ */}
      <section className="py-20 px-6 bg-gray-900 text-white">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold">Built different.</h2>
              <p className="mt-3 text-gray-400">Enterprise features at a fraction of the cost.</p>
            </div>
          </FadeUp>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { icon: '🔓', title: 'Open Source', desc: 'Full source code on GitHub. No vendor lock-in. Deploy on any cloud, on-premises, or air-gapped.' },
              { icon: '🧠', title: 'AI-Powered Intelligence', desc: 'Anomaly detection that learns your patterns. Predictive health scoring. Self-healing automation. Included free at every tier.' },
              { icon: '🛡️', title: 'Data Sovereignty', desc: 'Your backups never leave your infrastructure. AES-256-GCM with per-tenant keys. GDPR and DORA ready.' },
              { icon: '🔒', title: 'WORM Immutability', desc: 'Write-once backups with retention locks and legal hold. Ransomware can\'t delete what it can\'t modify.' },
              { icon: '🔍', title: 'Global Search (⌘K)', desc: 'Find any email, file, or chat across all workloads in milliseconds. Self-service restore without IT tickets.' },
              { icon: '📊', title: 'Built-in Analytics', desc: 'Backup performance, SLA compliance, failure analysis, storage trends. No separate monitoring tool needed.' },
            ].map((item, i) => (
              <FadeUp key={item.title} delay={i * 100}>
                <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 hover:border-gray-600 transition-colors">
                  <div className="text-3xl mb-4">{item.icon}</div>
                  <h3 className="text-lg font-bold mb-2">{item.title}</h3>
                  <p className="text-sm text-gray-400 leading-relaxed">{item.desc}</p>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ SECTION 6: Compare ═══ */}
      <section id="compare" className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900">How we compare</h2>
              <p className="mt-3 text-gray-500">Honest comparison. No marketing fluff.</p>
            </div>
          </FadeUp>

          <FadeUp delay={200}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-gray-200">
                    <th className="text-left py-3 px-4 font-semibold text-gray-900">Vendor</th>
                    <th className="text-center py-3 px-3 font-semibold text-gray-900">Price/user/mo</th>
                    <th className="text-center py-3 px-3 font-semibold text-gray-900">Storage</th>
                    <th className="text-center py-3 px-3 font-semibold text-gray-900">AI Intelligence</th>
                    <th className="text-center py-3 px-3 font-semibold text-gray-900">Open Source</th>
                    <th className="text-center py-3 px-3 font-semibold text-gray-900">Self-Hosted</th>
                  </tr>
                </thead>
                <tbody>
                  {COMPETITORS.map(c => (
                    <tr key={c.name} className={`border-b ${c.highlight ? 'bg-blue-50' : 'hover:bg-gray-50'}`}>
                      <td className="py-3 px-4 font-semibold">
                        {c.highlight && <Shield className="w-4 h-4 text-blue-600 inline mr-1" />}
                        <span className={c.highlight ? 'text-blue-700' : 'text-gray-700'}>{c.name}</span>
                      </td>
                      <td className="py-3 px-3 text-center font-medium">{c.price}</td>
                      <td className="py-3 px-3 text-center text-gray-600">{c.storage}</td>
                      <td className="py-3 px-3 text-center">
                        <span className={c.ai.includes('Included') ? 'text-green-600 font-semibold text-xs' : c.ai === 'None' ? 'text-gray-400 text-xs' : 'text-orange-500 text-xs'}>{c.ai}</span>
                      </td>
                      <td className="py-3 px-3 text-center">
                        {c.openSource ? <Check className="w-4 h-4 text-green-600 mx-auto" /> : <X className="w-4 h-4 text-gray-300 mx-auto" />}
                      </td>
                      <td className="py-3 px-3 text-center">
                        {c.selfHosted ? <Check className="w-4 h-4 text-green-600 mx-auto" /> : <X className="w-4 h-4 text-gray-300 mx-auto" />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-[10px] text-gray-400 mt-2">Shieldio includes AI intelligence (anomaly detection, health scoring, self-healing) at every tier. Competitors restrict AI features to premium plans.</p>
            </div>
          </FadeUp>
        </div>
      </section>

      {/* ═══ SECTION 7: Pricing ═══ */}
      <section id="pricing" className="py-20 px-6 bg-gray-50">
        <div className="max-w-5xl mx-auto">
          <FadeUp>
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900">Simple pricing. No surprises.</h2>
              <p className="mt-3 text-gray-500">Per-user, unlimited storage. Start free, upgrade when ready.</p>
            </div>
          </FadeUp>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                name: 'Community', price: 'Free', period: '', desc: 'For small teams',
                color: 'border-gray-200', btn: 'bg-gray-900 text-white hover:bg-gray-800',
                features: ['Up to 25 users', '3 workloads (M365)', 'Basic Smart Engine', 'Community support', 'Self-hosted'],
              },
              {
                name: 'Professional', price: '$1.50', period: '/user/mo', desc: 'For growing orgs',
                color: 'border-blue-400 ring-2 ring-blue-100', btn: 'bg-blue-600 text-white hover:bg-blue-700', popular: true,
                features: ['Unlimited users', 'All workloads + Teams', 'Full Smart Engine', 'WORM + legal hold', 'SSO + self-service restore', 'Email support + SLA'],
              },
              {
                name: 'Enterprise', price: '$3.00', period: '/user/mo', desc: 'For security-first orgs',
                color: 'border-gray-200', btn: 'bg-gray-900 text-white hover:bg-gray-800',
                features: ['Everything in Pro', 'Multi-SaaS (M365 + GWS)', 'MSP multi-tenant', 'SIEM integration', 'Custom rules + API', 'Priority support (1hr)'],
              },
            ].map((tier, i) => (
              <FadeUp key={tier.name} delay={i * 150}>
                <div className={`relative bg-white rounded-2xl border-2 ${tier.color} p-6 flex flex-col h-full`}>
                  {tier.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-blue-600 text-white text-xs font-semibold rounded-full">
                      Most Popular
                    </div>
                  )}
                  <h3 className="text-lg font-bold text-gray-900">{tier.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">{tier.desc}</p>
                  <div className="mt-4 mb-6">
                    <span className="text-4xl font-extrabold text-gray-900">{tier.price}</span>
                    {tier.period && <span className="text-gray-500 text-sm">{tier.period}</span>}
                  </div>
                  <ul className="space-y-2.5 flex-1">
                    {tier.features.map(f => (
                      <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
                        <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />{f}
                      </li>
                    ))}
                  </ul>
                  <Link to="/login" className={`mt-6 py-2.5 rounded-xl text-sm font-semibold text-center block transition-colors ${tier.btn}`}>
                    {tier.name === 'Enterprise' ? 'Contact Sales' : 'Get Started'}
                  </Link>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ SECTION 8: Deploy ═══ */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <FadeUp>
            <h2 className="text-2xl md:text-3xl font-bold text-gray-900 mb-4">Deploy in 5 minutes</h2>
            <div className="bg-gray-900 rounded-xl p-6 text-left font-mono text-sm max-w-lg mx-auto">
              <p className="text-gray-500"># Clone and start</p>
              <p className="text-green-400">$ git clone https://github.com/gpatwa/m365-vault.git</p>
              <p className="text-green-400">$ cd m365-vault && make dev</p>
              <p className="text-gray-500 mt-2"># Or deploy to Azure</p>
              <p className="text-green-400">$ make acr-push && make tf-apply</p>
              <p className="text-gray-500 mt-2"># Open http://localhost:5173</p>
              <p className="text-blue-400">✓ Ready to protect your data</p>
            </div>
          </FadeUp>
        </div>
      </section>

      {/* ═══ SECTION 9: CTA ═══ */}
      <section className="py-20 px-6 bg-gradient-to-br from-blue-600 to-indigo-700">
        <div className="max-w-3xl mx-auto text-center">
          <FadeUp>
            <h2 className="text-3xl md:text-4xl font-bold text-white">Ready to protect your cloud data?</h2>
            <p className="mt-4 text-blue-100 text-lg">Free for up to 25 users. No credit card. Deploy in minutes.</p>
            <div className="mt-8 flex items-center justify-center gap-4">
              <Link to="/login" className="px-8 py-3.5 bg-white text-blue-600 font-bold rounded-xl hover:bg-blue-50 transition-all hover:shadow-lg flex items-center gap-2">
                Start Free <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          </FadeUp>
        </div>
      </section>

      {/* ═══ Footer ═══ */}
      <footer className="py-12 px-6 bg-gray-900 text-gray-400">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Shield className="w-5 h-5 text-blue-400" />
                <span className="font-bold text-white">Shieldio</span>
              </div>
              <p className="text-sm">SaaS Data Protection Platform</p>
            </div>
            <div>
              <h4 className="font-semibold text-white text-sm mb-3">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#how" className="hover:text-white transition-colors">How It Works</a></li>
                <li><a href="#pricing" className="hover:text-white transition-colors">Pricing</a></li>
                <li><a href="#compare" className="hover:text-white transition-colors">Compare</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white text-sm mb-3">Resources</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="https://github.com/gpatwa/m365-vault" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">GitHub</a></li>
                <li><Link to="/legal" className="hover:text-white transition-colors">Documentation</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white text-sm mb-3">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/legal?tab=tos" className="hover:text-white transition-colors">Terms</Link></li>
                <li><Link to="/legal?tab=privacy" className="hover:text-white transition-colors">Privacy</Link></li>
                <li><Link to="/legal?tab=sla" className="hover:text-white transition-colors">SLA</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-6 text-center text-xs">
            &copy; 2026 Patwa Inc. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
