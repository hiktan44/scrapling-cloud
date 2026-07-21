"""Synchronous client for the Scrapling Cloud API."""

from __future__ import annotations

import time
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api.scrape.seymata.com"


class ScraplingCloudError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, detail: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class ScraplingCloud:
    """Client for Scrapling Cloud.

    >>> client = ScraplingCloud(api_key="sk_...")
    >>> result = client.scrape("https://example.com", formats=["markdown"])
    >>> print(result["markdown"])
    """

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL, timeout: float = 60.0, poll_timeout: float = 180.0) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self.base_url = base_url.rstrip("/")
        self.poll_timeout = poll_timeout
        self._http = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )

    # -- low level ---------------------------------------------------------
    def _request(self, method: str, path: str, **kwargs) -> Any:
        response = self._http.request(method, f"{self.base_url}{path}", **kwargs)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail")
            except Exception:
                detail = response.text
            raise ScraplingCloudError(f"{method} {path} failed ({response.status_code}): {detail}", response.status_code, detail)
        return response.json()

    def _run_job(self, path: str, body: dict) -> dict:
        job = self._request("POST", path, json=body)
        job_id = job.get("id")
        if not job_id:
            return job
        deadline = time.time() + self.poll_timeout
        while time.time() < deadline:
            detail = self._request("GET", f"/v1/jobs/{job_id}")
            status = detail.get("status")
            if status == "succeeded":
                return detail.get("result") or detail
            if status == "failed":
                raise ScraplingCloudError(f"Job {job_id} failed: {detail.get('error')}", detail=detail.get("error"))
            time.sleep(2)
        raise ScraplingCloudError(f"Job {job_id} did not finish within {self.poll_timeout}s")

    # -- core operations ---------------------------------------------------
    def scrape(self, url: str, formats: list[str] | None = None, mode: str = "auto", **options) -> dict:
        return self._run_job("/v1/scrape", {"url": url, "formats": formats or ["markdown"], "mode": mode, **options})

    def crawl(self, url: str, limit: int = 25, max_depth: int = 2, **options) -> dict:
        return self._run_job("/v1/crawl", {"url": url, "limit": limit, "max_depth": max_depth, **options})

    def map(self, url: str, limit: int = 250, **options) -> dict:
        return self._request("POST", "/v1/map", json={"url": url, "limit": limit, **options})

    def extract(self, urls: list[str] | str, prompt: str | None = None, schema: dict | None = None, **options) -> dict:
        body: dict = {**options}
        if isinstance(urls, str):
            body["url"] = urls
        else:
            body["urls"] = urls
        if prompt:
            body["prompt"] = prompt
        if schema:
            body["schema"] = schema
        return self._run_job("/v1/extract", body)

    def search(self, query: str, limit: int = 10, scrape_formats: list[str] | None = None, **options) -> dict:
        body = {"query": query, "limit": limit, **options}
        if scrape_formats:
            body["scrape_formats"] = scrape_formats
        return self._request("POST", "/v1/search", json=body)

    def parse(self, file_path: str) -> dict:
        with open(file_path, "rb") as handle:
            files = {"file": (file_path.split("/")[-1], handle)}
            # multipart request: drop the JSON content-type for this call
            response = self._http.post(f"{self.base_url}/v1/parse", files=files, headers={"Content-Type": None})
        if response.status_code >= 400:
            raise ScraplingCloudError(f"parse failed ({response.status_code})", response.status_code)
        return response.json()

    # -- monitors ----------------------------------------------------------
    def create_monitor(self, name: str, url: str, **options) -> dict:
        return self._request("POST", "/v1/monitors", json={"name": name, "url": url, **options})

    def list_monitors(self) -> list[dict]:
        return self._request("GET", "/v1/monitors")

    def run_monitor(self, monitor_id: str) -> dict:
        return self._request("POST", f"/v1/monitors/{monitor_id}/run", json={})

    def delete_monitor(self, monitor_id: str) -> dict:
        return self._request("DELETE", f"/v1/monitors/{monitor_id}")

    # -- account -----------------------------------------------------------
    def usage(self) -> dict:
        return self._request("GET", "/v1/usage")

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "ScraplingCloud":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
