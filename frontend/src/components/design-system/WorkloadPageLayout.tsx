/**
 * WorkloadPageLayout — shared layout for all workload pages.
 *
 * Provides consistent connected story from Dashboard → Workload:
 * - Breadcrumb navigation
 * - Hero summary bar with workload-specific stats
 * - Action banner for issues needing attention
 * - Content area for object list / detail view
 */
import { useNavigate } from 'react-router-dom';
import { RefreshCw, Loader2, type LucideIcon } from 'lucide-react';
import { getActivePlatformLabel } from '../../config/platforms';
import Breadcrumb, { type BreadcrumbItem } from './Breadcrumb';
import HeroSummaryBar, { type HeroStat } from './HeroSummaryBar';
import ActionBanner, { type ActionItem } from './ActionBanner';

interface WorkloadPageLayoutProps {
  /** Workload display name (e.g., "Exchange", "SharePoint") */
  workloadLabel: string;
  /** Workload icon component */
  workloadIcon: LucideIcon;
  /** Color for the icon */
  iconColor: string;
  /** Breadcrumb items (in addition to Dashboard and workload name) */
  extraBreadcrumbs?: BreadcrumbItem[];
  /** Hero stats for the summary bar */
  stats: {
    protected: number;
    total: number;
    lastBackup: string | null;
    totalItems: number;
    totalSize: number;
    successRate?: number;
  };
  /** Backup all handler */
  onBackupAll?: () => void;
  /** Is backup running? */
  isBackingUp?: boolean;
  /** Status message */
  statusMessage?: string;
  /** Children (main content) */
  children: React.ReactNode;
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return 'Never';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export default function WorkloadPageLayout({
  workloadLabel, workloadIcon: Icon, iconColor,
  extraBreadcrumbs = [], stats: rawStats,
  onBackupAll, isBackingUp, statusMessage,
  children,
}: WorkloadPageLayoutProps) {
  const navigate = useNavigate();
  const stats = rawStats || { total: 0, protected: 0, totalItems: 0, totalSize: 0, lastBackup: null, successRate: 0 };
  const pct = stats.total > 0 ? Math.round(stats.protected / stats.total * 100) : 0;
  const unprotected = stats.total - stats.protected;

  // Build breadcrumb
  const breadcrumbs: BreadcrumbItem[] = [
    { label: getActivePlatformLabel(), path: '/' },
    ...(extraBreadcrumbs.length > 0
      ? [{ label: workloadLabel, path: `/${workloadLabel.toLowerCase().replace(' ', '-')}` }, ...extraBreadcrumbs]
      : [{ label: workloadLabel }]
    ),
  ];

  // Build hero stats
  const heroStats: HeroStat[] = [
    {
      label: 'Protected',
      value: `${stats.protected}/${stats.total}`,
      subtitle: `${pct}% coverage`,
      color: pct === 100 ? 'green' : pct > 0 ? 'amber' : 'red',
    },
    {
      label: 'Last Backup',
      value: timeAgo(stats.lastBackup),
      subtitle: stats.lastBackup ? new Date(stats.lastBackup).toLocaleString() : 'No backups yet',
      color: stats.lastBackup ? 'green' : 'gray',
    },
    {
      label: 'Total Items',
      value: stats.totalItems.toLocaleString(),
      subtitle: formatSize(stats.totalSize),
      color: 'blue',
    },
    {
      label: 'Success Rate',
      value: `${stats.successRate ?? 100}%`,
      subtitle: stats.successRate === 100 ? 'All backups succeeded' : 'Some failures',
      color: (stats.successRate ?? 100) >= 95 ? 'green' : (stats.successRate ?? 100) >= 80 ? 'amber' : 'red',
    },
  ];

  // Build action items
  const actions: ActionItem[] = [];
  if (unprotected > 0) {
    actions.push({
      icon: 'warning',
      message: `${unprotected} ${workloadLabel} object${unprotected > 1 ? 's' : ''} not protected by any SLA policy`,
      action: { label: 'Assign SLA', onClick: () => navigate('/sla-policies') },
    });
  }
  if (!stats.lastBackup) {
    actions.push({
      icon: 'info',
      message: `No backups yet for ${workloadLabel}. Run your first backup to start protecting data.`,
      action: onBackupAll ? { label: 'Backup All', onClick: onBackupAll } : undefined,
    });
  }

  return (
    <div>
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbs} />

      {/* Page Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl bg-opacity-10 ${iconColor.replace('text-', 'bg-')}`}>
            <Icon className={`w-6 h-6 ${iconColor}`} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">{workloadLabel}</h1>
            <p className="text-xs text-gray-500">
              {stats.protected} protected • {stats.totalItems} items backed up • {formatSize(stats.totalSize)}
            </p>
          </div>
        </div>
        {onBackupAll && (
          <button
            onClick={onBackupAll}
            disabled={isBackingUp}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50 transition-colors"
          >
            {isBackingUp ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            {isBackingUp ? 'Backing up...' : 'Backup All'}
          </button>
        )}
      </div>

      {/* Status message */}
      {statusMessage && (
        <div className={`rounded-lg p-3 mb-4 text-sm ${
          statusMessage.includes('failed') || statusMessage.includes('error')
            ? 'bg-red-50 border border-red-200 text-red-700'
            : 'bg-green-50 border border-green-200 text-green-700'
        }`}>
          {statusMessage}
        </div>
      )}

      {/* Hero Stats */}
      <HeroSummaryBar stats={heroStats} />

      {/* Action Banners */}
      <ActionBanner items={actions} />


      {/* Content */}
      {children}
    </div>
  );
}
