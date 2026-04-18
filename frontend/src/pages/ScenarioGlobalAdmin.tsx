import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Shield, ArrowRight, AlertTriangle, KeyRound, Users, FileSearch,
  CheckCircle2, Check, Eye, GitBranch, Lock, Activity,
} from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { appUrl } from '../utils/appUrl';

// Illustrative recovery-scenario page. This is a sales-enablement narrative,
// not a fictional customer testimonial or an incident response playbook.

const INCIDENT_SIGNALS = [
  { icon: KeyRound, title: 'Privileged identity access', desc: 'Attacker phishes a privileged session or abuses a valid token. MFA is weakened or bypassed.' },
  { icon: Shield, title: 'Global Admin abuse', desc: 'Global Admin is assigned to a new account or an existing account is elevated.' },
  { icon: Lock, title: 'Conditional access modified', desc: 'CA policies and sign-in frequency requirements are loosened. Break-glass paths expanded.' },
  { icon: Activity, title: 'OAuth grants and service principals', desc: 'New app consents or service principals added. Scoped permissions quietly expand.' },
  { icon: Users, title: 'Group and role membership', desc: 'Security groups, role-assignable groups, and admin units shift. Blast radius grows.' },
  { icon: AlertTriangle, title: 'Data access expands', desc: 'Mailbox delegation, SharePoint site access, OneDrive sharing, and Teams membership start drifting.' },
];

const MANUAL_PAIN = [
  'Blast radius is unclear. Who is actually affected, which policies changed, and what is safe to touch first is hard to answer in real time.',
  'Policy drift is invisible. Conditional access and role changes over the last 24 hours are not trivially queryable across Entra.',
  'Restore order is unclear. Teams pull mailboxes and files back first because that is what leadership asks for, but the attacker still holds admin rights.',
  'Identity stays compromised while data is restored. The attacker re-encrypts, re-exfiltrates, or simply waits until attention drops.',
  'Triage is slow. Cross-referencing Entra audit logs, M365 audit logs, and third-party alerts takes hours or days.',
];

const PHASES = [
  {
    num: '01', label: 'Protect', icon: Shield,
    color: 'from-blue-500 to-blue-600',
    lede: 'Baseline identity and workload state is already captured.',
    points: [
      '12 Entra ID object types snapshotted: users, groups, role assignments, conditional access policies, OAuth grants, service principals, and administrative units.',
      'Exchange, OneDrive, SharePoint, and Teams protected on a schedule. Snapshots are WORM-locked for the SLA retention window.',
      'Per-tenant keys and audit trail are in place before any incident begins.',
    ],
  },
  {
    num: '02', label: 'Monitor', icon: Eye,
    color: 'from-blue-400 to-indigo-500',
    lede: 'Baselines track normal tenant behavior.',
    points: [
      'Change rate across identity objects and workload data is baselined per tenant.',
      'Privileged role counts, conditional access policy counts, and MFA enforcement levels are tracked over time.',
      'Unusual service-principal or OAuth-grant activity feeds into the anomaly model.',
    ],
  },
  {
    num: '03', label: 'Detect', icon: AlertTriangle,
    color: 'from-rose-500 to-red-600',
    lede: 'Destructive change and identity drift are flagged with evidence.',
    points: [
      'Global Admin count jumps. MFA enforcement drops on privileged users. Conditional access policies are modified or disabled.',
      'Mass rename or mass-deletion patterns across OneDrive and SharePoint are flagged.',
      'Alerts reference the specific object type, the affected users, and the time window, not just a generic anomaly score.',
    ],
  },
  {
    num: '04', label: 'Assess', icon: FileSearch,
    color: 'from-amber-400 to-amber-500',
    lede: 'Blast radius is computed across identity and data.',
    points: [
      'Diff the current Entra state against the last known-good snapshot. See exactly which policies, roles, OAuth grants, and group memberships changed.',
      'Map identity changes to the users, mailboxes, and sites they affect.',
      'Score affected users by business criticality. Surface a recommended recovery order before action is taken.',
    ],
  },
  {
    num: '05', label: 'Recover', icon: GitBranch,
    color: 'from-blue-400 to-blue-500',
    lede: 'Guided, identity-first restore in the safest business order.',
    points: [
      'Phase A: Revert privileged role assignments. Remove attacker-added Global Admins and service principals.',
      'Phase B: Restore conditional access, MFA enforcement, and OAuth grants to the last known-good state.',
      'Phase C: Recover critical users first, then high-priority departments, then full business data.',
      'Every restore action is logged and attributable. Broken changes can be rolled forward or reverted per object.',
    ],
  },
  {
    num: '06', label: 'Verify', icon: CheckCircle2,
    color: 'from-emerald-400 to-green-500',
    lede: 'Business recovery is confirmed with evidence.',
    points: [
      'Checksums confirm data restore integrity. Policy-active checks confirm conditional access is enforcing again.',
      'Sign-in tests verify privileged and critical users can authenticate cleanly.',
      'A recovery report bundles the timeline, the actions taken, the evidence, and the snapshots used.',
    ],
  },
];

const OUTCOMES = [
  { icon: Activity, title: 'Faster recovery coordination', desc: 'Teams start from a computed blast radius and a pre-computed recovery plan instead of improvising under pressure.' },
  { icon: Shield, title: 'Safer restore order', desc: 'Identity controls come back before data. Attackers lose their foothold before the tenant is fully restored.' },
  { icon: FileSearch, title: 'Clearer blast radius understanding', desc: 'Identity and data diff-against-baseline make the actual scope of the incident visible, not assumed.' },
  { icon: CheckCircle2, title: 'Stronger recovery confidence', desc: 'Recovery is scored with evidence. Leadership and security can sign off on "we are back" with a defensible artifact.' },
  { icon: Lock, title: 'Better evidence for review', desc: 'A timestamped log of detected changes, decisions, and restores supports security, legal, and procurement review after the fact.' },
];

export default function ScenarioGlobalAdmin() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Helmet>
        <title>Recovery Scenario — Compromised Global Admin in Microsoft 365 | KavachIQ</title>
        <meta name="description" content="How identity-first recovery helps a Microsoft 365 team restore Entra controls, contain blast radius, recover critical users, and verify business recovery after a compromised Global Admin." />
        <link rel="canonical" href="https://kavachiq.com/scenarios/compromised-global-admin" />
        <meta property="og:type" content="article" />
        <meta property="og:url" content="https://kavachiq.com/scenarios/compromised-global-admin" />
        <meta property="og:title" content="Recovery Scenario — Compromised Global Admin in Microsoft 365" />
        <meta property="og:description" content="A concrete Microsoft 365 recovery scenario: privileged identity compromise, blast radius, identity-first restore, verified business recovery." />
        <meta property="og:image" content="https://kavachiq.com/og-scenario-global-admin.jpg" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:image" content="https://kavachiq.com/og-scenario-global-admin.jpg" />
        <meta name="twitter:title" content="Recovery Scenario — Compromised Global Admin in Microsoft 365" />
        <meta name="twitter:description" content="A concrete Microsoft 365 recovery scenario from privileged identity compromise through verified business recovery." />
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
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-4">
            <Link to="/welcome" className="hover:text-foreground">KavachIQ</Link>
            <span>/</span>
            <span>Recovery scenarios</span>
            <span>/</span>
            <span className="text-foreground">Compromised Global Admin</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-rose-500/10 text-rose-400 rounded-full text-xs font-medium mb-5">
            <AlertTriangle className="w-3.5 h-3.5" />
            Illustrative recovery scenario
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold text-foreground leading-[1.1] tracking-tight mb-6">
            Recovery scenario: compromised Global Admin in{' '}
            <span className="bg-gradient-to-r from-teal-500 to-cyan-500 bg-clip-text text-transparent">
              Microsoft 365.
            </span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-3xl mb-8 leading-relaxed">
            See how identity-first recovery helps a Microsoft 365 team restore Entra controls, contain blast radius, recover critical users, and verify business recovery after a privileged identity compromise.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <Link to="/contact" className="px-6 py-3 bg-teal-600 text-white font-semibold rounded-xl hover:bg-teal-700 transition-all hover:shadow-lg hover:shadow-teal-200/20 flex items-center gap-2">
              Request a Demo <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/tour" className="px-6 py-3 border border-teal-500/30 text-teal-400 font-medium rounded-xl hover:bg-teal-500/10 transition-colors flex items-center gap-2">
              <Eye className="w-4 h-4" /> See the Product Tour
            </Link>
          </div>
          <p className="text-xs text-muted-foreground mt-6 max-w-2xl leading-relaxed">
            This page describes an illustrative scenario. It is not a customer testimonial and does not contain fabricated metrics. It is intended to help Microsoft 365 teams, IT and security leaders, and procurement reviewers understand KavachIQ in the context of a realistic privileged identity compromise.
          </p>
        </div>
      </section>

      {/* 2. Incident setup */}
      <section className="py-16 px-6 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <div className="mb-10">
            <div className="text-xs font-bold text-rose-400 tracking-widest mb-2">SECTION 1 · INCIDENT SETUP</div>
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">What the incident looks like in Microsoft 365</h2>
            <p className="text-muted-foreground max-w-3xl leading-relaxed">
              A privileged identity is compromised. The attacker works inside Microsoft Entra and Microsoft 365 to establish persistence, expand access, and weaken the controls that would normally catch them.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {INCIDENT_SIGNALS.map((s, i) => (
              <div key={i} className="bg-card border border-border rounded-xl p-5 h-full">
                <div className="w-9 h-9 rounded-lg bg-rose-500/10 flex items-center justify-center mb-3">
                  <s.icon className="w-5 h-5 text-rose-400" />
                </div>
                <h3 className="font-semibold text-foreground mb-1.5">{s.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 3. What goes wrong in a manual recovery */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <div className="text-xs font-bold text-amber-400 tracking-widest mb-2">SECTION 2 · WHY MANUAL RECOVERY IS HARD</div>
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">Where teams run into trouble</h2>
            <p className="text-muted-foreground leading-relaxed">
              Most Microsoft 365 teams can eventually recover from this scenario. What makes it painful is the first few hours.
            </p>
          </div>
          <div className="bg-card border border-border rounded-xl divide-y divide-border">
            {MANUAL_PAIN.map((p, i) => (
              <div key={i} className="flex gap-4 p-5">
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
                  <span className="text-xs font-bold text-amber-400">{String(i + 1).padStart(2, '0')}</span>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed pt-1">{p}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 4. How KavachIQ handles it — 6 phases */}
      <section className="py-16 px-6 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <div className="mb-10">
            <div className="text-xs font-bold text-teal-500 tracking-widest mb-2">SECTION 3 · HOW KAVACHIQ HANDLES RECOVERY</div>
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">Six phases, applied to this incident</h2>
            <p className="text-muted-foreground max-w-3xl leading-relaxed">
              KavachIQ runs the same six-phase workflow on every recovery. Applied to a compromised Global Admin, this is what each phase does.
            </p>
          </div>
          <div className="space-y-4">
            {PHASES.map((p) => (
              <div key={p.num} className="bg-card border border-border rounded-xl p-6">
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${p.color} flex items-center justify-center shrink-0`}>
                    <p.icon className="w-6 h-6 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1.5">
                      <span className="text-xs font-bold text-muted-foreground tracking-widest">PHASE {p.num}</span>
                      <span className="text-lg font-bold text-foreground">{p.label}</span>
                    </div>
                    <p className="text-sm text-foreground font-medium mb-3">{p.lede}</p>
                    <ul className="space-y-2">
                      {p.points.map((pt, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground leading-relaxed">
                          <Check className="w-4 h-4 text-teal-500 mt-0.5 shrink-0" />
                          <span>{pt}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 5. Identity-first recovery order */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <div className="text-xs font-bold text-teal-500 tracking-widest mb-2">SECTION 4 · IDENTITY-FIRST RECOVERY ORDER</div>
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">Why identity comes first, and in what order</h2>
            <p className="text-muted-foreground leading-relaxed">
              Restoring mailboxes and files before restoring identity controls is not safe. The attacker still holds Global Admin or residual privileged access.
            </p>
          </div>
          <ol className="space-y-4">
            {[
              { n: '01', t: 'Entra controls first', d: 'Privileged role assignments, conditional access policies, MFA enforcement, OAuth grants, service principals, administrative units, and security groups are reverted to the last known-good snapshot.' },
              { n: '02', t: 'Critical users next', d: 'Executives, privileged-role holders, compliance and security owners, and finance leads are restored and verified first.' },
              { n: '03', t: 'High-priority departments and sites', d: 'Directors, senior engineering, shared SharePoint sites, and legal repositories are recovered in the order their business criticality suggests.' },
              { n: '04', t: 'Full business data, verified end-to-end', d: 'Remaining mailboxes, sites, Teams, and OneDrive content are restored. Checksums and sign-in tests confirm the tenant is actually back online.' },
            ].map((x) => (
              <li key={x.n} className="flex gap-4">
                <div className="w-10 h-10 rounded-full bg-teal-500/10 border border-teal-500/30 flex items-center justify-center shrink-0">
                  <span className="text-xs font-bold text-teal-500">{x.n}</span>
                </div>
                <div>
                  <h3 className="font-semibold text-foreground mb-1">{x.t}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{x.d}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* 6. Outcome */}
      <section className="py-16 px-6 bg-muted/30">
        <div className="max-w-5xl mx-auto">
          <div className="mb-10">
            <div className="text-xs font-bold text-emerald-500 tracking-widest mb-2">SECTION 5 · OPERATIONAL OUTCOMES</div>
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">What changes for the team</h2>
            <p className="text-muted-foreground max-w-3xl leading-relaxed">
              KavachIQ does not eliminate incidents. It changes how a Microsoft 365 team runs the recovery and how defensibly they can sign off on being back online.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {OUTCOMES.map((o, i) => (
              <div key={i} className="bg-card border border-border rounded-xl p-5 h-full">
                <div className="w-9 h-9 rounded-lg bg-emerald-500/10 flex items-center justify-center mb-3">
                  <o.icon className="w-5 h-5 text-emerald-400" />
                </div>
                <h3 className="font-semibold text-foreground mb-1.5">{o.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{o.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 7. Final CTA */}
      <section className="py-20 px-6 bg-gradient-to-br from-teal-600 to-cyan-700">
        <div className="max-w-3xl mx-auto text-center text-white">
          <h2 className="text-3xl font-bold mb-4">Talk through your Microsoft 365 recovery scenario</h2>
          <p className="text-teal-100 mb-8 max-w-xl mx-auto leading-relaxed">
            Walk the compromised Global Admin scenario, or your specific incident, with a KavachIQ recovery engineer. Bring the Entra, policy, and workload questions that matter for your tenant.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/contact" className="inline-flex items-center gap-2 px-8 py-3.5 bg-white text-teal-700 font-semibold rounded-xl hover:bg-teal-50 transition-colors text-lg">
              Request a Demo <ArrowRight className="w-5 h-5" />
            </Link>
            <Link to="/tour" className="inline-flex items-center gap-2 px-8 py-3.5 border-2 border-white/30 text-white font-medium rounded-xl hover:bg-white/10 transition-colors text-lg">
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
