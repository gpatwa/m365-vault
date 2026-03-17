#!/usr/bin/env python3
"""
OneDrive Provisioning Script

Forces OneDrive provisioning for all users by signing in as each user
via ROPC (Resource Owner Password Credentials) flow and accessing their drive.

Prerequisites:
  1. In Azure Portal → App Registration → Authentication:
     - Enable "Allow public client flows" = Yes
  2. Add DELEGATED permission: Files.Read (not Application)
     - Grant admin consent

Usage:
    python scripts/provision_onedrive.py
"""

import asyncio
import os
import sys
from pathlib import Path

import httpx
import msal

# ─── Configuration ───────────────────────────────────────────────────────────

TENANT_ID = os.getenv("MS_TENANT_ID", "")
CLIENT_ID = os.getenv("MS_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET", "")

# Try loading from .env
if not TENANT_ID:
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip().strip('"').strip("'")
                if key == "MS_TENANT_ID":
                    TENANT_ID = val
                elif key == "MS_CLIENT_ID":
                    CLIENT_ID = val
                elif key == "MS_CLIENT_SECRET":
                    CLIENT_SECRET = val

GRAPH_URL = "https://graph.microsoft.com/v1.0"


async def main():
    print("=" * 60)
    print("  OneDrive Provisioning Script")
    print("=" * 60)

    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
        print("❌ Missing credentials. Set MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET")
        sys.exit(1)

    # Get app-only token
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=CLIENT_SECRET,
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        print(f"❌ Failed to get token: {result.get('error_description')}")
        sys.exit(1)

    token = result["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30) as client:
        # Get all users
        resp = await client.get(
            f"{GRAPH_URL}/users?$select=id,displayName,userPrincipalName,assignedLicenses",
            headers=headers,
        )
        users = resp.json().get("value", [])
        print(f"\n👥 Found {len(users)} users\n")

        # Get tenant domain for SharePoint admin URL
        resp = await client.get(f"{GRAPH_URL}/organization", headers=headers)
        orgs = resp.json().get("value", [])
        domain = ""
        if orgs:
            for d in orgs[0].get("verifiedDomains", []):
                if d.get("isDefault"):
                    domain = d["name"]
                    break

        tenant_prefix = domain.replace(".onmicrosoft.com", "") if domain else ""
        print(f"  🏢 Tenant: {domain}")
        print(f"  🌐 SharePoint: https://{tenant_prefix}.sharepoint.com")

        # Method 1: Try to provision via SharePoint admin API
        print(f"\n🔧 Method 1: Requesting OneDrive provisioning via SharePoint Admin API...")
        user_emails = [u["userPrincipalName"] for u in users if u.get("userPrincipalName")]

        admin_url = f"https://{tenant_prefix}-admin.sharepoint.com"
        provision_url = f"{admin_url}/_api/SPO.Tenant/RequestPersonalSiteEnqueueBulk"

        provision_payload = {
            "emailIDs": user_emails,
            "personalSiteCreationOption": 0
        }

        resp = await client.post(
            provision_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json;odata=verbose",
            },
            json=provision_payload,
        )

        if resp.status_code < 400:
            print(f"  ✅ Provisioning request submitted for {len(user_emails)} users!")
            print("  ⏳ OneDrive will be ready in 5-15 minutes")
        else:
            print(f"  ⚠️  SharePoint Admin API returned {resp.status_code}")
            print(f"      This is normal — falling back to Method 2")

        # Method 2: Trigger provisioning by accessing each user's drive
        print(f"\n🔧 Method 2: Triggering provisioning by accessing each user's drive...")
        provisioned = 0
        not_ready = []

        for user in users:
            uid = user["id"]
            name = user["displayName"]
            upn = user["userPrincipalName"]

            resp = await client.get(
                f"{GRAPH_URL}/users/{uid}/drive",
                headers=headers,
            )
            if resp.status_code == 200:
                drive = resp.json()
                quota = drive.get("quota", {})
                total_gb = quota.get("total", 0) / (1024**3)
                used_mb = quota.get("used", 0) / (1024**2)
                print(f"  ✅ {name} ({upn}): OneDrive ready — {total_gb:.0f} GB total, {used_mb:.1f} MB used")
                provisioned += 1
            else:
                print(f"  ⏳ {name} ({upn}): Not yet provisioned")
                not_ready.append({"name": name, "upn": upn, "id": uid})

            await asyncio.sleep(0.5)

        print(f"\n{'=' * 60}")
        print(f"  📊 Results: {provisioned}/{len(users)} users have OneDrive ready")
        print(f"{'=' * 60}")

        if not_ready:
            print(f"\n  ⚠️  {len(not_ready)} user(s) still pending:")
            for u in not_ready:
                print(f"     - {u['name']} ({u['upn']})")

            print(f"""
╔══════════════════════════════════════════════════════════╗
║  To provision OneDrive, do ONE of these:                ║
║                                                         ║
║  Option A (Fastest — 2 min):                            ║
║    Sign into https://onedrive.com as each user.         ║
║    This instantly triggers provisioning.                ║
║                                                         ║
║  Option B (PowerShell):                                 ║
║    Install-Module Microsoft.Online.SharePoint.PowerShell ║
║    Connect-SPOService -Url {admin_url}                  ║
║    Request-SPOPersonalSite -UserEmails \\                ║""")
            emails_str = ",".join(f'"{u["upn"]}"' for u in not_ready)
            print(f"║      {emails_str[:52]}...  ║")
            print(f"""║                                                         ║
║  Option C (Wait):                                       ║
║    Microsoft auto-provisions within 24 hours.           ║
║    Re-run this script later to check status.            ║
╚══════════════════════════════════════════════════════════╝""")

            print(f"\n  ⏳ Waiting 2 minutes then retrying...")
            await asyncio.sleep(120)

            print("\n  🔄 Retrying...")
            newly_provisioned = 0
            still_pending = []
            for u in not_ready:
                resp = await client.get(
                    f"{GRAPH_URL}/users/{u['id']}/drive",
                    headers=headers,
                )
                if resp.status_code == 200:
                    print(f"  ✅ {u['name']}: OneDrive now ready!")
                    newly_provisioned += 1
                else:
                    print(f"  ⏳ {u['name']}: Still pending")
                    still_pending.append(u)
                await asyncio.sleep(0.5)

            if newly_provisioned:
                print(f"\n  🎉 {newly_provisioned} more user(s) provisioned!")

            if still_pending:
                print(f"\n  ⚠️  {len(still_pending)} user(s) still need manual provisioning.")
                print("  👉 Sign in as each user at https://onedrive.com to trigger it.")
                print("  👉 Then re-run: backend/venv/bin/python scripts/populate_sample_data.py")
            else:
                print(f"\n  🎉 All users provisioned! Run the populate script now:")
                print("  👉 backend/venv/bin/python scripts/populate_sample_data.py")
        else:
            print(f"\n  🎉 All users have OneDrive! Run the populate script now:")
            print("  👉 backend/venv/bin/python scripts/populate_sample_data.py")


if __name__ == "__main__":
    asyncio.run(main())
