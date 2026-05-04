import asyncio
from traceback import format_exc

from rq import Worker

from .db import SessionLocal
from .jobs import mark_failed, mark_running, mark_succeeded, send_webhook
from .learning import record_failure, record_success
from .models import Job, JobKind
from .queue import get_queue, get_redis
from .scraper import crawl_url, map_url, scrape_url


def classify_error(error: str) -> str:
    lowered = error.lower()
    if "captcha" in lowered:
        return "captcha"
    if "403" in lowered or "blocked" in lowered:
        return "blocked"
    if "timeout" in lowered:
        return "timeout"
    if "empty" in lowered:
        return "empty-content"
    return "unknown"


async def _run(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            return
        mark_running(db, job)

        if job.kind == JobKind.scrape.value:
            result = await scrape_url(job.request)
        elif job.kind == JobKind.extract.value:
            payload = dict(job.request)
            payload["formats"] = ["json", "metadata"]
            result = await scrape_url(payload)
        elif job.kind == JobKind.map.value:
            result = await map_url(job.request)
        elif job.kind == JobKind.crawl.value:
            result = await crawl_url(job.request)
        elif job.kind == JobKind.batch.value:
            result = {
                "items": [
                    await scrape_url({"url": str(url), "formats": job.request.get("formats", ["markdown"]), "mode": job.request.get("mode", "static")})
                    for url in job.request.get("urls", [])
                ]
            }
        else:
            raise ValueError(f"Unsupported job kind: {job.kind}")

        mark_succeeded(db, job, result)
        if job.url:
            record_success(db, job.organization_id, job.url, job.request.get("mode", "static"))
            db.commit()
        await send_webhook(job)
    except Exception as exc:
        error = f"{exc}\n{format_exc()}"
        job = db.get(Job, job_id)
        if job is not None:
            reason = classify_error(error)
            mark_failed(db, job, str(exc), reason)
            if job.url:
                record_failure(db, job.organization_id, job.url, reason)
                db.commit()
            await send_webhook(job)
    finally:
        db.close()


def run_job(job_id: str) -> None:
    asyncio.run(_run(job_id))


def main() -> None:
    queue = get_queue()
    Worker([queue], connection=get_redis()).work()


if __name__ == "__main__":
    main()
