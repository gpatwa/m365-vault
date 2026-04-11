/**
 * BackupIndicators — Small inline visual indicators for workload object tables.
 *
 * Three subtle indicators that help admins spot anomalies at a glance:
 * 1. ItemCountDelta — colored +/- number next to total item count
 * 2. HealthDots — 7-day backup history as colored dots
 * 3. ValidationBadge — small icon for validation status
 */

import type { BackupDayStatus } from '../types';

// ── Item Count Delta ──

interface ItemCountDeltaProps {
  delta: number | null | undefined;
}

export function ItemCountDelta({ delta }: ItemCountDeltaProps) {
  if (delta == null || delta === 0) return null;

  const isPositive = delta > 0;
  return (
    <span
      className={`text-[11px] font-medium ml-1.5 ${
        isPositive ? 'text-green-500' : 'text-red-500'
      }`}
      title={`${isPositive ? 'Added' : 'Removed'} ${Math.abs(delta)} item${Math.abs(delta) !== 1 ? 's' : ''} since last backup`}
    >
      {isPositive ? '+' : ''}{delta}
    </span>
  );
}

// ── 7-Day Health Dots ──

interface HealthDotsProps {
  history: BackupDayStatus[] | null | undefined;
}

export function HealthDots({ history }: HealthDotsProps) {
  if (!history || history.length === 0) return null;

  return (
    <div className="flex gap-0.5 items-center" aria-label="7-day backup history">
      {history.map((day, i) => (
        <div
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${
            day.status === 'success' ? 'bg-green-500' :
            day.status === 'failed' ? 'bg-red-500' :
            'bg-muted-foreground/30'
          }`}
          title={`${day.date}: ${day.status}`}
        />
      ))}
    </div>
  );
}

// ── Validation Badge ──

interface ValidationBadgeProps {
  status: 'passed' | 'failed' | 'partial' | null | undefined;
}

export function ValidationBadge({ status }: ValidationBadgeProps) {
  if (!status) return null;

  switch (status) {
    case 'passed':
      return (
        <span
          className="text-green-500 text-[10px] font-medium ml-1.5"
          title="Backup integrity verified"
        >
          &#10003;
        </span>
      );
    case 'failed':
      return (
        <span
          className="text-red-500 text-[10px] font-medium ml-1.5"
          title="Validation failed"
        >
          &#10007;
        </span>
      );
    case 'partial':
      return (
        <span
          className="text-amber-500 text-[10px] font-medium ml-1.5"
          title="Partially validated"
        >
          ~
        </span>
      );
    default:
      return null;
  }
}
