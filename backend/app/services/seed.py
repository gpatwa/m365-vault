"""Environment seed data — deterministic, idempotent, atomic.

Creates a fully operational environment in one transaction:
  Users → Tenants → Memberships → Onboarding steps

Design principles:
  1. Idempotent: safe to run on every startup (INSERT ... ON CONFLICT DO NOTHING)
  2. Atomic: one transaction — either everything exists or nothing changes
  3. Complete: every user gets tenants, memberships, and onboarding steps
  4. No hardcoded IDs: everything is resolved by name, not by integer ID
"""
import logging
import os
import secrets

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def ensure_seed_users(engine: AsyncEngine):
    """Ensure seed users exist with complete tenant memberships and onboarding state.

    Runs on every startup. Idempotent — skips rows that already exist.
    Handles both fresh deploys (create everything) and existing deploys
    (fill gaps from previous incomplete seeds).
    """
    from app.services.auth import hash_password

    is_sqlite = "sqlite" in str(engine.url)
    if is_sqlite:
        return  # SQLite tests use conftest.py fixtures, not seed data

    SEED_USERS = [
        ("admin", "admin@kavachiq.com", "ADMIN"),
        ("demo", "demo@kavachiq.com", "ADMIN"),
        ("prospect", "prospect@kavachiq.com", "ADMIN"),
        ("viewer", "viewer@kavachiq.com", "VIEWER"),
    ]

    # Users who should be assigned to ALL tenants
    # Prospect is NOT here — they get assigned to their own tenant during onboarding
    TENANT_ACCESS = {
        "admin": "owner",     # Platform admin — owns all tenants
        "demo": "member",     # Demo user — needs full access for E2E
    }

    async with engine.begin() as conn:
        # ── 1. Ensure users exist ───────────────────────────────────────
        result = await conn.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar() or 0

        if user_count == 0:
            for username, email, role in SEED_USERS:
                pwd = _get_password(username)
                hashed = hash_password(pwd)
                await conn.execute(text(
                    "INSERT INTO users (username, email, password_hash, full_name, "
                    "role, is_active, email_verified, created_at) "
                    "VALUES (:username, :email, :hash, :name, :role, 1, 1, NOW())"
                ), {
                    "username": username, "email": email, "hash": hashed,
                    "name": f"{username.title()} User", "role": role,
                })
            logger.info(f"Seed: created {len(SEED_USERS)} users")

        # ── 2. Ensure tenant memberships ────────────────────────────────
        # Only admin and demo get ALL tenants. Other users get tenants via onboarding.
        for username, role in TENANT_ACCESS.items():
            await conn.execute(text("""
                INSERT INTO user_tenants (user_id, tenant_id, role, is_default, created_at)
                SELECT u.id, t.id, :role, 1, NOW()
                FROM users u, tenants t
                WHERE u.username = :username
                  AND NOT EXISTS (
                    SELECT 1 FROM user_tenants ut
                    WHERE ut.user_id = u.id AND ut.tenant_id = t.id
                  )
            """), {"username": username, "role": role})

        # Clean up: prospect should only have their own tenant (not all tenants)
        # Keep only their earliest membership (from original onboarding)
        await conn.execute(text("""
            DELETE FROM user_tenants ut
            USING users u
            WHERE ut.user_id = u.id
              AND u.username = 'prospect'
              AND ut.tenant_id != (
                SELECT ut2.tenant_id FROM user_tenants ut2
                JOIN users u2 ON ut2.user_id = u2.id
                WHERE u2.username = 'prospect'
                ORDER BY ut2.created_at ASC
                LIMIT 1
              )
        """))

        # ── 3. Ensure onboarding steps ──────────────────────────────────
        # Check if onboarding_steps table exists (might not on first deploy
        # if init_db hasn't run yet in this startup sequence)
        table_exists = await conn.scalar(text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'onboarding_steps'"
        ))
        if not table_exists:
            return  # Table will be created by init_db; backfill runs next startup

        # create_account for all users
        await conn.execute(text("""
            INSERT INTO onboarding_steps (user_id, step, completed_at)
            SELECT u.id, 'create_account', COALESCE(u.created_at, NOW())
            FROM users u
            WHERE NOT EXISTS (
                SELECT 1 FROM onboarding_steps os
                WHERE os.user_id = u.id AND os.step = 'create_account'
            )
        """))

        # connect_platform / discover_workloads / assign_protection for users with tenants
        for step in ("connect_platform", "discover_workloads", "assign_protection"):
            await conn.execute(text("""
                INSERT INTO onboarding_steps (user_id, step, completed_at)
                SELECT DISTINCT ut.user_id, :step, NOW()
                FROM user_tenants ut
                WHERE NOT EXISTS (
                    SELECT 1 FROM onboarding_steps os
                    WHERE os.user_id = ut.user_id AND os.step = :step
                )
            """), {"step": step})

        # first_backup for users whose tenants have completed backups
        await conn.execute(text("""
            INSERT INTO onboarding_steps (user_id, step, completed_at)
            SELECT DISTINCT ut.user_id, 'first_backup', COALESCE(MIN(bj.completed_at), NOW())
            FROM user_tenants ut
            JOIN backup_jobs bj ON bj.tenant_id = ut.tenant_id AND bj.status::text = 'completed'
            WHERE NOT EXISTS (
                SELECT 1 FROM onboarding_steps os
                WHERE os.user_id = ut.user_id AND os.step = 'first_backup'
            )
            GROUP BY ut.user_id
        """))

    logger.info("Seed: users, memberships, and onboarding steps verified")


async def ensure_workload_lifecycle(engine: AsyncEngine):
    """Create TenantWorkloadApp rows for legacy tenants that onboarded before
    the per-workload app separation feature.

    Legacy tenants have protected objects but no TenantWorkloadApp rows.
    This creates rows with correct lifecycle_status based on actual data:
    - Workloads with PROTECTED objects → lifecycle_status = 'protected'
    - Other workloads → not created (they don't exist for this tenant)

    The tenant's main client_id/client_secret_encrypted are used as credentials
    since legacy tenants used a single app for all workloads.
    """
    is_sqlite = "sqlite" in str(engine.url)
    if is_sqlite:
        return

    async with engine.begin() as conn:
        # Find active tenants with protected objects but no workload app rows
        await conn.execute(text("""
            INSERT INTO tenant_workload_apps (
                tenant_id, workload, client_id, client_secret_encrypted,
                consent_status, lifecycle_status, backup_ready, enabled, created_at, updated_at
            )
            SELECT DISTINCT
                po.tenant_id,
                LOWER(po.workload_type::text),
                t.client_id,
                t.client_secret_encrypted,
                'consented',
                'protected',
                1,
                1,
                NOW(),
                NOW()
            FROM protected_objects po
            JOIN tenants t ON po.tenant_id = t.id
            WHERE po.status = 'protected'
              AND t.status = 'active'
              AND t.client_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM tenant_workload_apps twa
                  WHERE twa.tenant_id = po.tenant_id
                    AND twa.workload = LOWER(po.workload_type::text)
              )
        """))

    logger.info("Seed: workload lifecycle records verified for legacy tenants")


async def sync_tenant_counters(engine: AsyncEngine):
    """Sync denormalized tenant object counters from protected_objects table."""
    is_sqlite = "sqlite" in str(engine.url)
    if is_sqlite:
        return

    async with engine.begin() as conn:
        await conn.execute(text("""
            UPDATE tenants SET
              total_mailboxes = (SELECT COUNT(*) FROM protected_objects WHERE tenant_id = tenants.id AND workload_type = 'EXCHANGE'),
              total_entra_objects = (SELECT COUNT(*) FROM protected_objects WHERE tenant_id = tenants.id AND workload_type = 'ENTRA_ID'),
              total_onedrives = (SELECT COUNT(*) FROM protected_objects WHERE tenant_id = tenants.id AND workload_type = 'ONEDRIVE'),
              total_sites = (SELECT COUNT(*) FROM protected_objects WHERE tenant_id = tenants.id AND workload_type = 'SHAREPOINT'),
              total_teams = (SELECT COUNT(*) FROM protected_objects WHERE tenant_id = tenants.id AND workload_type = 'TEAMS')
        """))
    logger.info("Seed: tenant counters synced")


def _get_password(username: str) -> str:
    """Get seed password from env var or generate a secure random one."""
    env_key = f"SEED_PASSWORD_{username.upper()}"
    pwd = os.environ.get(env_key)
    if pwd:
        return pwd
    generated = secrets.token_urlsafe(12)
    logger.warning(
        f"Auto-generated password for '{username}'. "
        f"Set {env_key} env var for deterministic credentials."
    )
    return generated
