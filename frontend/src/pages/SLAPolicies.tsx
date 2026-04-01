import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Shield, Plus, Pencil, Trash2, Lock, Clock, Calendar, Link } from 'lucide-react';
import { api } from '../api/client';
import { useTenantId } from '../hooks/useTenant';
import { WORKLOADS, WORKLOAD_KEYS } from '../config/workloads';
import type { SLAPolicy } from '../types';

export default function SLAPolicies() {
  const tenantId = useTenantId();
  const [showForm, setShowForm] = useState(false);
  const [editPolicy, setEditPolicy] = useState<SLAPolicy | null>(null);
  const [showAssign, setShowAssign] = useState<SLAPolicy | null>(null);
  const [assignMsg, setAssignMsg] = useState('');
  const [form, setForm] = useState({ name: '', description: '', backup_frequency_hours: 24, retention_days: 30, priority: 5, is_locked: false, worm_enabled: false, legal_hold: false });
  const qc = useQueryClient();

  const { data: policies, isLoading } = useQuery({
    queryKey: ['sla-policies'],
    queryFn: () => api.get<SLAPolicy[]>('/sla-policies/'),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/sla-policies/', data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sla-policies'] }); setShowForm(false); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => api.put(`/sla-policies/${id}`, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sla-policies'] }); setEditPolicy(null); setShowForm(false); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.del(`/sla-policies/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sla-policies'] }),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editPolicy) {
      updateMutation.mutate({ id: editPolicy.id, data: form });
    } else {
      createMutation.mutate(form);
    }
  };

  const openEdit = (p: SLAPolicy) => {
    setEditPolicy(p);
    setForm({ name: p.name, description: p.description || '', backup_frequency_hours: p.backup_frequency_hours, retention_days: p.retention_days, priority: p.priority, is_locked: !!p.is_locked, worm_enabled: !!(p as any).worm_enabled, legal_hold: !!(p as any).legal_hold });
    setShowForm(true);
  };

  const openNew = () => {
    setEditPolicy(null);
    setForm({ name: '', description: '', backup_frequency_hours: 24, retention_days: 30, priority: 5, is_locked: false, worm_enabled: false, legal_hold: false });
    setShowForm(true);
  };

  const handleAssign = async (workloadType: string) => {
    if (!showAssign) return;
    try {
      const result: any = await api.post('/sla-policies/assign', {
        sla_policy_id: showAssign.id,
        tenant_id: tenantId,
        workload_type: workloadType,
        assignment_type: 'application',
      });
      setAssignMsg(`Assigned to ${result.objects_updated} ${workloadType} objects`);
      qc.invalidateQueries({ queryKey: ['sla-policies'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      setTimeout(() => { setShowAssign(null); setAssignMsg(''); }, 2000);
    } catch (err: any) {
      setAssignMsg(`Failed: ${err.message}`);
    }
  };

  const handleAssignAll = async () => {
    if (!showAssign) return;
    try {
      const results: any[] = await Promise.all(
        WORKLOAD_KEYS.map(wt =>
          api.post('/sla-policies/assign', { sla_policy_id: showAssign.id, tenant_id: tenantId, workload_type: wt, assignment_type: 'application' })
        )
      );
      const total = results.reduce((sum, r) => sum + (r.objects_updated || 0), 0);
      setAssignMsg(`Assigned to ${total} objects across all workloads!`);
      qc.invalidateQueries({ queryKey: ['sla-policies'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      setTimeout(() => { setShowAssign(null); setAssignMsg(''); }, 2000);
    } catch (err: any) {
      setAssignMsg(`Failed: ${err.message}`);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">SLA Policies</h1>
          <p className="text-muted-foreground">Define backup frequency and retention policies</p>
        </div>
        <button onClick={openNew} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2">
          <Plus className="w-4 h-4" /> New Policy
        </button>
      </div>

      {showForm && (
        <div className="bg-card rounded-xl border shadow-sm p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">{editPolicy ? 'Edit Policy' : 'Create New SLA Policy'}</h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-foreground/80 mb-1">Name</label>
              <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground/80 mb-1">Priority (1=highest)</label>
              <input type="number" value={form.priority} onChange={e => setForm({ ...form, priority: +e.target.value })} min={1} max={10}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground/80 mb-1">Backup Frequency (hours)</label>
              <input type="number" value={form.backup_frequency_hours} onChange={e => setForm({ ...form, backup_frequency_hours: +e.target.value })} min={1}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground/80 mb-1">Retention (days)</label>
              <input type="number" value={form.retention_days} onChange={e => setForm({ ...form, retention_days: +e.target.value })} min={1}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-ring" />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-foreground/80 mb-1">Description</label>
              <input type="text" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-ring" />
            </div>
            <div className="col-span-2 flex items-center gap-6">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.is_locked} onChange={e => setForm({ ...form, is_locked: e.target.checked })} className="rounded" />
                <Lock className="w-4 h-4" /> Retention Lock
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.worm_enabled} onChange={e => setForm({ ...form, worm_enabled: e.target.checked })} className="rounded" />
                <Shield className="w-4 h-4 text-orange-500" /> WORM (Immutable)
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.legal_hold} onChange={e => setForm({ ...form, legal_hold: e.target.checked })} className="rounded" />
                <Lock className="w-4 h-4 text-red-500" /> Legal Hold
              </label>
            </div>
            <div className="col-span-2 flex gap-3">
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
                {editPolicy ? 'Update' : 'Create'} Policy
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-muted text-foreground/80 rounded-lg text-sm font-medium hover:bg-accent">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Assign panel */}
      {showAssign && (
        <div className="bg-card rounded-xl border-2 border-blue-300 shadow-sm p-6 mb-6">
          <h3 className="text-lg font-semibold mb-2">Assign "{showAssign.name}" to Workloads</h3>
          <p className="text-muted-foreground text-sm mb-4">Choose which workloads to protect with this SLA policy</p>
          {assignMsg && (
            <div className="bg-green-50 border border-green-200 text-green-700 rounded-lg p-3 mb-4 text-sm">{assignMsg}</div>
          )}
          <div className={`grid grid-cols-2 md:grid-cols-${WORKLOADS.length + 1} gap-3`}>
            {WORKLOADS.map(w => {
              const Icon = w.icon;
              return (
                <button key={w.key} onClick={() => handleAssign(w.key)}
                  className={`flex items-center gap-2 px-4 py-3 ${w.bgColor} hover:opacity-80 border ${w.borderColor} rounded-lg text-sm font-medium ${w.textColor}`}>
                  <Icon className="w-5 h-5" /> {w.label}
                </button>
              );
            })}
            <button onClick={handleAssignAll}
              className="flex items-center gap-2 px-4 py-3 bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-lg text-sm font-medium text-orange-700">
              <Shield className="w-5 h-5" /> All Workloads
            </button>
          </div>
          <button onClick={() => { setShowAssign(null); setAssignMsg(''); }} className="mt-3 text-sm text-muted-foreground hover:underline">Cancel</button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {policies?.map(p => (
          <div key={p.id} className="bg-card rounded-xl border shadow-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-blue-500" />
                <h3 className="font-semibold">{p.name}</h3>
                {p.is_locked ? <Lock className="w-4 h-4 text-orange-500" /> : null}
                {(p as any).worm_enabled ? <span className="px-1.5 py-0.5 bg-orange-100 text-orange-700 text-[10px] font-bold rounded" title="WORM: Write-Once Read-Many">WORM</span> : null}
                {(p as any).legal_hold ? <span className="px-1.5 py-0.5 bg-red-100 text-red-700 text-[10px] font-bold rounded" title="Legal Hold: Cannot delete">HOLD</span> : null}
              </div>
              <div className="flex gap-1">
                <button onClick={() => setShowAssign(p)} title="Assign to workloads" className="p-1.5 text-muted-foreground hover:text-green-600 rounded"><Link className="w-4 h-4" /></button>
                <button onClick={() => openEdit(p)} className="p-1.5 text-muted-foreground hover:text-blue-600 rounded"><Pencil className="w-4 h-4" /></button>
                <button onClick={() => { if (confirm('Delete this policy?')) deleteMutation.mutate(p.id); }} className="p-1.5 text-muted-foreground hover:text-red-600 rounded"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
            {p.description && <p className="text-sm text-muted-foreground mb-3">{p.description}</p>}
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Clock className="w-4 h-4" />
                Every <strong>{p.backup_frequency_hours}h</strong>
              </div>
              <div className="flex items-center gap-2 text-muted-foreground">
                <Calendar className="w-4 h-4" />
                Retain <strong>{p.retention_days} days</strong>
              </div>
              <div className="text-muted-foreground">
                Priority: {p.priority} &middot; {p.protected_objects_count || 0} objects assigned
              </div>
            </div>
            <button onClick={() => setShowAssign(p)}
              className="mt-3 w-full px-3 py-2 bg-muted/50 hover:bg-muted border rounded-lg text-sm text-muted-foreground font-medium flex items-center justify-center gap-2">
              <Link className="w-4 h-4" /> Assign to Workloads
            </button>
          </div>
        ))}
        {isLoading && <p className="text-muted-foreground">Loading...</p>}
        {!isLoading && !policies?.length && <p className="text-muted-foreground col-span-3 text-center py-8">No SLA policies defined yet. Create one to get started.</p>}
      </div>
    </div>
  );
}
