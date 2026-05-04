#!/usr/bin/env sh
set -eu

API_URL="${API_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-sk_demo_local_development_key}"

curl -fsS "$API_URL/health"
curl -fsS "$API_URL/v1/usage" -H "Authorization: Bearer $API_KEY"
curl -fsS -X POST "$API_URL/v1/scrape" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","formats":["markdown","links"]}'
