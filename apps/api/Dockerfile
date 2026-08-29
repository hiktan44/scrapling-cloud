FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Browser runtimes for dynamic/stealth rendering and screenshots. Scrapling
# 0.4.x drives Chromium through playwright (dynamic) and patchright (stealth).
# `scrapling install` also refreshes TLD data and stamps its dependency
# marker so fetchers don't attempt runtime installs.
RUN python -m playwright install --with-deps chromium \
    && python -m patchright install chromium \
    && scrapling install

COPY . .

EXPOSE 8000
CMD ["uvicorn", "scrapling_cloud.main:app", "--host", "0.0.0.0", "--port", "8000"]

# --- Agentic Security Firewall: Katman 2 (non-root hardening) ---
RUN (id -u appuser >/dev/null 2>&1 || useradd -m -u 10001 appuser) && { [ ! -d /app ] || chown -R appuser:appuser /app; }
USER appuser
