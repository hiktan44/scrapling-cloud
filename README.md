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
- Live public stats: <http://localhost:8000/v1/public/stats>

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

## Demo API Key (development only)

With `ENVIRONMENT=development` and `SEED_DEMO=true` (the defaults in
`.env.example`), a demo organization and API key are created on first startup:

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

The demo account is **never** seeded when `ENVIRONMENT=production`. If a demo
account from an older deployment already exists, startup locks it
(`SEED_DEMO=false`) and revokes its API keys.

## Security & Hardening

- **Secure by default**: `ENVIRONMENT` defaults to `production`. Shared demo
  credentials and default admin credentials are only active when you opt in
  with `ENVIRONMENT=development`.
- **Admin account**: in production you must set a private `ADMIN_PASSWORD`
  (and optionally `ADMIN_API_KEY`). Default or empty values keep the admin
  account locked; a previously-seeded default admin is locked automatically
  and the well-known development admin key is revoked.
- **Rate limiting** (Redis-backed, fails open if Redis is down):
  - `POST /v1/auth/login`: 10 req/min per IP
  - `POST /v1/auth/signup`: 5 req/min per IP
  - `POST /v1/playground/scrape`: 30 req/min per IP
- **Queue resilience**: jobs are enqueued with retry/backoff; if the queue is
  unreachable the job is marked failed, reserved credits are refunded, and
  the API returns a retryable `503` instead of a bare `500`. A worker-side
  sweep re-enqueues jobs stuck in `queued`, and `POST /v1/admin/requeue`
  triggers the same recovery manually.
- **Redis**: configured with `maxmemory` + `noeviction` so queued jobs are
  never silently dropped under memory pressure.

## Production Target

The prepared Coolify/self-host target is:

- Web: `https://www.seymata.com`
- API: `https://api.seymata.com`

Use `.env.production.example` as the Coolify environment template and follow
`coolify.md` for DNS, domain and Stripe webhook setup.

## License Attribution

Scrapling is licensed under BSD-3-Clause. Keep the upstream license notice when
shipping this product.
