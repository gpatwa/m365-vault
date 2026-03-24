import { Link } from 'react-router-dom';
import {
  Shield, Mail, HardDrive, Globe, MessageSquare, KeyRound,
  Brain, Lock, Search, BarChart3, Bell, RotateCcw,
  CheckCircle, ArrowRight, Zap, Server, ChevronRight,
} from 'lucide-react';

const WORKLOADS = [
  { icon: Mail, label: 'Exchange', desc: 'Emails, Calendar, Contacts', color: 'text-blue-600 bg-blue-50' },
  { icon: HardDrive, label: 'OneDrive', desc: 'Files & Folders', color: 'text-purple-600 bg-purple-50' },
  { icon: Globe, label: 'SharePoint', desc: 'Sites, Lists, Documents', color: 'text-green-600 bg-green-50' },
  { icon: MessageSquare, label: 'Teams', desc: 'Channels, Chats, Files', color: 'text-pink-600 bg-pink-50' },
  { icon: KeyRound, label: 'Entra ID', desc: 'Users, Groups, Policies', color: 'text-amber-600 bg-amber-50' },
];

const FEATURES = [
  { icon: Brain, title: 'Smart Engine', desc: 'Zero-cost anomaly detection, health scoring, and self-healing — no AI tokens burned' },
  { icon: Lock, title: 'WORM Storage', desc: 'Immutable backups with retention locks and legal hold for ransomware resilience' },
  { icon: Search, title: 'Global Search', desc: 'Find any email, file, or message across all workloads instantly with ⌘K' },
  { icon: Bell, title: 'Smart Alerts', desc: 'Email and webhook notifications for failures, anomalies, and SLA violations' },
  { icon: RotateCcw, title: 'Self-Service Restore', desc: 'End users recover their own deleted items without IT tickets' },
  { icon: BarChart3, title: 'Reports & Analytics', desc: 'Backup performance, storage trends, SLA compliance, and failure analysis' },
];

const TIERS = [
  {
    name: 'Community',
    price: 'Free',
    period: '',
    desc: 'For small teams getting started',
    color: 'border-gray-200',
    btn: 'bg-gray-900 text-white hover:bg-gray-800',
    features: ['Up to 25 users', 'Exchange, OneDrive, SharePoint', 'Basic Smart Engine', 'Community support (GitHub)', 'Self-hosted'],
  },
  {
    name: 'Professional',
    price: '$1.50',
    period: '/user/month',
    desc: 'For growing organizations',
    color: 'border-blue-400 ring-2 ring-blue-100',
    btn: 'bg-blue-600 text-white hover:bg-blue-700',
    popular: true,
    features: ['Unlimited users', 'All 5 workloads + Teams + Entra ID', 'Full Smart Engine + anomaly detection', 'WORM + legal hold', 'SSO (Entra ID OIDC)', 'Email support + SLA', 'Self-service restore portal'],
  },
  {
    name: 'Enterprise',
    price: '$3.00',
    period: '/user/month',
    desc: 'For security-first enterprises',
    color: 'border-gray-200',
    btn: 'bg-gray-900 text-white hover:bg-gray-800',
    features: ['Everything in Professional', 'Power Platform backup', 'MSP multi-tenant console', 'SIEM integration', 'Custom alert rules', 'Dedicated CSM', 'Priority support (1hr SLA)'],
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-white">
      {/* ═══ Navbar ═══ */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <Shield className="w-7 h-7 text-blue-600" />
            <span className="text-lg font-bold text-gray-900">Shieldio</span>
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-600">
            <a href="#features" className="hover:text-gray-900 transition-colors">Features</a>
            <a href="#workloads" className="hover:text-gray-900 transition-colors">Workloads</a>
            <a href="#pricing" className="hover:text-gray-900 transition-colors">Pricing</a>
            <Link to="/legal" className="hover:text-gray-900 transition-colors">Legal</Link>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
              Sign In
            </Link>
            <Link to="/login" className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* ═══ Hero ═══ */}
      <section className="pt-20 pb-16 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium mb-6">
            <Zap className="w-3 h-3" /> SaaS Data Protection Platform
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold text-gray-900 leading-tight tracking-tight">
            Protect Your<br />
            <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              Cloud Data
            </span>
          </h1>
          <p className="mt-6 text-xl text-gray-500 max-w-2xl mx-auto leading-relaxed">
            Back up Exchange, OneDrive, SharePoint, Teams, and Entra ID with
            enterprise-grade security. Self-hosted. Zero AI token costs.
            Open source.
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <Link
              to="/login"
              className="px-6 py-3 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              Start Free <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href="https://github.com/gpatwa/m365-vault"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 bg-gray-100 text-gray-700 font-medium rounded-xl hover:bg-gray-200 transition-colors flex items-center gap-2"
            >
              <Server className="w-4 h-4" /> View on GitHub
            </a>
          </div>
          <p className="mt-4 text-xs text-gray-400">
            Free for up to 25 users. No credit card required.
          </p>
        </div>
      </section>

      {/* ═══ Workloads ═══ */}
      <section id="workloads" className="py-16 px-6 bg-gray-50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900">5 Workloads Protected</h2>
            <p className="mt-2 text-gray-500">Comprehensive backup across your entire Microsoft 365 environment</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {WORKLOADS.map(w => (
              <div key={w.label} className="bg-white rounded-xl border border-gray-200 p-5 text-center hover:shadow-md transition-shadow">
                <div className={`w-12 h-12 rounded-xl ${w.color} flex items-center justify-center mx-auto mb-3`}>
                  <w.icon className="w-6 h-6" />
                </div>
                <h3 className="font-semibold text-gray-900">{w.label}</h3>
                <p className="text-xs text-gray-500 mt-1">{w.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ Features ═══ */}
      <section id="features" className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900">Built for Enterprise</h2>
            <p className="mt-2 text-gray-500">Intelligence, security, and compliance — all at zero marginal cost</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map(f => (
              <div key={f.title} className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition-shadow">
                <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center mb-4">
                  <f.icon className="w-5 h-5 text-blue-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ Why Shieldio ═══ */}
      <section className="py-16 px-6 bg-gray-900 text-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold">Why Shieldio?</h2>
            <p className="mt-2 text-gray-400">What makes us different from Veeam, Druva, and Commvault</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { title: 'Open Source', desc: 'Full source code transparency. No vendor lock-in. Deploy anywhere — any cloud, on-premises, or air-gapped.', icon: '🔓' },
              { title: 'Zero AI Token Cost', desc: 'Smart Engine runs on pure Python (scipy + regex). Same anomaly detection as competitors charging $5-10/user extra.', icon: '🧠' },
              { title: 'Data Sovereignty', desc: 'Your backup data never leaves your infrastructure. AES-256-GCM encryption with per-tenant keys. GDPR/DORA ready.', icon: '🛡️' },
            ].map(item => (
              <div key={item.title} className="text-center">
                <div className="text-4xl mb-4">{item.icon}</div>
                <h3 className="text-xl font-bold mb-2">{item.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ Pricing ═══ */}
      <section id="pricing" className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900">Simple, Transparent Pricing</h2>
            <p className="mt-2 text-gray-500">Per-user, unlimited storage. No hidden fees. No surprise overages.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {TIERS.map(tier => (
              <div key={tier.name} className={`relative bg-white rounded-2xl border-2 ${tier.color} p-6 flex flex-col`}>
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
                <ul className="space-y-3 flex-1">
                  {tier.features.map(f => (
                    <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
                      <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  to="/login"
                  className={`mt-6 py-2.5 rounded-xl text-sm font-semibold text-center transition-colors ${tier.btn}`}
                >
                  {tier.name === 'Enterprise' ? 'Contact Sales' : 'Get Started'}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ CTA ═══ */}
      <section className="py-16 px-6 bg-blue-600">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white">Ready to protect your cloud data?</h2>
          <p className="mt-3 text-blue-100 text-lg">Free for up to 25 users. Deploy in minutes.</p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <Link to="/login" className="px-6 py-3 bg-white text-blue-600 font-semibold rounded-xl hover:bg-blue-50 transition-colors flex items-center gap-2">
              Start Free <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
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
              <p className="text-sm">SaaS data protection platform.</p>
            </div>
            <div>
              <h4 className="font-semibold text-white text-sm mb-3">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
                <li><a href="#pricing" className="hover:text-white transition-colors">Pricing</a></li>
                <li><a href="#workloads" className="hover:text-white transition-colors">Workloads</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white text-sm mb-3">Resources</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="https://github.com/gpatwa/m365-vault" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">GitHub</a></li>
                <li><Link to="/legal" className="hover:text-white transition-colors">Documentation</Link></li>
                <li><Link to="/legal?tab=tos" className="hover:text-white transition-colors">API Reference</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white text-sm mb-3">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/legal?tab=tos" className="hover:text-white transition-colors">Terms of Service</Link></li>
                <li><Link to="/legal?tab=privacy" className="hover:text-white transition-colors">Privacy Policy</Link></li>
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
