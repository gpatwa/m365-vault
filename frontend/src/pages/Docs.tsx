import { Link } from 'react-router-dom';
import { Shield, FileText, Download, ExternalLink, Lock, Server, BookOpen, ShieldCheck, Activity, Zap } from 'lucide-react';

const DOCS = [
  {
    category: 'Security & Compliance',
    items: [
      { title: 'Security Architecture', desc: 'Encryption, authentication, RBAC, WORM, infrastructure security — 10 sections covering all controls.', file: 'SECURITY.md', icon: Lock, color: 'text-blue-600 bg-blue-500/10' },
      { title: 'Compliance Mapping', desc: 'SOC 2 (16 controls), GDPR (8 articles), HIPAA (14 safeguards), DORA (6 articles) mapped to Shieldio features.', file: 'COMPLIANCE_MAPPING.md', icon: ShieldCheck, color: 'text-green-600 bg-green-500/10' },
      { title: 'Tenant Security', desc: 'Per-tenant encryption, key isolation, data sovereignty, and access control architecture.', file: 'TENANT_SECURITY.md', icon: Shield, color: 'text-purple-600 bg-purple-500/10' },
    ],
  },
  {
    category: 'Architecture & API',
    items: [
      { title: 'Architecture Guide', desc: 'System architecture, control/data plane separation, worker framework, fault tolerance, and resiliency design.', file: 'ARCHITECTURE.md', icon: Server, color: 'text-indigo-600 bg-indigo-500/10' },
      { title: 'API Reference', desc: '115+ REST API endpoints organized by domain: workloads, jobs, health, search, recovery, reports.', file: 'API_REFERENCE.md', icon: Zap, color: 'text-amber-600 bg-amber-500/10' },
    ],
  },
  {
    category: 'Operations',
    items: [
      { title: 'Azure Deployment', desc: 'Terraform IaC, Container Apps, PostgreSQL, Key Vault, CI/CD pipeline, sleep/wake cost management.', file: 'AZURE_DEPLOYMENT.md', icon: Activity, color: 'text-cyan-600 bg-cyan-500/10' },
      { title: 'Onboarding Guide', desc: '3-step tenant onboarding wizard, Graph API permissions, workload discovery, SLA policy setup.', file: 'ONBOARDING.md', icon: BookOpen, color: 'text-pink-600 bg-pink-500/10' },
    ],
  },
];

export default function Docs() {
  return (
    <div className="min-h-screen bg-card">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 bg-card/80 backdrop-blur-sm border-b border-border">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link to="/welcome" className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-blue-600" />
            <span className="font-bold text-foreground">Shieldio</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm text-muted-foreground hover:text-foreground">Sign In</Link>
            <Link to="/login" className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">Start Free</Link>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 pt-24 pb-20">
        {/* Header */}
        <div className="mb-10">
          <h1 className="text-3xl font-bold text-foreground">Documentation</h1>
          <p className="text-muted-foreground mt-2">Security architecture, API reference, deployment guides, and compliance mapping.</p>
        </div>

        {/* Download All */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl p-6 mb-10 text-white flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold">Security Documentation Pack</h2>
            <p className="text-blue-100 text-sm mt-1">Download all security and compliance docs for your procurement review.</p>
          </div>
          <Link to="/docs/view/SECURITY.md"
            className="px-5 py-2.5 bg-card text-blue-400 font-semibold rounded-lg hover:bg-blue-500/10 flex items-center gap-2 text-sm transition-colors">
            <Download className="w-4 h-4" /> View Security Pack
          </Link>
        </div>

        {/* Doc Categories */}
        {DOCS.map(cat => (
          <div key={cat.category} className="mb-10">
            <h2 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-4">{cat.category}</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {cat.items.map(doc => (
                <Link
                  key={doc.file}
                  to={`/docs/view/${doc.file}`}
                  className="group bg-card border border-border rounded-xl p-5 hover:border-blue-300 hover:shadow-md transition-all"
                >
                  <div className="flex items-start gap-4">
                    <div className={`p-2.5 rounded-lg ${doc.color}`}>
                      <doc.icon className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <h3 className="font-semibold text-foreground group-hover:text-blue-600 transition-colors">{doc.title}</h3>
                        <ExternalLink className="w-4 h-4 text-muted-foreground group-hover:text-blue-400 transition-colors" />
                      </div>
                      <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{doc.desc}</p>
                      <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
                        <FileText className="w-3.5 h-3.5" />
                        {doc.file}
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        ))}

        {/* Interactive API Docs */}
        <div className="bg-muted/50 border border-border rounded-xl p-6 text-center">
          <h3 className="font-semibold text-foreground mb-2">Interactive API Documentation</h3>
          <p className="text-sm text-muted-foreground mb-4">Explore all 115+ API endpoints with Swagger UI — try requests live.</p>
          <div className="flex justify-center gap-3">
            <a href="https://m365vault-backend-dev.happyflower-239d5857.centralus.azurecontainerapps.io/docs" target="_blank" rel="noopener noreferrer"
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 flex items-center gap-2 transition-colors">
              <Zap className="w-4 h-4" /> Swagger UI
            </a>
            <a href="https://m365vault-backend-dev.happyflower-239d5857.centralus.azurecontainerapps.io/redoc" target="_blank" rel="noopener noreferrer"
              className="px-4 py-2 bg-gray-200 text-muted-foreground text-sm font-medium rounded-lg hover:bg-gray-300 flex items-center gap-2 transition-colors">
              <BookOpen className="w-4 h-4" /> ReDoc
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
