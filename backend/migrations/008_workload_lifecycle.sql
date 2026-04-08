-- Migration 008: Workload Lifecycle State Machine
-- Adds lifecycle_status column to tenant_workload_apps
-- States: disabled → enabled → discovered → protected → paused
--
-- Only enabled+ workloads get discovered.
-- Only discovered+ workloads get protected.
-- Only protected workloads get backed up and monitored.

-- Add lifecycle_status column (default: disabled for existing rows)
ALTER TABLE tenant_workload_apps
ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(20) DEFAULT 'disabled' NOT NULL;

-- Index for fast lookup of enabled/protected workloads per tenant
CREATE INDEX IF NOT EXISTS idx_tenant_workload_lifecycle
ON tenant_workload_apps (tenant_id, lifecycle_status);

-- Update existing enabled workload apps to 'enabled' lifecycle
-- (apps that were created before lifecycle tracking existed)
UPDATE tenant_workload_apps
SET lifecycle_status = 'enabled'
WHERE enabled = 1 AND lifecycle_status = 'disabled';

-- Update workload apps with protected objects to 'protected' lifecycle
-- (apps whose objects already have SLA assignments)
UPDATE tenant_workload_apps twa
SET lifecycle_status = 'protected'
WHERE twa.enabled = 1
  AND twa.lifecycle_status IN ('disabled', 'enabled')
  AND EXISTS (
    SELECT 1 FROM protected_objects po
    WHERE po.tenant_id = twa.tenant_id
      AND po.status = 'protected'
      AND (
        (twa.workload = 'exchange' AND po.workload_type = 'exchange')
        OR (twa.workload = 'onedrive' AND po.workload_type = 'onedrive')
        OR (twa.workload = 'sharepoint' AND po.workload_type = 'sharepoint')
        OR (twa.workload = 'teams' AND po.workload_type = 'teams')
        OR (twa.workload = 'entra_id' AND po.workload_type = 'entra_id')
      )
  );
