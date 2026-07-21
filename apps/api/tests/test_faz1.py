import io

import pytest

from scrapling_cloud import scraper
from scrapling_cloud.parse import parse_file


HTML = """<html><body>
  <nav>Menu</nav>
  <main>
    <h1>Title</h1>
    <p class="lead">Lead paragraph</p>
    <div class="ads">Buy now!</div>
    <img src="/a.png"><img src="https://cdn.example.com/b.jpg"><img src="data:image/png;base64,x">
  </main>
</body></html>"""


@pytest.mark.asyncio
async def test_new_formats_raw_html_and_images(monkeypatch) -> None:
    async def fake_fetch(url, mode="static", wait_for=None, proxy=None, headers=None, static_timeout=45, dynamic_timeout=90):
        return HTML

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch)
    result = await scraper.scrape_url({"url": "https://example.com/page", "formats": ["raw_html", "images"]})
    assert result["raw_html"] == HTML
    assert result["images"] == ["https://example.com/a.png", "https://cdn.example.com/b.jpg"]


@pytest.mark.asyncio
async def test_exclude_tags_filters_content(monkeypatch) -> None:
    async def fake_fetch(url, mode="static", wait_for=None, proxy=None, headers=None, static_timeout=45, dynamic_timeout=90):
        return HTML

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch)
    result = await scraper.scrape_url(
        {"url": "https://example.com", "formats": ["markdown"], "exclude_tags": [".ads"]}
    )
    assert "Buy now" not in result["markdown"]
    assert "Lead paragraph" in result["markdown"]


@pytest.mark.asyncio
async def test_include_tags_keeps_only_selection(monkeypatch) -> None:
    async def fake_fetch(url, mode="static", wait_for=None, proxy=None, headers=None, static_timeout=45, dynamic_timeout=90):
        return HTML

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch)
    result = await scraper.scrape_url(
        {"url": "https://example.com", "formats": ["markdown"], "include_tags": ["p.lead"]}
    )
    assert "Lead paragraph" in result["markdown"]
    assert "Title" not in result["markdown"]


def test_request_headers_mobile_adds_user_agent() -> None:
    headers = scraper._request_headers({"mobile": True})
    assert "iPhone" in headers["User-Agent"]
    explicit = scraper._request_headers({"mobile": True, "headers": {"User-Agent": "custom"}})
    assert explicit["User-Agent"] == "custom"


def test_request_timeouts_override() -> None:
    assert scraper._request_timeouts({}) == (45, 90)
    assert scraper._request_timeouts({"timeout": 10}) == (10, 10)
    assert scraper._request_timeouts({"timeout": 9999}) == (300, 300)


def test_pattern_matches_regex_and_substring() -> None:
    assert scraper._pattern_matches(r"/topic-\d+", "https://x.test/topic-42")
    assert scraper._pattern_matches("plain", "https://x.test/plain-page")
    assert not scraper._pattern_matches(r"^https://only\.this", "https://x.test/other")


def test_dedupe_key_strips_query() -> None:
    url = "https://x.test/page?utm=1&b=2"
    assert scraper._dedupe_key(url, False) == url
    assert scraper._dedupe_key(url, True) == "https://x.test/page"


def test_parse_file_txt_and_html() -> None:
    txt = parse_file("notes.txt", "hello world".encode())
    assert txt["markdown"] == "hello world"
    assert txt["file_type"] == "txt"

    html = parse_file("page.html", HTML.encode())
    assert "Lead paragraph" in html["markdown"]
    assert "Menu" not in html["markdown"]


def test_parse_file_unsupported() -> None:
    with pytest.raises(ValueError):
        parse_file("archive.zip", b"PK")


def test_parse_file_xlsx() -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Firmalar"
    sheet.append(["Name", "Site"])
    sheet.append(["Acme", "https://acme.test"])
    buffer = io.BytesIO()
    workbook.save(buffer)

    parsed = parse_file("firms.xlsx", buffer.getvalue())
    assert "Firmalar" in parsed["markdown"]
    assert "Acme | https://acme.test" in parsed["markdown"]


def test_cache_key_stable_and_sensitive() -> None:
    from scrapling_cloud.cache import cache_key

    base = {"url": "https://x.test", "formats": ["markdown"], "mode": "static"}
    assert cache_key(base) == cache_key({**base, "max_age": 3600, "webhook_url": "https://hook"})
    assert cache_key(base) != cache_key({**base, "formats": ["markdown", "links"]})
    assert cache_key(base) != cache_key({**base, "only_main_content": False})
