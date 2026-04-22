import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Shield, Mail, Linkedin, ArrowRight, Send, Calendar, Lock, Users, Server, FileSearch, KeyRound, ShieldCheck } from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { appUrl } from '../utils/appUrl';

type Reason =
  | 'demo'
  | 'sales'
  | 'security'
  | 'general';

const REASONS: { id: Reason; label: string; desc: string }[] = [
  { id: 'demo', label: 'Request a Demo', desc: 'See KavachIQ in your Microsoft 365 environment' },
  { id: 'sales', label: 'Talk to Sales', desc: 'Evaluate KavachIQ for a team, tenant, or procurement review' },
  { id: 'security', label: 'Security or Procurement', desc: 'SOC 2, GDPR, HIPAA, DORA, or vendor-risk questions' },
  { id: 'general', label: 'General Inquiry', desc: 'Anything else' },
];

export default function Contact() {
  const [form, setForm] = useState({ name: '', email: '', company: '', message: '' });
  const [reason, setReason] = useState<Reason>('demo');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const reasonLabel = REASONS.find(r => r.id === reason)?.label || 'General';
    window.location.href = `mailto:hello@kavachiq.com?subject=${encodeURIComponent(`[${reasonLabel}] ${form.name} (${form.company})`)}&body=${encodeURIComponent(form.message)}`;
    setSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Helmet>
        <title>Contact KavachIQ — Request a Demo</title>
        <meta name="description" content="Request a demo, talk to sales, or route a security and procurement question to KavachIQ. Identity-first cyber recovery for Microsoft 365." />
        <link rel="canonical" href="https://kavachiq.com/contact" />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://kavachiq.com/contact" />
        <meta property="og:title" content="Contact KavachIQ — Request a Demo" />
        <meta property="og:description" content="Demo, sales, and security contact paths for teams evaluating KavachIQ for Microsoft 365 recovery." />
        <meta property="og:image" content="https://kavachiq.com/og-contact.jpg" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:image" content="https://kavachiq.com/og-contact.jpg" />
        <meta name="twitter:title" content="Contact KavachIQ — Request a Demo" />
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
            <Link to="/contact" className="text-foreground font-medium">Contact</Link>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <a href={appUrl('/login')} className="hidden sm:inline text-sm text-muted-foreground hover:text-foreground">Sign In</a>
          </div>
        </div>
      </nav>

      <div className="pt-28 pb-20 px-6">
        <div className="max-w-5xl mx-auto">
          {/* Hero */}
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-teal-500/10 text-teal-400 rounded-full text-xs font-medium mb-4">
              <Shield className="w-3.5 h-3.5" /> Evaluate KavachIQ
            </div>
            <h1 className="text-3xl md:text-4xl font-extrabold mb-3">Talk to the KavachIQ team</h1>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Walk through a recovery scenario in your Microsoft 365 environment, share a specific incident, or route a security and procurement question. We reply within one business day.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 mb-8">
            {/* Left: Contact form spans 2 cols */}
            <div className="md:col-span-2 bg-card border border-border rounded-2xl p-6">
              <h2 className="text-lg font-semibold mb-4">Send a message</h2>
              {submitted ? (
                <div className="text-center py-10">
                  <div className="w-12 h-12 bg-teal-500/20 rounded-full flex items-center justify-center mx-auto mb-3">
                    <Send className="w-6 h-6 text-teal-400" />
                  </div>
                  <p className="text-foreground font-medium">Message sent.</p>
                  <p className="text-sm text-muted-foreground mt-1">We will reply within one business day.</p>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Reason for contact</label>
                    <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {REASONS.map(r => (
                        <button
                          type="button"
                          key={r.id}
                          onClick={() => setReason(r.id)}
                          className={`text-left px-3 py-2 rounded-lg border text-sm transition-all ${
                            reason === r.id
                              ? 'border-teal-500 bg-teal-500/10 text-foreground'
                              : 'border-border bg-background text-muted-foreground hover:border-teal-500/30'
                          }`}
                        >
                          <div className="font-medium">{r.label}</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">{r.desc}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium text-muted-foreground">Name</label>
                      <input type="text" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                        className="w-full mt-1 px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm focus:ring-2 focus:ring-ring" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-muted-foreground">Work email</label>
                      <input type="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
                        className="w-full mt-1 px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm focus:ring-2 focus:ring-ring" />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Company</label>
                    <input type="text" value={form.company} onChange={e => setForm({ ...form, company: e.target.value })}
                      className="w-full mt-1 px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm focus:ring-2 focus:ring-ring" />
                  </div>

                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Message</label>
                    <textarea required rows={4} value={form.message} onChange={e => setForm({ ...form, message: e.target.value })}
                      placeholder="Share context: tenant size, workloads in scope, timelines, or a specific incident you want to discuss."
                      className="w-full mt-1 px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm focus:ring-2 focus:ring-ring resize-none" />
                  </div>

                  <button type="submit"
                    className="w-full py-2.5 bg-teal-600 text-white rounded-lg font-medium hover:bg-teal-700 transition-colors flex items-center justify-center gap-2">
                    Send message <ArrowRight className="w-4 h-4" />
                  </button>
                </form>
              )}
            </div>

            {/* Right: demo + alternate paths */}
            <div className="space-y-6">
              <div className="bg-gradient-to-br from-teal-600 to-cyan-700 rounded-2xl p-6 text-white">
                <Calendar className="w-7 h-7 mb-3 text-teal-200" />
                <h3 className="text-lg font-semibold mb-2">Request a Demo</h3>
                <p className="text-sm text-teal-100 mb-4">
                  Walk through a recovery scenario with a KavachIQ engineer. Tenant-safe, no setup required.
                </p>
                <a href="mailto:hello@kavachiq.com?subject=Demo%20request"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-white text-teal-700 rounded-lg font-medium text-sm hover:bg-teal-50 transition-colors">
                  Request a Demo <ArrowRight className="w-4 h-4" />
                </a>
                <p className="text-xs text-teal-200/80 mt-4">
                  Typical first call runs 30 minutes. Deeper technical walkthroughs: about 60.
                </p>
              </div>

              <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Users className="w-4 h-4 text-teal-400" />
                    <span className="text-sm font-semibold text-foreground">Talk to Sales</span>
                  </div>
                  <a href="mailto:sales@kavachiq.com" className="text-sm text-muted-foreground hover:text-teal-400 transition-colors">
                    sales@kavachiq.com
                  </a>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Lock className="w-4 h-4 text-teal-400" />
                    <span className="text-sm font-semibold text-foreground">Security &amp; Procurement</span>
                  </div>
                  <a href="mailto:security@kavachiq.com" className="text-sm text-muted-foreground hover:text-teal-400 transition-colors">
                    security@kavachiq.com
                  </a>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Mail className="w-4 h-4 text-teal-400" />
                    <span className="text-sm font-semibold text-foreground">General</span>
                  </div>
                  <a href="mailto:hello@kavachiq.com" className="text-sm text-muted-foreground hover:text-teal-400 transition-colors">
                    hello@kavachiq.com
                  </a>
                </div>
                <div className="pt-2 border-t border-border">
                  <a href="https://linkedin.com/company/kavachiq" target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm text-muted-foreground hover:text-teal-400 transition-colors">
                    <Linkedin className="w-4 h-4" /> LinkedIn
                  </a>
                </div>
              </div>
            </div>
          </div>

          {/* What to expect in the demo */}
          <div className="mt-16">
            <div className="mb-8">
              <div className="text-xs font-bold text-teal-500 tracking-widest mb-2">WHAT TO EXPECT IN THE DEMO</div>
              <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-2">A practical walkthrough, built around your environment</h2>
              <p className="text-muted-foreground max-w-2xl leading-relaxed">
                A first demo is a working conversation with a KavachIQ recovery engineer. Bring your Microsoft 365 tenant details, a real incident scenario, or a procurement question. The agenda adapts to what you actually need.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                {
                  icon: Server,
                  title: 'Your environment and incident scope',
                  desc: 'Start from your Microsoft 365 tenant, workloads in scope, and the kind of incident you care about: ransomware, destructive change, mailbox loss, or identity compromise.',
                },
                {
                  icon: FileSearch,
                  title: 'Blast radius and recovery workflow',
                  desc: 'See how KavachIQ computes blast radius across identity and data, and how the six-phase Protect to Verify workflow applies to your case.',
                },
                {
                  icon: KeyRound,
                  title: 'Identity-first recovery order',
                  desc: 'Walk through how Microsoft Entra controls are restored before data, and how critical users come back ahead of broader business recovery.',
                },
                {
                  icon: ShieldCheck,
                  title: 'Security, controls, and next steps',
                  desc: 'Review tenant isolation, encryption, immutability, and audit. Route deeper security and procurement questions through the right path.',
                },
              ].map((item) => (
                <div key={item.title} className="bg-card border border-border rounded-xl p-5 h-full">
                  <div className="w-9 h-9 rounded-lg bg-teal-500/10 flex items-center justify-center mb-3">
                    <item.icon className="w-5 h-5 text-teal-400" />
                  </div>
                  <h3 className="font-semibold text-foreground text-sm mb-1.5">{item.title}</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-5 max-w-2xl leading-relaxed">
              Prefer to walk a scenario first? Browse <Link to="/scenarios" className="text-teal-500 hover:text-teal-400 underline underline-offset-2">our recovery scenarios</Link>, review the <Link to="/security" className="text-teal-500 hover:text-teal-400 underline underline-offset-2">security page</Link>, or read a <Link to="/overview" className="text-teal-500 hover:text-teal-400 underline underline-offset-2">one-page overview</Link>.
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-border">
        <div className="max-w-4xl mx-auto text-center text-xs text-muted-foreground">
          &copy; {new Date().getFullYear()} KavachIQ. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
