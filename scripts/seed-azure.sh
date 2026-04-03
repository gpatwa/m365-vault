#!/bin/bash
# Seed Azure Flexible Server with demo accounts, tenants, and org data.
#
# Usage:
#   ./scripts/seed-azure.sh
#   ./scripts/seed-azure.sh --host pgm365vault-dev.postgres.database.azure.com
#
# Prerequisites:
#   - pip install psycopg2-binary
#   - Azure Flexible Server firewall allows your IP
#
# What it creates:
#   - 5 user accounts (admin, demo, prospect, msp, viewer)
#   - 3 tenants (Patwa Inc, Acme Corporation, Acme Healthcare)
#   - 15 org context users (CEO → VPs → Directors → Staff)
#   - 3 agent profiles (Copilot, HR Bot, OpenClaw)

set -e

HOST="${1:-pgm365vault-dev.postgres.database.azure.com}"
DB="m365vault"
USER="m365vault"
PASS="M365vault_Dev2026!"
BASE_URL="${SHIELDIO_API_URL:-https://m365vault-backend-dev.mangodesert-7599c248.centralus.azurecontainerapps.io/api}"

echo "=== Shieldio Azure Seed Script ==="
echo "Host: $HOST"
echo "API:  $BASE_URL"
echo ""

# Step 1: Create user accounts via API (handles password hashing)
echo "--- Creating user accounts ---"
for USER_DATA in \
  '{"username":"admin","password":"Admin123","email":"admin@shieldio.com","full_name":"Admin"}' \
  '{"username":"demo","password":"ShieldiDemo2026!","email":"demo@shieldio.com","full_name":"Demo User"}' \
  '{"username":"prospect","password":"Prospect2026!","email":"prospect@shieldio.com","full_name":"Prospect"}' \
  '{"username":"msp","password":"MSPDemo2026!","email":"msp@shieldio.com","full_name":"MSP Admin"}' \
  '{"username":"viewer","password":"Viewer2026!","email":"viewer@shieldio.com","full_name":"Viewer"}'; do
  UNAME=$(echo "$USER_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['username'])")
  RESULT=$(curl -s -X POST "$BASE_URL/auth/register" -H 'Content-Type: application/json' -d "$USER_DATA" 2>&1)
  echo "  $UNAME: $(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('username','') or d.get('detail','exists'))" 2>/dev/null || echo 'created')"
done

# Step 2: Update roles + create tenants + seed org data via direct DB
echo ""
echo "--- Seeding database ---"
python3 << PYEOF
import psycopg2
conn = psycopg2.connect(host="$HOST", port=5432, dbname="$DB", user="$USER", password="$PASS", sslmode="require")
conn.autocommit = True
cur = conn.cursor()

# Roles
cur.execute("UPDATE users SET role = 'ADMIN' WHERE username IN ('admin', 'demo')")
cur.execute("UPDATE users SET role = 'MSP_ADMIN' WHERE username = 'msp'")
print("  Roles: admin=ADMIN, demo=ADMIN, msp=MSP_ADMIN")

# Tenants
cur.execute("""INSERT INTO tenants (name, ms_tenant_id, client_id, client_secret_encrypted, status, created_at, updated_at) VALUES
  ('Patwa Inc', '3725cec5-3e2d-402c-a5a6-460c325d8f87', 'd5c6ca1d-0f4a-4e14-a121-136fde89512d', 'from-keyvault', 'ACTIVE', NOW(), NOW()),
  ('Acme Corporation', 'demo-acme-00000000-0000-0000-0000-000000000000', 'demo-client', 'demo-secret', 'ACTIVE', NOW(), NOW()),
  ('Acme Healthcare', 'demo-acme-healthcare', 'demo-client', 'demo-secret', 'ACTIVE', NOW(), NOW())
ON CONFLICT DO NOTHING""")
print(f"  Tenants: {cur.rowcount} created")

cur.execute("SELECT id FROM tenants WHERE name = 'Patwa Inc'")
row = cur.fetchone()
if not row:
    cur.execute("SELECT id FROM tenants ORDER BY id LIMIT 1")
    row = cur.fetchone()
tid = row[0]

# Org context (15 users)
cur.execute("DELETE FROM user_contexts WHERE tenant_id = %s", (tid,))
for n,t,d,a,r,tier,s in [
    ("Gopal Patwa","CEO","Executive",1,4,"critical",92),
    ("Priya Sharma","VP Engineering","Engineering",0,3,"high",76),
    ("David Chen","VP Sales","Sales",0,2,"high",72),
    ("Rachel Kim","CFO","Finance",0,2,"high",68),
    ("Emily Davis","Director of HR","HR",0,2,"medium",58),
    ("James Wilson","Director of Finance","Finance",0,1,"medium",55),
    ("Lisa Thompson","Director of IT","IT",0,2,"medium",52),
    ("Alex Johnson","Senior Architect","Engineering",0,1,"medium",48),
    ("Sarah Chen","Head of Marketing","Marketing",0,1,"medium",45),
    ("Mike Williams","Sales Rep","Sales",0,0,"low",35),
    ("Tom Nakamura","Software Engineer","Engineering",0,0,"low",32),
    ("Fatima Al-Zahra","Account Exec","Sales",0,0,"low",30),
    ("Ben Cooper","DevOps Engineer","Engineering",0,0,"low",28),
    ("Mia Santos","Marketing Analyst","Marketing",0,0,"low",25),
    ("Jake Morrison","Financial Analyst","Finance",0,0,"low",22)]:
    p=n.lower().replace(" ",".").replace("-","")
    cur.execute("INSERT INTO user_contexts (tenant_id,ms_user_id,display_name,email,job_title,department,criticality_score,criticality_tier,is_global_admin,has_privileged_role,direct_reports_count,synced_at,computed_at,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW(),NOW(),NOW())",
        (tid,p,n,f"{p}@patwainc.onmicrosoft.com",t,d,s,tier,a,1 if a or tier in('critical','high')else 0,r))
print(f"  Org: 15 users for tenant {tid}")

# Agent profiles
cur.execute("DELETE FROM agent_profiles WHERE tenant_id = %s", (tid,))
for aid,n,at,m,sh,acts,perms,risk in [
    ("copilot-m365","Microsoft Copilot","copilot",1,0,45,'["Mail.Read"]',15),
    ("hr-bot","Custom HR Bot","custom",1,0,28,'["Mail.Send"]',25),
    ("openclaw-v2026","OpenClaw v2026.2","openclaw",0,1,156,'["Directory.ReadWrite.All"]',85)]:
    cur.execute("INSERT INTO agent_profiles (tenant_id,agent_id,agent_name,agent_type,is_managed,is_shadow,total_actions,permissions,risk_score,first_seen_at,last_seen_at,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW()-INTERVAL '7 days',NOW(),NOW(),NOW())",
        (tid,aid,n,at,m,sh,acts,perms,risk))
print("  Agents: 3 profiles")

conn.close()
print("")
print("=== Seed complete! ===")
print(f"  Login: admin/Admin123 or demo/ShieldiDemo2026!")
print(f"  Tenants: Patwa Inc (id={tid}), Acme Corporation, Acme Healthcare")
print(f"  Org: 15 users (1 critical, 3 high, 5 medium, 6 low)")
PYEOF
