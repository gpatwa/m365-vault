import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Shield, ArrowRight, AlertTriangle, Users, FileSearch,
  CheckCircle2, Check, Eye, GitBranch, Activity, HardDrive, Globe, Trash2,
} from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { appUrl } from '../utils/appUrl';

// Illustrative recovery-scenario page. Sales-enablement narrative, not a
// fictional customer testimonial and not fabricated metrics.

const INCIDENT_SIGNALS = [
  { icon: Trash2, title: 'High-volume deletion event', desc: 'Folders, libraries, sites, or entire OneDrive accounts are removed in a short window. Volume exceeds normal deletion patterns.' },
  { icon: Users, title: 'Unclear scope for users', desc: 'Employees notice missing content and surface requests to IT. Different teams report different symptoms, and the real scope is not yet visible.' },
  { icon: Globe, title: 'Multiple SharePoint sites affected', desc: 'Department sites, shared libraries, and project workspaces show deletions. Content spread across multiple site collections is now in flux.' },
  { icon: HardDrive, title: 'OneDrive accounts impacted', desc: 'Several users report missing files across OneDrive. Desktop and mobile sync start propagating the deletions further.' },
  { icon: Shield, title: 'Cause unclear at first', desc: 'Could be a compromised identity, a mistaken admin action, a runaway sync client, or a script or third-party app. The workflow still has to move forward while the cause is investigated.' },
  { icon: Activity, title: 'Business impact spreads', desc: 'Sales, legal, finance, and engineering teams begin escalating. The recycle bin is not a coordinated recovery plan, and version history does not cover deleted libraries.' },
];

const MANUAL_PAIN = [
  'Blast radius is unclear. Which sites, libraries, users, and files are actually affected is hard to see across many workspaces.',
  'Restore order is unclear. There is no obvious way to decide which content comes back first when business-critical data is mixed with lower-priority content.',
  'Recycle bins and version history are not a business recovery plan. Items age out. Some content types are not recoverable once the retention window passes.',
  'Restore is fragmented. Admins toggle between the SharePoint admin center, OneDrive admin views, and individual site recycle bins.',
  'Triage is slow. Cross-referencing M365 audit logs, SharePoint site activity, and user reports to confirm scope takes hours to days.',
];

const PHASES = [
  {
    num: '01', label: 'Protect', icon: Shield,
    color: 'from-blue-500 to-blue-600',
    lede: 'Baseline workload state is already captured.',
    points: [
      'SharePoint sites, OneDrive accounts, and Teams content snapshotted on a schedule with per-tenant encryption.',
      'Snapshots are WORM-locked for the SLA retention window. Attackers or scripts cannot purge protected copies.',
      'Identity state is snapshotted alongside data so admin and policy context is available during recovery.',
    ],
  },
  {
    num: '02', label: 'Monitor', icon: Eye,
    color: 'from-blue-400 to-indigo-500',
    lede: 'Baselines track normal deletion and change volume per tenant.',
    points: [
      'Per-site and per-user deletion rates are baselined over rolling windows.',
      'Large deltas in SharePoint library or OneDrive account content are continuously tracked.',
      'Correlated identity signals (recent privilege changes, new service principals) feed into the change picture.',
    ],
  },
  {
    num: '03', label: 'Detect', icon: AlertTriangle,
    color: 'from-rose-500 to-red-600',
    lede: 'High-volume deletion activity is flagged with evidence.',
    points: [
      'Mass deletions across sites and libraries that exceed baseline produce a specific, evidence-backed alert.',
      'OneDrive accounts showing abnormal deletion activity are surfaced individually.',
      'If the event correlates with a suspicious identity change, KavachIQ links the two so the team sees the full picture.',
    ],
  },
  {
    num: '04', label: 'Assess', icon: FileSearch,
    color: 'from-amber-400 to-amber-500',
    lede: 'Blast radius is computed across sites, libraries, users, and files.',
    points: [
      'Diff the current SharePoint and OneDrive state against the last known-good snapshot. See exactly which sites, libraries, folders, and files were removed.',
      'Group the affected content by site, department, and user. Surface the business-critical workspaces at the top of the list.',
      'Confirm identity and admin integrity before any data restore, so the scenario does not silently include a privileged identity compromise.',
    ],
  },
  {
    num: '05', label: 'Recover', icon: GitBranch,
    color: 'from-blue-400 to-blue-500',
    lede: 'Guided restore in a business-safe order.',
    points: [
      'Restore identity controls first if any admin or policy drift is detected alongside the deletions.',
      'Recover content for critical users, teams, and high-priority sites first. Executives, legal, finance, and compliance workspaces come back before broader tenant content.',
      'Restore shared document libraries and department data next. Granular per-item restore avoids noisy full-site rollbacks when only part of a library was removed.',
      'Complete broader tenant recovery after priority content is verified.',
    ],
  },
  {
    num: '06', label: 'Verify', icon: CheckCircle2,
    color: 'from-emerald-400 to-green-500',
    lede: 'Business recovery is confirmed with evidence.',
    points: [
      'Checksum validation confirms restored files match the protected snapshot.',
      'Access checks confirm the right users, groups, and sites can see the restored content.',
      'A recovery report bundles the timeline, the restore actions, and the snapshots used, for post-incident review.',
    ],
  },
];

const OUTCOMES = [
  { icon: Activity, title: 'Faster coordination', desc: 'Teams work from a computed blast radius and a prioritized restore queue instead of triaging from user tickets and admin-center clicks.' },
  { icon: FileSearch, title: 'Clearer view of affected content', desc: 'Specific sites, libraries, users, and files are identified. The team can brief leadership on scope with evidence, not estimates.' },
  { icon: Shield, title: 'Safer restore prioritization', desc: 'Critical workspaces come back first. Business continuity is restored before lower-priority content is touched.' },
  { icon: CheckCircle2, title: 'Reduced manual triage', desc: 'Cross-workload deletion patterns and identity correlation are surfaced directly. Less time in audit logs and admin centers.' },
  { icon: Eye, title: 'Stronger recovery confidence and evidence', desc: 'Recovery is scored and logged. Security, compliance, and procurement reviewers have a clean artifact of what happened and how it was handled.' },
];

export default function ScenarioDestructiveDeletion() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Helmet>
        <title>Recovery Scenario — Destructive Deletion Across SharePoint and OneDrive | KavachIQ</title>
        <meta name="description" content="How KavachIQ helps a Microsoft 365 team identify affected users, sites, and libraries, restore the right content in the right order, and verify recovery after a high-volume deletion event." />
        <link rel="canonical" href="https://kavachiq.com/scenarios/destructive-sharepoint-onedrive-deletion" />
        <meta property="og:type" content="article" />
        <meta property="og:url" content="https://kavachiq.com/scenarios/destructive-sharepoint-onedrive-deletion" />
        <meta property="og:title" content="Recovery Scenario — Destructive Deletion Across SharePoint and OneDrive" />
        <meta property="og:description" content="A concrete Microsoft 365 recovery scenario: blast radius across sites and libraries, prioritized restore, verified business recovery." />
        <meta property="og:image" content="https://kavachiq.com/og-scenario-destructive-deletion.jpg" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:image" content="https://kavachiq.com/og-scenario-destructive-deletion.jpg" />
        <meta name="twitter:title" content="Recovery Scenario — Destructive Deletion Across SharePoint and OneDrive" />
        <meta name="twitter:description" content="A concrete Microsoft 365 recovery scenario from high-volume deletion through verified business recovery." />
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
            <Link to="/security" className="hover:text-foreground">Security</Link>
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
            <span className="text-foreground">Destructive deletion</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-rose-500/10 text-rose-400 rounded-full text-xs font-medium mb-5">
            <AlertTriangle className="w-3.5 h-3.5" />
            Illustrative recovery scenario
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold text-foreground leading-[1.1] tracking-tight mb-6">
            Recovery scenario: destructive deletion across{' '}
            <span className="bg-gradient-to-r from-teal-500 to-cyan-500 bg-clip-text text-transparent">
              SharePoint and OneDrive.
            </span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-3xl mb-8 leading-relaxed">
            See how KavachIQ helps a Microsoft 365 team identify affected users, sites, libraries, and files, restore the right content in the right order, and verify recovery after a high-volume deletion event.
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
            This page describes an illustrative scenario. It is not a customer testimonial and does not contain fabricated metrics. It is intended to help Microsoft 365 teams, IT and security leaders, and procurement reviewers understand KavachIQ in the context of a realistic high-volume deletion event.
          </p>
          <p className="text-sm text-muted-foreground mt-6">
            Related: <Link to="/scenarios/compromised-global-admin" className="text-teal-500 hover:text-teal-400 underline underline-offset-2">Recovery scenario: compromised Global Admin</Link>
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
              A high-volume deletion event hits the tenant. Content disappears across SharePoint sites and OneDrive accounts. The cause could be a compromised identity, a mistaken admin action, or a runaway script or sync client. Recovery has to move forward while that is investigated.
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
              Most Microsoft 365 teams can eventually restore deleted content. What makes it painful is the first few hours.
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
              KavachIQ runs the same six-phase workflow on every recovery. Applied to a high-volume deletion event, this is what each phase does.
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

      {/* 5. Recovery order for this incident */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <div className="text-xs font-bold text-teal-500 tracking-widest mb-2">SECTION 4 · RECOVERY ORDER</div>
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">Business-safe restore order for this incident</h2>
            <p className="text-muted-foreground leading-relaxed">
              Identity-first thinking still applies. Confirm the control plane is trustworthy, then recover content in the order that restores business continuity fastest.
            </p>
          </div>
          <ol className="space-y-4">
            {[
              { n: '01', t: 'Confirm identity and admin integrity', d: 'If any admin, role, or policy drift is detected alongside the deletions, restore Entra controls first. Do not restore data into a tenant whose control plane is still in question.' },
              { n: '02', t: 'Critical users, teams, and high-priority sites', d: 'Executives, legal, finance, compliance, and incident-response workspaces are restored first. Their content unblocks decision-making for the rest of the recovery.' },
              { n: '03', t: 'Shared document libraries and department data', d: 'Department sites, shared libraries, and active project workspaces are restored next. Granular per-item restore avoids full-site rollbacks when only part of a library was affected.' },
              { n: '04', t: 'Broader tenant recovery, verified end-to-end', d: 'Remaining OneDrive accounts, secondary sites, and long-tail content are restored. Checksums and access checks confirm the tenant is actually back.' },
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
              KavachIQ does not prevent every deletion event. It changes how a Microsoft 365 team runs the recovery and how defensibly they can sign off on being back online.
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
            Walk the destructive-deletion scenario, or your specific incident, with a KavachIQ recovery engineer. Bring the site, library, OneDrive, and workflow details that matter for your tenant.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/contact" className="inline-flex items-center gap-2 px-8 py-3.5 bg-white text-teal-700 font-semibold rounded-xl hover:bg-teal-50 transition-colors text-lg">
              Request a Demo <ArrowRight className="w-5 h-5" />
            </Link>
            <Link to="/scenarios/compromised-global-admin" className="inline-flex items-center gap-2 px-8 py-3.5 border-2 border-white/30 text-white font-medium rounded-xl hover:bg-white/10 transition-colors text-lg">
              Read another scenario
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
