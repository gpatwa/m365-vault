import { Link } from 'react-router-dom';
import { Shield, KeyRound, Server, Github, ArrowRight, Brain, ShieldCheck, Check, X, AlertTriangle, Bot, Zap } from 'lucide-react';
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
            <Link to="/login?register=true" className="px-4 py-1.5 bg-gradient-to-r from-teal-500 to-cyan-500 text-white text-sm font-medium rounded-lg">
              Start Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero — Origin Story */}
      <section className="pt-28 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-teal-500/10 text-teal-400 rounded-full text-xs font-medium mb-6">
            <Shield className="w-3.5 h-3.5" />
            Data Protection, Reimagined
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold leading-[1.1] mb-6">
            We built Shieldio because{' '}
            <span className="bg-gradient-to-r from-teal-500 to-cyan-500 bg-clip-text text-transparent">
              identity comes first.
            </span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-4">
            Every backup vendor restores your files. None of them ask the right question first:
            did the attacker change who has admin access?
          </p>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            Shieldio is the first data protection platform built for the age of AI agents and identity-first recovery.
            We back up your Entra ID configuration, score your users by criticality, and pre-compute NIST recovery plans
            — so when ransomware hits at 2am, recovery starts instantly. Identity first. CEO second. Then everyone else.
          </p>
        </div>
      </section>

      {/* The Problem — Why Every Backup Vendor Gets It Wrong */}
      <section className="py-16 px-6 bg-muted/50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-bold mb-3">The problem no one talks about</h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              When a ransomware attack hits your Microsoft 365 tenant, the first 30 minutes determine everything.
              Here's what happens with every other vendor:
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-8">
            {/* Without Shieldio */}
            <div className="bg-card border border-red-500/20 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-red-500/10 rounded-lg flex items-center justify-center">
                  <X className="w-4 h-4 text-red-400" />
                </div>
                <h3 className="font-bold text-red-400">Without Shieldio</h3>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex items-start gap-2 text-muted-foreground">
                  <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                  <span>Attacker disables MFA, grants themselves Global Admin</span>
                </div>
                <div className="flex items-start gap-2 text-muted-foreground">
                  <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                  <span>You restore emails from backup — but attacker still has admin access</span>
                </div>
                <div className="flex items-start gap-2 text-muted-foreground">
                  <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                  <span>They re-encrypt everything. You're back to square one</span>
                </div>
                <div className="flex items-start gap-2 text-muted-foreground">
                  <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                  <span>Manual triage: who was affected? What changed? Days to weeks</span>
                </div>
              </div>
            </div>
            {/* With Shieldio */}
            <div className="bg-card border border-teal-500/20 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-teal-500/10 rounded-lg flex items-center justify-center">
                  <Check className="w-4 h-4 text-teal-400" />
                </div>
                <h3 className="font-bold text-teal-400">With Shieldio</h3>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex items-start gap-2 text-muted-foreground">
                  <Check className="w-4 h-4 text-teal-400 mt-0.5 shrink-0" />
                  <span>Phase 1: Restore Entra ID — MFA policies, roles, OAuth grants (5 min)</span>
                </div>
                <div className="flex items-start gap-2 text-muted-foreground">
                  <Check className="w-4 h-4 text-teal-400 mt-0.5 shrink-0" />
                  <span>Phase 2: Restore CEO + VPs — critical users recovered first (10 min)</span>
                </div>
                <div className="flex items-start gap-2 text-muted-foreground">
                  <Check className="w-4 h-4 text-teal-400 mt-0.5 shrink-0" />
                  <span>Phase 3: Restore high-priority directors and managers (15 min)</span>
                </div>
                <div className="flex items-start gap-2 text-muted-foreground">
                  <Check className="w-4 h-4 text-teal-400 mt-0.5 shrink-0" />
                  <span>Phase 4: Full recovery — everyone else, verified with checksums (30 min)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Competitive Comparison */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-bold mb-3">How Shieldio compares</h2>
            <p className="text-muted-foreground">We're not trying to replace Rubrik or Veeam. We're solving a problem they don't.</p>
          </div>
          <div className="bg-card rounded-2xl border border-border overflow-x-auto">
            <table className="w-full text-sm min-w-[700px]">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="text-left px-5 py-4 font-medium text-muted-foreground w-[200px]">Capability</th>
                  <th className="text-center px-4 py-4 font-bold text-teal-400">Shieldio</th>
                  <th className="text-center px-4 py-4 font-medium text-muted-foreground">Veeam</th>
                  <th className="text-center px-4 py-4 font-medium text-muted-foreground">Rubrik</th>
                  <th className="text-center px-4 py-4 font-medium text-muted-foreground">Druva</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {[
                  { cap: 'Entra ID config backup (12 object types)', us: true, veeam: false, rubrik: false, druva: false },
                  { cap: 'Identity-first NIST recovery order', us: true, veeam: false, rubrik: false, druva: false },
                  { cap: 'Criticality-scored backup priority', us: true, veeam: false, rubrik: false, druva: false },
                  { cap: 'AI agent monitoring (Agent Shield)', us: true, veeam: true, rubrik: true, druva: false },
                  { cap: 'Pre-computed recovery plans', us: true, veeam: false, rubrik: false, druva: false },
                  { cap: 'Self-hosted / open source option', us: true, veeam: false, rubrik: false, druva: false },
                  { cap: 'Exchange + OneDrive + SharePoint backup', us: true, veeam: true, rubrik: true, druva: true },
                  { cap: 'Anomaly detection (built-in, zero cost)', us: true, veeam: true, rubrik: true, druva: true },
                  { cap: 'SMB pricing (under $2/user)', us: true, veeam: false, rubrik: false, druva: false },
                  { cap: 'Privacy-first analytics (no Google tracking)', us: true, veeam: false, rubrik: false, druva: false },
                ].map(row => (
                  <tr key={row.cap} className="hover:bg-muted/30">
                    <td className="px-5 py-3 text-foreground font-medium">{row.cap}</td>
                    <td className="px-4 py-3 text-center">{row.us ? <Check className="w-5 h-5 text-teal-500 mx-auto" /> : <X className="w-5 h-5 text-red-400/50 mx-auto" />}</td>
                    <td className="px-4 py-3 text-center">{row.veeam ? <Check className="w-5 h-5 text-muted-foreground mx-auto" /> : <X className="w-5 h-5 text-red-400/50 mx-auto" />}</td>
                    <td className="px-4 py-3 text-center">{row.rubrik ? <Check className="w-5 h-5 text-muted-foreground mx-auto" /> : <X className="w-5 h-5 text-red-400/50 mx-auto" />}</td>
                    <td className="px-4 py-3 text-center">{row.druva ? <Check className="w-5 h-5 text-muted-foreground mx-auto" /> : <X className="w-5 h-5 text-red-400/50 mx-auto" />}</td>
                  </tr>
                ))}
                <tr className="bg-muted/30">
                  <td className="px-5 py-3 font-bold text-foreground">Starting price</td>
                  <td className="px-4 py-3 text-center font-bold text-teal-400">$1.50/user</td>
                  <td className="px-4 py-3 text-center text-muted-foreground">$3-5/user</td>
                  <td className="px-4 py-3 text-center text-muted-foreground">$6-10/user</td>
                  <td className="px-4 py-3 text-center text-muted-foreground">$4-8/user</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* What Makes Us Different — 6 pillars */}
      <section className="py-16 px-6 bg-muted/50">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold mb-10 text-center">Built differently</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: KeyRound, title: 'Identity-First Recovery', desc: 'We back up 12 Entra ID object types — conditional access policies, role assignments, OAuth grants, MFA configs. No competitor does this. When an attacker disables MFA, we revert it in seconds.', color: 'from-teal-500 to-cyan-500' },
              { icon: Brain, title: 'Context-Aware Intelligence', desc: 'Shieldio reads your Microsoft Graph to discover org hierarchy, VIP groups, and privileged roles. Every user gets a 4-factor criticality score. Your CEO is backed up first. Automatically.', color: 'from-amber-500 to-orange-500' },
              { icon: Bot, title: 'Agent Shield', desc: '88% of enterprises have had AI agent incidents. Shieldio detects shadow agents like OpenClaw, monitors Copilot actions, and enables one-click rollback. Enterprise competitors charge $6-15/user. We start at $1.50.', color: 'from-violet-500 to-purple-500' },
              { icon: ShieldCheck, title: 'NIST SP 800-184 Recovery', desc: 'Pre-computed 4-phase recovery plans refreshed every 6 hours. Phase 1: Identity controls. Phase 2: Critical users. Phase 3: High priority. Phase 4: Full recovery. No manual triage needed.', color: 'from-green-500 to-emerald-500' },
              { icon: Server, title: 'Open Source & Self-Hosted', desc: 'Apache 2.0 license. Deploy on your Azure, AWS, or on-prem. Audit every line of code. No vendor lock-in. Your data sovereignty is non-negotiable — and we prove it by showing our source.', color: 'from-blue-500 to-indigo-500' },
              { icon: Zap, title: 'Zero-Cost Intelligence', desc: 'Anomaly detection, health scoring, criticality analysis — all pure Python + scipy. No LLM tokens. No external API calls. No per-query charges. Intelligence that runs on your existing infrastructure.', color: 'from-rose-500 to-pink-500' },
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

      {/* The Numbers */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-10 text-center">By the numbers</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { value: '12', label: 'Entra ID object types backed up', sub: 'More than any competitor' },
              { value: '$1.50', label: 'Per user, per month', sub: 'Intelligence included free' },
              { value: '< 30min', label: 'Full recovery time', sub: 'Identity-first NIST order' },
              { value: '100%', label: 'Open source', sub: 'Apache 2.0 license' },
            ].map(n => (
              <div key={n.label} className="text-center p-4">
                <div className="text-3xl font-extrabold bg-gradient-to-r from-teal-500 to-cyan-500 bg-clip-text text-transparent">{n.value}</div>
                <div className="text-sm font-medium text-foreground mt-1">{n.label}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{n.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust & Compliance */}
      <section className="py-16 px-6 bg-muted/50">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-2xl font-bold mb-3">Enterprise-grade from day one</h2>
          <p className="text-muted-foreground mb-8">Not a roadmap promise. These controls are built into every deployment.</p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            {[
              { icon: '🔒', label: 'AES-256-GCM', desc: 'Encryption at Rest' },
              { icon: '🔑', label: 'Per-Tenant Keys', desc: 'Key Isolation' },
              { icon: '🛡️', label: 'WORM Storage', desc: 'Immutable Backups' },
              { icon: '✅', label: 'SOC 2 Ready', desc: '16 Controls' },
              { icon: '🇪🇺', label: 'GDPR Ready', desc: '8 Articles' },
              { icon: '🏥', label: 'HIPAA Ready', desc: '14 Safeguards' },
              { icon: '🏦', label: 'DORA Ready', desc: 'Financial Sector' },
              { icon: '📋', label: 'Full Audit Trail', desc: 'Every Action Logged' },
            ].map(b => (
              <div key={b.label} className="flex items-center gap-2.5 px-4 py-3 bg-card border border-border rounded-xl hover:border-teal-500/20 transition-all">
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

      {/* Who We Serve */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-10 text-center">Built for regulated industries</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: '🏥', title: 'Healthcare', desc: 'HIPAA-ready backup for clinics and medical groups. Protect patient data in Exchange and Teams. Identity-first recovery ensures admin access is restored before patient records.', users: '50-500 users' },
              { icon: '⚖️', title: 'Law Firms', desc: 'WORM-compliant immutable backups for legal hold. Self-hosted option keeps client data sovereign. Entra ID rollback protects privileged access to case files.', users: '20-200 users' },
              { icon: '🏦', title: 'Financial Services', desc: 'DORA and SOX compliance-ready. Criticality scoring prioritizes trading desks and compliance officers. Agent Shield monitors for unauthorized AI access to financial data.', users: '50-1,000 users' },
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

      {/* Open Source CTA */}
      <section className="py-16 px-6 bg-muted/50">
        <div className="max-w-3xl mx-auto text-center">
          <Github className="w-12 h-12 text-foreground mx-auto mb-4" />
          <h2 className="text-3xl font-bold mb-3">Open source. Always.</h2>
          <p className="text-muted-foreground mb-2 max-w-xl mx-auto">
            We believe the best security products are the ones you can audit. Shieldio is licensed under Apache 2.0
            — view every line of code, run it on your own infrastructure, contribute back to the project.
          </p>
          <p className="text-sm text-muted-foreground mb-8">
            No vendor lock-in. No trust-us security. No phone-home telemetry.
          </p>
          <div className="flex items-center justify-center gap-4">
            <a href="https://github.com/gpatwa/m365-vault" target="_blank" rel="noopener noreferrer"
              className="px-6 py-3 bg-card border border-border text-foreground font-medium rounded-xl hover:bg-muted transition-colors flex items-center gap-2">
              <Github className="w-4 h-4" /> View on GitHub
            </a>
            <Link to="/login?register=true"
              className="px-6 py-3 bg-gradient-to-r from-teal-500 to-cyan-500 text-white font-semibold rounded-xl hover:from-teal-400 hover:to-cyan-400 transition-all shadow-lg shadow-teal-500/20 flex items-center gap-2">
              Start Free <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 px-6 bg-gradient-to-br from-teal-600 to-cyan-700">
        <div className="max-w-3xl mx-auto text-center text-white">
          <h2 className="text-3xl font-bold mb-4">Ready to protect your M365 data?</h2>
          <p className="text-teal-100 mb-8">
            Connect your tenant in 2 minutes. See your org hierarchy, criticality scores, and recovery plan — with your real data.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link to="/login?register=true"
              className="px-8 py-3.5 bg-white text-teal-700 font-semibold rounded-xl hover:bg-teal-50 transition-colors text-lg flex items-center gap-2">
              Start Free Trial <ArrowRight className="w-5 h-5" />
            </Link>
            <Link to="/contact"
              className="px-8 py-3.5 border-2 border-white/30 text-white font-medium rounded-xl hover:bg-white/10 transition-colors text-lg">
              Book a Demo
            </Link>
          </div>
          <p className="text-teal-200 text-xs mt-4">Free for up to 25 users. No credit card. SOC 2 + GDPR + HIPAA + DORA ready.</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-border">
        <div className="max-w-4xl mx-auto text-center text-xs text-muted-foreground">
          2026 Shieldio. Open source under Apache 2.0 License.
        </div>
      </footer>
    </div>
  );
}
