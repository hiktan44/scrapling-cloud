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

# Browser runtimes: Chromium for dynamic rendering + screenshots, Firefox
# system deps + Camoufox build for stealth mode. Without these the dynamic
# and stealth modes silently fall back to static fetching.
RUN python -m playwright install --with-deps chromium firefox \
    && python -m camoufox fetch

COPY . .

EXPOSE 8000
CMD ["uvicorn", "scrapling_cloud.main:app", "--host", "0.0.0.0", "--port", "8000"]
