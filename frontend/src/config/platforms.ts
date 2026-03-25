/**
 * Platform configuration — defines SaaS platforms and their workloads.
 *
 * Each platform groups related workloads. When adding a new SaaS platform:
 * 1. Add platform entry here
 * 2. Add workloads to workloads.ts with matching `platform` key
 * 3. Backend: add new WorkloadType enums + workers
 * 4. Everything else (Dashboard, Jobs, nav, breadcrumbs) picks it up automatically
 */
import { Mail, Globe, type LucideIcon } from 'lucide-react';

export interface PlatformConfig {
  key: string;
  label: string;
  description: string;
  icon: LucideIcon;
  /** SVG icon for platform logo (rendered inline) */
  logoSvg?: string;
  color: string;
  bgColor: string;
  borderColor: string;
  iconColor: string;
  /** Workload keys that belong to this platform */
  workloads: string[];
  /** Whether this platform is available (GA) or coming soon */
  status: 'available' | 'coming_soon';
}

export const PLATFORMS: PlatformConfig[] = [
  {
    key: 'microsoft365',
    label: 'Microsoft 365',
    description: 'Exchange, OneDrive, SharePoint, Teams, Entra ID',
    icon: Globe,
    color: 'blue',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    iconColor: 'text-blue-600',
    workloads: ['exchange', 'onedrive', 'sharepoint', 'teams', 'entra_id'],
    status: 'available',
  },
  {
    key: 'google_workspace',
    label: 'Google Workspace',
    description: 'Gmail, Drive, Calendar, Chat, Admin',
    icon: Mail,
    color: 'red',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    iconColor: 'text-red-600',
    workloads: ['gmail', 'drive', 'calendar', 'chat', 'admin'],
    status: 'coming_soon',
  },
  {
    key: 'salesforce',
    label: 'Salesforce',
    description: 'Accounts, Opportunities, Cases, Reports',
    icon: Globe,
    color: 'sky',
    bgColor: 'bg-sky-50',
    borderColor: 'border-sky-200',
    iconColor: 'text-sky-600',
    workloads: ['accounts', 'opportunities', 'cases', 'reports_sf'],
    status: 'coming_soon',
  },
];

/** Quick lookup by platform key */
export const PLATFORM_MAP = Object.fromEntries(
  PLATFORMS.map(p => [p.key, p])
) as Record<string, PlatformConfig>;

/** Get platform for a given workload key */
export function getPlatformForWorkload(workloadKey: string): PlatformConfig | undefined {
  return PLATFORMS.find(p => p.workloads.includes(workloadKey));
}

/** Get the current active platform label (for breadcrumbs etc.) */
export function getActivePlatformLabel(): string {
  // For now, only M365 is available. When multi-platform:
  // derive from tenant data or show "All Platforms"
  const available = PLATFORMS.filter(p => p.status === 'available');
  if (available.length === 1) return available[0].label;
  return 'All Platforms';
}

/** Available platform keys */
export const AVAILABLE_PLATFORMS = PLATFORMS.filter(p => p.status === 'available');

/** Coming soon platforms */
export const COMING_SOON_PLATFORMS = PLATFORMS.filter(p => p.status === 'coming_soon');
