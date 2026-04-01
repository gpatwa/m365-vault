import { CheckCircle, XCircle, AlertTriangle, Loader2, Clock } from 'lucide-react';

export interface ActivityItem {
  id: string | number;
  type: 'success' | 'failure' | 'warning' | 'running' | 'queued';
  workload: string;
  message: string;
  time: string;
  action?: { label: string; onClick: () => void };
}

const typeConfig = {
  success: { Icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50' },
  failure: { Icon: XCircle, color: 'text-red-500', bg: 'bg-red-50' },
  warning: { Icon: AlertTriangle, color: 'text-amber-500', bg: 'bg-amber-50' },
  running: { Icon: Loader2, color: 'text-blue-500', bg: 'bg-blue-50', animate: true },
  queued: { Icon: Clock, color: 'text-muted-foreground', bg: 'bg-muted/50' },
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function ActivityFeed({ items, maxItems = 8 }: { items: ActivityItem[]; maxItems?: number }) {
  return (
    <div className="bg-card border border-border rounded-xl shadow-sm">
      <div className="px-4 py-3 border-b border-border">
        <h3 className="text-sm font-semibold text-foreground">Recent Activity</h3>
      </div>
      <div className="divide-y divide-border/50">
        {items.slice(0, maxItems).map(item => {
          const config = typeConfig[item.type];
          const Icon = config.Icon;
          return (
            <div key={item.id} className="px-4 py-2.5 flex items-center gap-3 hover:bg-muted/50 transition-colors">
              <div className={`p-1 rounded-full ${config.bg}`}>
                <Icon className={`w-3.5 h-3.5 ${config.color} ${(config as any).animate ? 'animate-spin' : ''}`} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-foreground truncate">{item.message}</p>
                <p className="text-[10px] text-muted-foreground">{item.workload} • {timeAgo(item.time)}</p>
              </div>
              {item.action && (
                <button
                  onClick={item.action.onClick}
                  className="text-[10px] font-semibold text-blue-600 hover:text-blue-800 whitespace-nowrap"
                >
                  {item.action.label}
                </button>
              )}
            </div>
          );
        })}
        {items.length === 0 && (
          <div className="px-4 py-8 text-center text-xs text-muted-foreground">
            No recent activity
          </div>
        )}
      </div>
    </div>
  );
}
