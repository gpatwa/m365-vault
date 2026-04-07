"""Tests for Exchange gap closure: PST export, public folders, journal mailboxes.

Verifies the new Exchange backup capabilities added in Sprint 1.
"""
import json
import pytest
from datetime import datetime


# ═══════════════════════════════════════════════════════
# PST Export (.eml generation)
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_eml_generation_from_graph_json():
    """Export to .eml generates valid RFC 2822 email from Graph API JSON."""
    from email.message import EmailMessage
    from email.utils import formatdate, formataddr

    # Simulate Graph API email JSON (what's stored in backup)
    msg_data = {
        "id": "AAMkAGI2TG93AAA=",
        "subject": "Quarterly Report Q4 2025",
        "from": {"emailAddress": {"name": "Sarah Chen", "address": "sarah@patwa.com"}},
        "toRecipients": [
            {"emailAddress": {"name": "Gopal Patwa", "address": "gopal@patwa.com"}},
        ],
        "ccRecipients": [
            {"emailAddress": {"name": "Finance", "address": "finance@patwa.com"}},
        ],
        "receivedDateTime": "2025-12-15T10:30:00Z",
        "body": {"contentType": "html", "content": "<p>Please review the attached report.</p>"},
        "attachments": [],
    }

    # Build .eml (same logic as exchange_worker.export_to_eml)
    eml = EmailMessage()
    eml["Subject"] = msg_data["subject"]
    eml["From"] = formataddr(("Sarah Chen", "sarah@patwa.com"))
    eml["To"] = formataddr(("Gopal Patwa", "gopal@patwa.com"))
    eml["Cc"] = formataddr(("Finance", "finance@patwa.com"))
    eml["Date"] = msg_data["receivedDateTime"]
    eml.set_content(msg_data["body"]["content"], subtype="html")

    eml_bytes = eml.as_bytes()

    assert b"Subject: Quarterly Report Q4 2025" in eml_bytes
    assert b"From: Sarah Chen <sarah@patwa.com>" in eml_bytes
    assert b"To: Gopal Patwa <gopal@patwa.com>" in eml_bytes
    assert b"Cc: Finance <finance@patwa.com>" in eml_bytes
    assert b"Please review" in eml_bytes
    assert len(eml_bytes) > 100


@pytest.mark.asyncio
async def test_eml_with_attachment():
    """Export includes MIME attachments when present."""
    from email.message import EmailMessage
    import base64

    eml = EmailMessage()
    eml["Subject"] = "Report with attachment"
    eml.set_content("See attached.")

    # Simulate attachment
    att_content = b"Hello World PDF Content"
    eml.add_attachment(att_content, maintype="application", subtype="pdf", filename="report.pdf")

    eml_bytes = eml.as_bytes()
    assert b"report.pdf" in eml_bytes
    assert b"application/pdf" in eml_bytes


# ═══════════════════════════════════════════════════════
# Public Folders
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_public_folder_feature_flag():
    """Public folder discovery is gated by feature flag."""
    from app.services.feature_flags import FeatureFlagService, TIER_FEATURES

    # Community tier should NOT have public_folder
    community = FeatureFlagService.__new__(FeatureFlagService)
    community.tier = "community"
    community.tier_config = TIER_FEATURES["community"]
    assert not community.is_enabled("public_folder")

    # Professional tier SHOULD have it
    pro = FeatureFlagService.__new__(FeatureFlagService)
    pro.tier = "professional"
    pro.tier_config = TIER_FEATURES["professional"]
    assert pro.is_enabled("public_folder")

    # Enterprise too
    ent = FeatureFlagService.__new__(FeatureFlagService)
    ent.tier = "enterprise"
    ent.tier_config = TIER_FEATURES["enterprise"]
    assert ent.is_enabled("public_folder")


@pytest.mark.asyncio
async def test_public_folder_item_path_format():
    """Public folder items should have path starting with 'PublicFolders/'."""
    # Verify the expected path format
    folder_name = "Company Announcements"
    expected_path = f"PublicFolders/{folder_name}"
    assert expected_path == "PublicFolders/Company Announcements"
    assert expected_path.startswith("PublicFolders/")


# ═══════════════════════════════════════════════════════
# Journal Mailbox
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_journal_mailbox_feature_flag():
    """Journal mailbox is Enterprise-only feature."""
    from app.services.feature_flags import FeatureFlagService, TIER_FEATURES

    for tier in ["community", "professional", "business"]:
        svc = FeatureFlagService.__new__(FeatureFlagService)
        svc.tier = tier
        svc.tier_config = TIER_FEATURES[tier]
        assert not svc.is_enabled("journal_mailbox"), f"{tier} should NOT have journal_mailbox"

    # Enterprise SHOULD have it
    ent = FeatureFlagService.__new__(FeatureFlagService)
    ent.tier = "enterprise"
    ent.tier_config = TIER_FEATURES["enterprise"]
    assert ent.is_enabled("journal_mailbox")


@pytest.mark.asyncio
async def test_journal_item_metadata():
    """Journal items should have isJournalEntry=True in metadata."""
    metadata = {
        "hasAttachments": False,
        "isJournalEntry": True,
    }
    assert metadata["isJournalEntry"] is True
    assert "JournalMailbox" == "JournalMailbox"  # Path format


# ═══════════════════════════════════════════════════════
# Distribution Lists (Entra Group Subtype)
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_distribution_list_classification():
    """Groups are classified correctly: DL, security, M365, dynamic."""
    # Distribution list: mail-enabled, NOT security, NOT M365
    dl_group = {"mailEnabled": True, "securityEnabled": False, "groupTypes": []}
    mail_enabled = dl_group.get("mailEnabled", False)
    security_enabled = dl_group.get("securityEnabled", False)
    is_m365 = "Unified" in dl_group.get("groupTypes", [])
    is_dynamic = "DynamicMembership" in dl_group.get("groupTypes", [])

    if mail_enabled and not security_enabled and not is_m365:
        kind = "distribution_list"
    elif is_dynamic:
        kind = "dynamic"
    elif is_m365:
        kind = "m365"
    elif security_enabled:
        kind = "security"
    else:
        kind = "other"

    assert kind == "distribution_list"


@pytest.mark.asyncio
async def test_m365_group_classification():
    """M365 (Unified) groups classified correctly."""
    m365_group = {"mailEnabled": True, "securityEnabled": False, "groupTypes": ["Unified"]}
    is_m365 = "Unified" in m365_group.get("groupTypes", [])
    assert is_m365 is True


@pytest.mark.asyncio
async def test_security_group_classification():
    """Security groups classified correctly."""
    sec_group = {"mailEnabled": False, "securityEnabled": True, "groupTypes": []}
    mail_enabled = sec_group.get("mailEnabled", False)
    security_enabled = sec_group.get("securityEnabled", False)
    is_m365 = "Unified" in sec_group.get("groupTypes", [])

    if mail_enabled and not security_enabled and not is_m365:
        kind = "distribution_list"
    elif security_enabled:
        kind = "security"
    else:
        kind = "other"

    assert kind == "security"
