import { useState, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Upload, CheckCircle, XCircle, AlertTriangle,
  Loader2, Trash2, Plus, Download, ArrowRight,
} from 'lucide-react';
import { api } from '../api/client';

interface TenantEntry {
  name: string;
  ms_tenant_id: string;
  client_id: string;
  client_secret: string;
  client_secret_masked?: string;
}

interface OnboardResult {
  name: string;
  ms_tenant_id: string;
  status: 'created' | 'skipped' | 'failed';
  reason?: string;
  tenant_id?: number;
}

type Step = 'upload' | 'preview' | 'executing' | 'done';

const STATUS_ICONS = {
  created: <CheckCircle className="w-4 h-4 text-green-400" />,
  skipped: <AlertTriangle className="w-4 h-4 text-amber-400" />,
  failed: <XCircle className="w-4 h-4 text-red-400" />,
};

export default function BulkOnboard() {
  const [step, setStep] = useState<Step>('upload');
  const [entries, setEntries] = useState<TenantEntry[]>([]);
  const [results, setResults] = useState<OnboardResult[]>([]);
  const [parseErrors, setParseErrors] = useState<any[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const parseMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(
        `${(window as any).__RUNTIME_CONFIG__?.API_BASE ? `${(window as any).__RUNTIME_CONFIG__.API_BASE}/api` : import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'}/msp/onboard-bulk/csv-parse`,
        { method: 'POST', body: formData, headers: { Authorization: `Bearer ${api.getToken()}` } },
      );
      if (!res.ok) throw new Error('CSV parse failed');
      return res.json();
    },
    onSuccess: (data) => {
      setEntries(data.entries || []);
      setParseErrors(data.errors || []);
      setStep('preview');
    },
  });

  const onboardMutation = useMutation({
    mutationFn: (tenants: TenantEntry[]) =>
      api.post<any>('/msp/onboard-bulk', { tenants }),
    onSuccess: (data) => {
      setResults(data.results || []);
      setStep('done');
    },
  });

  const handleFileUpload = (file: File) => {
    parseMutation.mutate(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.csv')) handleFileUpload(file);
  };

  const addManualRow = () => {
    setEntries(prev => [...prev, { name: '', ms_tenant_id: '', client_id: '', client_secret: '' }]);
    if (step === 'upload') setStep('preview');
  };

  const updateEntry = (idx: number, field: keyof TenantEntry, value: string) => {
    setEntries(prev => prev.map((e, i) => i === idx ? { ...e, [field]: value } : e));
  };

  const removeEntry = (idx: number) => {
    setEntries(prev => prev.filter((_, i) => i !== idx));
  };

  const handleExecute = () => {
    const valid = entries.filter(e => e.name && e.ms_tenant_id && e.client_id && e.client_secret);
    if (valid.length === 0) return;
    setStep('executing');
    onboardMutation.mutate(valid);
  };

  const csvTemplate = 'name,ms_tenant_id,client_id,client_secret\nContoso Corp,xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx,app-id-here,secret-here\n';

  const downloadTemplate = () => {
    const blob = new Blob([csvTemplate], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'kavachiq-bulk-onboard-template.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Bulk Tenant Onboarding</h1>
          <p className="text-sm text-muted-foreground">Onboard multiple client tenants at once</p>
        </div>
        {step === 'upload' && (
          <div className="flex items-center gap-2">
            <button onClick={downloadTemplate} className="flex items-center gap-2 px-3 py-2 bg-secondary text-muted-foreground rounded-lg text-sm hover:bg-accent transition-colors">
              <Download className="w-4 h-4" /> CSV Template
            </button>
            <button onClick={addManualRow} className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-500/100 transition-colors">
              <Plus className="w-4 h-4" /> Add Manually
            </button>
          </div>
        )}
      </div>

      {/* Step: Upload */}
      {step === 'upload' && (
        <div
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          className="border-2 border-dashed border-border rounded-xl p-12 text-center hover:border-blue-500 transition-colors cursor-pointer"
          onClick={() => fileRef.current?.click()}
        >
          <input
            ref={fileRef} type="file" accept=".csv" className="hidden"
            onChange={e => { const f = e.target.files?.[0]; if (f) handleFileUpload(f); }}
          />
          {parseMutation.isPending ? (
            <Loader2 className="w-10 h-10 text-blue-400 mx-auto animate-spin" />
          ) : (
            <>
              <Upload className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
              <p className="text-muted-foreground font-medium">Drop a CSV file here or click to upload</p>
              <p className="text-xs text-muted-foreground mt-1">Format: name, ms_tenant_id, client_id, client_secret</p>
            </>
          )}
        </div>
      )}

      {/* Step: Preview */}
      {step === 'preview' && (
        <div>
          {parseErrors.length > 0 && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-4">
              <p className="text-red-400 text-sm font-medium mb-1">{parseErrors.length} row(s) with errors:</p>
              {parseErrors.map((err, i) => (
                <p key={i} className="text-xs text-red-300">Row {err.row}: {err.error}</p>
              ))}
            </div>
          )}

          <div className="bg-card rounded-xl border border-border overflow-hidden mb-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-card/50">
                  <th className="text-left px-3 py-2 text-muted-foreground font-medium">Tenant Name</th>
                  <th className="text-left px-3 py-2 text-muted-foreground font-medium">MS Tenant ID</th>
                  <th className="text-left px-3 py-2 text-muted-foreground font-medium">Client ID</th>
                  <th className="text-left px-3 py-2 text-muted-foreground font-medium">Secret</th>
                  <th className="w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {entries.map((entry, idx) => (
                  <tr key={idx}>
                    <td className="px-3 py-1.5">
                      <input value={entry.name} onChange={e => updateEntry(idx, 'name', e.target.value)}
                        className="w-full px-2 py-1 bg-muted border border-border rounded text-foreground text-xs focus:border-ring focus:outline-none" />
                    </td>
                    <td className="px-3 py-1.5">
                      <input value={entry.ms_tenant_id} onChange={e => updateEntry(idx, 'ms_tenant_id', e.target.value)}
                        className="w-full px-2 py-1 bg-muted border border-border rounded text-foreground text-xs font-mono focus:border-ring focus:outline-none" />
                    </td>
                    <td className="px-3 py-1.5">
                      <input value={entry.client_id} onChange={e => updateEntry(idx, 'client_id', e.target.value)}
                        className="w-full px-2 py-1 bg-muted border border-border rounded text-foreground text-xs font-mono focus:border-ring focus:outline-none" />
                    </td>
                    <td className="px-3 py-1.5">
                      <input value={entry.client_secret_masked || entry.client_secret}
                        onChange={e => updateEntry(idx, 'client_secret', e.target.value)}
                        type="password"
                        className="w-full px-2 py-1 bg-muted border border-border rounded text-foreground text-xs font-mono focus:border-ring focus:outline-none" />
                    </td>
                    <td className="px-1">
                      <button onClick={() => removeEntry(idx)} className="p-1 text-muted-foreground hover:text-red-400">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button onClick={addManualRow} className="flex items-center gap-1 px-3 py-2 bg-secondary text-muted-foreground rounded-lg text-xs hover:bg-accent">
                <Plus className="w-3 h-3" /> Add Row
              </button>
              <button onClick={() => { setStep('upload'); setEntries([]); }} className="px-3 py-2 text-muted-foreground text-xs hover:text-muted-foreground">
                Start Over
              </button>
            </div>
            <button
              onClick={handleExecute}
              disabled={entries.filter(e => e.name && e.ms_tenant_id && e.client_id && e.client_secret).length === 0}
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500/100 disabled:opacity-50 transition-colors"
            >
              Onboard {entries.filter(e => e.name && e.ms_tenant_id).length} Tenant(s) <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step: Executing */}
      {step === 'executing' && (
        <div className="text-center py-16">
          <Loader2 className="w-10 h-10 text-blue-400 mx-auto animate-spin mb-4" />
          <p className="text-foreground font-medium">Onboarding {entries.length} tenant(s)...</p>
          <p className="text-xs text-muted-foreground mt-1">Encrypting credentials and creating tenant records</p>
        </div>
      )}

      {/* Step: Done */}
      {step === 'done' && (
        <div>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-green-400">{results.filter(r => r.status === 'created').length}</div>
              <div className="text-xs text-green-300">Created</div>
            </div>
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-amber-400">{results.filter(r => r.status === 'skipped').length}</div>
              <div className="text-xs text-amber-300">Skipped (duplicate)</div>
            </div>
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-red-400">{results.filter(r => r.status === 'failed').length}</div>
              <div className="text-xs text-red-300">Failed</div>
            </div>
          </div>

          <div className="bg-card rounded-xl border border-border overflow-hidden mb-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-card/50">
                  <th className="w-8"></th>
                  <th className="text-left px-3 py-2 text-muted-foreground font-medium">Tenant</th>
                  <th className="text-left px-3 py-2 text-muted-foreground font-medium">MS Tenant ID</th>
                  <th className="text-left px-3 py-2 text-muted-foreground font-medium">Status</th>
                  <th className="text-left px-3 py-2 text-muted-foreground font-medium">Detail</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {results.map((r, i) => (
                  <tr key={i}>
                    <td className="px-3 py-2">{STATUS_ICONS[r.status]}</td>
                    <td className="px-3 py-2 text-foreground">{r.name}</td>
                    <td className="px-3 py-2 text-muted-foreground font-mono text-xs">{r.ms_tenant_id}</td>
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium uppercase ${
                        r.status === 'created' ? 'bg-green-500/10 text-green-400' :
                        r.status === 'skipped' ? 'bg-amber-500/10 text-amber-400' :
                        'bg-red-500/10 text-red-400'
                      }`}>{r.status}</span>
                    </td>
                    <td className="px-3 py-2 text-xs text-muted-foreground">{r.reason || (r.tenant_id ? `ID: ${r.tenant_id}` : '')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center gap-3">
            <button onClick={() => { setStep('upload'); setEntries([]); setResults([]); }}
              className="px-4 py-2 bg-secondary text-muted-foreground rounded-lg text-sm hover:bg-accent">
              Onboard More
            </button>
            <a href="/msp" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-500/100 flex items-center gap-2">
              MSP Dashboard <ArrowRight className="w-4 h-4" />
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
