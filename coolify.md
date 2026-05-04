# Coolify Deployment for scrape.seymata.com

## Domains

- Web landing/dashboard: `https://scrape.seymata.com`
- Public API: `https://api.scrape.seymata.com`
- Stripe webhook: `https://api.scrape.seymata.com/v1/billing/stripe/webhook`

## Coolify Steps

1. Create a new Docker Compose application in Coolify.
2. Connect the GitHub repository and set the repository root as the compose project root.
3. Copy variables from `.env.production.example` into Coolify's environment editor.
4. Replace all `replace-*` and Stripe placeholders with real production secrets.
5. Attach public domains:
   - `web` service: `scrape.seymata.com`
   - `api` service: `api.scrape.seymata.com`
6. Enable HTTPS/Let's Encrypt for both domains.
7. In Stripe, configure the webhook endpoint:
   - `https://api.scrape.seymata.com/v1/billing/stripe/webhook`
8. Deploy the stack.
9. Smoke test:
   - `https://scrape.seymata.com`
   - `https://api.scrape.seymata.com/health`
   - `https://api.scrape.seymata.com/docs`

The API container runs schema creation on startup for the first version. Replace
that with Alembic migrations before a production data migration workflow is
needed.

## DNS Checklist

Create DNS records before deploying or before enabling SSL:

- `scrape.seymata.com` → Coolify server IP or Coolify proxy target.
- `api.scrape.seymata.com` → Coolify server IP or Coolify proxy target.

If Cloudflare is used, start with proxy disabled until Let's Encrypt certificates
are issued cleanly, then enable proxy if desired.
