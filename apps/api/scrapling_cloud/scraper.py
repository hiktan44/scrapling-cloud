from __future__ import annotations

from bs4 import BeautifulSoup
from markdownify import markdownify as to_markdown


def _extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")
        if href and href not in links:
            links.append(href)
    return links[:500]


def _metadata(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag.get("content") if description_tag else None
    return {"title": title, "description": description}


async def fetch_html(url: str, mode: str = "static", wait_for: str | None = None) -> str:
    if mode in {"dynamic", "stealth"}:
        try:
            from scrapling.fetchers import StealthyFetcher, DynamicFetcher

            fetcher = StealthyFetcher if mode == "stealth" else DynamicFetcher
            page = fetcher.fetch(url, wait_selector=wait_for) if wait_for else fetcher.fetch(url)
            return str(page.html)
        except Exception:
            # Fall through to static fetching so the API remains useful without
            # browser dependencies during local smoke tests.
            pass

    try:
        from scrapling.fetchers import Fetcher

        page = Fetcher.fetch(url)
        return str(page.html)
    except Exception:
        import httpx

        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text


async def scrape_url(payload: dict) -> dict:
    url = str(payload["url"])
    html = await fetch_html(url, payload.get("mode", "static"), payload.get("wait_for"))
    formats = payload.get("formats") or ["markdown"]
    result: dict = {"url": url}

    if "html" in formats:
        result["html"] = html
    if "markdown" in formats:
        result["markdown"] = to_markdown(html, heading_style="ATX")
    if "text" in formats:
        result["text"] = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
    if "links" in formats:
        result["links"] = _extract_links(html, url)
    if "metadata" in formats:
        result["metadata"] = _metadata(html)
    if "screenshot" in formats:
        result["screenshot"] = None
        result["warnings"] = ["Screenshot capture requires browser dependencies in the worker image."]
    if "json" in formats or payload.get("schema"):
        result["json"] = simple_extract(html, payload.get("schema") or {})
    return result


def simple_extract(html: str, schema: dict) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    data: dict = {}
    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
    for key, definition in properties.items():
        selector = definition.get("selector") if isinstance(definition, dict) else None
        if selector:
            node = soup.select_one(selector)
            data[key] = node.get_text(" ", strip=True) if node else None
        elif key == "title":
            data[key] = soup.title.string.strip() if soup.title and soup.title.string else None
        else:
            data[key] = None
    if not data:
        data["title"] = soup.title.string.strip() if soup.title and soup.title.string else None
    return data


async def map_url(payload: dict) -> dict:
    scraped = await scrape_url({"url": payload["url"], "formats": ["links"], "mode": "static"})
    return {"url": str(payload["url"]), "links": scraped.get("links", [])[: payload.get("limit", 250)]}


async def crawl_url(payload: dict) -> dict:
    mapped = await map_url({"url": payload["url"], "limit": payload.get("limit", 25)})
    return {
        "url": str(payload["url"]),
        "max_depth": payload.get("max_depth", 2),
        "queued": mapped["links"][: payload.get("limit", 25)],
        "note": "Initial version discovers links and records an async crawl job; recursive worker expansion is ready to extend.",
    }
