import { type LucideIcon } from 'lucide-react';

export interface HeroStat {
  label: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  color?: 'green' | 'blue' | 'amber' | 'red' | 'gray' | 'purple';
  onClick?: () => void;
  trend?: { direction: 'up' | 'down' | 'flat'; label: string };
}

const colorMap = {
  green: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200', icon: 'text-green-500' },
  blue: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', icon: 'text-blue-500' },
  amber: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', icon: 'text-amber-500' },
  red: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', icon: 'text-red-500' },
  gray: { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200', icon: 'text-gray-500' },
  purple: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', icon: 'text-purple-500' },
};

const trendIcons = { up: '↑', down: '↓', flat: '→' };
const trendColors = { up: 'text-green-600', down: 'text-red-600', flat: 'text-gray-500' };

export default function HeroSummaryBar({ stats, className = '' }: { stats: HeroStat[]; className?: string }) {
  return (
    <div className={`grid grid-cols-2 md:grid-cols-${Math.min(stats.length, 4)} gap-3 mb-6 ${className}`}>
      {stats.map((stat, i) => {
        const c = colorMap[stat.color || 'gray'];
        const Icon = stat.icon;
        return (
          <div
            key={i}
            onClick={stat.onClick}
            className={`${c.bg} border ${c.border} rounded-xl p-4 ${
              stat.onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''
            }`}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{stat.label}</p>
                <p className={`text-2xl font-bold mt-1 ${c.text}`}>{stat.value}</p>
                {stat.subtitle && (
                  <p className="text-xs text-gray-500 mt-0.5">{stat.subtitle}</p>
                )}
                {stat.trend && (
                  <p className={`text-xs mt-1 font-medium ${trendColors[stat.trend.direction]}`}>
                    {trendIcons[stat.trend.direction]} {stat.trend.label}
                  </p>
                )}
              </div>
              {Icon && (
                <div className={`p-2 rounded-lg ${c.bg}`}>
                  <Icon className={`w-5 h-5 ${c.icon}`} />
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
