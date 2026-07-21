"""Web search via a self-hosted SearXNG instance (Firecrawl /search parity).

Returns ranked results and can optionally scrape each result page.
"""

from __future__ import annotations

import asyncio

import httpx

from .config import get_settings
from .scraper import scrape_url

SEARCH_TIMEOUT = 25


class SearchUnavailable(RuntimeError):
    pass


async def web_search(
    query: str,
    limit: int = 10,
    categories: str = "general",
    language: str = "auto",
    time_range: str | None = None,
) -> list[dict]:
    settings = get_settings()
    if not settings.searxng_url:
        raise SearchUnavailable("Search backend is not configured (SEARXNG_URL unset).")

    params = {
        "q": query,
        "format": "json",
        "categories": categories,
        "language": language,
        "safesearch": 0,
    }
    if time_range in {"day", "week", "month", "year"}:
        params["time_range"] = time_range

    async with httpx.AsyncClient(timeout=SEARCH_TIMEOUT) as client:
        response = await client.get(f"{settings.searxng_url.rstrip('/')}/search", params=params)
        response.raise_for_status()
        data = response.json()

    results = []
    for item in data.get("results", [])[:limit]:
        results.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("content"),
                "engine": item.get("engine"),
                "score": item.get("score"),
            }
        )
    return results


async def search_and_scrape(
    query: str,
    limit: int,
    scrape_formats: list[str] | None,
    categories: str,
    language: str,
    time_range: str | None,
    mode: str,
) -> dict:
    results = await web_search(query, limit=limit, categories=categories, language=language, time_range=time_range)

    if scrape_formats:
        semaphore = asyncio.Semaphore(5)

        async def enrich(entry: dict) -> None:
            if not entry.get("url"):
                return
            try:
                async with semaphore:
                    scraped = await scrape_url({"url": entry["url"], "formats": scrape_formats, "mode": mode})
                for fmt in scrape_formats:
                    if fmt in scraped:
                        entry[fmt] = scraped[fmt]
            except Exception as exc:
                entry["scrape_error"] = str(exc)[:200]

        await asyncio.gather(*(enrich(entry) for entry in results))

    return {"query": query, "count": len(results), "results": results}
