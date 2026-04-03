import { AlertTriangle, XCircle, Info, CheckCircle, ArrowRight } from 'lucide-react';

export interface ActionItem {
  icon?: 'warning' | 'error' | 'info' | 'success';
  message: string;
  action?: { label: string; onClick: () => void };
}

const iconMap = {
  warning: { Icon: AlertTriangle, bg: 'bg-amber-500/100/10', border: 'border-amber-500/20', text: 'text-amber-400', icon: 'text-amber-400' },
  error: { Icon: XCircle, bg: 'bg-red-500/100/10', border: 'border-red-500/20', text: 'text-red-400', icon: 'text-red-400' },
  info: { Icon: Info, bg: 'bg-blue-500/100/10', border: 'border-blue-500/20', text: 'text-blue-400', icon: 'text-blue-400' },
  success: { Icon: CheckCircle, bg: 'bg-green-500/100/10', border: 'border-green-500/20', text: 'text-green-400', icon: 'text-green-400' },
};

export default function ActionBanner({ items }: { items: ActionItem[] }) {
  if (!items.length) return null;

  return (
    <div className="space-y-2 mb-6">
      {items.map((item, i) => {
        const style = iconMap[item.icon || 'info'];
        return (
          <div
            key={i}
            className={`${style.bg} border ${style.border} rounded-lg px-4 py-3 flex items-center gap-3`}
          >
            <style.Icon className={`w-4.5 h-4.5 ${style.icon} flex-shrink-0`} />
            <span className={`text-sm ${style.text} flex-1`}>{item.message}</span>
            {item.action && (
              <button
                onClick={item.action.onClick}
                className={`text-xs font-semibold ${style.text} hover:underline flex items-center gap-1`}
              >
                {item.action.label}
                <ArrowRight className="w-3 h-3" />
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
