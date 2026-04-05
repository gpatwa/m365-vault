-- Shieldio — Schema migration for Per-Workload App Separation (Phase 8)
-- Each workload (Entra ID, Exchange, SharePoint, etc.) gets its own Entra app registration.
--
-- Usage:
--   psql -h <host> -U <user> -d <db> -f backend/migrations/004_workload_apps.sql

CREATE TABLE IF NOT EXISTS tenant_workload_apps (
    id                      SERIAL PRIMARY KEY,
    tenant_id               INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    workload                VARCHAR(30) NOT NULL,   -- entra_id, exchange, sharepoint, onedrive, teams

    -- Entra App Registration
    client_id               VARCHAR(255) NOT NULL,
    client_secret_encrypted TEXT NOT NULL,           -- AES-256 encrypted
    app_object_id           VARCHAR(255),            -- Entra object ID (for managing the app)
    sp_object_id            VARCHAR(255),            -- Service Principal object ID

    -- Consent Status
    consent_status          VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- pending, consented, partial, revoked, error

    -- Permission Tracking
    permissions_requested   TEXT,                    -- JSON array
    permissions_granted     TEXT,                    -- JSON array
    backup_ready            INTEGER DEFAULT 0,
    restore_ready           INTEGER DEFAULT 0,

    -- Workload-specific Configuration
    config_json             TEXT,                    -- JSON: workload-specific settings

    -- Secret Lifecycle
    secret_expires_at       TIMESTAMP,
    secret_rotation_warned  INTEGER DEFAULT 0,

    -- Metadata
    enabled                 INTEGER DEFAULT 1,
    last_used_at            TIMESTAMP,
    error_message           TEXT,
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW(),

    -- Constraints
    UNIQUE (tenant_id, workload)
);

CREATE INDEX IF NOT EXISTS idx_twa_tenant   ON tenant_workload_apps(tenant_id);
CREATE INDEX IF NOT EXISTS idx_twa_workload ON tenant_workload_apps(workload);
CREATE INDEX IF NOT EXISTS idx_twa_status   ON tenant_workload_apps(consent_status);
