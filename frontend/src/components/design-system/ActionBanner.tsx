import { AlertTriangle, XCircle, Info, CheckCircle, ArrowRight } from 'lucide-react';

export interface ActionItem {
  icon?: 'warning' | 'error' | 'info' | 'success';
  message: string;
  action?: { label: string; onClick: () => void };
}

const iconMap = {
  warning: { Icon: AlertTriangle, bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', icon: 'text-amber-500' },
  error: { Icon: XCircle, bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', icon: 'text-red-500' },
  info: { Icon: Info, bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', icon: 'text-blue-500' },
  success: { Icon: CheckCircle, bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', icon: 'text-green-500' },
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
