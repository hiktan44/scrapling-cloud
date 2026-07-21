import asyncio
import logging
import re
import threading
import time
from traceback import format_exc

from rq import Worker

from .analyzer import extract_multi, extract_with_prompt, extract_with_schema
from .db import SessionLocal
from .intel import analyze_company, extract_socials, social_for_url
from .jobs import mark_failed, mark_running, mark_succeeded, requeue_stuck_jobs, send_webhook
from .learning import record_failure, record_success
from .tracking import compute_change
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
            payload = dict(job.request)
            if payload.get("change_tracking"):
                formats = list(payload.get("formats") or ["markdown"])
                if "markdown" not in formats:
                    formats.append("markdown")
                payload["formats"] = formats
            result = await scrape_url(payload)
            if payload.get("change_tracking"):
                result["change_tracking"] = compute_change(
                    db,
                    job.organization_id,
                    str(payload.get("url")),
                    result.get("markdown") or "",
                    payload.get("change_tracking_tag") or "",
                )
                db.commit()
        elif job.kind == JobKind.extract.value:
            payload = dict(job.request)
            prompt = payload.get("prompt") or payload.get("instructions")
            targets = [str(target) for target in (payload.get("urls") or [])]
            if not targets and payload.get("url"):
                targets = [str(payload["url"])]

            expand_limit = int(payload.get("limit") or 10)
            expanded: list[str] = []
            for target in targets:
                if target.endswith("/*"):
                    mapped = await map_url({"url": target[:-2], "limit": expand_limit})
                    expanded.extend(mapped.get("links") or [])
                else:
                    expanded.append(target)
            urls = list(dict.fromkeys(expanded))[:20]

            if len(urls) <= 1:
                single = dict(payload)
                if urls:
                    single["url"] = urls[0]
                single["formats"] = ["json", "metadata", "markdown"]
                result = await scrape_url(single)
                if payload.get("schema"):
                    result["extraction"] = await extract_with_schema(result, payload["schema"], prompt)
                elif prompt:
                    result["extraction"] = await extract_with_prompt(result, prompt)
            else:
                extract_semaphore = asyncio.Semaphore(5)
                extract_pages: list[dict | None] = [None] * len(urls)

                async def scrape_extract_url(index: int, target_url: str) -> None:
                    try:
                        async with extract_semaphore:
                            page = await scrape_url({"url": target_url, "formats": ["markdown", "metadata"], "mode": payload.get("mode", "static")})
                        page["status"] = "ok"
                    except Exception as exc:
                        page = {"url": target_url, "status": "error", "error": str(exc)[:300]}
                    extract_pages[index] = page
                    db.add(JobEvent(job_id=job.id, message=f"Extract {index + 1}/{len(urls)}: {target_url}", data={"status": page["status"]}))
                    db.commit()

                await asyncio.gather(*(scrape_extract_url(index, target_url) for index, target_url in enumerate(urls)))
                scraped_ok = [page for page in extract_pages if page and page.get("status") == "ok"]
                result = {
                    "urls": urls,
                    "pages": [
                        {"url": page.get("url"), "status": page.get("status"), "title": (page.get("metadata") or {}).get("title"), "error": page.get("error")}
                        for page in extract_pages
                        if page
                    ],
                    "extraction": await extract_multi(scraped_ok, payload.get("schema"), prompt),
                }
        elif job.kind == JobKind.map.value:
            result = await map_url(job.request)
        elif job.kind == JobKind.crawl.value:
            result = await crawl_url(job.request)
        elif job.kind == JobKind.batch.value:
            urls = [str(url) for url in job.request.get("urls", [])]
            batch_items: list[dict | None] = [None] * len(urls)
            batch_semaphore = asyncio.Semaphore(int(job.request.get("max_concurrency") or 5))
            batch_completed = 0

            async def scrape_batch_url(index: int, target_url: str) -> None:
                nonlocal batch_completed
                try:
                    async with batch_semaphore:
                        item = await scrape_url(
                            {
                                "url": target_url,
                                "formats": job.request.get("formats", ["markdown"]),
                                "mode": job.request.get("mode", "static"),
                                "only_main_content": job.request.get("only_main_content", True),
                            }
                        )
                    item["status"] = "ok"
                except Exception as exc:
                    item = {"url": target_url, "status": "error", "error": str(exc)[:300]}
                batch_items[index] = item
                batch_completed += 1
                db.add(JobEvent(job_id=job.id, message=f"Batch {batch_completed}/{len(urls)}: {target_url}", data={"status": item["status"]}))
                db.commit()

            await asyncio.gather(*(scrape_batch_url(index, target_url) for index, target_url in enumerate(urls)))
            finished_items = [entry for entry in batch_items if entry is not None]
            result = {
                "items": finished_items,
                "total": len(urls),
                "succeeded": sum(1 for entry in finished_items if entry.get("status") == "ok"),
            }
        elif job.kind == JobKind.intel.value:
            urls = [str(target) for target in (job.request.get("urls") or [])]
            items: list[dict | None] = [None] * len(urls)
            semaphore = asyncio.Semaphore(6)
            completed = 0
            mode = job.request.get("mode", "static")

            async def process_url(index: int, target_url: str) -> None:
                nonlocal completed
                item = {"url": target_url, "status": "ok", "socials": {}, "analysis": "", "error": None}
                site_host = re.sub(r"^https?://(www\.)?", "", target_url.lower()).split("/")[0]
                preset = social_for_url(target_url)
                if preset:
                    # Site yerine sosyal medya profili listelenmiş; taramaya gerek yok
                    item["socials"] = preset
                    item["analysis"] = "Firma, web sitesi yerine bu sosyal medya hesabını listelemiş."
                    items[index] = item
                    completed += 1
                    db.add(JobEvent(job_id=job.id, message=f"İşlendi {completed}/{len(urls)}: {target_url}", data={"status": item["status"]}))
                    db.commit()
                    return
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


def _monitor_sweep(stop: threading.Event, interval_seconds: int = 60) -> None:
    """Run due page monitors on schedule."""
    from .monitors import due_monitors, run_monitor_check

    while not stop.is_set():
        try:
            db = SessionLocal()
            try:
                for monitor in due_monitors(db):
                    try:
                        asyncio.run(run_monitor_check(db, monitor))
                    except Exception:
                        logger.exception("monitor check failed for %s", monitor.id)
            finally:
                db.close()
        except Exception:
            logger.exception("monitor sweep failed")
        stop.wait(interval_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    stop = threading.Event()
    threading.Thread(target=_requeue_sweep, args=(stop,), daemon=True).start()
    threading.Thread(target=_monitor_sweep, args=(stop,), daemon=True).start()
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
