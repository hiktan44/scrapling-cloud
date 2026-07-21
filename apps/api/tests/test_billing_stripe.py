import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scrapling_cloud import billing_stripe
from scrapling_cloud.db import Base
from scrapling_cloud.models import Organization
from scrapling_cloud.plans import PLANS, get_plan, plan_for_price_id


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    org = Organization(name="Bill Org", plan="starter", monthly_credits=10000, used_credits=5000, concurrency_limit=3)
    session.add(org)
    session.commit()
    yield session, org
    session.close()


def test_plan_catalog() -> None:
    assert set(PLANS) == {"starter", "growth", "scale"}
    assert get_plan("growth").monthly_credits == 50_000
    assert get_plan("unknown") is None


def test_apply_plan_upgrades_and_refills(db_session) -> None:
    session, org = db_session
    billing_stripe.apply_plan(session, org, "growth")
    assert org.plan == "growth"
    assert org.monthly_credits == 50_000
    assert org.concurrency_limit == 8
    assert org.used_credits == 0


def test_apply_plan_downgrade_no_refill(db_session) -> None:
    session, org = db_session
    org.used_credits = 4000
    billing_stripe.apply_plan(session, org, "starter", refill=False)
    assert org.plan == "starter"
    assert org.used_credits == 4000  # preserved on downgrade


def test_checkout_requires_stripe_config(db_session, monkeypatch) -> None:
    session, org = db_session

    class FakeSettings:
        stripe_secret_key = ""
        stripe_price_growth = ""
        stripe_price_scale = ""

    monkeypatch.setattr(billing_stripe, "get_settings", lambda: FakeSettings())
    from scrapling_cloud import plans as plans_module

    monkeypatch.setattr(plans_module, "get_settings", lambda: FakeSettings())
    with pytest.raises(billing_stripe.StripeNotConfigured):
        billing_stripe.create_checkout_session(session, org, "growth", "https://ok", "https://cancel")


def test_checkout_rejects_free_plan(db_session) -> None:
    session, org = db_session
    with pytest.raises(ValueError):
        billing_stripe.create_checkout_session(session, org, "starter", "https://ok", "https://cancel")


def test_handle_checkout_completed_event(db_session) -> None:
    session, org = db_session
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"organization_id": org.id, "plan": "growth"}, "subscription": "sub_123", "customer": "cus_1"}},
    }
    result = billing_stripe.handle_event(session, event)
    assert result == "activated:growth"
    assert org.plan == "growth"
    assert org.stripe_subscription_id == "sub_123"


def test_handle_subscription_deleted_downgrades(db_session) -> None:
    session, org = db_session
    org.stripe_customer_id = "cus_9"
    org.plan = "growth"
    org.stripe_subscription_id = "sub_9"
    session.commit()
    event = {"type": "customer.subscription.deleted", "data": {"object": {"customer": "cus_9", "id": "sub_9"}}}
    result = billing_stripe.handle_event(session, event)
    assert result == "downgraded"
    assert org.plan == "starter"
    assert org.stripe_subscription_id is None
