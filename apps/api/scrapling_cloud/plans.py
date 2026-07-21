"""Subscription plan catalog.

Maps plan keys to their monthly credit allowance and concurrency limit, and
to the Stripe price ID configured for that plan (via env). Keeping this in one
place lets the Stripe webhook translate a subscription into an org's limits.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import get_settings


@dataclass(frozen=True)
class Plan:
    key: str
    name: str
    monthly_credits: int
    concurrency_limit: int
    monthly_price_usd: int


PLANS: dict[str, Plan] = {
    "starter": Plan("starter", "Starter", 10_000, 3, 0),
    "growth": Plan("growth", "Growth", 50_000, 8, 49),
    "scale": Plan("scale", "Scale", 200_000, 20, 199),
}

DEFAULT_PLAN = "starter"


def get_plan(key: str) -> Plan | None:
    return PLANS.get(key)


def plan_price_id(key: str) -> str | None:
    """Stripe price ID for a plan, read from settings (env)."""
    settings = get_settings()
    return {
        "growth": settings.stripe_price_growth,
        "scale": settings.stripe_price_scale,
    }.get(key)


def plan_for_price_id(price_id: str) -> Plan | None:
    settings = get_settings()
    mapping = {
        settings.stripe_price_growth: PLANS["growth"],
        settings.stripe_price_scale: PLANS["scale"],
    }
    return mapping.get(price_id)
