"""OIDC authentication service for Entra ID SSO.

Handles:
- Authorization URL generation for Entra ID login
- Authorization code exchange for tokens
- User info extraction from ID token claims
- Auto-provisioning users on first SSO login
"""
import logging
from datetime import datetime

import msal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


class OIDCAuthService:
    """Entra ID OIDC authentication."""

    def __init__(self):
        self._app = None

    @property
    def enabled(self) -> bool:
        return settings.SSO_ENABLED and bool(settings.SSO_CLIENT_ID)

    def _get_msal_app(self) -> msal.ConfidentialClientApplication:
        """Get or create MSAL confidential client app."""
        if not self._app:
            authority = f"https://login.microsoftonline.com/{settings.SSO_TENANT_ID}"
            self._app = msal.ConfidentialClientApplication(
                client_id=settings.SSO_CLIENT_ID,
                client_credential=settings.SSO_CLIENT_SECRET,
                authority=authority,
            )
        return self._app

    def get_authorization_url(self, state: str = None) -> dict:
        """Generate Entra ID authorization URL for SSO login."""
        if not self.enabled:
            raise ValueError("SSO is not enabled")

        app = self._get_msal_app()
        flow = app.initiate_auth_code_flow(
            scopes=["openid", "profile", "email"],
            redirect_uri=settings.SSO_REDIRECT_URI,
            state=state,
        )

        return {
            "auth_url": flow.get("auth_uri"),
            "state": flow.get("state"),
            "flow": flow,  # Must be stored server-side for callback
        }

    async def exchange_code(self, code: str, flow: dict) -> dict:
        """Exchange authorization code for tokens."""
        app = self._get_msal_app()

        result = app.acquire_token_by_auth_code_flow(
            auth_code_flow=flow,
            auth_response={"code": code, "state": flow.get("state")},
        )

        if "error" in result:
            raise ValueError(f"Token exchange failed: {result.get('error_description', result.get('error'))}")

        return {
            "access_token": result.get("access_token"),
            "id_token": result.get("id_token"),
            "id_token_claims": result.get("id_token_claims", {}),
        }

    def get_user_info(self, id_token_claims: dict) -> dict:
        """Extract user info from ID token claims."""
        return {
            "subject_id": id_token_claims.get("oid") or id_token_claims.get("sub"),
            "email": id_token_claims.get("preferred_username") or id_token_claims.get("email"),
            "name": id_token_claims.get("name"),
            "given_name": id_token_claims.get("given_name"),
            "family_name": id_token_claims.get("family_name"),
            "tenant_id": id_token_claims.get("tid"),
        }

    async def provision_user(self, claims: dict, db: AsyncSession) -> User:
        """Find or create a user from SSO claims.

        On first login: creates a new User with role=VIEWER.
        On subsequent logins: returns existing user.
        """
        subject_id = claims["subject_id"]
        email = claims["email"]

        # Look up by SSO subject ID first
        result = await db.execute(
            select(User).where(
                User.sso_provider == "entra_id",
                User.sso_subject_id == subject_id,
            )
        )
        user = result.scalar_one_or_none()

        if user:
            # Update last login info
            user.full_name = claims.get("name") or user.full_name
            user.updated_at = datetime.utcnow()
            await db.flush()
            return user

        # Check if a local user exists with same email (link accounts)
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if user:
            # Link SSO to existing account
            user.sso_provider = "entra_id"
            user.sso_subject_id = subject_id
            user.full_name = claims.get("name") or user.full_name
            user.updated_at = datetime.utcnow()
            await db.flush()
            logger.info(f"Linked SSO to existing user: {email}")
            return user

        # Create new user
        username = email.split("@")[0] if email else f"sso_{subject_id[:8]}"

        # Ensure unique username
        existing = await db.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none():
            username = f"{username}_{subject_id[:4]}"

        user = User(
            username=username,
            email=email,
            password_hash=None,  # SSO-only, no password
            full_name=claims.get("name"),
            role=UserRole.VIEWER,  # Default role; admin upgrades manually
            is_active=1,
            sso_provider="entra_id",
            sso_subject_id=subject_id,
        )
        db.add(user)
        await db.flush()
        logger.info(f"Auto-provisioned SSO user: {email} (role=viewer)")
        return user


# Singleton
oidc_service = OIDCAuthService()
