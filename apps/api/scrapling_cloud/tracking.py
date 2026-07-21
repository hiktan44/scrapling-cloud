"""Change tracking (Firecrawl changeTracking parity, git-diff mode).

Stores the last markdown per (organization, url, tag) and reports
new/same/changed with a unified diff on subsequent scrapes.
"""

from __future__ import annotations

import difflib
import hashlib
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import PageSnapshot

MAX_STORED_CHARS = 200_000
MAX_DIFF_CHARS = 50_000


def compute_change(db: Session, organization_id: str, url: str, markdown: str, tag: str = "") -> dict:
    """Compare markdown against the stored snapshot and update it. Caller commits."""
    content = (markdown or "")[:MAX_STORED_CHARS]
    digest = hashlib.sha256(content.encode()).hexdigest()
    snapshot = db.scalar(
        select(PageSnapshot).where(
            PageSnapshot.organization_id == organization_id,
            PageSnapshot.url == url,
            PageSnapshot.tag == tag,
        )
    )
    now = datetime.utcnow()

    if snapshot is None:
        db.add(
            PageSnapshot(
                organization_id=organization_id,
                url=url[:2000],
                tag=tag,
                markdown_hash=digest,
                markdown=content,
                scraped_at=now,
            )
        )
        return {"change_status": "new", "previous_scrape_at": None, "diff": None}

    previous_at = snapshot.scraped_at.isoformat() if snapshot.scraped_at else None
    if snapshot.markdown_hash == digest:
        snapshot.scraped_at = now
        return {"change_status": "same", "previous_scrape_at": previous_at, "diff": None}

    diff_text = "\n".join(
        difflib.unified_diff(
            snapshot.markdown.splitlines(),
            content.splitlines(),
            fromfile="previous",
            tofile="current",
            lineterm="",
        )
    )[:MAX_DIFF_CHARS]
    snapshot.markdown = content
    snapshot.markdown_hash = digest
    snapshot.scraped_at = now
    return {"change_status": "changed", "previous_scrape_at": previous_at, "diff": diff_text}
