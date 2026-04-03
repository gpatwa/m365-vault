import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronRight, type LucideIcon } from 'lucide-react';

export interface WorkloadStat {
  key: string;
  label: string;
  icon: LucideIcon;
  iconColor: string;
  protected: number;
  total: number;
  lastBackup: string | null;
  itemCount: number;
  path: string;
}

interface PlatformCardProps {
  name: string;
  icon: React.ReactNode;
  totalProtected: number;
  totalObjects: number;
  healthScore: number;
  workloads: WorkloadStat[];
  defaultExpanded?: boolean;
}

function getStatusColor(protected_: number, total: number) {
  if (total === 0) return { bg: 'bg-muted', text: 'text-muted-foreground', label: '—' };
  if (protected_ === total) return { bg: 'bg-green-500/10', text: 'text-green-400', label: '✅' };
  if (protected_ === 0) return { bg: 'bg-red-500/10', text: 'text-red-400', label: '❌' };
  return { bg: 'bg-amber-500/10', text: 'text-amber-400', label: '⚠' };
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return 'never';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function PlatformCard({
  name, icon, totalProtected, totalObjects, healthScore, workloads, defaultExpanded = false
}: PlatformCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const navigate = useNavigate();
  const pct = totalObjects > 0 ? Math.round(totalProtected / totalObjects * 100) : 0;
  const status = getStatusColor(totalProtected, totalObjects);

  return (
    <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center gap-4 hover:bg-muted/50 transition-colors"
      >
        <div className="flex-shrink-0">{icon}</div>
        <div className="flex-1 text-left">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-foreground">{name}</h3>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${status.bg} ${status.text}`}>
              {totalProtected}/{totalObjects}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">{workloads.length} workloads • {pct}% protected</p>
        </div>

        {/* Health score pill */}
        <div className={`px-3 py-1.5 rounded-lg text-sm font-bold ${
          healthScore >= 80 ? 'bg-green-500/10 text-green-400' :
          healthScore >= 50 ? 'bg-amber-500/10 text-amber-400' :
          'bg-red-500/10 text-red-400'
        }`}>
          {healthScore}
        </div>

        {/* Protection bar */}
        <div className="w-24 h-2 bg-muted rounded-full overflow-hidden hidden sm:block">
          <div
            className={`h-full rounded-full transition-all ${
              pct === 100 ? 'bg-green-500/100' : pct > 0 ? 'bg-amber-500/100' : 'bg-red-400'
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>

        {expanded ? <ChevronDown className="w-4 h-4 text-muted-foreground" /> : <ChevronRight className="w-4 h-4 text-muted-foreground" />}
      </button>

      {/* Expanded: workload grid */}
      {expanded && (
        <div className="px-5 pb-4 border-t border-border">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mt-3">
            {workloads.map(wl => {
              const wlStatus = getStatusColor(wl.protected, wl.total);
              const Icon = wl.icon;
              return (
                <button
                  key={wl.key}
                  onClick={() => navigate(wl.path)}
                  className="bg-muted hover:bg-card border border-border hover:border-border rounded-lg p-3 text-left transition-all hover:shadow-sm group"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Icon className={`w-4 h-4 ${wl.iconColor}`} />
                    <span className="text-xs font-semibold text-muted-foreground">{wl.label}</span>
                    <span className={`text-[9px] px-1 rounded ${wlStatus.bg} ${wlStatus.text} font-bold ml-auto`}>
                      {wl.protected}/{wl.total}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">{timeAgo(wl.lastBackup)}</span>
                    <span className="text-[10px] text-muted-foreground">{wl.itemCount} items</span>
                  </div>
                  {/* Mini progress bar */}
                  <div className="w-full h-1 bg-background rounded-full mt-2 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        wl.protected === wl.total ? 'bg-green-400' :
                        wl.protected > 0 ? 'bg-amber-400' : 'bg-red-300'
                      }`}
                      style={{ width: `${wl.total > 0 ? (wl.protected / wl.total * 100) : 0}%` }}
                    />
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
