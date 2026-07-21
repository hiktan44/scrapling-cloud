from __future__ import annotations

import asyncio
import base64
import re
import urllib.robotparser
import xml.etree.ElementTree as ElementTree
from collections import deque
from urllib.parse import parse_qs, unquote, urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify as to_markdown

from .analyzer import analyze_crawl, summarize_page
from .cache import cache_get, cache_set
from .config import get_settings


PROGRAM_HINTS = {
    "digital": "Digital Europe",
    "horizon": "Horizon Europe",
    "erasmus": "Erasmus+",
    "life": "LIFE",
    "eic": "European Innovation Council",
    "eurostars": "Eurostars",
    "cef": "Connecting Europe Facility",
    "eu4health": "EU4Health",
    "creative": "Creative Europe",
    "citizens": "Citizens, Equality, Rights and Values",
}


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


def same_or_subdomain(url: str, root_url: str) -> bool:
    url_host = urlparse(url).netloc.lower().removeprefix("www.")
    root_host = urlparse(root_url).netloc.lower().removeprefix("www.")
    return url_host == root_host or url_host.endswith("." + root_host)


def resolve_proxy(payload: dict) -> str | None:
    """Return the configured proxy URL when this request should go through it.

    Stealth mode implies the proxy whenever one is configured; other modes
    opt in with the request-level `proxy` flag.
    """
    settings = get_settings()
    if not settings.proxy_provider_url:
        return None
    if payload.get("mode") == "stealth" or payload.get("proxy"):
        return settings.proxy_provider_url
    return None


def _pattern_matches(pattern: str, url: str) -> bool:
    """Match a crawl filter pattern as regex, falling back to substring."""
    try:
        if re.search(pattern, url):
            return True
    except re.error:
        pass
    return pattern in url


def allowed_by_patterns(url: str, include: list[str], exclude: list[str]) -> bool:
    if include and not any(_pattern_matches(pattern, url) for pattern in include):
        return False
    if exclude and any(_pattern_matches(pattern, url) for pattern in exclude):
        return False
    return True


def titleize_token(token: str) -> str:
    upper_tokens = {"ai", "eu", "ict", "sme", "eic", "erc", "ri", "msca", "edf", "cef", "5g", "6g", "iot"}
    if token.lower() in upper_tokens:
        return token.upper()
    if token.isdigit():
        return token
    return token.capitalize()


def humanize_slug(slug: str) -> str:
    cleaned = unquote(slug).replace("_", "-").strip("-")
    parts = [part for part in cleaned.split("-") if part and not part.isdigit()]
    return " ".join(titleize_token(part) for part in parts[:16])


def infer_program(url: str, slug: str) -> str | None:
    haystack = f"{url} {slug}".lower()
    for marker, name in PROGRAM_HINTS.items():
        if marker in haystack:
            return name
    return None


def extract_years(text: str) -> list[str]:
    years: list[str] = []
    for year in [part for part in text.replace("/", "-").split("-") if part.isdigit() and len(part) == 4]:
        if year.startswith("20") and year not in years:
            years.append(year)
    return years[:4]


def extract_record_from_url(url: str) -> dict | None:
    parsed = urlparse(url)
    path = parsed.path
    record_paths = ("/topic-details/", "/call/", "/calls/", "/opportunity-details/")
    if not any(marker in path for marker in record_paths):
        return None
    slug = path.rstrip("/").split("/")[-1]
    if not slug:
        return None
    query = parse_qs(parsed.query)
    title = humanize_slug(slug)
    years = extract_years(slug)
    program = infer_program(url, slug)
    keywords = [part for part in unquote(slug).replace("_", "-").split("-") if len(part) > 2 and not part.isdigit()][:12]
    return {
        "id": slug,
        "title": title,
        "url": url,
        "source": parsed.netloc,
        "type": "topic" if "topic" in path.lower() else "page",
        "program": program,
        "years": years,
        "keywords": keywords,
        "programme_period": (query.get("programmePeriod") or [None])[0],
        "framework_programme": (query.get("frameworkProgramme") or [None])[0],
        "summary": f"{title} başlıklı potansiyel fon/ihale konusu. Detay ve uygunluk bilgileri kaynak URL üzerinden takip edilmeli.",
        "action": "Detay sayfasını aç, başvuru koşulları ve son tarihleri kontrol et.",
    }


def build_records(pages: list[dict], discovered: list[str]) -> list[dict]:
    records: list[dict] = []
    seen_ids: set[str] = set()
    urls: list[str] = []
    for page in pages:
        urls.append(str(page.get("url")))
        urls.extend(page.get("links") or [])
    urls.extend(discovered)
    for url in urls:
        record = extract_record_from_url(url)
        if not record or record["id"] in seen_ids:
            continue
        seen_ids.add(record["id"])
        records.append(record)
    return records[:250]


def _metadata(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag.get("content") if description_tag else None
    return {"title": title, "description": description}


FETCH_STATIC_TIMEOUT = 45
FETCH_DYNAMIC_TIMEOUT = 90

MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)


def _request_headers(payload: dict) -> dict[str, str] | None:
    headers = dict(payload.get("headers") or {})
    if payload.get("mobile") and not any(key.lower() == "user-agent" for key in headers):
        headers["User-Agent"] = MOBILE_USER_AGENT
    return {str(k): str(v) for k, v in list(headers.items())[:20]} or None


def _request_timeouts(payload: dict) -> tuple[int, int]:
    """(static_timeout, dynamic_timeout) seconds, honoring the request override."""
    override = payload.get("timeout")
    if override:
        bounded = max(5, min(int(override), 300))
        return bounded, bounded
    return FETCH_STATIC_TIMEOUT, FETCH_DYNAMIC_TIMEOUT


async def fetch_html(
    url: str,
    mode: str = "static",
    wait_for: str | None = None,
    proxy: str | None = None,
    headers: dict[str, str] | None = None,
    static_timeout: int = FETCH_STATIC_TIMEOUT,
    dynamic_timeout: int = FETCH_DYNAMIC_TIMEOUT,
) -> str:
    if mode in {"dynamic", "stealth"}:
        try:
            from scrapling.fetchers import StealthyFetcher, DynamicFetcher

            fetcher = StealthyFetcher if mode == "stealth" else DynamicFetcher

            def _render() -> str:
                kwargs: dict = {}
                if wait_for:
                    kwargs["wait_selector"] = wait_for
                if proxy:
                    kwargs["proxy"] = proxy
                if headers:
                    kwargs["extra_headers"] = headers
                while True:
                    try:
                        page = fetcher.fetch(url, **kwargs)
                        break
                    except TypeError:
                        # Older Scrapling fetcher signatures - drop optional
                        # kwargs one at a time until the call is accepted.
                        for optional in ("extra_headers", "proxy"):
                            if optional in kwargs:
                                kwargs.pop(optional)
                                break
                        else:
                            raise
                return str(page.html)

            # Scrapling fetchers are synchronous and have no reliable socket
            # timeout; run them in a thread and bound the wait so a drip-feeding
            # or fingerprint-stalling site cannot hang the worker forever.
            return await asyncio.wait_for(asyncio.to_thread(_render), timeout=dynamic_timeout)
        except Exception:
            # Fall through to static fetching so the API remains useful without
            # browser dependencies during local smoke tests.
            pass

    try:
        from scrapling.fetchers import Fetcher

        if not proxy and not headers:
            page = await asyncio.wait_for(asyncio.to_thread(Fetcher.fetch, url), timeout=static_timeout)
            return str(page.html)
    except Exception:
        pass

    import httpx

    async with httpx.AsyncClient(timeout=min(static_timeout, 60), follow_redirects=True, proxy=proxy, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


SCREENSHOT_TIMEOUT_MS = 60_000


def _capture_screenshot_sync(url: str, full_page: bool, wait_for: str | None, proxy: str | None) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            proxy={"server": proxy} if proxy else None,
        )
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(url, wait_until="load", timeout=SCREENSHOT_TIMEOUT_MS)
            if wait_for:
                page.wait_for_selector(wait_for, timeout=15_000)
            image = page.screenshot(full_page=full_page, type="jpeg", quality=80)
        finally:
            browser.close()
    return "data:image/jpeg;base64," + base64.b64encode(image).decode()


async def capture_screenshot(url: str, full_page: bool = False, wait_for: str | None = None, proxy: str | None = None) -> str:
    return await asyncio.wait_for(
        asyncio.to_thread(_capture_screenshot_sync, url, full_page, wait_for, proxy),
        timeout=FETCH_DYNAMIC_TIMEOUT + 30,
    )


_BOILERPLATE_TAGS = ("script", "style", "noscript", "template", "svg", "nav", "header", "footer", "aside", "form", "iframe")


def main_content_html(html: str) -> str:
    """Reduce a page to its main content for markdown/text conversion.

    Prefers an explicit <main>/<article> region, then strips obvious
    boilerplate (navigation, footers, scripts) from whatever remains.
    """
    soup = BeautifulSoup(html, "html.parser")
    root = soup.find("main") or soup.find("article") or soup.body or soup
    for tag in root.find_all(_BOILERPLATE_TAGS):
        tag.decompose()
    for tag in root.find_all(attrs={"role": ("navigation", "banner", "contentinfo", "complementary")}):
        tag.decompose()
    return str(root)


def _extract_images(html: str, base_url: str, limit: int = 200) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    images: list[str] = []
    for tag in soup.find_all("img"):
        source = tag.get("src") or (tag.get("srcset") or "").split(",")[0].strip().split(" ")[0]
        if not source or source.startswith("data:"):
            continue
        absolute = urljoin(base_url, source)
        if absolute not in images:
            images.append(absolute)
        if len(images) >= limit:
            break
    return images


def apply_tag_filters(html: str, include_tags: list[str], exclude_tags: list[str]) -> str:
    """CSS-selector content filtering (Firecrawl includeTags/excludeTags)."""
    if not include_tags and not exclude_tags:
        return html
    soup = BeautifulSoup(html, "html.parser")
    if include_tags:
        kept: list[str] = []
        for selector in include_tags:
            try:
                kept.extend(str(node) for node in soup.select(selector))
            except Exception:
                continue
        return "\n".join(kept)
    for selector in exclude_tags:
        try:
            for node in soup.select(selector):
                node.decompose()
        except Exception:
            continue
    return str(soup)


async def scrape_url(payload: dict) -> dict:
    url = str(payload["url"])

    cached = cache_get(payload)
    if cached is not None:
        return cached

    proxy = resolve_proxy(payload)
    headers = _request_headers(payload)
    static_timeout, dynamic_timeout = _request_timeouts(payload)
    html = await fetch_html(
        url,
        payload.get("mode", "static"),
        payload.get("wait_for"),
        proxy,
        headers,
        static_timeout,
        dynamic_timeout,
    )
    formats = payload.get("formats") or ["markdown"]
    result: dict = {"url": url}

    # Firecrawl-style onlyMainContent: markdown/text/summary come from the
    # reduced page, while html/raw_html/links/metadata see the full document.
    content_html = main_content_html(html) if payload.get("only_main_content", True) else html
    content_html = apply_tag_filters(content_html, payload.get("include_tags") or [], payload.get("exclude_tags") or [])

    if "html" in formats:
        result["html"] = html
    if "raw_html" in formats:
        result["raw_html"] = html
    if "markdown" in formats or "summary" in formats:
        markdown = to_markdown(content_html, heading_style="ATX")
        if "markdown" in formats:
            result["markdown"] = markdown
    if "text" in formats:
        result["text"] = BeautifulSoup(content_html, "html.parser").get_text("\n", strip=True)
    if "links" in formats:
        result["links"] = _extract_links(html, url)
    if "images" in formats:
        result["images"] = _extract_images(html, url)
    if "metadata" in formats:
        result["metadata"] = _metadata(html)
    if "summary" in formats:
        result["summary"] = await summarize_page({"url": url, "markdown": markdown})
    if "screenshot" in formats:
        try:
            result["screenshot"] = await capture_screenshot(
                url,
                full_page=bool(payload.get("screenshot_full_page")),
                wait_for=payload.get("wait_for"),
                proxy=proxy,
            )
        except Exception as exc:
            result["screenshot"] = None
            result.setdefault("warnings", []).append(f"Screenshot capture failed: {exc}")
    if "json" in formats or payload.get("schema"):
        result["json"] = simple_extract(html, payload.get("schema") or {})

    cache_set(payload, result)
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


SITEMAP_MAX_BYTES = 5 * 1024 * 1024
SITEMAP_MAX_DOCS = 10


async def _fetch_text(url: str, timeout: int = 15) -> str | None:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code != 200 or len(response.content) > SITEMAP_MAX_BYTES:
                return None
            return response.text
    except Exception:
        return None


def _parse_sitemap(xml_text: str) -> tuple[list[str], list[str]]:
    """Return (page_urls, child_sitemap_urls) from a sitemap or sitemap index."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return [], []
    tag = root.tag.lower()
    locs = [element.text.strip() for element in root.iter() if element.tag.lower().endswith("loc") and element.text]
    if tag.endswith("sitemapindex"):
        return [], locs
    return locs, []


async def collect_sitemap_urls(root_url: str) -> list[str]:
    """Discover URLs via robots.txt sitemap declarations and common sitemap paths."""
    parsed = urlparse(root_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    candidates: list[str] = []
    robots = await _fetch_text(urljoin(base, "/robots.txt"), timeout=10)
    if robots:
        for line in robots.splitlines():
            if line.lower().startswith("sitemap:"):
                candidates.append(line.split(":", 1)[1].strip())
    candidates.extend([urljoin(base, "/sitemap.xml"), urljoin(base, "/sitemap_index.xml")])

    urls: list[str] = []
    seen_docs: set[str] = set()
    queue = deque(candidates)
    while queue and len(seen_docs) < SITEMAP_MAX_DOCS:
        sitemap_url = queue.popleft()
        if sitemap_url in seen_docs:
            continue
        seen_docs.add(sitemap_url)
        text = await _fetch_text(sitemap_url)
        if not text:
            continue
        page_urls, children = _parse_sitemap(text)
        urls.extend(page_urls)
        queue.extend(children)
    return urls


async def map_url(payload: dict) -> dict:
    root_url = str(payload["url"])
    limit = int(payload.get("limit", 250))
    sitemap_mode = payload.get("sitemap", "include")
    in_scope = same_or_subdomain if payload.get("include_subdomains") else same_site

    links: list[str] = []
    sitemap_count = 0
    if sitemap_mode != "skip":
        for link in await collect_sitemap_urls(root_url):
            normalized = normalize_link(link, root_url)
            if normalized and in_scope(normalized, root_url):
                links.append(normalized)
        sitemap_count = len(links)
    if sitemap_mode != "only":
        try:
            scraped = await scrape_url({"url": root_url, "formats": ["links"], "mode": "static", "only_main_content": False})
            links.extend(link for link in scraped.get("links", []) if in_scope(link, root_url))
        except Exception:
            if not links:
                raise

    search = (payload.get("search") or "").strip().lower()
    deduped: list[str] = []
    seen: set[str] = set()
    for link in links:
        if link in seen:
            continue
        seen.add(link)
        if search and search not in link.lower():
            continue
        deduped.append(link)

    return {
        "url": root_url,
        "links": deduped[:limit],
        "total_discovered": len(seen),
        "from_sitemap": sitemap_count,
    }


async def _load_robots(root_url: str) -> urllib.robotparser.RobotFileParser | None:
    parsed = urlparse(root_url)
    robots_text = await _fetch_text(f"{parsed.scheme}://{parsed.netloc}/robots.txt", timeout=10)
    if not robots_text:
        return None
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(robots_text.splitlines())
    return parser


def _dedupe_key(url: str, ignore_query: bool) -> str:
    if not ignore_query:
        return url
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


async def crawl_url(payload: dict) -> dict:
    root_url = str(payload["url"])
    limit = int(payload.get("limit", 25))
    max_depth = int(payload.get("max_depth", 2))
    formats = payload.get("formats") or ["markdown", "links", "metadata"]
    mode = payload.get("mode", "static")
    include = payload.get("include") or []
    exclude = payload.get("exclude") or []
    delay = min(float(payload.get("delay") or 0), 30.0)
    ignore_query = bool(payload.get("ignore_query_parameters"))
    in_scope = same_or_subdomain if payload.get("allow_subdomains") else same_site
    only_main_content = payload.get("only_main_content", True)

    robots = None
    if payload.get("respect_robots", True):
        robots = await _load_robots(root_url)

    queue = deque([(root_url, 0)])
    seen: set[str] = set()
    pages: list[dict] = []
    discovered: list[str] = []
    errors: list[dict] = []
    robots_skipped = 0

    while queue and len(pages) < limit:
        current_url, depth = queue.popleft()
        dedupe = _dedupe_key(current_url, ignore_query)
        if dedupe in seen:
            continue
        seen.add(dedupe)
        if not in_scope(current_url, root_url) or not allowed_by_patterns(current_url, include, exclude):
            continue
        if robots is not None and not robots.can_fetch("*", current_url):
            robots_skipped += 1
            continue

        try:
            if delay and pages:
                await asyncio.sleep(delay)
            scraped = await scrape_url(
                {"url": current_url, "formats": formats, "mode": mode, "only_main_content": only_main_content}
            )
            page_links = [link for link in scraped.get("links", []) if in_scope(link, root_url)]
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
                if depth < max_depth and _dedupe_key(link, ignore_query) not in seen and len(seen) + len(queue) < max(limit * 4, limit):
                    queue.append((link, depth + 1))
        except Exception as exc:
            errors.append({"url": current_url, "depth": depth, "error": str(exc)})

    records = build_records(pages, discovered)
    ai = None
    if payload.get("ai_extract", True):
        ai = await analyze_crawl(pages, root_url, payload.get("analysis_prompt"), records)

    return {
        "url": root_url,
        "max_depth": max_depth,
        "limit": limit,
        "pages_scraped": len(pages),
        "links_discovered": len(discovered),
        "record_count": len(records),
        "records": records,
        "ai": ai,
        "pages": pages,
        "discovered": discovered[: max(limit * 3, 50)],
        "errors": errors,
        "robots_skipped": robots_skipped,
    }
