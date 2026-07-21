"""Scrapling Cloud MCP server.

Exposes scrape/crawl/map/extract/search/parse as MCP tools that any MCP
client (Claude, Cursor, VS Code, ...) can call. It is a thin client over the
public HTTP API, authenticated with the user's own API key.

Run:
    SCRAPLING_API_KEY=sk_... SCRAPLING_API_URL=https://api.scrape.seymata.com \
        python -m scrapling_cloud.mcp_server

Async jobs (scrape/crawl/extract) are polled to completion so tools return the
final result directly.
"""

from __future__ import annotations

import os
import time

import httpx
from mcp.server.fastmcp import FastMCP

API_URL = os.environ.get("SCRAPLING_API_URL", "https://api.scrape.seymata.com").rstrip("/")
API_KEY = os.environ.get("SCRAPLING_API_KEY", "")
POLL_TIMEOUT = int(os.environ.get("SCRAPLING_POLL_TIMEOUT", "180"))

mcp = FastMCP("scrapling-cloud")


def _headers() -> dict:
    if not API_KEY:
        raise RuntimeError("Set SCRAPLING_API_KEY to your Scrapling Cloud API key.")
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def _post(path: str, body: dict) -> dict:
    with httpx.Client(timeout=60) as client:
        response = client.post(f"{API_URL}{path}", json=body, headers=_headers())
        response.raise_for_status()
        return response.json()


def _get(path: str) -> dict:
    with httpx.Client(timeout=60) as client:
        response = client.get(f"{API_URL}{path}", headers=_headers())
        response.raise_for_status()
        return response.json()


def _run_job(path: str, body: dict) -> dict:
    """Submit an async job and poll until it finishes."""
    job = _post(path, body)
    job_id = job.get("id")
    if not job_id:
        return job
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        detail = _get(f"/v1/jobs/{job_id}")
        if detail.get("status") in ("succeeded", "failed"):
            return detail
        time.sleep(2)
    return {"status": "timeout", "id": job_id}


@mcp.tool()
def scrape(url: str, formats: list[str] | None = None, mode: str = "auto", only_main_content: bool = True) -> dict:
    """Scrape a single URL. formats: markdown, html, raw_html, text, links, images, metadata, screenshot, summary, json."""
    return _run_job("/v1/scrape", {"url": url, "formats": formats or ["markdown"], "mode": mode, "only_main_content": only_main_content})


@mcp.tool()
def crawl(url: str, limit: int = 25, max_depth: int = 2, ai_extract: bool = False) -> dict:
    """Crawl a website starting from url, up to `limit` pages and `max_depth` deep."""
    return _run_job("/v1/crawl", {"url": url, "limit": limit, "max_depth": max_depth, "ai_extract": ai_extract})


@mcp.tool()
def map_site(url: str, limit: int = 250, include_subdomains: bool = False) -> dict:
    """Discover URLs on a site via sitemap + on-page links (fast, no full scrape)."""
    return _post("/v1/map", {"url": url, "limit": limit, "include_subdomains": include_subdomains})


@mcp.tool()
def extract(urls: list[str], prompt: str, schema: dict | None = None) -> dict:
    """Extract structured data from one or more URLs (wildcards like site.com/* allowed) guided by a prompt/schema."""
    body: dict = {"urls": urls, "prompt": prompt}
    if schema:
        body["schema"] = schema
    return _run_job("/v1/extract", body)


@mcp.tool()
def search(query: str, limit: int = 10, scrape_results: bool = False) -> dict:
    """Web search; optionally scrape each result to markdown."""
    body: dict = {"query": query, "limit": limit}
    if scrape_results:
        body["scrape_formats"] = ["markdown"]
    return _post("/v1/search", body)


@mcp.tool()
def usage() -> dict:
    """Current plan and remaining credits."""
    return _get("/v1/usage")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
