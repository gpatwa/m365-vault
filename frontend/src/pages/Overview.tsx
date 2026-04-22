import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Shield, ArrowRight, KeyRound, Brain, FileSearch, GitBranch,
  HardDrive, CheckCircle2, Check, Server, ShieldCheck, Scale,
  Mail, Globe, MessageSquare,
} from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { appUrl } from '../utils/appUrl';

// Sales one-pager. Send this URL as a post-meeting follow-up. Print-friendly
// CSS below ensures "Save as PDF" produces a clean artifact for procurement
// files. Content reuses proof points from /welcome, /security, and scenario
// pages, tightened to one scrollable page.

export default function Overview() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Helmet>
        <title>KavachIQ Overview — Identity-First Cyber Recovery for Microsoft 365</title>
        <meta name="description" content="A one-page overview of KavachIQ for Microsoft 365: what it is, who it is for, and why identity-first recovery matters. Forwardable after an intro call or demo." />
        <link rel="canonical" href="https://kavachiq.com/overview" />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://kavachiq.com/overview" />
        <meta property="og:title" content="KavachIQ Overview — Identity-First Cyber Recovery for Microsoft 365" />
        <meta property="og:description" content="One-page overview of KavachIQ for Microsoft 365. Forwardable after a call." />
        <meta property="og:image" content="https://kavachiq.com/og-overview.jpg" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:image" content="https://kavachiq.com/og-overview.jpg" />
        <meta name="twitter:title" content="KavachIQ Overview — Identity-First Cyber Recovery for Microsoft 365" />
        <meta name="twitter:description" content="One-page overview of KavachIQ for Microsoft 365. Forwardable after a call." />
        <style type="text/css">{`
          @media print {
            nav, footer, .no-print { display: none !important; }
            section { page-break-inside: avoid; padding-top: 1rem !important; padding-bottom: 1rem !important; }
            body, .min-h-screen { background: white !important; color: black !important; }
            .bg-card, .bg-muted\\/30, .bg-gradient-to-br { background: white !important; box-shadow: none !important; border: 1px solid #e5e7eb !important; }
            .text-white, .text-teal-100, .text-foreground { color: black !important; }
            .text-muted-foreground { color: #374151 !important; }
            .text-teal-400, .text-teal-500 { color: #0d9488 !important; }
            h1, h2, h3 { color: black !important; }
          }
        `}</style>
      </Helmet>

      {/* Nav (hidden in print) */}
      <nav className="fixed top-0 w-full z-50 bg-card/80 backdrop-blur-sm border-b border-border no-print">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link to="/welcome" className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-teal-500" />
            <span className="font-bold text-foreground">KavachIQ</span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <Link to="/welcome" className="hover:text-foreground">Home</Link>
            <Link to="/tour" className="hover:text-foreground">Product Tour</Link>
            <Link to="/security" className="hover:text-foreground">Security</Link>
            <Link to="/scenarios" className="hover:text-foreground">Scenarios</Link>
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
      <section className="pt-28 pb-10 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-4 no-print">
            <Link to="/welcome" className="hover:text-foreground">KavachIQ</Link>
            <span>/</span>
            <span className="text-foreground">Overview</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-teal-500/10 text-teal-400 rounded-full text-xs font-medium mb-5">
            <Shield className="w-3.5 h-3.5" />
            One-page overview
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold text-foreground leading-[1.1] tracking-tight mb-5">
            KavachIQ is the identity-first cyber recovery platform for{' '}
            <span className="bg-gradient-to-r from-teal-500 to-cyan-500 bg-clip-text text-transparent">
              Microsoft Entra and Microsoft 365.
            </span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-3xl leading-relaxed mb-6">
            We help Microsoft 365 teams assess blast radius, restore Microsoft Entra controls first, recover critical users next, and bring business data back online with confidence. Purpose-built for Microsoft 365 recovery, not a generic backup product.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 no-print">
            <Link to="/contact" className="px-6 py-3 bg-teal-600 text-white font-semibold rounded-xl hover:bg-teal-700 transition-all flex items-center gap-2">
              Request a Demo <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/tour" className="px-6 py-3 border border-teal-500/30 text-teal-400 font-medium rounded-xl hover:bg-teal-500/10 transition-colors">
              See the Product Tour
            </Link>
          </div>
        </div>
      </section>

      {/* The problem */}
      <section className="py-10 px-6 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <div className="text-xs font-bold text-rose-400 tracking-widest mb-2">THE PROBLEM</div>
          <h2 className="text-2xl font-bold text-foreground mb-3">Microsoft 365 incidents rarely look like clean data-loss events</h2>
          <p className="text-muted-foreground leading-relaxed mb-5 max-w-3xl">
            Real incidents mix compromised identities, destructive admin actions, and ambiguous blast radius. Data is not the only thing that moves. Roles, conditional access, OAuth grants, groups, and retention policies all drift at the same time.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { t: 'Identity compromise', d: 'MFA weakened, Global Admin abused, conditional access modified, OAuth grants expanded.' },
              { t: 'Destructive change', d: 'Mass deletions across SharePoint and OneDrive. Mailboxes purged. Retention policies shift at the same time.' },
              { t: 'Blast radius unknown', d: 'Who was affected, what changed, and what to restore first is the hardest part of any incident.' },
            ].map(p => (
              <div key={p.t} className="bg-card border border-border rounded-xl p-4">
                <h3 className="font-semibold text-foreground mb-1 text-sm">{p.t}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{p.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why backup alone is not enough + Why identity-first matters */}
      <section className="py-10 px-6">
        <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-card border border-border rounded-xl p-5">
            <div className="text-xs font-bold text-amber-400 tracking-widest mb-2">WHY BACKUP ALONE IS NOT ENOUGH</div>
            <h2 className="text-xl font-bold text-foreground mb-3">Backup preserves data. Recovery is a different problem.</h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Microsoft and third-party backup products keep copies of mailboxes, sites, files, and increasingly identity configuration. Recovery is where teams struggle. When the pressure is on, the question is not "do I have a backup?" It is "what changed, who is affected, what do I restore first, and how do I know we are actually back online?"
            </p>
          </div>
          <div className="bg-card border border-border rounded-xl p-5">
            <div className="text-xs font-bold text-teal-500 tracking-widest mb-2">WHY IDENTITY-FIRST MATTERS</div>
            <h2 className="text-xl font-bold text-foreground mb-3">Data recovery without identity recovery is incomplete.</h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Restoring mailboxes before restoring identity controls is unsafe. Attackers and broken policies stay in place until identity is corrected. KavachIQ restores Entra controls first, recovers critical users next, and verifies recovery with evidence before the broader tenant is touched.
            </p>
          </div>
        </div>
      </section>

      {/* What KavachIQ does — capabilities */}
      <section className="py-10 px-6 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <div className="text-xs font-bold text-teal-500 tracking-widest mb-2">WHAT KAVACHIQ DOES</div>
          <h2 className="text-2xl font-bold text-foreground mb-5">Six capabilities, purpose-built for Microsoft 365 recovery</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { icon: KeyRound, title: 'Entra Recovery', desc: 'Snapshot and restore 12 Entra ID object types: users, groups, roles, conditional access, OAuth grants, service principals, and more.' },
              { icon: Brain, title: 'Criticality-Based Recovery', desc: 'Score users and systems by role, sensitivity, activity, and business dependency. Recover what matters first.' },
              { icon: FileSearch, title: 'Blast Radius Analysis', desc: 'See what changed, who was affected, which systems are at risk. Diff identity and data state across snapshots.' },
              { icon: GitBranch, title: 'Guided Recovery Plans', desc: 'Pre-computed, NIST-aligned plans refreshed on schedule. Identity first, critical users next, full recovery after.' },
              { icon: HardDrive, title: 'M365 Data Recovery', desc: 'Unlimited point-in-time restore across Exchange, OneDrive, SharePoint, and Teams.' },
              { icon: CheckCircle2, title: 'Recovery Verification', desc: 'Checksum validation, policy-active checks, and sign-in tests confirm you are actually back online.' },
            ].map(f => (
              <div key={f.title} className="bg-card border border-border rounded-xl p-4">
                <div className="w-9 h-9 rounded-lg bg-teal-500/10 flex items-center justify-center mb-3">
                  <f.icon className="w-5 h-5 text-teal-400" />
                </div>
                <h3 className="font-semibold text-foreground mb-1 text-sm">{f.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Workloads + who for */}
      <section className="py-10 px-6">
        <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="text-xs font-bold text-teal-500 tracking-widest mb-2">WORKLOADS PROTECTED</div>
            <h2 className="text-xl font-bold text-foreground mb-4">Microsoft Entra and Microsoft 365</h2>
            <div className="space-y-2">
              {[
                { icon: KeyRound, label: 'Microsoft Entra', desc: '12 identity object types, policy and role drift' },
                { icon: Mail, label: 'Exchange Online', desc: 'Mailboxes, calendars, contacts' },
                { icon: HardDrive, label: 'OneDrive', desc: 'User files and folders' },
                { icon: Globe, label: 'SharePoint', desc: 'Sites, lists, documents' },
                { icon: MessageSquare, label: 'Teams', desc: 'Chats, channels, files' },
              ].map(w => (
                <div key={w.label} className="flex items-center gap-3 bg-card border border-border rounded-lg px-3 py-2">
                  <w.icon className="w-4 h-4 text-teal-400 shrink-0" />
                  <div className="text-sm">
                    <span className="font-medium text-foreground">{w.label}</span>
                    <span className="text-muted-foreground"> — {w.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs font-bold text-teal-500 tracking-widest mb-2">WHO IT IS FOR</div>
            <h2 className="text-xl font-bold text-foreground mb-4">Microsoft 365 teams that own recovery</h2>
            <div className="space-y-3">
              <div className="bg-card border border-border rounded-lg p-3 flex items-start gap-3">
                <Server className="w-5 h-5 text-teal-400 mt-0.5 shrink-0" />
                <div>
                  <div className="font-semibold text-foreground text-sm mb-0.5">Microsoft 365 and Entra admins</div>
                  <p className="text-xs text-muted-foreground leading-relaxed">Practical recovery workflow for the people inside M365 every day. Built on Microsoft Graph.</p>
                </div>
              </div>
              <div className="bg-card border border-border rounded-lg p-3 flex items-start gap-3">
                <ShieldCheck className="w-5 h-5 text-teal-400 mt-0.5 shrink-0" />
                <div>
                  <div className="font-semibold text-foreground text-sm mb-0.5">IT and security leaders</div>
                  <p className="text-xs text-muted-foreground leading-relaxed">Know your recovery time, order, and confidence before an incident. Aligned to NIST SP 800-184.</p>
                </div>
              </div>
              <div className="bg-card border border-border rounded-lg p-3 flex items-start gap-3">
                <Scale className="w-5 h-5 text-teal-400 mt-0.5 shrink-0" />
                <div>
                  <div className="font-semibold text-foreground text-sm mb-0.5">Procurement and risk</div>
                  <p className="text-xs text-muted-foreground leading-relaxed">Enterprise controls on day one. Per-tenant keys, audit trail, compliance-mapped evidence.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Proof points */}
      <section className="py-10 px-6 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <div className="text-xs font-bold text-teal-500 tracking-widest mb-2">PROOF POINTS</div>
          <h2 className="text-2xl font-bold text-foreground mb-5">What is built into every deployment</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'AES-256-GCM', desc: 'Encryption at rest' },
              { label: 'Per-tenant keys', desc: 'Key isolation' },
              { label: 'WORM storage', desc: 'Immutable backups' },
              { label: 'SSO + MFA', desc: 'Entra OIDC' },
              { label: 'SOC 2', desc: '16 controls mapped' },
              { label: 'GDPR', desc: '8 articles mapped' },
              { label: 'HIPAA', desc: '14 safeguards mapped' },
              { label: 'DORA', desc: 'Financial sector' },
            ].map(b => (
              <div key={b.label} className="bg-card border border-border rounded-lg px-3 py-2.5">
                <div className="text-sm font-semibold text-foreground">{b.label}</div>
                <div className="text-xs text-muted-foreground">{b.desc}</div>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5">
            <div className="bg-card border border-border rounded-xl p-4">
              <div className="text-sm font-semibold text-foreground mb-1">Six-phase recovery workflow</div>
              <div className="text-xs text-muted-foreground">Protect · Monitor · Detect · Assess · Recover · Verify</div>
            </div>
            <div className="bg-card border border-border rounded-xl p-4">
              <div className="text-sm font-semibold text-foreground mb-1">Recovery scenarios</div>
              <div className="text-xs text-muted-foreground">Compromised Global Admin, destructive SharePoint/OneDrive deletion, bulk mailbox deletion with retention drift.</div>
            </div>
            <div className="bg-card border border-border rounded-xl p-4">
              <div className="text-sm font-semibold text-foreground mb-1">Deployed on Azure</div>
              <div className="text-xs text-muted-foreground">Azure Container Apps, Azure Storage, Azure Database for PostgreSQL. Region configured at deployment.</div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-10 px-6 bg-gradient-to-br from-teal-600 to-cyan-700">
        <div className="max-w-4xl mx-auto text-center text-white">
          <h2 className="text-2xl md:text-3xl font-bold mb-3">See KavachIQ in your Microsoft 365 environment</h2>
          <p className="text-teal-100 mb-6 max-w-xl mx-auto leading-relaxed">
            Walk a recovery scenario with a KavachIQ engineer. Typical first call runs 30 minutes.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 no-print">
            <Link to="/contact" className="inline-flex items-center gap-2 px-6 py-3 bg-white text-teal-700 font-semibold rounded-xl hover:bg-teal-50 transition-colors">
              Request a Demo <ArrowRight className="w-5 h-5" />
            </Link>
            <Link to="/scenarios" className="inline-flex items-center gap-2 px-6 py-3 border-2 border-white/30 text-white font-medium rounded-xl hover:bg-white/10 transition-colors">
              Browse recovery scenarios
            </Link>
          </div>
          <p className="mt-6 text-xs text-teal-100/80">
            kavachiq.com <span className="mx-2">·</span> hello@kavachiq.com <span className="mx-2">·</span> security@kavachiq.com
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-6 px-6 border-t border-border no-print">
        <div className="max-w-4xl mx-auto text-center text-xs text-muted-foreground">
          &copy; {new Date().getFullYear()} KavachIQ. All rights reserved.
          <span className="mx-2">·</span>
          <Check className="w-3 h-3 inline -mt-0.5" /> Tip: print this page to save a PDF overview.
        </div>
      </footer>
    </div>
  );
}
