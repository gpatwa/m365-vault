import { clsx } from 'clsx';

const statusColors: Record<string, string> = {
  protected: 'bg-green-500/100/10 text-green-400',
  unprotected: 'bg-muted text-muted-foreground',
  active: 'bg-green-500/100/10 text-green-400',
  completed: 'bg-green-500/100/10 text-green-400',
  in_progress: 'bg-blue-500/100/10 text-blue-400',
  queued: 'bg-yellow-500/100/10 text-yellow-400',
  failed: 'bg-red-500/100/10 text-red-400',
  partial: 'bg-orange-500/100/10 text-orange-400',
  error: 'bg-red-500/100/10 text-red-400',
  paused: 'bg-yellow-500/100/10 text-yellow-400',
  expired: 'bg-muted text-muted-foreground',
  success: 'bg-green-500/100/10 text-green-400',
  onboarding: 'bg-blue-500/100/10 text-blue-400',
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span className={clsx(
      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize',
      statusColors[status] || 'bg-muted text-muted-foreground'
    )}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}
