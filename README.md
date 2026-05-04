# Scrapling Cloud

Scrapling Cloud is a self-hosted SaaS platform built around
[`scrapling[all]`](https://github.com/D4Vinci/Scrapling). It exposes a
Firecrawl-inspired API for scraping, crawling, mapping, extraction, API keys,
usage credits, Stripe billing, and safe domain-level learning.

## Services

- `web`: Next.js dashboard, docs, playground, billing and job history.
- `api`: FastAPI public API, API-key auth, usage accounting and Stripe webhook.
- `worker`: Python queue consumer that runs Scrapling jobs.
- `postgres`: tenant data, jobs, API keys, usage, learning profiles.
- `redis`: job queue, rate limiting and cache.

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- Web dashboard: <http://localhost:3000>
- FastAPI docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

For local development without Docker:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn scrapling_cloud.main:app --reload --port 8000
```

```bash
cd apps/web
npm install
npm run dev
```

## Demo API Key

On first API startup, a demo organization and API key are created:

```text
sk_demo_local_development_key
```

Use it with:

```bash
curl -X POST http://localhost:8000/v1/scrape \
  -H "Authorization: Bearer sk_demo_local_development_key" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","formats":["markdown","links"]}'
```

## Production Target

The prepared Coolify/self-host target is:

- Web: `https://www.seymata.com`
- API: `https://api.seymata.com`

Use `.env.production.example` as the Coolify environment template and follow
`coolify.md` for DNS, domain and Stripe webhook setup.

## License Attribution

Scrapling is licensed under BSD-3-Clause. Keep the upstream license notice when
shipping this product.
