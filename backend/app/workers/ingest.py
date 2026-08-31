from __future__ import annotations

import asyncio
import logging

from app.db.health import check_db_connection
from app.db.session import dispose_engine
from app.ingest.queue import DocumentIngestJob, IngestQueue, YoutubeIngestJob
from app.lib.redis import close_redis, get_redis, verify_redis_configuration

logger = logging.getLogger(__name__)


async def run_document_ingest(job: DocumentIngestJob) -> None:
    from app.background_tasks.document_background import ingest_document_source

    await ingest_document_source(
        job.conversation_id,
        job.document_id,
        job.user_id,
        job.path,
        job.filename,
        job.content_type,
    )


async def run_youtube_ingest(job: YoutubeIngestJob) -> None:
    from app.background_tasks.youtube_background import ingest_youtube_source

    await ingest_youtube_source(
        job.conversation_id,
        job.document_id,
        job.user_id,
        job.url,
        job.video_id,
    )


async def dispatch_ingest_job(job: DocumentIngestJob | YoutubeIngestJob) -> None:
    if isinstance(job, DocumentIngestJob):
        await run_document_ingest(job)
        return
    await run_youtube_ingest(job)


async def run_worker() -> None:
    verify_redis_configuration()
    await check_db_connection()
    queue = IngestQueue(get_redis())
    logger.info("ingest worker listening on %s", queue.key)
    try:
        while True:
            job = await queue.dequeue(timeout=5)
            if job is None:
                continue
            try:
                await dispatch_ingest_job(job)
            except Exception:
                logger.exception(
                    "ingest job failed",
                    extra={
                        "kind": job.kind,
                        "document_id": str(job.document_id),
                    },
                )
    finally:
        await close_redis()
        await dispose_engine()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("ingest worker stopped")


if __name__ == "__main__":
    main()
