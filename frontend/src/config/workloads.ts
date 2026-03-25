/**
 * Central workload configuration — single source of truth.
 *
 * When adding a new workload:
 * 1. Add enum value to backend WorkloadType (backend/app/models/protected_object.py)
 * 2. Add entry here
 * 3. Everything else (Jobs swimlanes, SLA assign, Dashboard, nav) picks it up automatically
 */
import { Mail, HardDrive, Globe, KeyRound, MessageSquare, type LucideIcon } from 'lucide-react';

export interface WorkloadConfig {
  key: string;
  label: string;
  description: string;
  platform: string;    // Platform key (microsoft365, google_workspace, salesforce)
  icon: LucideIcon;
  color: string;       // Tailwind color name (blue, purple, green, amber)
  bgColor: string;     // bg-{color}-50
  borderColor: string; // border-{color}-200
  textColor: string;   // text-{color}-700
  barColor: string;    // bg-{color}-500
  ringColor: string;   // ring-{color}-400
  iconColor: string;   // text-{color}-600
}

export const WORKLOADS: WorkloadConfig[] = [
  {
    key: 'exchange',
    label: 'Exchange',
    description: 'Mailboxes, calendars, contacts',
    platform: 'microsoft365',
    icon: Mail,
    color: 'blue',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-700',
    barColor: 'bg-blue-500',
    ringColor: 'ring-blue-400',
    iconColor: 'text-blue-600',
  },
  {
    key: 'onedrive',
    label: 'OneDrive',
    description: 'Files and folders',
    platform: 'microsoft365',
    icon: HardDrive,
    color: 'purple',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    textColor: 'text-purple-700',
    barColor: 'bg-purple-500',
    ringColor: 'ring-purple-400',
    iconColor: 'text-purple-600',
  },
  {
    key: 'sharepoint',
    label: 'SharePoint',
    description: 'Sites, lists, documents',
    platform: 'microsoft365',
    icon: Globe,
    color: 'green',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    textColor: 'text-green-700',
    barColor: 'bg-green-500',
    ringColor: 'ring-green-400',
    iconColor: 'text-green-600',
  },
  {
    key: 'teams',
    label: 'Teams',
    description: 'Channels, messages, files',
    platform: 'microsoft365',
    icon: MessageSquare,
    color: 'pink',
    bgColor: 'bg-pink-50',
    borderColor: 'border-pink-200',
    textColor: 'text-pink-700',
    barColor: 'bg-pink-500',
    ringColor: 'ring-pink-400',
    iconColor: 'text-pink-600',
  },
  {
    key: 'entra_id',
    label: 'Entra ID',
    description: 'Users, groups, policies',
    platform: 'microsoft365',
    icon: KeyRound,
    color: 'amber',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    textColor: 'text-amber-700',
    barColor: 'bg-amber-500',
    ringColor: 'ring-amber-400',
    iconColor: 'text-amber-600',
  },
];

/** Workload keys as union type */
export type WorkloadKey = typeof WORKLOADS[number]['key'];

/** Quick lookup by key */
export const WORKLOAD_MAP = Object.fromEntries(
  WORKLOADS.map(w => [w.key, w])
) as Record<string, WorkloadConfig>;

/** Just the keys array */
export const WORKLOAD_KEYS = WORKLOADS.map(w => w.key);
