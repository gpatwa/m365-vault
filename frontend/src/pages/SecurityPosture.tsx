import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Shield, Check, X, AlertTriangle, RefreshCw, Loader2, Lock, Key, Users, Database, Server, FileText, Scale, Package } from 'lucide-react';
import { api } from '../api/client';
import Breadcrumb from '../components/design-system/Breadcrumb';

interface PostureCheck {
  name: string; category: string; passed: boolean;
  severity: string; detail: string; fix: string;
}

interface PostureData {
  score: number; grade: string; total_checks: number;
  passed: number; failed: number; critical_passed: string;
  scanned_at: string;
  categories: Record<string, { passed: number; total: number }>;
  checks: PostureCheck[];
}

const CATEGORY_META: Record<string, { icon: any; label: string; color: string }> = {
  encryption: { icon: Lock, label: 'Encryption', color: 'text-teal-400' },
  authentication: { icon: Key, label: 'Authentication', color: 'text-blue-400' },
  access_control: { icon: Users, label: 'Access Control', color: 'text-purple-400' },
  data_protection: { icon: Database, label: 'Data Protection', color: 'text-green-400' },
  infrastructure: { icon: Server, label: 'Infrastructure', color: 'text-amber-400' },
  audit: { icon: FileText, label: 'Audit & Monitoring', color: 'text-cyan-400' },
  compliance: { icon: Scale, label: 'Compliance', color: 'text-indigo-400' },
  dependencies: { icon: Package, label: 'Dependencies', color: 'text-pink-400' },
};

const GRADE_COLORS: Record<string, string> = {
  'A+': 'text-teal-400', 'A': 'text-teal-400', 'B': 'text-green-400',
  'C': 'text-amber-400', 'D': 'text-orange-400', 'F': 'text-red-400',
};

export default function SecurityPosture() {
  const [expandedCat, setExpandedCat] = useState<string | null>(null);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['security-posture'],
    queryFn: () => api.get<PostureData>('/security-posture/posture'),
  });

  const d = data;

  return (
    <div>
      <Breadcrumb items={[{ label: 'Administration', path: '/settings' }, { label: 'Security Posture' }]} />

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-teal-500/10 rounded-xl flex items-center justify-center">
            <Shield className="w-5 h-5 text-teal-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Security Posture</h1>
            <p className="text-xs text-muted-foreground">Real-time security assessment of your KavachIQ deployment</p>
          </div>
        </div>
        <button onClick={() => refetch()} disabled={isFetching}
          className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700 transition-colors disabled:opacity-50">
          {isFetching ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          Scan Now
        </button>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-teal-500" />
          <span className="ml-3 text-muted-foreground">Running security assessment...</span>
        </div>
      )}

      {d && (
        <>
          {/* Score Card */}
          <div className="bg-card border border-border rounded-2xl p-8 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-8">
                <div className="text-center">
                  <div className={`text-6xl font-extrabold ${GRADE_COLORS[d.grade] || 'text-foreground'}`}>
                    {d.score}
                  </div>
                  <div className={`text-2xl font-bold mt-1 ${GRADE_COLORS[d.grade] || 'text-foreground'}`}>
                    Grade {d.grade}
                  </div>
                </div>
                <div className="border-l border-border pl-8 space-y-2">
                  <div className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-teal-500" />
                    <span className="text-sm text-foreground">{d.passed} checks passed</span>
                  </div>
                  {d.failed > 0 && (
                    <div className="flex items-center gap-2">
                      <X className="w-4 h-4 text-red-400" />
                      <span className="text-sm text-foreground">{d.failed} checks failed</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-teal-500" />
                    <span className="text-sm text-foreground">Critical: {d.critical_passed} passed</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Scanned: {new Date(d.scanned_at).toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Category Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {Object.entries(d.categories).map(([key, cat]) => {
              const meta = CATEGORY_META[key] || { icon: Shield, label: key, color: 'text-foreground' };
              const Icon = meta.icon;
              const allPassed = cat.passed === cat.total;
              return (
                <button key={key} onClick={() => setExpandedCat(expandedCat === key ? null : key)}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    expandedCat === key ? 'border-teal-500/50 bg-teal-500/5' :
                    allPassed ? 'border-border bg-card hover:border-teal-500/30' :
                    'border-amber-500/30 bg-amber-500/5 hover:border-amber-500/50'
                  }`}>
                  <div className="flex items-center gap-2 mb-2">
                    <Icon className={`w-4 h-4 ${meta.color}`} />
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{meta.label}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className={`text-lg font-bold ${allPassed ? 'text-teal-400' : 'text-amber-400'}`}>
                      {cat.passed}/{cat.total}
                    </span>
                    {allPassed ? <Check className="w-4 h-4 text-teal-500" /> : <AlertTriangle className="w-4 h-4 text-amber-400" />}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Expanded Category Checks */}
          {expandedCat && (
            <div className="bg-card border border-border rounded-xl p-5 mb-6">
              <h3 className="text-sm font-semibold text-foreground mb-3 uppercase tracking-wider">
                {CATEGORY_META[expandedCat]?.label || expandedCat} Checks
              </h3>
              <div className="space-y-2">
                {d.checks.filter(c => c.category === expandedCat).map((check, i) => (
                  <div key={i} className={`flex items-start gap-3 p-3 rounded-lg ${
                    check.passed ? 'bg-teal-500/5 border border-teal-500/10' : 'bg-red-500/5 border border-red-500/10'
                  }`}>
                    {check.passed ?
                      <Check className="w-5 h-5 text-teal-500 shrink-0 mt-0.5" /> :
                      <X className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                    }
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-foreground">{check.name}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-semibold ${
                          check.severity === 'critical' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                          check.severity === 'high' ? 'bg-orange-500/10 text-orange-400 border border-orange-500/20' :
                          'bg-muted text-muted-foreground border border-border'
                        }`}>
                          {check.severity}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">{check.detail}</p>
                      {check.fix && !check.passed && (
                        <p className="text-xs text-amber-400 mt-1">Fix: {check.fix}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* All Checks List (when no category expanded) */}
          {!expandedCat && (
            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground w-8"></th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Check</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Category</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Severity</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {d.checks.map((check, i) => (
                    <tr key={i} className={`${check.passed ? '' : 'bg-red-500/5'}`}>
                      <td className="px-4 py-2.5">
                        {check.passed ? <Check className="w-4 h-4 text-teal-500" /> : <X className="w-4 h-4 text-red-400" />}
                      </td>
                      <td className="px-4 py-2.5 font-medium text-foreground">{check.name}</td>
                      <td className="px-4 py-2.5 text-muted-foreground capitalize">{check.category.replace('_', ' ')}</td>
                      <td className="px-4 py-2.5">
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-semibold ${
                          check.severity === 'critical' ? 'bg-red-500/10 text-red-400' :
                          check.severity === 'high' ? 'bg-orange-500/10 text-orange-400' :
                          'bg-muted text-muted-foreground'
                        }`}>{check.severity}</span>
                      </td>
                      <td className="px-4 py-2.5 text-xs text-muted-foreground max-w-xs truncate">{check.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
