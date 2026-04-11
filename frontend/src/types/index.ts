export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Tenant {
  id: number;
  name: string;
  ms_tenant_id: string;
  client_id: string;
  status: string;
  total_mailboxes: number;
  total_onedrives: number;
  total_sites: number;
  total_teams: number;
  total_entra_objects: number;
  last_discovery_at: string | null;
  created_at: string;
}

export interface SLAPolicy {
  id: number;
  name: string;
  description: string | null;
  backup_frequency_hours: number;
  retention_days: number;
  priority: number;
  is_locked: number;
  worm_enabled: number;
  legal_hold: number;
  is_active: number;
  created_at: string;
  protected_objects_count?: number;
}

export interface BackupDayStatus {
  date: string;
  status: 'success' | 'failed' | 'none';
}

export interface ProtectedObject {
  id: number;
  display_name: string;
  email?: string;
  site_url?: string;
  status: string;
  sla_policy_id: number | null;
  last_backup_at: string | null;
  last_backup_status: string | null;
  total_items: number;
  total_size_bytes: number;
  criticality_score?: number;
  criticality_tier?: string;
  item_count_delta?: number | null;
  validation_status?: 'passed' | 'failed' | 'partial' | null;
  backup_history_7d?: BackupDayStatus[] | null;
}

export interface Snapshot {
  id: number;
  snapshot_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  item_count: number;
  size_bytes: number;
}

export interface SnapshotItem {
  id: number;
  item_type: string;
  name: string;
  path: string | null;
  size_bytes: number;
  subject?: string;
  sender?: string;
  file_name?: string;
  mime_type?: string;
  received_at?: string;
  last_modified?: string;
  blob_path?: string;
}

export interface BackupJob {
  id: number;
  tenant_id: number;
  workload_type: string;
  sla_policy_id: number | null;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  objects_total: number;
  objects_processed: number;
  objects_failed: number;
  total_size_bytes: number;
  total_items: number;
  error_message: string | null;
  retry_count: number;
  max_retries: number;
  progress_details?: any;
}

export interface FailedJobsSummary {
  total_failed: number;
  retriable: number;
  ready_now: number;
  jobs: FailedJobInfo[];
}

export interface FailedJobInfo {
  job_id: number;
  workload_type: string;
  status: string;
  retry_count: number;
  max_retries: number;
  can_auto_retry: boolean;
  backoff_ready: boolean;
  next_retry_at: string | null;
  objects_total: number;
  objects_processed: number;
  objects_failed: number;
  failed_object_ids: number[];
  error_message: string | null;
  completed_at: string | null;
}

export interface RestoreJob {
  id: number;
  tenant_id: number;
  source_snapshot_id: number;
  source_object_id: number;
  restore_type: string;
  target_object_id: number | null;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  items_total: number;
  items_restored: number;
  items_failed: number;
  error_message: string | null;
}

export interface DashboardSummary {
  tenants: number;
  total_objects: number;
  total_protected: number;
  protection_rate: number;
  workloads: Record<string, {
    total: number;
    protected: number;
    unprotected: number;
    protection_rate: number;
  }>;
  jobs_24h: {
    backup_total: number;
    backup_successful: number;
    backup_failed: number;
    restore_total: number;
  };
  snapshots: {
    total: number;
    total_size_bytes: number;
    total_size_gb: number;
  };
  storage: {
    total_size_bytes: number;
    total_size_mb: number;
    total_files: number;
    storage_path: string;
  };
}

export interface ActivityData {
  date: string;
  backups: number;
  backups_successful: number;
  restores: number;
  data_backed_up_bytes: number;
}

export interface AuditLogEntry {
  id: number;
  user_id: number | null;
  action: string;
  resource_type: string | null;
  resource_id: number | null;
  details: string | null;
  severity: string;
  ip_address: string | null;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface FailedItemEntry {
  id: number;
  snapshot_id: number;
  protected_object_id: number;
  ms_item_id: string | null;
  item_type: string | null;
  item_name: string | null;
  item_path: string | null;
  error_category: string;
  error_message: string;
  error_code: string | null;
  http_status: number | null;
  retries_attempted: number;
  resolution_hint: string;
  is_resolved: boolean;
  resolved_at: string | null;
  resolved_by: string | null;
  can_retry: boolean;
  retry_snapshot_id: number | null;
  created_at: string | null;
}

export interface FailedItemsSummary {
  total_failed: number;
  total_unresolved: number;
  categories: FailedItemCategory[];
  by_workload?: Record<string, {
    total: number;
    unresolved: number;
    retriable: number;
    top_category: string | null;
    top_category_count: number;
  }>;
}

export interface FailedItemCategory {
  category: string;
  count: number;
  resolved: number;
  unresolved: number;
  retriable: number;
  resolution_hint: string;
}
