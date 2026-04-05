"""Stripe Billing API — checkout, portal, webhooks, subscription management.

Endpoints:
- POST /api/billing/checkout — create Stripe Checkout session (redirect URL)
- POST /api/billing/portal — create Stripe Customer Portal session
- GET  /api/billing/subscription — current subscription status
- GET  /api/billing/config — publishable key for frontend
- POST /api/billing/webhook — Stripe webhook handler (no auth)
"""
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/billing", tags=["Billing"])

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Price ID → tier mapping
PRICE_TO_TIER = {}


def _init_price_map():
    """Build price → tier mapping from config."""
    global PRICE_TO_TIER
    if settings.STRIPE_PRICE_PROFESSIONAL:
        PRICE_TO_TIER[settings.STRIPE_PRICE_PROFESSIONAL] = "professional"
    if settings.STRIPE_PRICE_BUSINESS:
        PRICE_TO_TIER[settings.STRIPE_PRICE_BUSINESS] = "business"
    if settings.STRIPE_PRICE_ENTERPRISE:
        PRICE_TO_TIER[settings.STRIPE_PRICE_ENTERPRISE] = "enterprise"


_init_price_map()


# ── Models ──

class CheckoutRequest(BaseModel):
    tenant_id: int
    price_id: str
    quantity: int = 1  # Number of users
    success_url: str = None
    cancel_url: str = None


class PortalRequest(BaseModel):
    tenant_id: int


# ── Endpoints ──

@router.get("/config")
async def billing_config():
    """Return publishable key and price IDs for frontend."""
    return {
        "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "prices": {
            "professional": settings.STRIPE_PRICE_PROFESSIONAL,
            "business": settings.STRIPE_PRICE_BUSINESS,
            "enterprise": settings.STRIPE_PRICE_ENTERPRISE,
        },
        "trial_days": settings.TRIAL_PERIOD_DAYS,
    }


@router.post("/checkout")
async def create_checkout(
    req: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout session. Returns URL to redirect user to."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(503, detail="Stripe not configured")

    tenant = await db.get(Tenant, req.tenant_id)
    if not tenant:
        raise HTTPException(404, detail="Tenant not found")

    # Create or retrieve Stripe customer
    if not tenant.stripe_customer_id:
        customer = stripe.Customer.create(
            email=current_user.email,
            name=tenant.name,
            metadata={"tenant_id": str(tenant.id), "kavachiq_user": current_user.username},
        )
        tenant.stripe_customer_id = customer.id
        await db.commit()

    # Build success/cancel URLs
    frontend = settings.FRONTEND_URL.rstrip("/")
    success_url = req.success_url or f"{frontend}/billing?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = req.cancel_url or f"{frontend}/billing?canceled=true"

    # Create checkout session with trial
    session = stripe.checkout.Session.create(
        customer=tenant.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{
            "price": req.price_id,
            "quantity": req.quantity,
        }],
        mode="subscription",
        subscription_data={
            "trial_period_days": settings.TRIAL_PERIOD_DAYS,
            "metadata": {"tenant_id": str(tenant.id)},
        },
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"tenant_id": str(tenant.id)},
    )

    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/portal")
async def create_portal(
    req: PortalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Customer Portal session for self-serve management."""
    tenant = await db.get(Tenant, req.tenant_id)
    if not tenant or not tenant.stripe_customer_id:
        raise HTTPException(400, detail="No billing account found. Start a subscription first.")

    frontend = settings.FRONTEND_URL.rstrip("/")
    session = stripe.billing_portal.Session.create(
        customer=tenant.stripe_customer_id,
        return_url=f"{frontend}/billing",
    )

    return {"portal_url": session.url}


@router.get("/subscription")
async def get_subscription(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current subscription status for a tenant."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404, detail="Tenant not found")

    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "stripe_customer_id": tenant.stripe_customer_id,
        "subscription_id": tenant.subscription_id,
        "subscription_status": tenant.subscription_status or "free",
        "subscription_tier": tenant.subscription_tier or "community",
        "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
        "current_period_end": tenant.current_period_end.isoformat() if tenant.current_period_end else None,
    }


# ── Stripe Webhook ──

@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events. No auth — uses webhook signature verification."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if settings.STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError:
            raise HTTPException(400, detail="Invalid webhook signature")
    else:
        # Dev mode — no signature verification
        import json
        event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info(f"Stripe webhook: {event_type}")

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data, db)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(data, db)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data, db)
    elif event_type == "customer.subscription.trial_will_end":
        await _handle_trial_ending(data, db)
    elif event_type == "invoice.paid":
        await _handle_invoice_paid(data, db)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(data, db)
    else:
        logger.info(f"Unhandled Stripe event: {event_type}")

    return {"status": "ok"}


# ── Webhook Handlers ──

async def _handle_checkout_completed(session: dict, db: AsyncSession):
    """Checkout completed — activate subscription."""
    tenant_id = session.get("metadata", {}).get("tenant_id")
    if not tenant_id:
        logger.warning("Checkout session missing tenant_id metadata")
        return

    tenant = await db.get(Tenant, int(tenant_id))
    if not tenant:
        return

    subscription_id = session.get("subscription")
    if subscription_id:
        # Fetch subscription to get tier
        sub = stripe.Subscription.retrieve(subscription_id)
        price_id = sub["items"]["data"][0]["price"]["id"] if sub["items"]["data"] else None
        tier = PRICE_TO_TIER.get(price_id, "professional")

        tenant.subscription_id = subscription_id
        tenant.subscription_status = sub.get("status", "active")
        tenant.subscription_tier = tier
        if sub.get("trial_end"):
            from datetime import datetime
            tenant.trial_ends_at = datetime.fromtimestamp(sub["trial_end"])
        if sub.get("current_period_end"):
            from datetime import datetime
            tenant.current_period_end = datetime.fromtimestamp(sub["current_period_end"])

        await db.commit()
        logger.info(f"Tenant {tenant_id} subscription activated: {tier} ({tenant.subscription_status})")


async def _handle_subscription_updated(sub: dict, db: AsyncSession):
    """Subscription changed — update tier/status."""
    tenant_id = sub.get("metadata", {}).get("tenant_id")
    if not tenant_id:
        return

    tenant = await db.get(Tenant, int(tenant_id))
    if not tenant:
        return

    price_id = sub["items"]["data"][0]["price"]["id"] if sub.get("items", {}).get("data") else None
    tier = PRICE_TO_TIER.get(price_id, tenant.subscription_tier)

    tenant.subscription_status = sub.get("status", tenant.subscription_status)
    tenant.subscription_tier = tier
    if sub.get("current_period_end"):
        from datetime import datetime
        tenant.current_period_end = datetime.fromtimestamp(sub["current_period_end"])

    await db.commit()
    logger.info(f"Tenant {tenant_id} subscription updated: {tier} ({tenant.subscription_status})")


async def _handle_subscription_deleted(sub: dict, db: AsyncSession):
    """Subscription canceled — downgrade to community."""
    tenant_id = sub.get("metadata", {}).get("tenant_id")
    if not tenant_id:
        return

    tenant = await db.get(Tenant, int(tenant_id))
    if not tenant:
        return

    tenant.subscription_status = "canceled"
    tenant.subscription_tier = "community"
    await db.commit()
    logger.info(f"Tenant {tenant_id} subscription canceled → community")


async def _handle_trial_ending(sub: dict, db: AsyncSession):
    """Trial ending in 3 days — send reminder email."""
    tenant_id = sub.get("metadata", {}).get("tenant_id")
    if not tenant_id:
        return

    # Find user email for this tenant
    tenant = await db.get(Tenant, int(tenant_id))
    if not tenant or not tenant.stripe_customer_id:
        return

    try:
        customer = stripe.Customer.retrieve(tenant.stripe_customer_id)
        email = customer.get("email")
        if email:
            from app.services.email_service import email_service
            await email_service.send_trial_reminder(email, customer.get("name", ""), 3)
            logger.info(f"Trial reminder sent to {email} for tenant {tenant_id}")
    except Exception as e:
        logger.warning(f"Failed to send trial reminder: {e}")


async def _handle_invoice_paid(invoice: dict, db: AsyncSession):
    """Invoice paid — update period end."""
    sub_id = invoice.get("subscription")
    if not sub_id:
        return

    result = await db.execute(select(Tenant).where(Tenant.subscription_id == sub_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return

    if invoice.get("period_end"):
        from datetime import datetime
        tenant.current_period_end = datetime.fromtimestamp(invoice["period_end"])
    tenant.subscription_status = "active"
    await db.commit()


async def _handle_payment_failed(invoice: dict, db: AsyncSession):
    """Payment failed — set past_due, send email."""
    sub_id = invoice.get("subscription")
    if not sub_id:
        return

    result = await db.execute(select(Tenant).where(Tenant.subscription_id == sub_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return

    tenant.subscription_status = "past_due"
    await db.commit()

    # Send payment failed email
    if tenant.stripe_customer_id:
        try:
            customer = stripe.Customer.retrieve(tenant.stripe_customer_id)
            email = customer.get("email")
            if email:
                from app.services.email_service import email_service
                await email_service.send_payment_failed(email, customer.get("name", ""))
        except Exception as e:
            logger.warning(f"Failed to send payment failed email: {e}")

    logger.info(f"Tenant {tenant.id} payment failed → past_due")
