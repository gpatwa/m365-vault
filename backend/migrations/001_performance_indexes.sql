-- Performance Indexes for Scale
-- Run against PostgreSQL after schema creation
-- Handles up to 500K+ protected objects, millions of snapshot items

-- Enable trigram extension for text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Backup Jobs
CREATE INDEX IF NOT EXISTS ix_backup_jobs_tenant_workload ON backup_jobs(tenant_id, workload_type);
CREATE INDEX IF NOT EXISTS ix_backup_jobs_tenant_status ON backup_jobs(tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_backup_jobs_completed_at ON backup_jobs(completed_at DESC);
CREATE INDEX IF NOT EXISTS ix_backup_jobs_created_at ON backup_jobs(created_at DESC);

-- Protected Objects
CREATE INDEX IF NOT EXISTS ix_protected_objects_tenant_workload ON protected_objects(tenant_id, workload_type);
CREATE INDEX IF NOT EXISTS ix_protected_objects_tenant_status ON protected_objects(tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_protected_objects_sla_policy ON protected_objects(sla_policy_id);
CREATE INDEX IF NOT EXISTS ix_protected_objects_last_backup ON protected_objects(last_backup_at DESC);

-- Snapshots
CREATE INDEX IF NOT EXISTS ix_snapshots_status ON snapshots(status);
CREATE INDEX IF NOT EXISTS ix_snapshots_completed_at ON snapshots(completed_at DESC);
CREATE INDEX IF NOT EXISTS ix_snapshots_obj_status ON snapshots(protected_object_id, status);

-- Snapshot Items
CREATE INDEX IF NOT EXISTS ix_snapshot_items_type ON snapshot_items(item_type);
CREATE INDEX IF NOT EXISTS ix_snapshot_items_snap_type ON snapshot_items(snapshot_id, item_type);
CREATE INDEX IF NOT EXISTS ix_snapshot_items_name ON snapshot_items(name);

-- Failed Items
CREATE INDEX IF NOT EXISTS ix_failed_items_error_category ON failed_items(error_category);
CREATE INDEX IF NOT EXISTS ix_failed_items_is_resolved ON failed_items(is_resolved);
CREATE INDEX IF NOT EXISTS ix_failed_items_created_at ON failed_items(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_failed_items_snap_resolved ON failed_items(snapshot_id, is_resolved);

-- Audit Logs
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_severity ON audit_logs(severity);
CREATE INDEX IF NOT EXISTS ix_audit_logs_resource ON audit_logs(resource_type);

-- Anomaly Events
CREATE INDEX IF NOT EXISTS ix_anomaly_events_resolved ON anomaly_events(resolved);
CREATE INDEX IF NOT EXISTS ix_anomaly_events_detected ON anomaly_events(detected_at DESC);
CREATE INDEX IF NOT EXISTS ix_anomaly_events_workload ON anomaly_events(workload_type);

-- Health Baselines
CREATE INDEX IF NOT EXISTS ix_health_baselines_lookup ON health_baselines(tenant_id, workload_type, metric_name);

-- Restore Jobs
CREATE INDEX IF NOT EXISTS ix_restore_jobs_created_at ON restore_jobs(created_at DESC);

-- Users (SSO lookup)
CREATE INDEX IF NOT EXISTS ix_users_sso_subject ON users(sso_subject_id) WHERE sso_subject_id IS NOT NULL;

-- Text search (trigram)
CREATE INDEX IF NOT EXISTS ix_protected_objects_name_trgm ON protected_objects USING gin(display_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_snapshot_items_name_trgm ON snapshot_items USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_failed_items_name_trgm ON failed_items USING gin(item_name gin_trgm_ops);
