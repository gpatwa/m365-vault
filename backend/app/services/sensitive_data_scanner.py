"""Sensitive Data Discovery — zero-cost PII/PHI/PCI scanner.

Scans backed-up items for sensitive data patterns using regex.
No external dependencies, no LLM tokens — pure Python.

Detects: SSN, credit cards (Luhn-validated), email addresses,
phone numbers, PHI keywords, financial keywords, certificate files.

Results are stored in SnapshotItem.metadata_json for reporting.
"""
import json
import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshot import Snapshot, SnapshotItem

logger = logging.getLogger(__name__)


@dataclass
class ScanFinding:
    pattern_name: str
    category: str  # pii, phi, pci, financial, credential
    severity: str  # low, medium, high, critical
    count: int
    sample: str = ""  # Redacted sample for context


@dataclass
class ScanResult:
    total_items_scanned: int = 0
    items_with_findings: int = 0
    total_findings: int = 0
    findings_by_category: dict = field(default_factory=dict)
    findings_by_pattern: dict = field(default_factory=dict)


# ── Pattern Definitions ──

PATTERNS = [
    # PII
    {"name": "ssn", "category": "pii", "severity": "critical",
     "regex": r"\b\d{3}-\d{2}-\d{4}\b", "description": "Social Security Number"},

    {"name": "credit_card", "category": "pci", "severity": "critical",
     "regex": r"\b(?:\d{4}[\s-]?){3}\d{4}\b", "description": "Credit Card Number",
     "validator": "_validate_luhn"},

    {"name": "email_address", "category": "pii", "severity": "low",
     "regex": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
     "description": "Email Address"},

    {"name": "phone_us", "category": "pii", "severity": "medium",
     "regex": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
     "description": "US Phone Number"},

    {"name": "passport", "category": "pii", "severity": "critical",
     "regex": r"\b[A-Z]{1,2}\d{6,9}\b", "description": "Passport Number"},

    # PHI (Health)
    {"name": "medical_record", "category": "phi", "severity": "critical",
     "regex": r"\b(?:MRN|medical record|patient id|health id)[\s:]*\d{4,12}\b",
     "description": "Medical Record Number", "flags": re.IGNORECASE},

    {"name": "phi_keywords", "category": "phi", "severity": "high",
     "regex": r"\b(?:diagnosis|prescription|patient|medical record|health insurance|HIPAA|protected health|treatment plan|blood type|allergies|medication)\b",
     "description": "PHI Keywords", "flags": re.IGNORECASE},

    # Financial
    {"name": "bank_account", "category": "financial", "severity": "critical",
     "regex": r"\b(?:account|routing|IBAN|SWIFT|BIC)[\s:#]*[A-Z0-9]{8,34}\b",
     "description": "Bank Account / Routing Number", "flags": re.IGNORECASE},

    {"name": "financial_keywords", "category": "financial", "severity": "medium",
     "regex": r"\b(?:confidential|restricted|bank account|routing number|wire transfer|tax id|EIN|W-?2|W-?9|1099)\b",
     "description": "Financial Keywords", "flags": re.IGNORECASE},

    # Credentials
    {"name": "api_key", "category": "credential", "severity": "critical",
     "regex": r"\b(?:api[_-]?key|apikey|access[_-]?token|secret[_-]?key|bearer)[\s:=]+['\"]?[A-Za-z0-9_\-]{20,}['\"]?",
     "description": "API Key / Secret", "flags": re.IGNORECASE},

    {"name": "certificate_file", "category": "credential", "severity": "high",
     "regex": r"\b[\w-]+\.(?:pfx|pem|key|cer|p12|jks)\b",
     "description": "Certificate File Reference", "flags": re.IGNORECASE},
]

# Compile patterns
COMPILED_PATTERNS = []
for p in PATTERNS:
    flags = p.get("flags", 0)
    COMPILED_PATTERNS.append({
        **p,
        "compiled": re.compile(p["regex"], flags),
    })


def _validate_luhn(number_str: str) -> bool:
    """Validate credit card number using Luhn algorithm."""
    digits = re.sub(r"[\s-]", "", number_str)
    if not digits.isdigit() or len(digits) < 13 or len(digits) > 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


class SensitiveDataScanner:
    """Scans backup data for sensitive information patterns."""

    async def scan_snapshot(
        self,
        snapshot: Snapshot,
        db: AsyncSession,
        storage,
        wrapped_dek: str,
    ) -> ScanResult:
        """Scan all items in a snapshot for sensitive data.

        Updates each item's metadata_json with findings.
        """
        result = ScanResult()

        # Get all items in snapshot
        items_result = await db.execute(
            select(SnapshotItem).where(SnapshotItem.snapshot_id == snapshot.id)
        )
        items = items_result.scalars().all()

        for item in items:
            try:
                # Retrieve decrypted content
                data = await storage.retrieve_item(item.blob_path, wrapped_dek)
                if not data:
                    continue

                # Decode to text for scanning
                try:
                    text = data.decode("utf-8") if isinstance(data, bytes) else str(data)
                except UnicodeDecodeError:
                    continue  # Skip binary files

                # Run all patterns
                item_findings = self._scan_text(text)
                result.total_items_scanned += 1

                if item_findings:
                    result.items_with_findings += 1

                    # Update item metadata
                    existing_meta = json.loads(item.metadata_json) if item.metadata_json else {}
                    existing_meta["sensitive_data"] = {
                        "scan_status": "flagged",
                        "findings": [
                            {"pattern": f.pattern_name, "category": f.category,
                             "severity": f.severity, "count": f.count}
                            for f in item_findings
                        ],
                    }
                    item.metadata_json = json.dumps(existing_meta)

                    for f in item_findings:
                        result.total_findings += f.count
                        result.findings_by_category[f.category] = (
                            result.findings_by_category.get(f.category, 0) + f.count
                        )
                        result.findings_by_pattern[f.pattern_name] = (
                            result.findings_by_pattern.get(f.pattern_name, 0) + f.count
                        )

            except Exception as e:
                logger.error(f"Scan error for item {item.id}: {e}")

        await db.flush()
        logger.info(
            f"Sensitive data scan complete: {result.total_items_scanned} items scanned, "
            f"{result.items_with_findings} flagged, {result.total_findings} findings"
        )
        return result

    def _scan_text(self, text: str) -> list[ScanFinding]:
        """Scan text against all patterns."""
        findings = []
        for pattern in COMPILED_PATTERNS:
            matches = pattern["compiled"].findall(text)
            if not matches:
                continue

            # Run validator if specified
            if pattern.get("validator") == "_validate_luhn":
                matches = [m for m in matches if _validate_luhn(m)]
                if not matches:
                    continue

            findings.append(ScanFinding(
                pattern_name=pattern["name"],
                category=pattern["category"],
                severity=pattern["severity"],
                count=len(matches),
            ))

        return findings

    async def get_scan_results(self, tenant_id: int, db: AsyncSession) -> dict:
        """Get aggregated scan results across all snapshots for a tenant."""
        from app.models.protected_object import ProtectedObject

        result = await db.execute(
            select(SnapshotItem)
            .join(Snapshot, SnapshotItem.snapshot_id == Snapshot.id)
            .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
            .where(
                ProtectedObject.tenant_id == tenant_id,
                SnapshotItem.metadata_json.like('%"sensitive_data"%'),
            )
        )
        flagged_items = result.scalars().all()

        by_category = {}
        by_severity = {}
        by_workload = {}

        for item in flagged_items:
            meta = json.loads(item.metadata_json) if item.metadata_json else {}
            sd = meta.get("sensitive_data", {})
            for finding in sd.get("findings", []):
                cat = finding["category"]
                sev = finding["severity"]
                by_category[cat] = by_category.get(cat, 0) + finding["count"]
                by_severity[sev] = by_severity.get(sev, 0) + finding["count"]

        return {
            "total_flagged_items": len(flagged_items),
            "by_category": by_category,
            "by_severity": by_severity,
        }


# Singleton
sensitive_data_scanner = SensitiveDataScanner()
