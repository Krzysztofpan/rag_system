from __future__ import annotations

import asyncio
import logging

from app.db.health import check_db_connection
from app.db.session import dispose_engine
from app.lib.redis import close_redis, get_redis, verify_redis_configuration
from app.studio.queue import NoteTitleJob, StudioQueue

logger = logging.getLogger(__name__)


async def run_note_title_job(job: NoteTitleJob) -> None:
    from app.studio.note_title import apply_note_title

    await apply_note_title(
        job.conversation_id,
        job.resource_id,
        job.user_id,
    )


async def dispatch_studio_job(job: NoteTitleJob) -> None:
    await run_note_title_job(job)


async def run_worker() -> None:
    verify_redis_configuration()
    try:
        ok, message = await check_db_connection()
        if not ok:
            raise RuntimeError(f"Database connection failed: {message}")
        queue = StudioQueue(get_redis())
        logger.info("studio worker listening on %s", queue.key)
        while True:
            job = await queue.dequeue(timeout=5)
            if job is None:
                continue
            try:
                await dispatch_studio_job(job)
            except Exception:
                logger.exception(
                    "studio job failed",
                    extra={
                        "kind": job.kind,
                        "resource_id": str(job.resource_id),
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
        logger.info("studio worker stopped")


if __name__ == "__main__":
    main()
