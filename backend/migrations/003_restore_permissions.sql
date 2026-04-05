-- KavachIQ — Schema migration for Restore Permission Model
-- Adds: audit tracking, RESTORE_OPERATOR role, approval workflow
--
-- Usage:
--   psql -h <host> -U <user> -d <db> -f backend/migrations/003_restore_permissions.sql

-- ═══ restore_jobs: tracking + approval ═══
ALTER TABLE restore_jobs ADD COLUMN IF NOT EXISTS initiated_by_user_id INTEGER REFERENCES users(id);
ALTER TABLE restore_jobs ADD COLUMN IF NOT EXISTS approval_required INTEGER DEFAULT 0;
ALTER TABLE restore_jobs ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20);

-- ═══ users: new role ═══
ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'restore_operator';

-- ═══ restore_approvals: approval workflow ═══
CREATE TABLE IF NOT EXISTS restore_approvals (
    id SERIAL PRIMARY KEY,
    restore_job_id INTEGER NOT NULL REFERENCES restore_jobs(id),
    requested_by_user_id INTEGER NOT NULL REFERENCES users(id),
    approved_by_user_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, rejected, expired
    reason TEXT,
    requested_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_restore_approvals_status ON restore_approvals(status);
CREATE INDEX IF NOT EXISTS idx_restore_approvals_job ON restore_approvals(restore_job_id);
