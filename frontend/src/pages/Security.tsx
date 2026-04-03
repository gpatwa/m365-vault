import { useQuery } from '@tanstack/react-query';
import { Shield, Lock, Eye, ShieldCheck, CheckCircle2, XCircle, FileText, Server, Key, Users } from 'lucide-react';
import { api } from '../api/client';

const CATEGORY_CONFIG: Record<string, { label: string; icon: typeof Shield; color: string; bg: string }> = {
  encryption: { label: 'Encryption', icon: Lock, color: 'text-blue-600', bg: 'bg-blue-500/10' },
  data_protection: { label: 'Data Protection', icon: ShieldCheck, color: 'text-green-600', bg: 'bg-green-500/10' },
  authentication: { label: 'Authentication', icon: Key, color: 'text-purple-600', bg: 'bg-purple-500/10' },
  monitoring: { label: 'Monitoring', icon: Eye, color: 'text-amber-600', bg: 'bg-amber-500/10' },
  infrastructure: { label: 'Infrastructure', icon: Server, color: 'text-muted-foreground', bg: 'bg-muted/50' },
};

const COMPLIANCE_CONFIG: Record<string, { label: string; full: string; color: string }> = {
  soc2: { label: 'SOC 2', full: 'SOC 2 Trust Services Criteria', color: 'border-blue-500/20 bg-blue-500/10 text-blue-400' },
  gdpr: { label: 'GDPR', full: 'General Data Protection Regulation', color: 'border-green-500/20 bg-green-500/10 text-green-400' },
  hipaa: { label: 'HIPAA', full: 'Health Insurance Portability & Accountability Act', color: 'border-purple-500/20 bg-purple-500/10 text-purple-800' },
  dora: { label: 'DORA', full: 'Digital Operational Resilience Act', color: 'border-amber-500/20 bg-amber-500/10 text-amber-400' },
};

export default function SecurityPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['security-posture'],
    queryFn: () => api.get<any>('/security/posture'),
  });

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-blue-500/20 border-t-blue-600 rounded-full animate-spin" /></div>;
  }

  const score = data?.security_score;
  const features = data?.features || [];

  // Group features by category
  const grouped: Record<string, any[]> = {};
  for (const f of features) {
    if (!grouped[f.category]) grouped[f.category] = [];
    grouped[f.category].push(f);
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Security Posture</h1>
        <p className="text-sm text-muted-foreground">Encryption, compliance, and data protection status</p>
      </div>

      {/* Security Score + Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {/* Score */}
        <div className="bg-card rounded-xl border border-border p-6 flex flex-col items-center justify-center">
          <div className={`text-5xl font-extrabold ${
            score?.grade === 'A' ? 'text-green-600' : score?.grade === 'B' ? 'text-blue-600' : 'text-amber-600'
          }`}>
            {score?.grade || '-'}
          </div>
          <div className="text-sm text-muted-foreground mt-1">Security Grade</div>
          <div className="text-xs text-muted-foreground mt-0.5">{score?.active_features}/{score?.total_features} controls active</div>
        </div>

        {/* Encryption */}
        <div className="bg-card rounded-xl border border-border p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="p-2 bg-blue-500/10 rounded-lg"><Lock className="w-4 h-4 text-blue-600" /></div>
            <span className="text-sm font-semibold text-foreground">Encryption</span>
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <CheckCircle2 className="w-3.5 h-3.5 text-green-500" /> {data?.encryption?.algorithm}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <CheckCircle2 className="w-3.5 h-3.5 text-green-500" /> Per-tenant key isolation
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <CheckCircle2 className="w-3.5 h-3.5 text-green-500" /> {data?.encryption?.transit} in transit
            </div>
          </div>
        </div>

        {/* Immutability */}
        <div className="bg-card rounded-xl border border-border p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="p-2 bg-green-500/10 rounded-lg"><ShieldCheck className="w-4 h-4 text-green-600" /></div>
            <span className="text-sm font-semibold text-foreground">Immutability</span>
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <CheckCircle2 className="w-3.5 h-3.5 text-green-500" /> {data?.immutability?.worm_policies || 0} WORM policies
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <CheckCircle2 className="w-3.5 h-3.5 text-green-500" /> {data?.immutability?.locked_snapshots || 0} locked snapshots
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              {data?.immutability?.legal_hold_policies > 0
                ? <><CheckCircle2 className="w-3.5 h-3.5 text-green-500" /> Legal hold active</>
                : <><XCircle className="w-3.5 h-3.5 text-muted-foreground" /> No legal holds</>}
            </div>
          </div>
        </div>

        {/* Coverage */}
        <div className="bg-card rounded-xl border border-border p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="p-2 bg-purple-500/10 rounded-lg"><Users className="w-4 h-4 text-purple-600" /></div>
            <span className="text-sm font-semibold text-foreground">Coverage</span>
          </div>
          <div className="text-2xl font-bold text-foreground">{data?.coverage?.coverage_percent || 0}%</div>
          <div className="text-xs text-muted-foreground">{data?.coverage?.protected || 0} / {data?.coverage?.total_objects || 0} objects protected</div>
          <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500/100 rounded-full transition-all"
              style={{ width: `${data?.coverage?.coverage_percent || 0}%` }}
            />
          </div>
        </div>
      </div>

      {/* Compliance Badges */}
      <div className="bg-card rounded-xl border border-border p-5 mb-6">
        <h2 className="text-sm font-semibold text-foreground mb-4">Compliance Readiness</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(data?.compliance || {}).map(([key, info]: [string, any]) => {
            const config = COMPLIANCE_CONFIG[key];
            if (!config) return null;
            return (
              <div key={key} className={`border rounded-xl p-4 text-center ${config.color}`}>
                <div className="text-lg font-bold">{config.label}</div>
                <div className="text-[10px] mt-0.5 opacity-70">{config.full}</div>
                <div className="mt-2 flex items-center justify-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span className="text-xs font-medium">{info.controls_mapped || info.articles_mapped || info.safeguards_mapped} controls mapped</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Security Features by Category */}
      <div className="bg-card rounded-xl border border-border p-5 mb-6">
        <h2 className="text-sm font-semibold text-foreground mb-4">Security Controls ({score?.active_features}/{score?.total_features} active)</h2>
        <div className="space-y-4">
          {Object.entries(grouped).map(([category, items]) => {
            const config = CATEGORY_CONFIG[category] || { label: category, icon: Shield, color: 'text-muted-foreground', bg: 'bg-muted/50' };
            const Icon = config.icon;
            return (
              <div key={category}>
                <div className="flex items-center gap-2 mb-2">
                  <div className={`p-1.5 ${config.bg} rounded-lg`}><Icon className={`w-3.5 h-3.5 ${config.color}`} /></div>
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{config.label}</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 ml-8">
                  {items.map((f: any) => (
                    <div key={f.name} className="flex items-start gap-2 p-2.5 bg-muted/50 rounded-lg">
                      {f.status === 'active'
                        ? <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                        : <XCircle className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />}
                      <div>
                        <div className="text-xs font-medium text-foreground">{f.name}</div>
                        <div className="text-[10px] text-muted-foreground mt-0.5">{f.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Security Documentation Pack */}
      <div className="bg-gradient-to-r from-gray-900 to-gray-800 rounded-xl p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold">Security Documentation Pack</h2>
            <p className="text-sm text-muted-foreground mt-1">Download our security architecture and compliance mapping for your procurement review.</p>
          </div>
          <div className="flex gap-3">
            <a href="/docs/SECURITY.md" target="_blank" className="px-4 py-2 bg-card/10 hover:bg-card/20 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
              <FileText className="w-4 h-4" /> Security Architecture
            </a>
            <a href="/docs/COMPLIANCE_MAPPING.md" target="_blank" className="px-4 py-2 bg-card/10 hover:bg-card/20 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
              <Shield className="w-4 h-4" /> Compliance Mapping
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
