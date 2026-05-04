from scrapling_cloud.billing import estimate_credits
from scrapling_cloud.models import JobKind


def test_static_scrape_is_low_credit() -> None:
    assert estimate_credits(JobKind.scrape.value, {"formats": ["markdown"], "mode": "static"}) == 1


def test_dynamic_screenshot_schema_costs_more() -> None:
    credits = estimate_credits(
        JobKind.scrape.value,
        {"formats": ["markdown", "screenshot"], "mode": "dynamic", "schema": {"properties": {"title": {}}}},
    )
    assert credits == 11


def test_batch_scales_by_url_count() -> None:
    assert estimate_credits(JobKind.batch.value, {"urls": ["https://a.test", "https://b.test"]}) == 2
