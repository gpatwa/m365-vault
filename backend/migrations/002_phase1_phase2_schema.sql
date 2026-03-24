-- Shieldio — Schema migration for Phase 1 + Phase 2 features
-- Run against Azure PostgreSQL after deploying new container images
--
-- Usage:
--   psql -h <host> -U <user> -d <db> -f backend/migrations/002_phase1_phase2_schema.sql

-- ═══ New enum values ═══
ALTER TYPE workloadtype ADD VALUE IF NOT EXISTS 'TEAMS';
ALTER TYPE itemtype ADD VALUE IF NOT EXISTS 'CHAT';
ALTER TYPE itemtype ADD VALUE IF NOT EXISTS 'CHAT_ATTACHMENT';
ALTER TYPE itemtype ADD VALUE IF NOT EXISTS 'CHAT_MESSAGE';
ALTER TYPE itemtype ADD VALUE IF NOT EXISTS 'CHANNEL_MESSAGE';
ALTER TYPE itemtype ADD VALUE IF NOT EXISTS 'TEAM_CHANNEL';
ALTER TYPE itemtype ADD VALUE IF NOT EXISTS 'MEETING';

-- ═══ New columns on existing tables ═══

-- Users: SSO support
ALTER TABLE users ADD COLUMN IF NOT EXISTS sso_provider VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS sso_subject_id VARCHAR(255);

-- SLA Policies: WORM + Legal Hold
ALTER TABLE sla_policies ADD COLUMN IF NOT EXISTS worm_enabled INTEGER DEFAULT 0;
ALTER TABLE sla_policies ADD COLUMN IF NOT EXISTS legal_hold INTEGER DEFAULT 0;

-- Snapshots: WORM lock + validation
ALTER TABLE snapshots ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;
ALTER TABLE snapshots ADD COLUMN IF NOT EXISTS validation_status VARCHAR(50);
ALTER TABLE snapshots ADD COLUMN IF NOT EXISTS validated_at TIMESTAMP;

-- Tenants: Teams count
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS total_teams INTEGER DEFAULT 0;

-- Restore Jobs: cross-tenant + malware scan
ALTER TABLE restore_jobs ADD COLUMN IF NOT EXISTS target_tenant_id INTEGER;
ALTER TABLE restore_jobs ADD COLUMN IF NOT EXISTS scan_status VARCHAR(50);
ALTER TABLE restore_jobs ADD COLUMN IF NOT EXISTS scan_details TEXT;

-- ═══ New tables ═══

CREATE TABLE IF NOT EXISTS health_baselines (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    workload_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    avg_value FLOAT DEFAULT 0.0,
    std_dev FLOAT DEFAULT 0.0,
    min_value FLOAT DEFAULT 0.0,
    max_value FLOAT DEFAULT 0.0,
    sample_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_health_baselines_tenant_id ON health_baselines(tenant_id);

CREATE TABLE IF NOT EXISTS anomaly_events (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    workload_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    expected_value FLOAT NOT NULL,
    actual_value FLOAT NOT NULL,
    z_score FLOAT NOT NULL,
    severity VARCHAR(20) DEFAULT 'warning',
    message VARCHAR(1000),
    resolved INTEGER DEFAULT 0,
    detected_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_anomaly_events_tenant_id ON anomaly_events(tenant_id);

-- ═══ Performance indexes (from 001_performance_indexes.sql) ═══
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS ix_backup_jobs_tenant_workload ON backup_jobs(tenant_id, workload_type);
CREATE INDEX IF NOT EXISTS ix_backup_jobs_tenant_status ON backup_jobs(tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_backup_jobs_completed_at ON backup_jobs(completed_at DESC);
CREATE INDEX IF NOT EXISTS ix_backup_jobs_created_at ON backup_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_protected_objects_tenant_workload ON protected_objects(tenant_id, workload_type);
CREATE INDEX IF NOT EXISTS ix_protected_objects_tenant_status ON protected_objects(tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_protected_objects_sla_policy ON protected_objects(sla_policy_id);
CREATE INDEX IF NOT EXISTS ix_protected_objects_last_backup ON protected_objects(last_backup_at DESC);
CREATE INDEX IF NOT EXISTS ix_snapshots_status ON snapshots(status);
CREATE INDEX IF NOT EXISTS ix_snapshots_completed_at ON snapshots(completed_at DESC);
CREATE INDEX IF NOT EXISTS ix_snapshots_obj_status ON snapshots(protected_object_id, status);
CREATE INDEX IF NOT EXISTS ix_snapshot_items_type ON snapshot_items(item_type);
CREATE INDEX IF NOT EXISTS ix_snapshot_items_snap_type ON snapshot_items(snapshot_id, item_type);
CREATE INDEX IF NOT EXISTS ix_snapshot_items_name ON snapshot_items(name);
CREATE INDEX IF NOT EXISTS ix_failed_items_error_category ON failed_items(error_category);
CREATE INDEX IF NOT EXISTS ix_failed_items_is_resolved ON failed_items(is_resolved);
CREATE INDEX IF NOT EXISTS ix_failed_items_created_at ON failed_items(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_failed_items_snap_resolved ON failed_items(snapshot_id, is_resolved);
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_severity ON audit_logs(severity);
CREATE INDEX IF NOT EXISTS ix_audit_logs_resource ON audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS ix_anomaly_events_resolved ON anomaly_events(resolved);
CREATE INDEX IF NOT EXISTS ix_anomaly_events_detected ON anomaly_events(detected_at DESC);
CREATE INDEX IF NOT EXISTS ix_anomaly_events_workload ON anomaly_events(workload_type);
CREATE INDEX IF NOT EXISTS ix_health_baselines_lookup ON health_baselines(tenant_id, workload_type, metric_name);
CREATE INDEX IF NOT EXISTS ix_restore_jobs_created_at ON restore_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_users_sso_subject ON users(sso_subject_id) WHERE sso_subject_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_protected_objects_name_trgm ON protected_objects USING gin(display_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_snapshot_items_name_trgm ON snapshot_items USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_failed_items_name_trgm ON failed_items USING gin(item_name gin_trgm_ops);
