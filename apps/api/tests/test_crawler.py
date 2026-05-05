import pytest

from scrapling_cloud import scraper


@pytest.mark.asyncio
async def test_crawl_follows_same_site_links(monkeypatch) -> None:
    pages = {
        "https://example.com/start": '<html><head><title>Start</title></head><body><a href="/next">Next</a><a href="https://other.test/out">Out</a></body></html>',
        "https://example.com/next": "<html><head><title>Next</title></head><body>Deep text</body></html>",
    }

    async def fake_fetch(url: str, mode: str = "static", wait_for: str | None = None) -> str:
        return pages[url]

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch)
    result = await scraper.crawl_url({"url": "https://example.com/start", "limit": 5, "max_depth": 2})

    assert result["pages_scraped"] == 2
    assert [page["url"] for page in result["pages"]] == ["https://example.com/start", "https://example.com/next"]
    assert "https://other.test/out" not in result["discovered"]


def test_extract_record_from_topic_url() -> None:
    record = scraper.extract_record_from_url(
        "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/digital-2025-ai-continuum"
    )

    assert record is not None
    assert record["title"] == "Digital AI Continuum"
    assert record["program"] == "Digital Europe"
    assert record["years"] == ["2025"]


def test_topic_index_is_not_extracted_as_record() -> None:
    record = scraper.extract_record_from_url("https://ec.europa.eu/info/funding-tenders/opportunities/data/topic-list.html")

    assert record is None
