from __future__ import annotations

from collections import deque
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify as to_markdown


def _extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = normalize_link(anchor.get("href"), base_url)
        if href and href not in links:
            links.append(href)
    return links[:500]


def normalize_link(href: str | None, base_url: str) -> str | None:
    if not href:
        return None
    raw = href.strip()
    if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    absolute, _fragment = urldefrag(urljoin(base_url, raw))
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return absolute


def same_site(url: str, root_url: str) -> bool:
    url_host = urlparse(url).netloc.lower().removeprefix("www.")
    root_host = urlparse(root_url).netloc.lower().removeprefix("www.")
    return url_host == root_host


def allowed_by_patterns(url: str, include: list[str], exclude: list[str]) -> bool:
    if include and not any(pattern in url for pattern in include):
        return False
    if exclude and any(pattern in url for pattern in exclude):
        return False
    return True


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
    root_url = str(payload["url"])
    limit = int(payload.get("limit", 25))
    max_depth = int(payload.get("max_depth", 2))
    formats = payload.get("formats") or ["markdown", "links", "metadata"]
    mode = payload.get("mode", "static")
    include = payload.get("include") or []
    exclude = payload.get("exclude") or []

    queue = deque([(root_url, 0)])
    seen: set[str] = set()
    pages: list[dict] = []
    discovered: list[str] = []
    errors: list[dict] = []

    while queue and len(pages) < limit:
        current_url, depth = queue.popleft()
        if current_url in seen:
            continue
        seen.add(current_url)
        if not same_site(current_url, root_url) or not allowed_by_patterns(current_url, include, exclude):
            continue

        try:
            scraped = await scrape_url({"url": current_url, "formats": formats, "mode": mode})
            page_links = [link for link in scraped.get("links", []) if same_site(link, root_url)]
            page = {
                "url": current_url,
                "depth": depth,
                "title": (scraped.get("metadata") or {}).get("title"),
                "description": (scraped.get("metadata") or {}).get("description"),
                "markdown": scraped.get("markdown"),
                "text": scraped.get("text"),
                "links": page_links,
                "metadata": scraped.get("metadata"),
            }
            pages.append(page)
            for link in page_links:
                if link not in discovered:
                    discovered.append(link)
                if depth < max_depth and link not in seen and len(seen) + len(queue) < max(limit * 4, limit):
                    queue.append((link, depth + 1))
        except Exception as exc:
            errors.append({"url": current_url, "depth": depth, "error": str(exc)})

    return {
        "url": root_url,
        "max_depth": max_depth,
        "limit": limit,
        "pages_scraped": len(pages),
        "links_discovered": len(discovered),
        "pages": pages,
        "discovered": discovered[: max(limit * 3, 50)],
        "errors": errors,
    }
