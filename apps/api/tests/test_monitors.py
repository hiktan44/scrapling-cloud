import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scrapling_cloud.db import Base
from scrapling_cloud.models import Monitor, MonitorCheck, Organization
from scrapling_cloud.monitors import _should_notify, check_cost, due_monitors, run_monitor_check


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    org = Organization(name="Mon Org", monthly_credits=100)
    session.add(org)
    session.commit()
    yield session, org
    session.close()


def make_monitor(session, org, **kwargs):
    defaults = dict(organization_id=org.id, name="test", url="https://x.test/page", interval_minutes=5)
    defaults.update(kwargs)
    monitor = Monitor(**defaults)
    session.add(monitor)
    session.commit()
    return monitor


def test_check_cost_by_mode_and_judge(db_session) -> None:
    session, org = db_session
    assert check_cost(make_monitor(session, org)) == 1
    assert check_cost(make_monitor(session, org, mode="dynamic")) == 5
    assert check_cost(make_monitor(session, org, mode="stealth", judge_enabled=True)) == 10


def test_due_monitors_selects_never_checked_and_overdue(db_session) -> None:
    session, org = db_session
    from datetime import datetime, timedelta

    never = make_monitor(session, org)
    overdue = make_monitor(session, org)
    overdue.last_checked_at = datetime.utcnow() - timedelta(minutes=10)
    fresh = make_monitor(session, org)
    fresh.last_checked_at = datetime.utcnow()
    disabled = make_monitor(session, org, enabled=False)
    session.commit()

    due_ids = {monitor.id for monitor in due_monitors(session)}
    assert never.id in due_ids
    assert overdue.id in due_ids
    assert fresh.id not in due_ids
    assert disabled.id not in due_ids


@pytest.mark.asyncio
async def test_run_monitor_check_detects_change(monkeypatch, db_session) -> None:
    session, org = db_session
    monitor = make_monitor(session, org)
    content = {"value": "# v1"}

    async def fake_scrape(payload):
        return {"url": payload["url"], "markdown": content["value"]}

    from scrapling_cloud import monitors as monitors_module

    monkeypatch.setattr(monitors_module, "scrape_url", fake_scrape)

    first = await run_monitor_check(session, monitor)
    assert first.change_status == "new"

    second = await run_monitor_check(session, monitor)
    assert second.change_status == "same"

    content["value"] = "# v2"
    third = await run_monitor_check(session, monitor)
    assert third.change_status == "changed"
    assert "+# v2" in third.diff
    assert org.used_credits == 3


@pytest.mark.asyncio
async def test_run_monitor_check_insufficient_credits(db_session) -> None:
    session, org = db_session
    org.used_credits = org.monthly_credits
    monitor = make_monitor(session, org)
    check = await run_monitor_check(session, monitor)
    assert check.change_status == "error"
    assert "credits" in check.error.lower()
    assert check.credits == 0


def test_should_notify_matrix(db_session) -> None:
    session, org = db_session
    monitor = make_monitor(session, org, notify_on="changed")

    changed = MonitorCheck(monitor_id=monitor.id, organization_id=org.id, change_status="changed")
    same = MonitorCheck(monitor_id=monitor.id, organization_id=org.id, change_status="same")
    assert _should_notify(monitor, changed)
    assert not _should_notify(monitor, same)

    monitor.notify_on = "always"
    assert _should_notify(monitor, same)

    monitor.notify_on = "meaningful"
    changed.meaningful = False
    assert not _should_notify(monitor, changed)
    changed.meaningful = True
    assert _should_notify(monitor, changed)
    changed.meaningful = None
    assert _should_notify(monitor, changed)
