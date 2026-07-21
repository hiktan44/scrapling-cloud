import hashlib
import hmac

import pytest

from scrapling_cloud import scraper
from scrapling_cloud.jobs import webhook_secret_for


def test_parse_sitemap_urlset() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://example.com/a</loc></url>
      <url><loc>https://example.com/b</loc></url>
    </urlset>"""
    urls, children = scraper._parse_sitemap(xml)
    assert urls == ["https://example.com/a", "https://example.com/b"]
    assert children == []


def test_parse_sitemap_index() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://example.com/sitemap-1.xml</loc></sitemap>
    </sitemapindex>"""
    urls, children = scraper._parse_sitemap(xml)
    assert urls == []
    assert children == ["https://example.com/sitemap-1.xml"]


def test_parse_sitemap_invalid_xml() -> None:
    assert scraper._parse_sitemap("not xml at all") == ([], [])


def test_main_content_prefers_main_tag() -> None:
    html = """<html><body>
      <nav>Menu items</nav>
      <main><h1>Title</h1><p>Real content</p></main>
      <footer>Copyright</footer>
    </body></html>"""
    reduced = scraper.main_content_html(html)
    assert "Real content" in reduced
    assert "Menu items" not in reduced
    assert "Copyright" not in reduced


def test_main_content_strips_boilerplate_without_main() -> None:
    html = """<html><body>
      <nav>Menu</nav>
      <div><p>Body text</p></div>
      <script>var x = 1;</script>
      <footer>Foot</footer>
    </body></html>"""
    reduced = scraper.main_content_html(html)
    assert "Body text" in reduced
    assert "Menu" not in reduced
    assert "var x" not in reduced


@pytest.mark.asyncio
async def test_scrape_only_main_content_toggles_markdown(monkeypatch) -> None:
    html = "<html><body><nav>NAVBAR</nav><main><p>Hello world</p></main></body></html>"

    async def fake_fetch(url, mode="static", wait_for=None, proxy=None):
        return html

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch)

    reduced = await scraper.scrape_url({"url": "https://example.com", "formats": ["markdown"]})
    assert "NAVBAR" not in reduced["markdown"]
    assert "Hello world" in reduced["markdown"]

    full = await scraper.scrape_url({"url": "https://example.com", "formats": ["markdown"], "only_main_content": False})
    assert "NAVBAR" in full["markdown"]


def test_same_or_subdomain() -> None:
    assert scraper.same_or_subdomain("https://blog.example.com/x", "https://example.com")
    assert scraper.same_or_subdomain("https://www.example.com/x", "https://example.com")
    assert not scraper.same_or_subdomain("https://example.org/x", "https://example.com")


def test_webhook_secret_is_deterministic_and_org_scoped() -> None:
    first = webhook_secret_for("org-1")
    assert first == webhook_secret_for("org-1")
    assert first != webhook_secret_for("org-2")
    # sanity: the documented verification recipe reproduces the signature shape
    body = b'{"id":"j1"}'
    signature = hmac.new(first.encode(), body, hashlib.sha256).hexdigest()
    assert len(signature) == 64


def test_resolve_proxy_respects_mode_and_flag(monkeypatch) -> None:
    from scrapling_cloud import config

    class FakeSettings:
        proxy_provider_url = "http://user:pass@proxy.test:8080"

    monkeypatch.setattr(scraper, "get_settings", lambda: FakeSettings())
    assert scraper.resolve_proxy({"mode": "stealth"}) == FakeSettings.proxy_provider_url
    assert scraper.resolve_proxy({"mode": "static", "proxy": True}) == FakeSettings.proxy_provider_url
    assert scraper.resolve_proxy({"mode": "static"}) is None
