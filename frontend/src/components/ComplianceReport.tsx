import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, Download, Shield, CheckCircle, Loader2, X } from 'lucide-react';
import { api } from '../api/client';
import { useBranding } from '../contexts/BrandingContext';

interface ComplianceReportProps {
  tenantId: number;
  tenantName: string;
  onClose: () => void;
}

interface ReportData {
  report_type: string;
  title: string;
  framework: string;
  generated_at: string;
  tenant: { name: string; ms_tenant_id: string; status: string };
  backup_coverage: { total_objects: number; protected_objects: number; coverage_pct: number; workloads: any[] };
  encryption: { algorithm: string; key_management: string; at_rest: string; in_transit: string };
  backup_reliability: { period: string; total_jobs: number; successful_jobs: number; success_rate: number };
  sla_policies: { name: string; frequency_hours: number; retention_days: number; worm_enabled: boolean }[];
  controls: { id: string; name: string; control: string }[];
}

const REPORT_TYPES = [
  { value: 'hipaa', label: 'HIPAA', desc: 'Healthcare' },
  { value: 'soc2', label: 'SOC 2', desc: 'Trust Services' },
  { value: 'gdpr', label: 'GDPR', desc: 'EU Data Protection' },
  { value: 'dora', label: 'DORA', desc: 'Financial Services' },
];

export default function ComplianceReport({ tenantId, tenantName, onClose }: ComplianceReportProps) {
  const [reportType, setReportType] = useState('hipaa');
  const branding = useBranding();

  const { data, isLoading } = useQuery({
    queryKey: ['compliance-report', tenantId, reportType],
    queryFn: () => api.get<ReportData>(`/msp/compliance-report/${tenantId}?report_type=${reportType}`),
  });

  const handlePrint = () => window.print();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 rounded-2xl border border-gray-700 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gray-900 border-b border-gray-700 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-blue-400" />
            <div>
              <h2 className="text-lg font-bold text-white">Compliance Report</h2>
              <p className="text-xs text-gray-400">{tenantName}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {REPORT_TYPES.map(rt => (
              <button key={rt.value} onClick={() => setReportType(rt.value)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  reportType === rt.value ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
                }`}>{rt.label}</button>
            ))}
            <button onClick={handlePrint} className="ml-2 flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-500">
              <Download className="w-3 h-3" /> Print/PDF
            </button>
            <button onClick={onClose} className="ml-1 p-1 text-gray-500 hover:text-white">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
          </div>
        ) : data ? (
          <div className="px-6 py-6 space-y-6 print:bg-white print:text-black" id="compliance-report">
            {/* Report title */}
            <div className="text-center border-b border-gray-700 pb-6 print:border-black">
              <div className="flex items-center justify-center gap-2 mb-2">
                <Shield className="w-6 h-6 text-blue-400 print:text-blue-600" />
                <span className="text-lg font-bold text-white print:text-black">{branding.companyName}</span>
              </div>
              <h1 className="text-xl font-bold text-white print:text-black">{data.title}</h1>
              <p className="text-sm text-gray-400 print:text-gray-600 mt-1">
                Tenant: {data.tenant.name} | Generated: {new Date(data.generated_at).toLocaleDateString()}
              </p>
            </div>

            {/* Backup Coverage */}
            <div>
              <h3 className="text-sm font-semibold text-gray-300 print:text-black mb-3">Backup Coverage</h3>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-gray-800 print:bg-gray-100 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-green-400 print:text-green-600">{data.backup_coverage.coverage_pct}%</div>
                  <div className="text-[10px] text-gray-500">Protected</div>
                </div>
                <div className="bg-gray-800 print:bg-gray-100 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-white print:text-black">{data.backup_coverage.protected_objects}</div>
                  <div className="text-[10px] text-gray-500">Objects</div>
                </div>
                <div className="bg-gray-800 print:bg-gray-100 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-white print:text-black">{data.backup_coverage.workloads.length}</div>
                  <div className="text-[10px] text-gray-500">Workloads</div>
                </div>
              </div>
              {data.backup_coverage.workloads.length > 0 && (
                <div className="mt-2 space-y-1">
                  {data.backup_coverage.workloads.map(wl => (
                    <div key={wl.workload} className="flex items-center justify-between text-xs px-2 py-1 bg-gray-800/50 print:bg-gray-50 rounded">
                      <span className="text-gray-300 print:text-black capitalize">{wl.workload}</span>
                      <span className="text-gray-500">{wl.protected_objects} objects | Last: {wl.last_backup ? new Date(wl.last_backup).toLocaleDateString() : 'Never'}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Encryption */}
            <div>
              <h3 className="text-sm font-semibold text-gray-300 print:text-black mb-3">Encryption Status</h3>
              <div className="space-y-2">
                {Object.entries(data.encryption).map(([key, val]) => (
                  <div key={key} className="flex items-start gap-2 text-xs">
                    <CheckCircle className="w-3.5 h-3.5 text-green-400 print:text-green-600 mt-0.5 shrink-0" />
                    <div>
                      <span className="text-gray-300 print:text-black font-medium capitalize">{key.replace(/_/g, ' ')}: </span>
                      <span className="text-gray-400 print:text-gray-600">{val}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Backup Reliability */}
            <div>
              <h3 className="text-sm font-semibold text-gray-300 print:text-black mb-3">Backup Reliability ({data.backup_reliability.period})</h3>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-gray-800 print:bg-gray-100 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-white print:text-black">{data.backup_reliability.total_jobs}</div>
                  <div className="text-[10px] text-gray-500">Total Jobs</div>
                </div>
                <div className="bg-gray-800 print:bg-gray-100 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-green-400 print:text-green-600">{data.backup_reliability.successful_jobs}</div>
                  <div className="text-[10px] text-gray-500">Successful</div>
                </div>
                <div className="bg-gray-800 print:bg-gray-100 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-white print:text-black">{data.backup_reliability.success_rate}%</div>
                  <div className="text-[10px] text-gray-500">Success Rate</div>
                </div>
              </div>
            </div>

            {/* Framework Controls */}
            <div>
              <h3 className="text-sm font-semibold text-gray-300 print:text-black mb-3">{data.framework} — Controls</h3>
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-700 print:border-gray-300">
                    <th className="text-left py-2 text-gray-400 print:text-gray-600 font-medium">ID</th>
                    <th className="text-left py-2 text-gray-400 print:text-gray-600 font-medium">Requirement</th>
                    <th className="text-left py-2 text-gray-400 print:text-gray-600 font-medium">Control</th>
                    <th className="text-center py-2 w-16">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/50 print:divide-gray-200">
                  {data.controls.map(c => (
                    <tr key={c.id}>
                      <td className="py-2 text-gray-300 print:text-black font-mono">{c.id}</td>
                      <td className="py-2 text-gray-300 print:text-black">{c.name}</td>
                      <td className="py-2 text-gray-400 print:text-gray-600">{c.control}</td>
                      <td className="py-2 text-center"><CheckCircle className="w-4 h-4 text-green-400 print:text-green-600 mx-auto" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* SLA Policies */}
            {data.sla_policies.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-300 print:text-black mb-3">Retention Policies</h3>
                <div className="space-y-1">
                  {data.sla_policies.map(p => (
                    <div key={p.name} className="flex items-center justify-between text-xs px-2 py-1.5 bg-gray-800/50 print:bg-gray-50 rounded">
                      <span className="text-gray-300 print:text-black font-medium">{p.name}</span>
                      <span className="text-gray-500">Every {p.frequency_hours}h | {p.retention_days}d retention{p.worm_enabled ? ' | WORM' : ''}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Footer */}
            <div className="text-center text-[10px] text-gray-600 print:text-gray-400 pt-4 border-t border-gray-700 print:border-gray-300">
              Generated by {branding.companyName} on {new Date(data.generated_at).toLocaleString()} | This report is provided as compliance evidence and does not constitute legal advice.
            </div>
          </div>
        ) : (
          <div className="text-center py-20 text-gray-500">Failed to load report</div>
        )}
      </div>
    </div>
  );
}
