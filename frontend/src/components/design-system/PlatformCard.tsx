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
  if (total === 0) return { bg: 'bg-gray-100', text: 'text-gray-500', label: '—' };
  if (protected_ === total) return { bg: 'bg-green-500/15', text: 'text-green-400', label: '✅' };
  if (protected_ === 0) return { bg: 'bg-red-500/15', text: 'text-red-400', label: '❌' };
  return { bg: 'bg-amber-500/15', text: 'text-amber-400', label: '⚠' };
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
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center gap-4 hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex-shrink-0">{icon}</div>
        <div className="flex-1 text-left">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-gray-900">{name}</h3>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${status.bg} ${status.text}`}>
              {totalProtected}/{totalObjects}
            </span>
          </div>
          <p className="text-xs text-gray-500">{workloads.length} workloads • {pct}% protected</p>
        </div>

        {/* Health score pill */}
        <div className={`px-3 py-1.5 rounded-lg text-sm font-bold ${
          healthScore >= 80 ? 'bg-green-500/15 text-green-400' :
          healthScore >= 50 ? 'bg-amber-500/15 text-amber-400' :
          'bg-red-500/15 text-red-400'
        }`}>
          {healthScore}
        </div>

        {/* Protection bar */}
        <div className="w-24 h-2 bg-gray-100 rounded-full overflow-hidden hidden sm:block">
          <div
            className={`h-full rounded-full transition-all ${
              pct === 100 ? 'bg-green-500' : pct > 0 ? 'bg-amber-500' : 'bg-red-400'
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>

        {expanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
      </button>

      {/* Expanded: workload grid */}
      {expanded && (
        <div className="px-5 pb-4 border-t border-gray-700">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mt-3">
            {workloads.map(wl => {
              const wlStatus = getStatusColor(wl.protected, wl.total);
              const Icon = wl.icon;
              return (
                <button
                  key={wl.key}
                  onClick={() => navigate(wl.path)}
                  className="bg-gray-800/50 hover:bg-white border border-gray-700 hover:border-gray-200 rounded-lg p-3 text-left transition-all hover:shadow-sm group"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Icon className={`w-4 h-4 ${wl.iconColor}`} />
                    <span className="text-xs font-semibold text-gray-700">{wl.label}</span>
                    <span className={`text-[9px] px-1 rounded ${wlStatus.bg} ${wlStatus.text} font-bold ml-auto`}>
                      {wl.protected}/{wl.total}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-gray-400">{timeAgo(wl.lastBackup)}</span>
                    <span className="text-[10px] text-gray-400">{wl.itemCount} items</span>
                  </div>
                  {/* Mini progress bar */}
                  <div className="w-full h-1 bg-gray-200 rounded-full mt-2 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        wl.protected === wl.total ? 'bg-green-400' :
                        wl.protected > 0 ? 'bg-amber-400' : 'bg-red-400'
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
