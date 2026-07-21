import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scrapling_cloud.db import Base
from scrapling_cloud.models import Organization
from scrapling_cloud.schemas import ExtractRequest
from scrapling_cloud.tracking import compute_change


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    org = Organization(name="Test Org")
    session.add(org)
    session.commit()
    yield session, org.id
    session.close()


def test_change_tracking_new_same_changed(db_session) -> None:
    session, org_id = db_session

    first = compute_change(session, org_id, "https://x.test/page", "# Hello\ncontent v1")
    session.commit()
    assert first["change_status"] == "new"
    assert first["diff"] is None

    same = compute_change(session, org_id, "https://x.test/page", "# Hello\ncontent v1")
    session.commit()
    assert same["change_status"] == "same"
    assert same["previous_scrape_at"] is not None

    changed = compute_change(session, org_id, "https://x.test/page", "# Hello\ncontent v2")
    session.commit()
    assert changed["change_status"] == "changed"
    assert "-content v1" in changed["diff"]
    assert "+content v2" in changed["diff"]


def test_change_tracking_tags_are_isolated(db_session) -> None:
    session, org_id = db_session
    compute_change(session, org_id, "https://x.test/p", "v1", tag="")
    session.commit()
    tagged = compute_change(session, org_id, "https://x.test/p", "v1", tag="monitor:1")
    session.commit()
    assert tagged["change_status"] == "new"


def test_extract_request_accepts_urls_and_wildcards() -> None:
    request = ExtractRequest(urls=["https://x.test/a", "https://x.test/blog/*"], prompt="extract titles")
    assert request.urls is not None and len(request.urls) == 2

    with pytest.raises(ValueError):
        ExtractRequest(prompt="no targets given")

    with pytest.raises(ValueError):
        ExtractRequest(urls=["ftp://bad.example"], prompt="x")


def test_extract_request_single_url_still_works() -> None:
    request = ExtractRequest(url="https://x.test", prompt="extract")
    assert str(request.url).startswith("https://x.test")


def test_extract_multi_url_billing() -> None:
    from scrapling_cloud.billing import estimate_credits

    single = estimate_credits("extract", {"url": "https://x.test", "prompt": "p"})
    multi = estimate_credits("extract", {"urls": ["https://a.test", "https://b.test", "https://c.test"], "prompt": "p"})
    assert multi == single + 4
