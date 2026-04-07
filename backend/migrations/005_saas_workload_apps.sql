-- Migration 005: SaaS Workload Apps
-- Platform-owned per-workload Entra app registrations.
-- These are the 5 multi-tenant apps KavachIQ creates in its OWN tenant.
-- Customers consent to these apps during onboarding.
-- Auto-populated by workload_bootstrap.py on startup.

CREATE TABLE IF NOT EXISTS saas_workload_apps (
    id SERIAL PRIMARY KEY,
    workload VARCHAR(30) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    app_id VARCHAR(255) NOT NULL,
    app_object_id VARCHAR(255),
    client_secret_encrypted TEXT NOT NULL,
    permissions_configured TEXT,
    sign_in_audience VARCHAR(50) DEFAULT 'AzureADMultipleOrgs',
    redirect_uris TEXT,
    secret_expires_at TIMESTAMP,
    secret_key_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active',
    error_message TEXT,
    last_validated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast lookup by workload
CREATE INDEX IF NOT EXISTS idx_saas_workload_apps_workload ON saas_workload_apps(workload);
CREATE INDEX IF NOT EXISTS idx_saas_workload_apps_status ON saas_workload_apps(status);
