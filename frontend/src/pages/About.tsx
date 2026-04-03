import { Link } from 'react-router-dom';
import { Shield, Lock, Globe, KeyRound, Server, Github, ArrowRight, Eye, Brain, ShieldCheck } from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';

export default function About() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 bg-card/80 backdrop-blur-sm border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link to="/welcome" className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-teal-500" />
            <span className="font-bold text-foreground">Shieldio</span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <Link to="/welcome" className="hover:text-foreground">Home</Link>
            <Link to="/about" className="text-foreground font-medium">About</Link>
            <Link to="/welcome#pricing" className="hover:text-foreground">Pricing</Link>
            <Link to="/contact" className="hover:text-foreground">Contact</Link>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link to="/login" className="text-sm text-muted-foreground hover:text-foreground">Sign In</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-24 pb-16 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-teal-500/20 rounded-2xl mb-6">
            <Shield className="w-8 h-8 text-teal-400" />
          </div>
          <h1 className="text-4xl font-extrabold mb-4">
            Protecting the world's SaaS data.{' '}
            <span className="bg-gradient-to-r from-teal-500 to-cyan-500 bg-clip-text text-transparent">Identity first.</span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Microsoft 365 has a 93-day recycle bin — not a backup. When ransomware hits or an AI agent goes rogue,
            Shieldio already has a context-aware recovery plan: identity controls first, then critical users, then everyone else.
          </p>
        </div>
      </section>

      {/* Why We Exist */}
      <section className="py-16 px-6 bg-muted/50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold mb-8 text-center">Why Shieldio Exists</h2>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="bg-card border border-border rounded-xl p-6">
              <div className="w-10 h-10 bg-red-500/10 rounded-lg flex items-center justify-center mb-4">
                <Lock className="w-5 h-5 text-red-400" />
              </div>
              <h3 className="font-semibold mb-2">Microsoft Won't Save You</h3>
              <p className="text-sm text-muted-foreground">The M365 recycle bin is not a disaster recovery plan. It doesn't protect against ransomware, admin errors, or rogue AI agents.</p>
            </div>
            <div className="bg-card border border-border rounded-xl p-6">
              <div className="w-10 h-10 bg-amber-500/10 rounded-lg flex items-center justify-center mb-4">
                <Brain className="w-5 h-5 text-amber-400" />
              </div>
              <h3 className="font-semibold mb-2">AI Agents Are the New Threat</h3>
              <p className="text-sm text-muted-foreground">88% of organizations have had AI agent security incidents. OpenClaw, Copilot, custom agents — they all need monitoring and rollback.</p>
            </div>
            <div className="bg-card border border-border rounded-xl p-6">
              <div className="w-10 h-10 bg-teal-500/10 rounded-lg flex items-center justify-center mb-4">
                <KeyRound className="w-5 h-5 text-teal-400" />
              </div>
              <h3 className="font-semibold mb-2">Identity Must Come First</h3>
              <p className="text-sm text-muted-foreground">If attackers have admin access, restoring data is pointless. Shieldio backs up Entra ID first — roles, MFA policies, OAuth grants.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Differentiators */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold mb-8 text-center">What Makes Us Different</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {[
              { icon: Eye, title: 'Context-Aware Recovery', desc: 'Auto-discovers your org hierarchy from Microsoft Graph. CEO gets recovered first, then VPs, then everyone else. No manual configuration.' },
              { icon: ShieldCheck, title: 'NIST SP 800-184 Compliant', desc: 'Pre-computed 4-phase recovery plans: identity controls, critical users, high priority, full recovery. Ready before you need them.' },
              { icon: Server, title: 'Self-Hosted & Open Source', desc: 'Apache 2.0 license. Deploy on your own Azure, AWS, or on-premises infrastructure. Your data never leaves your environment.' },
              { icon: Globe, title: 'Agent Shield', desc: 'Monitor AI agents accessing your M365 data. Detect shadow agents, track OAuth tokens, revert unauthorized changes. Industry first for SMBs.' },
            ].map(d => (
              <div key={d.title} className="flex gap-4 p-5 bg-card border border-border rounded-xl">
                <div className="w-10 h-10 bg-teal-500/10 rounded-lg flex items-center justify-center shrink-0">
                  <d.icon className="w-5 h-5 text-teal-400" />
                </div>
                <div>
                  <h3 className="font-semibold mb-1">{d.title}</h3>
                  <p className="text-sm text-muted-foreground">{d.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust Badges */}
      <section className="py-16 px-6 bg-muted/50">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-2xl font-bold mb-8">Enterprise-Grade Security</h2>
          <div className="flex flex-wrap items-center justify-center gap-4">
            {[
              { icon: '🔒', label: 'AES-256-GCM', desc: 'Encryption at Rest' },
              { icon: '🔑', label: 'Per-Tenant Keys', desc: 'Key Isolation' },
              { icon: '🛡️', label: 'WORM Storage', desc: 'Immutable Backups' },
              { icon: '✅', label: 'SOC 2 Ready', desc: '16 Controls' },
              { icon: '🇪🇺', label: 'GDPR Ready', desc: '8 Articles' },
              { icon: '🏥', label: 'HIPAA Ready', desc: '14 Safeguards' },
              { icon: '🏦', label: 'DORA Ready', desc: 'Financial Sector' },
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

      {/* Open Source */}
      <section className="py-16 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <Github className="w-10 h-10 text-foreground mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-3">Open Source. Always.</h2>
          <p className="text-muted-foreground mb-6">
            Shieldio is licensed under Apache 2.0. View the source, audit the code, self-host on your infrastructure.
            No vendor lock-in. No trust-us security.
          </p>
          <div className="flex items-center justify-center gap-4">
            <a href="https://github.com/gpatwa/m365-vault" target="_blank" rel="noopener noreferrer"
              className="px-6 py-3 bg-card border border-border text-foreground font-medium rounded-xl hover:bg-muted transition-colors flex items-center gap-2">
              <Github className="w-4 h-4" /> View on GitHub
            </a>
            <Link to="/login?register=true"
              className="px-6 py-3 bg-teal-600 text-white font-semibold rounded-xl hover:bg-teal-700 transition-colors flex items-center gap-2">
              Start Free <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
