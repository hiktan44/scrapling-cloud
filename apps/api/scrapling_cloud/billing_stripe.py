"""Stripe self-serve billing: checkout, customer portal, webhook handling.

Every function degrades gracefully when Stripe is not configured so the API
stays deployable before live keys are added (endpoints return 503).
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from .config import get_settings
from .models import Organization, UsageEvent
from .plans import DEFAULT_PLAN, PLANS, plan_for_price_id, plan_price_id

logger = logging.getLogger(__name__)


class StripeNotConfigured(RuntimeError):
    pass


def _client():
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise StripeNotConfigured("Stripe is not configured (STRIPE_SECRET_KEY unset).")
    import stripe

    stripe.api_key = settings.stripe_secret_key
    return stripe


def create_checkout_session(db: Session, organization: Organization, plan_key: str, success_url: str, cancel_url: str) -> str:
    if plan_key not in PLANS or plan_key == DEFAULT_PLAN:
        raise ValueError("Choose a paid plan (growth or scale).")
    price_id = plan_price_id(plan_key)
    if not price_id:
        raise StripeNotConfigured(f"No Stripe price configured for plan '{plan_key}'.")
    stripe = _client()

    customer_id = organization.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(name=organization.name, metadata={"organization_id": organization.id})
        customer_id = customer["id"]
        organization.stripe_customer_id = customer_id
        db.commit()

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"organization_id": organization.id, "plan": plan_key},
    )
    return session["url"]


def create_portal_session(organization: Organization, return_url: str) -> str:
    if not organization.stripe_customer_id:
        raise ValueError("No Stripe customer for this organization yet. Subscribe first.")
    stripe = _client()
    session = stripe.billing_portal.Session.create(customer=organization.stripe_customer_id, return_url=return_url)
    return session["url"]


def apply_plan(db: Session, organization: Organization, plan_key: str, refill: bool = True) -> None:
    """Set an org's plan and limits; optionally reset the monthly credit usage."""
    plan = PLANS.get(plan_key)
    if plan is None:
        return
    organization.plan = plan.key
    organization.monthly_credits = plan.monthly_credits
    organization.concurrency_limit = plan.concurrency_limit
    if refill:
        organization.used_credits = 0
        db.add(UsageEvent(organization_id=organization.id, credits=0, reason=f"plan_activated:{plan.key}"))
    db.commit()


def verify_and_parse_event(payload: bytes, signature: str | None) -> dict:
    settings = get_settings()
    stripe = _client()
    if settings.stripe_webhook_secret and signature:
        return stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    # No signing secret configured: parse without verification (dev only).
    import json

    logger.warning("stripe webhook signature not verified (STRIPE_WEBHOOK_SECRET unset)")
    return json.loads(payload)


def handle_event(db: Session, event: dict) -> str:
    event_type = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}

    def org_by_customer(customer_id: str | None) -> Organization | None:
        if not customer_id:
            return None
        from sqlalchemy import select

        return db.scalar(select(Organization).where(Organization.stripe_customer_id == customer_id))

    if event_type == "checkout.session.completed":
        org_id = (obj.get("metadata") or {}).get("organization_id")
        plan_key = (obj.get("metadata") or {}).get("plan")
        org = db.get(Organization, org_id) if org_id else org_by_customer(obj.get("customer"))
        if org:
            if obj.get("subscription"):
                org.stripe_subscription_id = obj["subscription"]
            apply_plan(db, org, plan_key or org.plan)
            return f"activated:{plan_key}"

    elif event_type in {"invoice.paid", "invoice.payment_succeeded"}:
        # Monthly renewal: refill the credit allowance.
        org = org_by_customer(obj.get("customer"))
        if org:
            apply_plan(db, org, org.plan, refill=True)
            return "renewed"

    elif event_type == "customer.subscription.updated":
        org = org_by_customer(obj.get("customer"))
        items = (obj.get("items") or {}).get("data") or []
        price_id = items[0]["price"]["id"] if items and items[0].get("price") else None
        plan = plan_for_price_id(price_id) if price_id else None
        if org and plan:
            org.stripe_subscription_id = obj.get("id")
            apply_plan(db, org, plan.key, refill=False)
            return f"updated:{plan.key}"

    elif event_type == "customer.subscription.deleted":
        org = org_by_customer(obj.get("customer"))
        if org:
            org.stripe_subscription_id = None
            apply_plan(db, org, DEFAULT_PLAN, refill=False)
            return "downgraded"

    return f"ignored:{event_type}"
