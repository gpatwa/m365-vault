import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Shield, ArrowRight, AlertTriangle, Mail, FileSearch,
  CheckCircle2, Check, Eye, GitBranch, Activity, Trash2, Calendar, Lock,
} from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { appUrl } from '../utils/appUrl';

// Illustrative recovery-scenario page. Sales-enablement narrative, not a
// fictional customer testimonial and not fabricated metrics.

const INCIDENT_SIGNALS = [
  { icon: Trash2, title: 'Bulk mailbox deletion', desc: 'A large batch of mailboxes is removed in a short window. A scripted offboarding, a mistaken admin action, or an abused privileged session all produce the same pattern.' },
  { icon: Calendar, title: 'Calendar and contacts loss', desc: 'Mailbox deletion also removes the calendar and contacts for every affected user. Meeting history and shared calendars surface the issue quickly.' },
  { icon: Lock, title: 'Retention policy drift', desc: 'Retention tags, retention labels, and retention policies were modified around the same time. What is still recoverable via native tools is now uncertain.' },
  { icon: Activity, title: 'Native recovery windows', desc: 'Deleted mailboxes enter the 30-day soft-delete window. Some are already beyond that window or have been explicitly purged. Native recovery for those cases is limited or unavailable.' },
  { icon: Shield, title: 'Legal hold uncertainty', desc: 'Mailboxes under legal hold or litigation hold may be partially preserved, but the team has to confirm hold state per mailbox before any restore action.' },
  { icon: AlertTriangle, title: 'Cause is unclear at first', desc: 'Script? Admin error? Compromised identity? Recovery has to move forward while the cause is investigated, without restoring unsafely.' },
];

const MANUAL_PAIN = [
  'Recovery windows are tight. Microsoft 365 soft-delete for mailboxes is 30 days by default, and purged mailboxes are not recoverable through native tools.',
  'Retention drift makes the surviving state ambiguous. Which retention labels and policies were active at the time of deletion is not trivial to reconstruct.',
  'Soft-delete, hard-delete, and purge are easy to confuse. Admins spend time in PowerShell validating state per mailbox before they can decide on a restore path.',
  'Restore is fragmented. Mailbox-by-mailbox restore via native tools or PowerShell scripts is slow and hard to prioritize when hundreds of mailboxes are affected.',
  'Compliance review runs in parallel. Legal and compliance need evidence of what was deleted, when, by whom, and what was restored, before sign-off.',
];

const PHASES = [
  {
    num: '01', label: 'Protect', icon: Shield,
    color: 'from-blue-500 to-blue-600',
    lede: 'Exchange Online state is already captured on a schedule.',
    points: [
      'Mailboxes, calendars, and contacts snapshotted with per-tenant encryption. Snapshots are WORM-locked for the SLA retention window.',
      'Retention policy state (tags, labels, policies) is captured alongside mailbox data so the control plane context is preserved.',
      'Identity and Entra ID state are snapshotted in parallel, in case the incident correlates with an admin or policy change.',
    ],
  },
  {
    num: '02', label: 'Monitor', icon: Eye,
    color: 'from-blue-400 to-indigo-500',
    lede: 'Baselines track normal mailbox and retention activity per tenant.',
    points: [
      'Mailbox count, deletion rate, and purge rate are baselined over rolling windows.',
      'Retention tag, label, and policy counts are tracked. Large shifts in retention configuration are surfaced.',
      'Correlated identity signals (recent privilege changes, new service principals) feed into the change picture.',
    ],
  },
  {
    num: '03', label: 'Detect', icon: AlertTriangle,
    color: 'from-rose-500 to-red-600',
    lede: 'Bulk deletion and retention drift are flagged with evidence.',
    points: [
      'Bulk mailbox deletion that exceeds baseline produces a specific, evidence-backed alert with the affected user list and the time window.',
      'Retention policy or retention label changes are reported as part of the same incident, not as a separate noise source.',
      'If the event correlates with a suspicious identity change, KavachIQ links the two so the team sees the full picture.',
    ],
  },
  {
    num: '04', label: 'Assess', icon: FileSearch,
    color: 'from-amber-400 to-amber-500',
    lede: 'Blast radius is computed across mailboxes, retention state, and hold status.',
    points: [
      'Diff the current Exchange state against the last known-good snapshot. See which mailboxes are missing, which are soft-deleted, and which are beyond the native recovery window.',
      'Compare retention tags, labels, and policies before and after. Surface any drift that needs to be reverted alongside the mailbox restore.',
      'Confirm legal-hold and litigation-hold state per mailbox before planning restore actions. Hold-bearing mailboxes require a different restore path.',
    ],
  },
  {
    num: '05', label: 'Recover', icon: GitBranch,
    color: 'from-blue-400 to-blue-500',
    lede: 'Guided mailbox restore in a business-safe order.',
    points: [
      'Restore identity controls first if any admin or policy drift is detected alongside the deletions.',
      'Recover mailboxes for critical users first. Executives, compliance officers, legal, and finance come back before broader mailbox restore.',
      'Restore retention tags, labels, and policies to the known-good state so restored mailboxes land under the correct retention posture.',
      'Recover broader mailbox population after priority users are verified. Calendar and contacts are restored alongside mailbox content.',
    ],
  },
  {
    num: '06', label: 'Verify', icon: CheckCircle2,
    color: 'from-emerald-400 to-green-500',
    lede: 'Mailbox recovery is confirmed with evidence.',
    points: [
      'Checksum validation confirms restored mailbox content matches the protected snapshot.',
      'Sign-in and mailbox access checks verify users can open their mailbox, calendar, and contacts cleanly.',
      'Retention policies and holds are confirmed active on the restored mailboxes. A recovery report bundles the timeline, actions taken, and snapshots used.',
    ],
  },
];

const OUTCOMES = [
  { icon: Activity, title: 'Recovery past native windows', desc: 'Mailboxes purged or past the 30-day soft-delete window are recoverable from KavachIQ snapshots, not dependent on Microsoft 365 native recovery timelines.' },
  { icon: FileSearch, title: 'Clear retention state, before and after', desc: 'Retention tag, label, and policy state is visible per mailbox before deletion and after restore. Drift is addressed explicitly, not assumed to be intact.' },
  { icon: Shield, title: 'Prioritized mailbox restore', desc: 'Critical users come back first. Legal, compliance, finance, and executive mailboxes are verified before broader mailbox restore runs.' },
  { icon: Mail, title: 'Reduced PowerShell burden', desc: 'Coordinated, guided restore replaces cycles of mailbox-by-mailbox PowerShell scripts and admin-center clicks.' },
  { icon: CheckCircle2, title: 'Evidence for compliance review', desc: 'A timestamped log of detected deletions, policy changes, decisions, and restore actions supports legal and compliance review after the incident.' },
];

export default function ScenarioBulkMailboxDeletion() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Helmet>
        <title>Recovery Scenario — Bulk Mailbox Deletion and Retention Drift in Microsoft 365 | KavachIQ</title>
        <meta name="description" content="How KavachIQ helps a Microsoft 365 team recover from bulk mailbox deletion and retention drift, including mailboxes past the native recovery window, with evidence for compliance review." />
        <link rel="canonical" href="https://kavachiq.com/scenarios/bulk-mailbox-deletion-retention-drift" />
        <meta property="og:type" content="article" />
        <meta property="og:url" content="https://kavachiq.com/scenarios/bulk-mailbox-deletion-retention-drift" />
        <meta property="og:title" content="Recovery Scenario — Bulk Mailbox Deletion and Retention Drift in Microsoft 365" />
        <meta property="og:description" content="A concrete Microsoft 365 recovery scenario: bulk mailbox deletion, retention drift, prioritized restore, evidence for compliance review." />
        <meta property="og:image" content="https://kavachiq.com/og-scenario-bulk-mailbox-deletion.jpg" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:image" content="https://kavachiq.com/og-scenario-bulk-mailbox-deletion.jpg" />
        <meta name="twitter:title" content="Recovery Scenario — Bulk Mailbox Deletion and Retention Drift in Microsoft 365" />
        <meta name="twitter:description" content="A concrete Microsoft 365 recovery scenario from bulk mailbox deletion through verified business recovery." />
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
            <span className="text-foreground">Bulk mailbox deletion and retention drift</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-rose-500/10 text-rose-400 rounded-full text-xs font-medium mb-5">
            <AlertTriangle className="w-3.5 h-3.5" />
            Illustrative recovery scenario
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold text-foreground leading-[1.1] tracking-tight mb-6">
            Recovery scenario: bulk mailbox deletion and{' '}
            <span className="bg-gradient-to-r from-teal-500 to-cyan-500 bg-clip-text text-transparent">
              retention drift in Microsoft 365.
            </span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-3xl mb-8 leading-relaxed">
            See how KavachIQ helps a Microsoft 365 team recover mailboxes that are beyond the native recovery window, restore the correct retention posture, and produce evidence for compliance review after a high-volume deletion event.
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
            This page describes an illustrative scenario. It is not a customer testimonial and does not contain fabricated metrics. It is intended to help Microsoft 365 teams, IT and security leaders, and procurement reviewers understand KavachIQ in the context of a realistic Exchange-heavy incident.
          </p>
          <p className="text-sm text-muted-foreground mt-6">
            Related: <Link to="/scenarios/compromised-global-admin" className="text-teal-500 hover:text-teal-400 underline underline-offset-2">compromised Global Admin</Link>
            {' '}&middot;{' '}
            <Link to="/scenarios/destructive-sharepoint-onedrive-deletion" className="text-teal-500 hover:text-teal-400 underline underline-offset-2">destructive deletion across SharePoint and OneDrive</Link>
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
              A large batch of mailboxes is removed in a short window. Retention policies and labels have drifted around the same time. Some mailboxes are already beyond the native recovery window. Compliance and legal need answers before the team can close the incident.
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
              Some of this work is possible with native tools and PowerShell. What makes it painful at scale is the combination of tight recovery windows, retention ambiguity, and compliance expectations.
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
              KavachIQ runs the same six-phase workflow on every recovery. Applied to a bulk mailbox deletion and retention-drift event, this is what each phase does.
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
              Identity-first thinking still applies. Confirm the control plane is trustworthy, then recover mailboxes in the order that restores business continuity fastest and that supports compliance review.
            </p>
          </div>
          <ol className="space-y-4">
            {[
              { n: '01', t: 'Confirm identity and admin integrity', d: 'If any admin, role, or policy drift is detected alongside the mailbox deletions, restore Entra controls first. Do not restore mailbox content into a tenant whose control plane is still in question.' },
              { n: '02', t: 'Critical mailboxes first', d: 'Executives, compliance officers, legal, finance, and incident-response mailboxes are restored first. Calendar and contacts are restored alongside mailbox content so priority users can return to normal operations.' },
              { n: '03', t: 'Retention posture, before broader restore', d: 'Retention tags, labels, and policies are reverted to the known-good state. Legal holds and litigation holds are confirmed active before the broader mailbox restore runs.' },
              { n: '04', t: 'Broader mailbox restore, verified end-to-end', d: 'Remaining mailboxes are restored with checksum and sign-in verification. A recovery report documents what was deleted, when, by whom, and what was restored, for compliance review.' },
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
              KavachIQ does not prevent every mailbox deletion or retention change. It changes how a Microsoft 365 team runs the recovery, and how defensibly compliance can sign off on being back online.
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
            Walk the bulk mailbox deletion scenario, or your specific incident, with a KavachIQ recovery engineer. Bring the mailbox, retention, and compliance questions that matter for your tenant.
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
