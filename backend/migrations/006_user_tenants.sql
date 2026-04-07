-- Migration 006: User-Tenant membership
-- Scopes each user to only the tenants they can access.
-- Standard SaaS multi-tenant isolation pattern.

CREATE TABLE IF NOT EXISTS user_tenants (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'member',  -- owner, admin, member, viewer
    is_default INTEGER DEFAULT 0,       -- default tenant for this user
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_user_tenants_user ON user_tenants(user_id);
CREATE INDEX IF NOT EXISTS idx_user_tenants_tenant ON user_tenants(tenant_id);

-- Seed: assign admin to all existing tenants
INSERT INTO user_tenants (user_id, tenant_id, role, is_default, created_at)
SELECT u.id, t.id, 'owner', 1, NOW()
FROM users u, tenants t
WHERE u.username = 'admin'
  AND NOT EXISTS (SELECT 1 FROM user_tenants ut WHERE ut.user_id = u.id AND ut.tenant_id = t.id);

-- Seed: assign demo/prospect to demo tenants
INSERT INTO user_tenants (user_id, tenant_id, role, is_default, created_at)
SELECT u.id, t.id, 'member', 1, NOW()
FROM users u, tenants t
WHERE u.username IN ('demo', 'prospect')
  AND t.ms_tenant_id LIKE 'demo-%'
  AND NOT EXISTS (SELECT 1 FROM user_tenants ut WHERE ut.user_id = u.id AND ut.tenant_id = t.id);
