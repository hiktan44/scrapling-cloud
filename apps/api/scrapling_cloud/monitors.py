"""Scheduled page monitoring: periodic scrape + diff + optional AI judgment.

The worker's monitor sweep calls run_monitor_check for every due monitor;
the API exposes the same function for manual "run now" triggers.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .analyzer import judge_change
from .jobs import post_signed_webhook
from .models import Monitor, MonitorCheck, Organization, UsageEvent
from .scraper import scrape_url
from .tracking import compute_change

logger = logging.getLogger(__name__)

MAX_CHECKS_PER_SWEEP = 20


def check_cost(monitor: Monitor) -> int:
    credits = 1
    if monitor.mode == "dynamic":
        credits += 4
    if monitor.mode == "stealth":
        credits += 8
    if monitor.judge_enabled:
        credits += 1
    return credits


def _charge(db: Session, organization: Organization, credits: int, monitor_id: str) -> bool:
    if organization.monthly_credits - organization.used_credits < credits:
        return False
    organization.used_credits += credits
    db.add(UsageEvent(organization_id=organization.id, credits=credits, reason=f"monitor_check:{monitor_id}"))
    return True


async def run_monitor_check(db: Session, monitor: Monitor) -> MonitorCheck:
    organization = db.get(Organization, monitor.organization_id)
    credits = check_cost(monitor)
    check = MonitorCheck(monitor_id=monitor.id, organization_id=monitor.organization_id, change_status="error", credits=0)

    if organization is None or not _charge(db, organization, credits, monitor.id):
        check.error = "Insufficient credits for monitor check."
        monitor.last_checked_at = datetime.utcnow()
        monitor.last_status = "error"
        db.add(check)
        db.commit()
        return check

    check.credits = credits
    try:
        scraped = await scrape_url({"url": monitor.url, "formats": ["markdown"], "mode": monitor.mode, "only_main_content": True})
        change = compute_change(db, monitor.organization_id, monitor.url, scraped.get("markdown") or "", tag=f"monitor:{monitor.id}")
        check.change_status = change["change_status"]
        check.diff = change.get("diff")
        check.error = None

        if monitor.judge_enabled and monitor.goal and change["change_status"] == "changed" and change.get("diff"):
            verdict = await judge_change(monitor.goal, change["diff"], monitor.url)
            check.meaningful = verdict.get("meaningful")
            check.reason = verdict.get("reason")
    except Exception as exc:
        check.change_status = "error"
        check.error = str(exc)[:1000]

    monitor.last_checked_at = datetime.utcnow()
    monitor.last_status = check.change_status
    db.add(check)
    db.commit()

    if monitor.webhook_url and _should_notify(monitor, check):
        try:
            await post_signed_webhook(
                monitor.webhook_url,
                {
                    "event": "monitor.check",
                    "monitor_id": monitor.id,
                    "monitor_name": monitor.name,
                    "url": monitor.url,
                    "change_status": check.change_status,
                    "meaningful": check.meaningful,
                    "reason": check.reason,
                    "diff": check.diff,
                    "error": check.error,
                    "checked_at": monitor.last_checked_at.isoformat(),
                },
                monitor.organization_id,
                f"monitor {monitor.id}",
            )
        except Exception:
            logger.exception("monitor webhook delivery failed for %s", monitor.id)
    return check


def _should_notify(monitor: Monitor, check: MonitorCheck) -> bool:
    if monitor.notify_on == "always":
        return True
    if check.change_status != "changed":
        return False
    if monitor.notify_on == "meaningful":
        # Judge unavailable (None) still notifies - missing a real change is
        # worse than a false alarm.
        return check.meaningful is not False
    return True  # notify_on == "changed"


def due_monitors(db: Session, limit: int = MAX_CHECKS_PER_SWEEP) -> list[Monitor]:
    now = datetime.utcnow()
    monitors = db.scalars(select(Monitor).where(Monitor.enabled.is_(True)).order_by(Monitor.last_checked_at)).all()
    due: list[Monitor] = []
    for monitor in monitors:
        if monitor.last_checked_at is None or monitor.last_checked_at <= now - timedelta(minutes=monitor.interval_minutes):
            due.append(monitor)
        if len(due) >= limit:
            break
    return due
