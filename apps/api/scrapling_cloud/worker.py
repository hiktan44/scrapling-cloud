import asyncio
import logging
import re
import threading
import time
from traceback import format_exc

from rq import Worker

from .analyzer import extract_with_prompt
from .db import SessionLocal
from .intel import analyze_company, extract_socials
from .jobs import mark_failed, mark_running, mark_succeeded, requeue_stuck_jobs, send_webhook
from .learning import record_failure, record_success
from .models import Job, JobEvent, JobKind, JobStatus
from .queue import get_queue, get_redis
from .scraper import crawl_url, map_url, scrape_url

logger = logging.getLogger(__name__)


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
        if job.status != JobStatus.queued.value:
            # Duplicate delivery (recovery sweep or a retried enqueue) -
            # the job already ran or is running, so skip it idempotently.
            logger.info("skipping job %s with status %s", job_id, job.status)
            return
        mark_running(db, job)

        if job.kind == JobKind.scrape.value:
            result = await scrape_url(job.request)
        elif job.kind == JobKind.extract.value:
            payload = dict(job.request)
            payload["formats"] = ["json", "metadata", "markdown"]
            result = await scrape_url(payload)
            prompt = payload.get("prompt") or payload.get("instructions")
            if prompt and not payload.get("schema"):
                result["extraction"] = await extract_with_prompt(result, prompt)
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
        elif job.kind == JobKind.intel.value:
            urls = [str(target) for target in (job.request.get("urls") or [])]
            items: list[dict | None] = [None] * len(urls)
            semaphore = asyncio.Semaphore(4)
            completed = 0
            mode = job.request.get("mode", "static")

            async def process_url(index: int, target_url: str) -> None:
                nonlocal completed
                item = {"url": target_url, "status": "ok", "socials": {}, "analysis": "", "error": None}
                site_host = re.sub(r"^https?://(www\.)?", "", target_url.lower()).split("/")[0]
                try:
                    async with semaphore:
                        scraped = await scrape_url(
                            {"url": target_url, "formats": ["markdown", "links", "metadata"], "mode": mode}
                        )
                        item["socials"] = extract_socials(scraped.get("links") or [], scraped.get("markdown"), site_host)
                        item["analysis"] = await analyze_company(scraped)
                except Exception as exc:
                    item["status"] = "error"
                    item["error"] = str(exc)[:300]
                items[index] = item
                completed += 1
                db.add(JobEvent(job_id=job.id, message=f"İşlendi {completed}/{len(urls)}: {target_url}", data={"status": item["status"]}))
                db.commit()

            await asyncio.gather(*(process_url(index, target_url) for index, target_url in enumerate(urls)))
            finished = [entry for entry in items if entry is not None]
            result = {
                "items": finished,
                "total": len(urls),
                "succeeded": sum(1 for entry in finished if entry["status"] == "ok"),
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


def _requeue_sweep(stop: threading.Event, interval_seconds: int = 60) -> None:
    """Periodically re-enqueue jobs that never reached the queue."""
    while not stop.is_set():
        try:
            db = SessionLocal()
            try:
                requeue_stuck_jobs(db)
            finally:
                db.close()
        except Exception:
            logger.exception("requeue sweep failed")
        stop.wait(interval_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    stop = threading.Event()
    threading.Thread(target=_requeue_sweep, args=(stop,), daemon=True).start()
    while True:
        try:
            queue = get_queue()
            Worker([queue], connection=get_redis()).work()
        except KeyboardInterrupt:
            stop.set()
            raise
        except Exception:
            # A Redis restart or network drop must not kill the worker for
            # good - log and re-enter the work loop.
            logger.exception("worker loop interrupted; restarting in 5s")
            time.sleep(5)


if __name__ == "__main__":
    main()
