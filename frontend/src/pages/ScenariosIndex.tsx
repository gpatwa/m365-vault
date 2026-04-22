import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Shield, ArrowRight, KeyRound, Trash2, Mail, Eye,
} from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { appUrl } from '../utils/appUrl';

const SCENARIOS: {
  slug: string;
  title: string;
  label: string;
  icon: typeof KeyRound;
  color: string;
  breaks: string;
  helps: string;
}[] = [
  {
    slug: 'compromised-global-admin',
    title: 'Compromised Global Admin',
    label: 'Identity compromise',
    icon: KeyRound,
    color: 'from-amber-500 to-orange-500',
    breaks: 'A privileged identity is compromised. MFA is weakened, Global Admin is abused, conditional access is modified, and OAuth grants or service principals are added. Blast radius grows quickly.',
    helps: 'Restore Entra controls before data. Revert privileged role changes, MFA, conditional access, OAuth grants, and groups. Recover critical users, then verify with policy-active and sign-in checks.',
  },
  {
    slug: 'destructive-sharepoint-onedrive-deletion',
    title: 'Destructive deletion across SharePoint and OneDrive',
    label: 'Data destruction',
    icon: Trash2,
    color: 'from-rose-500 to-red-500',
    breaks: 'A high-volume deletion event removes content across SharePoint sites and OneDrive accounts. Cause is unclear. Recycle bins and version history are not a coordinated business recovery plan.',
    helps: 'Identify affected sites, libraries, users, and files. Confirm identity integrity first if any admin drift is detected. Restore critical workspaces first, then broader tenant content, verified end to end.',
  },
  {
    slug: 'bulk-mailbox-deletion-retention-drift',
    title: 'Bulk mailbox deletion and retention drift',
    label: 'Exchange + retention',
    icon: Mail,
    color: 'from-blue-500 to-indigo-500',
    breaks: 'A large batch of mailboxes is removed. Retention tags, labels, and policies have shifted. Some mailboxes are beyond the native 30-day soft-delete window. Compliance needs answers.',
    helps: 'Recover mailboxes past the native window. Restore retention posture alongside mailbox content. Produce a timestamped recovery report for legal and compliance review.',
  },
];

export default function ScenariosIndex() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Helmet>
        <title>Recovery Scenarios — KavachIQ for Microsoft 365</title>
        <meta name="description" content="Illustrative recovery scenarios for Microsoft 365. How KavachIQ handles identity compromise, destructive deletion across SharePoint and OneDrive, and bulk mailbox deletion with retention drift." />
        <link rel="canonical" href="https://kavachiq.com/scenarios" />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://kavachiq.com/scenarios" />
        <meta property="og:title" content="Recovery Scenarios — KavachIQ for Microsoft 365" />
        <meta property="og:description" content="Illustrative Microsoft 365 recovery scenarios: identity compromise, destructive deletion, bulk mailbox loss and retention drift." />
        <meta property="og:image" content="https://kavachiq.com/og-scenarios.jpg" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:image" content="https://kavachiq.com/og-scenarios.jpg" />
        <meta name="twitter:title" content="Recovery Scenarios — KavachIQ for Microsoft 365" />
        <meta name="twitter:description" content="Illustrative Microsoft 365 recovery scenarios: identity compromise, destructive deletion, bulk mailbox loss and retention drift." />
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
      <section className="pt-28 pb-12 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-4">
            <Link to="/welcome" className="hover:text-foreground">KavachIQ</Link>
            <span>/</span>
            <span className="text-foreground">Recovery scenarios</span>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-teal-500/10 text-teal-400 rounded-full text-xs font-medium mb-5">
            <Shield className="w-3.5 h-3.5" />
            Illustrative recovery scenarios
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold text-foreground leading-[1.1] tracking-tight mb-5">
            Recovery scenarios for{' '}
            <span className="bg-gradient-to-r from-teal-500 to-cyan-500 bg-clip-text text-transparent">
              Microsoft 365.
            </span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-3xl leading-relaxed">
            Concrete, operator-grade walkthroughs of how KavachIQ runs identity-first cyber recovery for common Microsoft 365 incidents. Each scenario is illustrative, not a customer testimonial.
          </p>
        </div>
      </section>

      {/* Scenario cards */}
      <section className="pb-16 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {SCENARIOS.map((s) => (
              <Link
                key={s.slug}
                to={`/scenarios/${s.slug}`}
                className="group bg-card border border-border rounded-xl p-6 hover:border-teal-500/40 hover:shadow-lg hover:shadow-teal-500/5 transition-all flex flex-col"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${s.color} flex items-center justify-center shrink-0`}>
                    <s.icon className="w-5 h-5 text-white" />
                  </div>
                  <span className="text-[10px] font-bold text-muted-foreground tracking-widest uppercase">{s.label}</span>
                </div>
                <h2 className="text-lg font-bold text-foreground mb-3 leading-snug">{s.title}</h2>
                <div className="space-y-3 mb-5 flex-1">
                  <div>
                    <div className="text-[11px] font-bold text-rose-400 tracking-widest uppercase mb-1">What breaks</div>
                    <p className="text-sm text-muted-foreground leading-relaxed">{s.breaks}</p>
                  </div>
                  <div>
                    <div className="text-[11px] font-bold text-teal-500 tracking-widest uppercase mb-1">How KavachIQ helps</div>
                    <p className="text-sm text-muted-foreground leading-relaxed">{s.helps}</p>
                  </div>
                </div>
                <span className="text-sm font-medium text-teal-500 group-hover:text-teal-400 inline-flex items-center gap-1">
                  Read the scenario <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-16 px-6 bg-gradient-to-br from-teal-600 to-cyan-700">
        <div className="max-w-3xl mx-auto text-center text-white">
          <h2 className="text-2xl md:text-3xl font-bold mb-4">Talk through your Microsoft 365 recovery scenario</h2>
          <p className="text-teal-100 mb-8 max-w-xl mx-auto leading-relaxed">
            Walk any of these scenarios, or your specific incident, with a KavachIQ recovery engineer.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/contact" className="inline-flex items-center gap-2 px-8 py-3.5 bg-white text-teal-700 font-semibold rounded-xl hover:bg-teal-50 transition-colors text-lg">
              Request a Demo <ArrowRight className="w-5 h-5" />
            </Link>
            <Link to="/tour" className="inline-flex items-center gap-2 px-8 py-3.5 border-2 border-white/30 text-white font-medium rounded-xl hover:bg-white/10 transition-colors text-lg">
              <Eye className="w-5 h-5" /> See the Product Tour
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
