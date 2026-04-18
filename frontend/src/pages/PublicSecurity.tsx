import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Shield, ArrowRight, Lock, KeyRound, Archive, Users, FileText, Eye,
  CheckCircle2, Activity, ShieldCheck, Server, GitBranch,
} from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { appUrl } from '../utils/appUrl';

// Public marketing security page for enterprise buyers, security reviewers,
// and procurement teams. Consolidates trust signals previously only on the
// homepage #security anchor. Companion to /docs, not a replacement.

const PRINCIPLES = [
  {
    icon: Shield,
    title: 'Microsoft-native access model',
    desc: 'KavachIQ uses Microsoft Entra OAuth admin consent. Your Global Admin approves scoped access. No passwords are stored, only tenant-scoped API tokens.',
  },
  {
    icon: Users,
    title: 'Tenant-scoped by design',
    desc: 'Every backup, snapshot, restore job, and audit record is scoped to a tenant. Cross-tenant access is not a path in the product.',
  },
  {
    icon: KeyRound,
    title: 'Identity-aware recovery',
    desc: 'Identity and workload state are captured and restored together. Recovery actions are logged, attributable, and reversible per object.',
  },
  {
    icon: ShieldCheck,
    title: 'Enterprise controls on day one',
    desc: 'Encryption, per-tenant keys, immutable storage, SSO, MFA, audit trail, and compliance mapping are built in from the first deployment.',
  },
];

const CONTROLS = [
  { icon: Lock, title: 'Encryption at rest', desc: 'AES-256-GCM for all stored data. Keys are rotated and managed per tenant.' },
  { icon: KeyRound, title: 'Per-tenant keys', desc: 'Each tenant has its own data encryption key, wrapped by a master key. A tenant key compromise cannot expose another tenant.' },
  { icon: Archive, title: 'WORM / immutable backups', desc: 'Snapshots under a WORM-enabled SLA are locked for the retention window. Deletion is blocked at the storage and API layers until the lock expires.' },
  { icon: Shield, title: 'SSO and MFA', desc: 'Sign in via Microsoft Entra OIDC. MFA enforcement is inherited from the tenant.' },
  { icon: FileText, title: 'Audit trail', desc: 'Every privileged action is logged with timestamp, user, tenant, and result. Audit records are exportable for security and compliance review.' },
  { icon: Users, title: 'Role-based access', desc: 'Platform admin, MSP admin, tenant admin, and viewer roles. Least-privilege by default. Viewer accounts cannot take destructive actions.' },
  { icon: Eye, title: 'Tenant-scoped access', desc: 'Every API call and UI action is scoped to an explicit tenant. Cross-tenant operations require platform-admin privileges and produce audit records.' },
  { icon: CheckCircle2, title: 'Recovery verification', desc: 'Checksum validation, policy-active checks, and sign-in tests confirm a recovery actually restored the expected state.' },
];

const COMPLIANCE = [
  { icon: '✅', framework: 'SOC 2', detail: '16 controls mapped: access control, encryption, audit, change management, incident response, and monitoring.' },
  { icon: '🇪🇺', framework: 'GDPR', detail: '8 articles mapped: right to erasure, data portability export, breach notification, and processor obligations.' },
  { icon: '🏥', framework: 'HIPAA', detail: '14 safeguards mapped: administrative, physical, and technical safeguards for ePHI in Microsoft 365.' },
  { icon: '🏦', framework: 'DORA', detail: 'Digital Operational Resilience Act controls for financial-sector operational recovery mapped against KavachIQ capabilities.' },
];

const ARCHITECTURE = [
  { icon: Server, title: 'Deployed on Azure', desc: 'Primary deployment is on Microsoft Azure Container Apps with Azure Storage and Azure Database for PostgreSQL.' },
  { icon: GitBranch, title: 'Control plane and data plane', desc: 'Control plane (API, scheduler, UI) is separate from the data plane (snapshot storage). Snapshots live in tenant-scoped, per-tenant-encrypted storage.' },
  { icon: Activity, title: 'Microsoft Graph integration', desc: 'Built on Microsoft Graph for Entra, Exchange, OneDrive, SharePoint, and Teams. Permissions use least-privilege scopes per workload.' },
  { icon: FileText, title: 'API and onboarding', desc: 'Documented API for tenant onboarding, workload enablement, and restore operations. OAuth admin consent handles permission grants.' },
];

export default function PublicSecurity() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Helmet>
        <title>Security — KavachIQ for Microsoft 365</title>
        <meta name="description" content="Enterprise security for Microsoft 365 cyber recovery. Tenant-scoped access, encryption, immutable backups, audit trail, and compliance-mapped controls from day one." />
        <link rel="canonical" href="https://kavachiq.com/security" />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://kavachiq.com/security" />
        <meta property="og:title" content="Security — KavachIQ for Microsoft 365" />
        <meta property="og:description" content="Enterprise security controls, tenant isolation, encryption, immutability, and compliance mappings for KavachIQ." />
        <meta property="og:image" content="https://kavachiq.com/og-security.jpg" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:image" content="https://kavachiq.com/og-security.jpg" />
        <meta name="twitter:title" content="Security — KavachIQ for Microsoft 365" />
        <meta name="twitter:description" content="Enterprise security controls, tenant isolation, encryption, immutability, and compliance mappings for KavachIQ." />
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
            <Link to="/tour" className="hover:text-foreground">Product Tour</Link>
            <Link to="/security" className="text-foreground font-medium">Security</Link>
            <Link to="/about" className="hover:text-foreground">About</Link>
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
      <section className="pt-28 pb-16 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-teal-500/10 text-teal-400 rounded-full text-xs font-medium mb-5">
            <ShieldCheck className="w-3.5 h-3.5" />
            Enterprise trust
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold text-foreground leading-[1.1] tracking-tight mb-6">
            Enterprise security for{' '}
            <span className="bg-gradient-to-r from-teal-500 to-cyan-500 bg-clip-text text-transparent">
              Microsoft 365 cyber recovery.
            </span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-3xl mb-8 leading-relaxed">
            KavachIQ is built for security-aware and regulated teams. Tenant-scoped access, encryption, immutability, auditability, and compliance-mapped controls from day one.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <Link to="/contact" className="px-6 py-3 bg-teal-600 text-white font-semibold rounded-xl hover:bg-teal-700 transition-all hover:shadow-lg hover:shadow-teal-200/20 flex items-center gap-2">
              Request a Demo <ArrowRight className="w-4 h-4" />
            </Link>
            <a href="mailto:security@kavachiq.com?subject=Security%20and%20procurement%20inquiry" className="px-6 py-3 border border-teal-500/30 text-teal-400 font-medium rounded-xl hover:bg-teal-500/10 transition-colors flex items-center gap-2">
              Security &amp; Procurement
            </a>
          </div>
        </div>
      </section>

      {/* Principles */}
      <section className="py-16 px-6 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <div className="mb-10">
            <div className="text-xs font-bold text-teal-500 tracking-widest mb-2">SECURITY PRINCIPLES</div>
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">How KavachIQ thinks about trust</h2>
            <p className="text-muted-foreground max-w-3xl leading-relaxed">
              A small set of principles drives how the product handles customer data and recovery actions.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {PRINCIPLES.map((p, i) => (
              <div key={i} className="bg-card border border-border rounded-xl p-5 h-full">
                <div className="w-10 h-10 rounded-lg bg-teal-500/10 flex items-center justify-center mb-3">
                  <p.icon className="w-5 h-5 text-teal-400" />
                </div>
                <h3 className="font-semibold text-foreground mb-1.5">{p.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{p.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Core controls */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="mb-10">
            <div className="text-xs font-bold text-teal-500 tracking-widest mb-2">CORE CONTROLS</div>
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">Controls built into every deployment</h2>
            <p className="text-muted-foreground max-w-3xl leading-relaxed">
              Encryption, immutability, access, and logging are enforced from the first tenant onboarded. Not a later upgrade.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {CONTROLS.map((c, i) => (
              <div key={i} className="bg-card border border-border rounded-xl p-5 h-full">
                <div className="w-9 h-9 rounded-lg bg-teal-500/10 flex items-center justify-center mb-3">
                  <c.icon className="w-5 h-5 text-teal-400" />
                </div>
                <h3 className="font-semibold text-foreground text-sm mb-1.5">{c.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{c.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Compliance */}
      <section className="py-16 px-6 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <div className="mb-10">
            <div className="text-xs font-bold text-teal-500 tracking-widest mb-2">COMPLIANCE AND REVIEW</div>
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">Compliance-mapped controls</h2>
            <p className="text-muted-foreground max-w-3xl leading-relaxed">
              KavachIQ controls are mapped to common compliance frameworks. Mapping is an internal evidence exercise and not a substitute for a formal audit report. For audit artifacts, contact the security and procurement path below.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {COMPLIANCE.map((c, i) => (
              <div key={i} className="bg-card border border-border rounded-xl p-5 flex items-start gap-4">
                <div className="text-3xl leading-none shrink-0">{c.icon}</div>
                <div>
                  <div className="font-semibold text-foreground">{c.framework}</div>
                  <p className="text-sm text-muted-foreground leading-relaxed mt-1">{c.detail}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-6 max-w-3xl leading-relaxed">
            Mapping terminology: "mapped" means KavachIQ controls are cross-referenced to each framework's control IDs with supporting evidence in internal documentation. If your review process requires a SOC 2 report, a DPA, or other formal artifacts, route your request through the security and procurement path.
          </p>
        </div>
      </section>

      {/* Architecture trust signals */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="mb-10">
            <div className="text-xs font-bold text-teal-500 tracking-widest mb-2">DEPLOYMENT ARCHITECTURE</div>
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">How KavachIQ is deployed</h2>
            <p className="text-muted-foreground max-w-3xl leading-relaxed">
              The deployment model is built for Microsoft-native operations and enterprise review.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {ARCHITECTURE.map((a, i) => (
              <div key={i} className="bg-card border border-border rounded-xl p-5 h-full">
                <div className="w-10 h-10 rounded-lg bg-teal-500/10 flex items-center justify-center mb-3">
                  <a.icon className="w-5 h-5 text-teal-400" />
                </div>
                <h3 className="font-semibold text-foreground mb-1.5">{a.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{a.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Follow-up */}
      <section className="py-16 px-6 bg-muted/30">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <div className="text-xs font-bold text-teal-500 tracking-widest mb-2">NEXT STEPS</div>
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">Security and procurement follow-up</h2>
            <p className="text-muted-foreground leading-relaxed">
              Security reviewers, procurement teams, and risk owners can route requests through the paths below.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-card border border-border rounded-xl p-5">
              <div className="w-9 h-9 rounded-lg bg-teal-500/10 flex items-center justify-center mb-3">
                <Lock className="w-5 h-5 text-teal-400" />
              </div>
              <h3 className="font-semibold text-foreground mb-1.5">Security &amp; Procurement</h3>
              <p className="text-xs text-muted-foreground mb-3 leading-relaxed">Vendor-risk questionnaires, SOC 2 requests, DPA, and review artifacts.</p>
              <a href="mailto:security@kavachiq.com" className="text-sm text-teal-500 hover:text-teal-400 font-medium">security@kavachiq.com</a>
            </div>
            <div className="bg-card border border-border rounded-xl p-5">
              <div className="w-9 h-9 rounded-lg bg-teal-500/10 flex items-center justify-center mb-3">
                <FileText className="w-5 h-5 text-teal-400" />
              </div>
              <h3 className="font-semibold text-foreground mb-1.5">Documentation</h3>
              <p className="text-xs text-muted-foreground mb-3 leading-relaxed">Security architecture, compliance mapping, tenant security, and API reference.</p>
              <Link to="/docs" className="text-sm text-teal-500 hover:text-teal-400 font-medium">Review documentation <ArrowRight className="w-3.5 h-3.5 inline" /></Link>
            </div>
            <div className="bg-card border border-border rounded-xl p-5">
              <div className="w-9 h-9 rounded-lg bg-teal-500/10 flex items-center justify-center mb-3">
                <Users className="w-5 h-5 text-teal-400" />
              </div>
              <h3 className="font-semibold text-foreground mb-1.5">Talk to the team</h3>
              <p className="text-xs text-muted-foreground mb-3 leading-relaxed">Walk through your environment, workloads, and recovery requirements.</p>
              <Link to="/contact" className="text-sm text-teal-500 hover:text-teal-400 font-medium">Request a Demo <ArrowRight className="w-3.5 h-3.5 inline" /></Link>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 px-6 bg-gradient-to-br from-teal-600 to-cyan-700">
        <div className="max-w-3xl mx-auto text-center text-white">
          <h2 className="text-3xl font-bold mb-4">Ready for a security review?</h2>
          <p className="text-teal-100 mb-8 max-w-xl mx-auto leading-relaxed">
            Request a walkthrough of KavachIQ security controls, tenant isolation, and compliance-mapped evidence. Or send a procurement questionnaire directly to the security path.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/contact" className="inline-flex items-center gap-2 px-8 py-3.5 bg-white text-teal-700 font-semibold rounded-xl hover:bg-teal-50 transition-colors text-lg">
              Request a Demo <ArrowRight className="w-5 h-5" />
            </Link>
            <a href="mailto:security@kavachiq.com?subject=Security%20review" className="inline-flex items-center gap-2 px-8 py-3.5 border-2 border-white/30 text-white font-medium rounded-xl hover:bg-white/10 transition-colors text-lg">
              Security Questions
            </a>
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
