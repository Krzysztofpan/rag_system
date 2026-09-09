from __future__ import annotations

import asyncio
import logging
import time

from langsmith import traceable

from app.db.health import check_db_connection
from app.db.session import dispose_engine
from app.ingest.queue import DocumentIngestJob, IngestQueue, YoutubeIngestJob
from app.lib.redis import close_redis, get_redis, verify_redis_configuration
from app.lib.tracing import conversation_tracing

logger = logging.getLogger(__name__)


async def run_document_ingest(job: DocumentIngestJob) -> None:
    with conversation_tracing(
        job.conversation_id,
        user_id=job.user_id,
        tags=["ingest"],
        extra_metadata={
            "document_id": job.document_id,
            "filename": job.filename,
            "content_type": job.content_type,
            "ingest_kind": job.kind,
        },
    ):
        await _ingest_document_job(job)


@traceable(name="ingest", run_type="chain")
async def _ingest_document_job(job: DocumentIngestJob) -> None:
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
    with conversation_tracing(
        job.conversation_id,
        user_id=job.user_id,
        tags=["ingest"],
        extra_metadata={
            "document_id": job.document_id,
            "video_id": job.video_id,
            "ingest_kind": job.kind,
        },
    ):
        await _ingest_youtube_job(job)


@traceable(name="ingest", run_type="chain")
async def _ingest_youtube_job(job: YoutubeIngestJob) -> None:
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


def warm_simple_ingest_runtime() -> None:
    """Load the markdown/txt/youtube path before the first job.

    ComplexParser/Docling/RapidOCR stay unloaded until a PDF/DOCX/image
    actually needs them.
    """
    from app.background_tasks.document_background import (  # noqa: F401
        ingest_document_source,
    )
    from app.background_tasks.youtube_background import (  # noqa: F401
        ingest_youtube_source,
    )
    from app.container import get_vector_store
    from app.lib.file_types import FileTypes
    from app.services.chunker.simple import SimpleChunker

    SimpleChunker(FileTypes.MD)
    get_vector_store()


async def run_worker() -> None:
    verify_redis_configuration()
    try:
        ok, message = await check_db_connection()
        if not ok:
            raise RuntimeError(f"Database connection failed: {message}")
        logger.info("warming simple ingest runtime")
        started = time.perf_counter()
        warm_simple_ingest_runtime()
        logger.info(
            "simple ingest runtime ready in %.1fs",
            time.perf_counter() - started,
        )
        queue = IngestQueue(get_redis())
        logger.info("ingest worker listening on %s", queue.key)
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
