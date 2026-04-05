-- KavachIQ — Admin Invite model for non-admin user onboarding
-- Allows prospects to invite their Global Admin to complete OAuth consent.

CREATE TABLE IF NOT EXISTS admin_invites (
    id                  SERIAL PRIMARY KEY,
    tenant_name         VARCHAR(255) NOT NULL,
    invited_by_user_id  INTEGER NOT NULL REFERENCES users(id),
    admin_email         VARCHAR(255) NOT NULL,
    token               VARCHAR(255) UNIQUE NOT NULL,
    status              VARCHAR(20) DEFAULT 'pending',  -- pending, completed, expired
    ms_tenant_id        VARCHAR(255),
    completed_at        TIMESTAMP,
    expires_at          TIMESTAMP NOT NULL,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_invites_token ON admin_invites(token);
CREATE INDEX IF NOT EXISTS idx_admin_invites_status ON admin_invites(status);
