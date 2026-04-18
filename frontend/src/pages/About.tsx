import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Shield, KeyRound, ArrowRight, Brain, ShieldCheck, Check, AlertTriangle, FileSearch, GitBranch, CheckCircle2 } from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { appUrl } from '../utils/appUrl';

export default function About() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Helmet>
        <title>About KavachIQ — Identity-First Cyber Recovery for Microsoft 365</title>
        <meta name="description" content="KavachIQ is the identity-first cyber recovery platform for Microsoft Entra and Microsoft 365. Restore identity controls first, recover critical users next, verify business recovery." />
        <link rel="canonical" href="https://kavachiq.com/about" />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://kavachiq.com/about" />
        <meta property="og:title" content="About KavachIQ — Identity-First Cyber Recovery for Microsoft 365" />
        <meta property="og:description" content="Purpose-built for Microsoft 365 recovery. Identity first. Critical users next. Verified business recovery." />
        <meta property="og:image" content="https://kavachiq.com/og-about.jpg" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="About KavachIQ — Identity-First Cyber Recovery for Microsoft 365" />
        <meta name="twitter:description" content="Purpose-built for Microsoft 365 recovery. Identity first. Critical users next. Verified business recovery." />
      </Helmet>

      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 bg-card/80 backdrop-blur-sm border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link to="/welcome" className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-teal-500" />
            <span className="font-bold text-foreground">KavachIQ</span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <Link to="/welcome" className="hover:text-foreground">Home</Link>
            <Link to="/about" className="text-foreground font-medium">About</Link>
            <Link to="/tour" className="hover:text-foreground">Product Tour</Link>
            <Link to="/contact" className="hover:text-foreground">Contact</Link>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <a href={appUrl('/login')} className="hidden sm:inline text-sm text-muted-foreground hover:text-foreground">Sign In</a>
            <Link to="/contact" className="px-4 py-1.5 bg-gradient-to-r from-teal-500 to-cyan-500 text-white text-sm font-medium rounded-lg">
              Request a Demo
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-28 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-teal-500/10 text-teal-400 rounded-full text-xs font-medium mb-6">
            <Shield className="w-3.5 h-3.5" />
            Identity-first cyber recovery for Microsoft 365
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold leading-[1.1] mb-6">
            Recovery starts with{' '}
            <span className="bg-gradient-to-r from-teal-500 to-cyan-500 bg-clip-text text-transparent">
              who has admin access.
            </span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-4">
            When a Microsoft 365 incident happens, restoring data is not enough. Identity controls, policies, roles, and group access must come back in the right order.
          </p>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            KavachIQ is a focused cyber recovery platform for Microsoft Entra and Microsoft 365. We help teams assess blast radius, restore identity controls first, recover critical users next, and verify business recovery with evidence.
          </p>
        </div>
      </section>

      {/* The Problem vs Solution */}
      <section className="py-16 px-6 bg-muted/50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-bold mb-3">The recovery gap most teams miss</h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              When a ransomware or destructive-change incident hits a Microsoft 365 tenant, the first thirty minutes determine everything.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-card border border-red-500/20 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-red-500/10 rounded-lg flex items-center justify-center">
                  <AlertTriangle className="w-4 h-4 text-red-400" />
                </div>
                <h3 className="font-bold text-red-400">Without identity-first recovery</h3>
              </div>
              <div className="space-y-3 text-sm">
                {[
                  'Attacker disables MFA, grants themselves Global Admin',
                  'You restore mailboxes and files, but attacker still holds admin access',
                  'Policies and roles stay misconfigured. Re-compromise is fast',
                  'Manual triage: who was affected, what changed, where to start',
                ].map(t => (
                  <div key={t} className="flex items-start gap-2 text-muted-foreground">
                    <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                    <span>{t}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-card border border-teal-500/20 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-teal-500/10 rounded-lg flex items-center justify-center">
                  <Check className="w-4 h-4 text-teal-400" />
                </div>
                <h3 className="font-bold text-teal-400">With KavachIQ</h3>
              </div>
              <div className="space-y-3 text-sm">
                {[
                  'Phase 1: Restore Entra ID. MFA, conditional access, roles, OAuth grants',
                  'Phase 2: Recover critical users. Executives, admins, compliance owners',
                  'Phase 3: Restore high-priority departments and sites',
                  'Phase 4: Full business recovery, verified with evidence',
                ].map(t => (
                  <div key={t} className="flex items-start gap-2 text-muted-foreground">
                    <Check className="w-4 h-4 text-teal-400 mt-0.5 shrink-0" />
                    <span>{t}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Product capability pillars */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold mb-3 text-center">Purpose-built for Microsoft 365 recovery</h2>
          <p className="text-center text-muted-foreground max-w-2xl mx-auto mb-10">
            Six capabilities that work together to get Microsoft 365 teams back online.
          </p>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: KeyRound, title: 'Entra Recovery', desc: 'Snapshot and restore 12 Entra ID object types: users, groups, roles, conditional access, OAuth grants, service principals, administrative units, and more.', color: 'from-amber-500 to-orange-500' },
              { icon: Brain, title: 'Criticality-Based Recovery', desc: 'Score users and systems by role weight, data sensitivity, activity, and business dependency. Recover what matters first, automatically.', color: 'from-teal-500 to-cyan-500' },
              { icon: FileSearch, title: 'Blast Radius Analysis', desc: 'See exactly what changed, who was affected, and which systems are at risk. Diff identity and data state across snapshots.', color: 'from-rose-500 to-red-500' },
              { icon: GitBranch, title: 'Guided Recovery Plans', desc: 'Pre-computed, NIST SP 800-184-aligned plans refreshed on schedule. Phase 1 identity, Phase 2 critical users, Phase 3 high-priority, Phase 4 full recovery.', color: 'from-green-500 to-emerald-500' },
              { icon: ShieldCheck, title: 'Microsoft 365 Data Recovery', desc: 'Unlimited point-in-time restore across Exchange, OneDrive, SharePoint, and Teams. Granular per-item and workload-wide restore.', color: 'from-blue-500 to-indigo-500' },
              { icon: CheckCircle2, title: 'Recovery Verification', desc: 'Recovery confidence scored with evidence: checksum validation, policy-active checks, and sign-in tests confirm business recovery.', color: 'from-purple-500 to-violet-500' },
            ].map(d => (
              <div key={d.title} className="bg-card border border-border rounded-xl p-6 hover:border-teal-500/30 transition-all hover:shadow-lg hover:shadow-teal-500/5">
                <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${d.color} flex items-center justify-center mb-4`}>
                  <d.icon className="w-5 h-5 text-white" />
                </div>
                <h3 className="font-bold mb-2">{d.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{d.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Positioning statement */}
      <section className="py-16 px-6 bg-muted/50">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-6">Focused, not generic</h2>
          <div className="space-y-4 text-muted-foreground leading-relaxed">
            <p>
              Microsoft 365 is where the modern workplace actually lives. Mailboxes, files, meetings, chats, policies, and identities all sit inside one tenant.
            </p>
            <p>
              When an incident hits, generalized backup products and broad cyber-resilience suites solve adjacent problems. They do not focus on Microsoft 365 recovery in the way a Microsoft 365 admin actually runs one.
            </p>
            <p className="text-foreground font-medium">
              KavachIQ exists to be the practical, identity-aware recovery platform for Microsoft 365 teams. Nothing more, nothing less.
            </p>
          </div>
        </div>
      </section>

      {/* Trust & Compliance */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-2xl font-bold mb-3">Enterprise controls on day one</h2>
          <p className="text-muted-foreground mb-8">Encryption, immutability, and compliance mappings are built into every deployment.</p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            {[
              { icon: '🔒', label: 'AES-256-GCM', desc: 'Encryption at Rest' },
              { icon: '🔑', label: 'Per-Tenant Keys', desc: 'Key Isolation' },
              { icon: '🛡️', label: 'WORM Storage', desc: 'Immutable Backups' },
              { icon: '✅', label: 'SOC 2', desc: '16 controls mapped' },
              { icon: '🇪🇺', label: 'GDPR', desc: '8 articles mapped' },
              { icon: '🏥', label: 'HIPAA', desc: '14 safeguards mapped' },
              { icon: '🏦', label: 'DORA', desc: 'Financial sector' },
              { icon: '📋', label: 'Full Audit Trail', desc: 'Every action logged' },
            ].map(b => (
              <div key={b.label} className="flex items-center gap-2.5 px-4 py-3 bg-card border border-border rounded-xl">
                <span className="text-lg">{b.icon}</span>
                <div className="text-left">
                  <div className="text-xs font-semibold text-foreground">{b.label}</div>
                  <div className="text-[10px] text-muted-foreground">{b.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Industries */}
      <section className="py-16 px-6 bg-muted/50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-3 text-center">Built for regulated and security-aware teams</h2>
          <p className="text-muted-foreground text-center max-w-2xl mx-auto mb-10">
            Microsoft 365 is the system of record for many regulated environments. Recovery has to fit the way these teams actually operate.
          </p>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: '🏥', title: 'Healthcare', desc: 'HIPAA-ready recovery for clinics and medical groups. Protect Entra ID and patient data across Exchange and Teams. Identity-first recovery ensures admin access is restored before patient records.', users: '50-500 users' },
              { icon: '⚖️', title: 'Law Firms', desc: 'WORM-backed immutable storage supports legal hold. Entra ID rollback protects privileged access to case files. Per-tenant keys and audit trail support client confidentiality.', users: '20-200 users' },
              { icon: '🏦', title: 'Financial Services', desc: 'DORA and SOX-aligned controls. Criticality scoring prioritizes trading desks and compliance officers. Recovery verification produces the evidence auditors expect.', users: '50-1,000 users' },
            ].map(s => (
              <div key={s.title} className="bg-card border border-border rounded-xl p-6">
                <span className="text-3xl">{s.icon}</span>
                <h3 className="font-bold mt-3 mb-1">{s.title}</h3>
                <span className="text-[10px] text-teal-400 font-semibold uppercase">{s.users}</span>
                <p className="text-sm text-muted-foreground mt-2 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 px-6 bg-gradient-to-br from-teal-600 to-cyan-700">
        <div className="max-w-3xl mx-auto text-center text-white">
          <h2 className="text-3xl font-bold mb-4">See KavachIQ in your Microsoft 365 environment</h2>
          <p className="text-teal-100 mb-8 max-w-xl mx-auto">
            Request a walkthrough with a recovery engineer. Bring your Entra, ransomware, or incident-scenario questions.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/contact"
              className="px-8 py-3.5 bg-white text-teal-700 font-semibold rounded-xl hover:bg-teal-50 transition-colors text-lg flex items-center gap-2">
              Request a Demo <ArrowRight className="w-5 h-5" />
            </Link>
            <Link to="/tour"
              className="px-8 py-3.5 border-2 border-white/30 text-white font-medium rounded-xl hover:bg-white/10 transition-colors text-lg">
              See the Product Tour
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-border">
        <div className="max-w-4xl mx-auto text-center text-xs text-muted-foreground">
          &copy; {new Date().getFullYear()} KavachIQ. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
