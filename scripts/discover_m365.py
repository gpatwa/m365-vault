#!/usr/bin/env python3
"""
M365 Workload Discovery & Provisioning Script

Discovers real users, mailboxes, OneDrive accounts, and SharePoint sites
from your M365 tenant via Graph API. Outputs a JSON manifest of what's
available so the onboarding flow only creates backup objects for real,
licensed resources.

Also provisions OneDrive for users who don't have it yet.

Prerequisites:
  - Azure AD app with Application permissions:
    User.Read.All, Mail.Read, Files.Read.All, Sites.Read.All
  - Admin consent granted

Usage:
    python scripts/discover_m365.py                      # interactive
    python scripts/discover_m365.py --json               # JSON output only
    python scripts/discover_m365.py --provision           # also trigger OneDrive provisioning
    python scripts/discover_m365.py --register <backend>  # register objects with backend API

Environment:
    MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET
    (or reads from backend/.env)
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

# ─── Configuration ───────────────────────────────────────────────────────────

TENANT_ID = os.getenv("MS_TENANT_ID", "")
CLIENT_ID = os.getenv("MS_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET", "")

# Try loading from .env
if not TENANT_ID:
    for env_path in [
        Path(__file__).parent.parent / "backend" / ".env",
        Path(__file__).parent.parent / ".env",
    ]:
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
            break

GRAPH_URL = "https://graph.microsoft.com/v1.0"


async def get_token() -> str:
    """Acquire app-only token using client credentials."""
    try:
        import msal
        app = msal.ConfidentialClientApplication(
            CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}",
            client_credential=CLIENT_SECRET,
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" in result:
            return result["access_token"]
        raise RuntimeError(result.get("error_description", "Token acquisition failed"))
    except ImportError:
        # Fallback: direct HTTP token request (no msal needed)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
                data={
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "scope": "https://graph.microsoft.com/.default",
                    "grant_type": "client_credentials",
                },
            )
            data = resp.json()
            if "access_token" in data:
                return data["access_token"]
            raise RuntimeError(data.get("error_description", "Token acquisition failed"))


async def discover_users(client: httpx.AsyncClient, headers: dict) -> list[dict]:
    """Discover all licensed users in the tenant."""
    users = []
    url = f"{GRAPH_URL}/users?$select=id,displayName,userPrincipalName,mail,assignedLicenses&$top=999"

    while url:
        resp = await client.get(url, headers=headers)
        data = resp.json()
        for u in data.get("value", []):
            # Skip guest/external users and service accounts
            upn = u.get("userPrincipalName", "")
            if "#EXT#" in upn or not u.get("assignedLicenses"):
                continue
            users.append({
                "id": u["id"],
                "displayName": u["displayName"],
                "upn": upn,
                "mail": u.get("mail", upn),
            })
        url = data.get("@odata.nextLink")

    return users


async def discover_exchange(client: httpx.AsyncClient, headers: dict, users: list[dict]) -> list[dict]:
    """Check which users have active mailboxes."""
    mailboxes = []
    for user in users:
        resp = await client.get(
            f"{GRAPH_URL}/users/{user['id']}/mailFolders/inbox?$select=id,displayName,totalItemCount",
            headers=headers,
        )
        if resp.status_code == 200:
            inbox = resp.json()
            mailboxes.append({
                "user_id": user["id"],
                "displayName": user["displayName"],
                "upn": user["upn"],
                "mail": user["mail"],
                "inbox_count": inbox.get("totalItemCount", 0),
                "status": "active",
            })
        elif resp.status_code == 404:
            mailboxes.append({
                "user_id": user["id"],
                "displayName": user["displayName"],
                "upn": user["upn"],
                "mail": user["mail"],
                "inbox_count": 0,
                "status": "no_mailbox",
            })
        else:
            error = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
            mailboxes.append({
                "user_id": user["id"],
                "displayName": user["displayName"],
                "upn": user["upn"],
                "mail": user["mail"],
                "inbox_count": 0,
                "status": f"error: {error[:80]}",
            })
        await asyncio.sleep(0.3)  # Rate limiting

    return mailboxes


async def discover_onedrive(client: httpx.AsyncClient, headers: dict, users: list[dict]) -> list[dict]:
    """Check which users have OneDrive provisioned."""
    drives = []
    for user in users:
        resp = await client.get(
            f"{GRAPH_URL}/users/{user['id']}/drive?$select=id,driveType,quota",
            headers=headers,
        )
        if resp.status_code == 200:
            drive = resp.json()
            quota = drive.get("quota", {})
            drives.append({
                "user_id": user["id"],
                "displayName": user["displayName"],
                "upn": user["upn"],
                "drive_id": drive["id"],
                "total_bytes": quota.get("total", 0),
                "used_bytes": quota.get("used", 0),
                "status": "active",
            })
        elif resp.status_code == 404:
            drives.append({
                "user_id": user["id"],
                "displayName": user["displayName"],
                "upn": user["upn"],
                "drive_id": None,
                "total_bytes": 0,
                "used_bytes": 0,
                "status": "not_provisioned",
            })
        else:
            error = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
            drives.append({
                "user_id": user["id"],
                "displayName": user["displayName"],
                "upn": user["upn"],
                "drive_id": None,
                "total_bytes": 0,
                "used_bytes": 0,
                "status": f"error: {error[:80]}",
            })
        await asyncio.sleep(0.3)

    return drives


async def discover_sharepoint(client: httpx.AsyncClient, headers: dict) -> list[dict]:
    """Discover all SharePoint sites."""
    sites = []
    url = f"{GRAPH_URL}/sites?search=*&$select=id,displayName,webUrl,siteCollection&$top=999"

    while url:
        resp = await client.get(url, headers=headers)
        data = resp.json()
        for s in data.get("value", []):
            # Skip personal OneDrive sites
            web_url = s.get("webUrl", "")
            if "/personal/" in web_url:
                continue
            sites.append({
                "site_id": s["id"],
                "displayName": s.get("displayName", "Unnamed"),
                "webUrl": web_url,
                "hostname": s.get("siteCollection", {}).get("hostname", ""),
                "status": "active",
            })
        url = data.get("@odata.nextLink")

    return sites


async def provision_onedrive(
    client: httpx.AsyncClient, headers: dict,
    unprovisioned: list[dict], tenant_prefix: str
) -> int:
    """Try to provision OneDrive for users who don't have it."""
    if not unprovisioned:
        return 0

    # Method 1: SharePoint Admin bulk provisioning
    user_emails = [u["upn"] for u in unprovisioned]
    admin_url = f"https://{tenant_prefix}-admin.sharepoint.com"
    provision_url = f"{admin_url}/_api/SPO.Tenant/RequestPersonalSiteEnqueueBulk"

    resp = await client.post(
        provision_url,
        headers={
            "Authorization": headers["Authorization"],
            "Content-Type": "application/json",
            "Accept": "application/json;odata=verbose",
        },
        json={"emailIDs": user_emails, "personalSiteCreationOption": 0},
    )

    if resp.status_code < 400:
        return len(user_emails)

    # Method 2: Access each user's drive to trigger provisioning
    triggered = 0
    for user in unprovisioned:
        resp = await client.get(
            f"{GRAPH_URL}/users/{user['user_id']}/drive",
            headers=headers,
        )
        triggered += 1
        await asyncio.sleep(0.5)

    return triggered


def human_size(nbytes: int) -> str:
    """Format bytes as human-readable."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} PB"


async def main():
    parser = argparse.ArgumentParser(description="Discover M365 workloads")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    parser.add_argument("--provision", action="store_true", help="Provision OneDrive for unprovisioned users")
    parser.add_argument("--register", metavar="URL", help="Register discovered objects with backend API")
    args = parser.parse_args()

    quiet = args.json

    if not quiet:
        print("=" * 60)
        print("  M365 Workload Discovery")
        print("=" * 60)

    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
        print("ERROR: Missing credentials. Set MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET", file=sys.stderr)
        sys.exit(1)

    if not quiet:
        print(f"\n  Tenant ID: {TENANT_ID[:8]}...{TENANT_ID[-4:]}")
        print(f"  Client ID: {CLIENT_ID[:8]}...{CLIENT_ID[-4:]}")

    # Get token
    token = await get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30) as client:
        # Get tenant info
        resp = await client.get(f"{GRAPH_URL}/organization?$select=displayName,verifiedDomains", headers=headers)
        orgs = resp.json().get("value", [])
        tenant_name = orgs[0]["displayName"] if orgs else "Unknown"
        domain = ""
        for d in (orgs[0].get("verifiedDomains", []) if orgs else []):
            if d.get("isDefault"):
                domain = d["name"]
                break
        tenant_prefix = domain.replace(".onmicrosoft.com", "")

        if not quiet:
            print(f"  Tenant: {tenant_name} ({domain})\n")

        # ── Discover Users ──
        if not quiet:
            print("👥 Discovering users...")
        users = await discover_users(client, headers)
        if not quiet:
            print(f"   Found {len(users)} licensed users\n")

        # ── Discover Exchange ──
        if not quiet:
            print("📧 Discovering Exchange mailboxes...")
        mailboxes = await discover_exchange(client, headers, users)
        active_mailboxes = [m for m in mailboxes if m["status"] == "active"]
        if not quiet:
            for m in mailboxes:
                icon = "✅" if m["status"] == "active" else "❌"
                count = f" ({m['inbox_count']} inbox items)" if m["status"] == "active" else f" [{m['status']}]"
                print(f"   {icon} {m['displayName']} <{m['upn']}>{count}")
            print(f"   → {len(active_mailboxes)}/{len(users)} have active mailboxes\n")

        # ── Discover OneDrive ──
        if not quiet:
            print("💾 Discovering OneDrive accounts...")
        drives = await discover_onedrive(client, headers, users)
        active_drives = [d for d in drives if d["status"] == "active"]
        unprovisioned = [d for d in drives if d["status"] == "not_provisioned"]
        if not quiet:
            for d in drives:
                if d["status"] == "active":
                    print(f"   ✅ {d['displayName']}: {human_size(d['used_bytes'])} / {human_size(d['total_bytes'])}")
                else:
                    print(f"   ❌ {d['displayName']}: {d['status']}")
            print(f"   → {len(active_drives)}/{len(users)} have OneDrive provisioned")

            if unprovisioned and args.provision:
                print(f"\n   🔧 Provisioning OneDrive for {len(unprovisioned)} users...")
                count = await provision_onedrive(client, headers, unprovisioned, tenant_prefix)
                print(f"   ⏳ Triggered provisioning for {count} users (takes 5-15 min)")
                print(f"   👉 Re-run this script in 15 minutes to verify")
            elif unprovisioned:
                print(f"   💡 Run with --provision to trigger OneDrive for {len(unprovisioned)} users")
            print()

        # ── Discover SharePoint ──
        if not quiet:
            print("🌐 Discovering SharePoint sites...")
        sites = await discover_sharepoint(client, headers)
        if not quiet:
            for s in sites:
                print(f"   ✅ {s['displayName']}: {s['webUrl']}")
            print(f"   → {len(sites)} sites found\n")

        # ── Build manifest ──
        manifest = {
            "tenant": {
                "id": TENANT_ID,
                "name": tenant_name,
                "domain": domain,
            },
            "exchange": {
                "total_users": len(users),
                "active_mailboxes": len(active_mailboxes),
                "mailboxes": mailboxes,
            },
            "onedrive": {
                "total_users": len(users),
                "active_drives": len(active_drives),
                "not_provisioned": len(unprovisioned),
                "drives": drives,
            },
            "sharepoint": {
                "total_sites": len(sites),
                "sites": sites,
            },
            "summary": {
                "exchange_ready": len(active_mailboxes),
                "onedrive_ready": len(active_drives),
                "sharepoint_ready": len(sites),
                "onedrive_pending": len(unprovisioned),
            },
        }

        # ── Output ──
        if args.json:
            print(json.dumps(manifest, indent=2))
        else:
            print("=" * 60)
            print("  📊 Discovery Summary")
            print("=" * 60)
            print(f"   Exchange:   {len(active_mailboxes):3d} / {len(users)} mailboxes ready")
            print(f"   OneDrive:   {len(active_drives):3d} / {len(users)} drives ready")
            print(f"   SharePoint: {len(sites):3d} sites ready")
            if unprovisioned:
                print(f"\n   ⚠️  {len(unprovisioned)} users need OneDrive provisioning")
                if not args.provision:
                    print(f"      Run: python scripts/discover_m365.py --provision")
            print()

        # ── Register with backend ──
        if args.register:
            if not quiet:
                print(f"\n📡 Registering discovered objects with {args.register}...")
            # TODO: Implement backend registration
            # This would call the tenant API to update backup objects
            # based on what's actually available
            print("   (Registration not yet implemented — use the UI to onboard)")

        # Save manifest
        manifest_path = Path(__file__).parent.parent / "m365_discovery.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        if not quiet:
            print(f"   💾 Manifest saved to: {manifest_path}")


if __name__ == "__main__":
    asyncio.run(main())
