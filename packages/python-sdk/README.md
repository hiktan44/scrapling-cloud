# Scrapling Cloud Python SDK

Thin Python client for the [Scrapling Cloud](https://scrape.seymata.com) API.

## Install

```bash
pip install scrapling-cloud-sdk
```

## Usage

```python
from scrapling_cloud_sdk import ScraplingCloud

client = ScraplingCloud(api_key="sk_...")

# Scrape a page to markdown (async job polled to completion)
page = client.scrape("https://example.com", formats=["markdown", "links"])
print(page["markdown"])

# Discover URLs (sitemap + on-page links)
urls = client.map("https://scrapy.org")

# Structured extraction across multiple pages (wildcards allowed)
data = client.extract(
    urls=["https://example.com", "https://example.com/blog/*"],
    prompt="Extract each article title and date",
    schema={"type": "object", "properties": {"articles": {"type": "array"}}},
)

# Web search, optionally scraping each result
results = client.search("Horizon Europe calls 2026", limit=5, scrape_formats=["markdown"])

# Monitor a page for changes
mon = client.create_monitor("EU calls", "https://ec.europa.eu/...", interval_minutes=60, judge_enabled=True, goal="New funding calls")

# Parse a local PDF/DOCX/XLSX to markdown
doc = client.parse("report.pdf")

print(client.usage())
```

`base_url` defaults to `https://api.scrape.seymata.com`; override it for
self-hosted deployments.
