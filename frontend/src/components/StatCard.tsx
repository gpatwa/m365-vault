import { type LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  color?: string;
}

const colorMap: Record<string, string> = {
  blue: 'bg-blue-500/10 text-blue-400',
  green: 'bg-green-500/10 text-green-400',
  red: 'bg-red-500/10 text-red-400',
  yellow: 'bg-yellow-500/10 text-yellow-400',
  purple: 'bg-purple-500/10 text-purple-400',
  indigo: 'bg-indigo-500/10 text-indigo-400',
  amber: 'bg-amber-500/10 text-amber-400',
};

export default function StatCard({ title, value, subtitle, icon: Icon, color = 'blue' }: StatCardProps) {
  return (
    <div className="bg-card rounded-xl border border-border p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground font-medium">{title}</p>
          <p className="text-2xl font-bold mt-1 text-foreground">{value}</p>
          {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-lg ${colorMap[color] || colorMap.blue}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}
