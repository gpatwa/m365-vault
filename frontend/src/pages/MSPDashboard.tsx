import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useTenantContext } from '../contexts/TenantContext';
import ComplianceReport from '../components/ComplianceReport';
import OffboardWorkflow from '../components/OffboardWorkflow';
import {
  Shield, AlertTriangle, CheckCircle, HardDrive, FileText, LogOut,
  Users, Server, Activity, ChevronRight, Search,
} from 'lucide-react';
import { api } from '../api/client';

interface TenantSummary {
  id: number;
  name: string;
  status: string;
  ms_tenant_id: string;
  protected_objects: number;
  total_objects: number;
  protection_pct: number;
  workload_count: number;
  backups_24h: number;
  failed_24h: number;
  storage_bytes: number;
  storage_gb: number;
  last_backup: string | null;
  health_score: number;
  health_status: string;
  alerts: string[];
  alert_count: number;
}

interface MSPOverview {
  summary: {
    total_tenants: number;
    active_tenants: number;
    total_protected_users: number;
    total_storage_bytes: number;
    total_storage_gb: number;
    total_alerts: number;
    overall_health: number;
  };
  tenants: TenantSummary[];
}

const HEALTH_COLORS: Record<string, string> = {
  healthy: 'text-green-400 bg-green-500/10 border-green-500/30',
  at_risk: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  critical: 'text-red-400 bg-red-500/10 border-red-500/30',
};

const HEALTH_RING: Record<string, string> = {
  healthy: 'ring-green-500/30',
  at_risk: 'ring-amber-500/30',
  critical: 'ring-red-500/30',
};

function HealthBadge({ score, status }: { score: number; status: string }) {
  return (
    <div className={`w-12 h-12 rounded-full flex items-center justify-center text-sm font-bold border-2 ring-2 ${HEALTH_COLORS[status]} ${HEALTH_RING[status]}`}>
      {score}
    </div>
  );
}

function StatCard({ icon: Icon, label, value, sub }: { icon: typeof Shield; label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-card rounded-xl p-4 border border-border">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
          <Icon className="w-5 h-5 text-blue-400" />
        </div>
        <div>
          <div className="text-2xl font-bold text-foreground">{value}</div>
          <div className="text-xs text-muted-foreground">{label}</div>
          {sub && <div className="text-[10px] text-muted-foreground">{sub}</div>}
        </div>
      </div>
    </div>
  );
}

export default function MSPDashboard() {
  const navigate = useNavigate();
  const { setTenant } = useTenantContext();
  const [search, setSearch] = useState('');
  const [complianceTenant, setComplianceTenant] = useState<{ id: number; name: string } | null>(null);
  const [offboardTenant, setOffboardTenant] = useState<{ id: number; name: string } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['msp-overview'],
    queryFn: () => api.get<MSPOverview>('/msp/overview'),
    refetchInterval: 30000,
  });

  const summary = data?.summary;
  const tenants = data?.tenants || [];
  const filtered = search
    ? tenants.filter(t => t.name.toLowerCase().includes(search.toLowerCase()))
    : tenants;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-muted-foreground animate-pulse">Loading MSP dashboard...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">MSP Dashboard</h1>
          <p className="text-sm text-muted-foreground">All client tenants at a glance</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search tenants..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-9 pr-4 py-2 bg-card border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-ring w-64"
            />
          </div>
        </div>
      </div>

      {/* Summary stats */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <StatCard icon={Server} label="Total Tenants" value={summary.total_tenants} sub={`${summary.active_tenants} active`} />
          <StatCard icon={Users} label="Protected Users" value={summary.total_protected_users} />
          <StatCard icon={HardDrive} label="Total Storage" value={`${summary.total_storage_gb} GB`} />
          <StatCard icon={Activity} label="Overall Health" value={summary.overall_health} sub={summary.overall_health >= 80 ? 'Healthy' : summary.overall_health >= 50 ? 'At Risk' : 'Critical'} />
          <StatCard icon={AlertTriangle} label="Active Alerts" value={summary.total_alerts} sub={summary.total_alerts === 0 ? 'All clear' : 'Needs attention'} />
        </div>
      )}

      {/* Tenant cards */}
      <div className="space-y-3">
        {filtered.map(tenant => (
          <button
            key={tenant.id}
            onClick={() => { setTenant(tenant.id, tenant.name); navigate('/'); }}
            className="w-full bg-card rounded-xl p-4 border border-border hover:border-border transition-all text-left flex items-center gap-4 group"
          >
            {/* Health score */}
            <HealthBadge score={tenant.health_score} status={tenant.health_status} />

            {/* Tenant info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground text-sm">{tenant.name}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                  tenant.status === 'active' ? 'bg-green-500/10 text-green-400' : 'bg-gray-600 text-muted-foreground'
                }`}>
                  {tenant.status}
                </span>
              </div>
              <div className="text-xs text-muted-foreground mt-0.5 truncate">{tenant.ms_tenant_id}</div>
            </div>

            {/* Metrics */}
            <div className="hidden md:flex items-center gap-6 text-center">
              <div>
                <div className="text-sm font-semibold text-foreground">{tenant.protection_pct}%</div>
                <div className="text-[10px] text-muted-foreground">Protected</div>
              </div>
              <div>
                <div className="text-sm font-semibold text-foreground">{tenant.protected_objects}/{tenant.total_objects}</div>
                <div className="text-[10px] text-muted-foreground">Objects</div>
              </div>
              <div>
                <div className="text-sm font-semibold text-foreground">{tenant.workload_count}</div>
                <div className="text-[10px] text-muted-foreground">Workloads</div>
              </div>
              <div>
                <div className={`text-sm font-semibold ${tenant.failed_24h > 0 ? 'text-red-400' : 'text-foreground'}`}>
                  {tenant.backups_24h}
                </div>
                <div className="text-[10px] text-muted-foreground">Backups 24h</div>
              </div>
              <div>
                <div className="text-sm font-semibold text-foreground">{tenant.storage_gb} GB</div>
                <div className="text-[10px] text-muted-foreground">Storage</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">
                  {tenant.last_backup ? new Date(tenant.last_backup).toLocaleDateString() : 'Never'}
                </div>
                <div className="text-[10px] text-muted-foreground">Last Backup</div>
              </div>
            </div>

            {/* Alerts */}
            <div className="flex items-center gap-2">
              {tenant.alert_count > 0 ? (
                <div className="flex items-center gap-1 px-2 py-1 bg-red-500/10 rounded-lg">
                  <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
                  <span className="text-xs text-red-400 font-medium">{tenant.alert_count}</span>
                </div>
              ) : (
                <div className="flex items-center gap-1 px-2 py-1 bg-green-500/10 rounded-lg">
                  <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                  <span className="text-xs text-green-400 font-medium">OK</span>
                </div>
              )}
              <button
                onClick={(e) => { e.stopPropagation(); setComplianceTenant({ id: tenant.id, name: tenant.name }); }}
                className="p-1.5 bg-secondary rounded-lg hover:bg-blue-600 transition-colors"
                title="Compliance Report"
              >
                <FileText className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground" />
              </button>
              {tenant.status === 'active' && (
                <button
                  onClick={(e) => { e.stopPropagation(); setOffboardTenant({ id: tenant.id, name: tenant.name }); }}
                  className="p-1.5 bg-secondary rounded-lg hover:bg-red-600 transition-colors"
                  title="Offboard Tenant"
                >
                  <LogOut className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground" />
                </button>
              )}
              <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-muted-foreground transition-colors" />
            </div>
          </button>
        ))}

        {filtered.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            {search ? `No tenants matching "${search}"` : 'No tenants found'}
          </div>
        )}
      </div>

      {/* Offboard Workflow Modal */}
      {offboardTenant && (
        <OffboardWorkflow
          tenantId={offboardTenant.id}
          tenantName={offboardTenant.name}
          onClose={() => setOffboardTenant(null)}
          onComplete={() => { setOffboardTenant(null); /* refetch overview */ }}
        />
      )}

      {/* Compliance Report Modal */}
      {complianceTenant && (
        <ComplianceReport
          tenantId={complianceTenant.id}
          tenantName={complianceTenant.name}
          onClose={() => setComplianceTenant(null)}
        />
      )}
    </div>
  );
}
