"""Security posture API — surfaces security status for prospects and admins."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.snapshot import Snapshot, SnapshotStatus
from app.models.sla_policy import SLAPolicy
from app.models.protected_object import ProtectedObject, ProtectionStatus
from app.services.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/security", tags=["Security"])


@router.get("/posture")
async def security_posture(
    tenant_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get security posture summary — encryption, WORM, compliance status."""

    # Encryption status
    encryption = {
        "algorithm": "AES-256-GCM",
        "key_management": "Per-tenant DEK wrapped by master KEK",
        "transit": "TLS 1.2+",
        "status": "active",
    }

    # WORM / Immutability
    worm_policies = (await db.execute(
        select(func.count()).where(SLAPolicy.worm_enabled == 1)
    )).scalar() or 0

    legal_hold_policies = (await db.execute(
        select(func.count()).where(SLAPolicy.legal_hold == 1)
    )).scalar() or 0

    locked_snapshots = (await db.execute(
        select(func.count()).where(
            Snapshot.locked_until.isnot(None),
            Snapshot.status == SnapshotStatus.COMPLETED,
        )
    )).scalar() or 0

    immutability = {
        "worm_policies": worm_policies,
        "legal_hold_policies": legal_hold_policies,
        "locked_snapshots": locked_snapshots,
        "status": "active" if worm_policies > 0 else "available",
    }

    # Protection coverage
    total_objects = (await db.execute(select(func.count(ProtectedObject.id)))).scalar() or 0
    protected = (await db.execute(
        select(func.count()).where(ProtectedObject.status == ProtectionStatus.PROTECTED)
    )).scalar() or 0

    coverage = {
        "total_objects": total_objects,
        "protected": protected,
        "coverage_percent": round(protected / total_objects * 100, 1) if total_objects > 0 else 0,
    }

    # Authentication
    auth = {
        "method": "JWT + bcrypt",
        "sso_enabled": settings.SSO_ENABLED,
        "sso_provider": "Entra ID (OIDC)" if settings.SSO_ENABLED else None,
        "mfa": "Via Entra ID Conditional Access" if settings.SSO_ENABLED else "Available via SSO",
        "password_policy": {
            "min_length": settings.PASSWORD_MIN_LENGTH,
            "require_uppercase": settings.PASSWORD_REQUIRE_UPPERCASE,
            "require_digit": settings.PASSWORD_REQUIRE_DIGIT,
        },
        "rbac_roles": ["admin", "operator", "viewer"],
        "refresh_tokens": True,
    }

    # Infrastructure
    infrastructure = {
        "rate_limiting": f"{settings.RATE_LIMIT_REQUESTS_PER_MINUTE} req/min/IP",
        "https": "Enforced" if settings.FORCE_HTTPS else "Available",
        "cors": "Configurable",
        "logging": settings.LOG_FORMAT,
        "health_checks": "/health (DB + storage)",
        "iac": "Terraform",
    }

    # Compliance readiness
    compliance = {
        "soc2": {"status": "ready", "controls_mapped": 16},
        "gdpr": {"status": "ready", "articles_mapped": 8},
        "hipaa": {"status": "ready", "safeguards_mapped": 14},
        "dora": {"status": "ready", "articles_mapped": 6},
    }

    # Security features
    features = [
        {"name": "AES-256-GCM Encryption", "category": "encryption", "status": "active",
         "description": "All backup data encrypted at rest with authenticated encryption"},
        {"name": "Per-Tenant Key Isolation", "category": "encryption", "status": "active",
         "description": "Each tenant has a unique Data Encryption Key (DEK)"},
        {"name": "TLS 1.2+ In Transit", "category": "encryption", "status": "active",
         "description": "All API, Graph, database, and storage connections use TLS"},
        {"name": "WORM Immutable Storage", "category": "data_protection", "status": "active" if worm_policies > 0 else "available",
         "description": "Write-once-read-many prevents backup deletion within retention period"},
        {"name": "Legal Hold", "category": "data_protection", "status": "active" if legal_hold_policies > 0 else "available",
         "description": "Prevents any deletion regardless of retention policy"},
        {"name": "Malware Scanning", "category": "data_protection", "status": "active",
         "description": "YARA rule-based scanning before restore to prevent reinfection"},
        {"name": "Sensitive Data Discovery", "category": "data_protection", "status": "active",
         "description": "PII/PHI/PCI pattern detection across backup data"},
        {"name": "Backup Validation", "category": "data_protection", "status": "active",
         "description": "Automated checksum verification of stored backup data"},
        {"name": "SSO / OIDC", "category": "authentication", "status": "active" if settings.SSO_ENABLED else "available",
         "description": "Enterprise SSO via Microsoft Entra ID with MFA support"},
        {"name": "Role-Based Access Control", "category": "authentication", "status": "active",
         "description": "Three roles: Admin, Operator, Viewer with endpoint-level enforcement"},
        {"name": "Audit Logging", "category": "monitoring", "status": "active",
         "description": "All admin actions logged with user, action, timestamp, IP"},
        {"name": "Anomaly Detection", "category": "monitoring", "status": "active",
         "description": "Z-score baseline deviation detects unusual backup patterns"},
        {"name": "Smart Alerts", "category": "monitoring", "status": "active",
         "description": "Email + webhook notifications for failures and anomalies"},
        {"name": "Rate Limiting", "category": "infrastructure", "status": "active",
         "description": f"{settings.RATE_LIMIT_REQUESTS_PER_MINUTE} requests/minute per IP"},
        {"name": "SHA-256 Content Integrity", "category": "infrastructure", "status": "active",
         "description": "Every backed-up item has content hash for integrity verification"},
    ]

    return {
        "encryption": encryption,
        "immutability": immutability,
        "coverage": coverage,
        "authentication": auth,
        "infrastructure": infrastructure,
        "compliance": compliance,
        "features": features,
        "security_score": _compute_security_score(features),
    }


def _compute_security_score(features: list) -> dict:
    """Compute overall security score based on active features."""
    total = len(features)
    active = sum(1 for f in features if f["status"] == "active")
    score = round(active / total * 100) if total > 0 else 0
    return {
        "score": score,
        "active_features": active,
        "total_features": total,
        "grade": "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D",
    }


@router.get("/pack")
async def security_pack():
    """Return security documentation metadata for download."""
    return {
        "documents": [
            {
                "name": "Security Architecture",
                "description": "Comprehensive security controls, encryption, authentication, and compliance readiness",
                "file": "SECURITY.md",
                "pages": 10,
            },
            {
                "name": "Compliance Mapping",
                "description": "SOC 2, GDPR, HIPAA, and DORA control mapping",
                "file": "COMPLIANCE_MAPPING.md",
                "pages": 4,
            },
            {
                "name": "Security Audit Report",
                "description": "Automated security scan results (OWASP, dependencies, encryption)",
                "file": "security-audit-report.json",
                "generated": True,
            },
        ],
    }
