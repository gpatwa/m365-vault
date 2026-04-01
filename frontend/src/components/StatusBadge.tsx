import { clsx } from 'clsx';

const statusColors: Record<string, string> = {
  protected: 'bg-green-500/15 text-green-800',
  unprotected: 'bg-gray-100 text-gray-800',
  active: 'bg-green-500/15 text-green-800',
  completed: 'bg-green-500/15 text-green-800',
  in_progress: 'bg-blue-500/15 text-blue-800',
  queued: 'bg-yellow-100 text-yellow-800',
  failed: 'bg-red-500/15 text-red-800',
  partial: 'bg-orange-100 text-orange-800',
  error: 'bg-red-500/15 text-red-800',
  paused: 'bg-yellow-100 text-yellow-800',
  expired: 'bg-gray-100 text-gray-500',
  success: 'bg-green-500/15 text-green-800',
  onboarding: 'bg-blue-500/15 text-blue-800',
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span className={clsx(
      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize',
      statusColors[status] || 'bg-gray-100 text-gray-800'
    )}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}
