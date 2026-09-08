from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.studio.queue import NoteTitleJob
from app.workers.studio import dispatch_studio_job


async def test_dispatch_note_title_job():
    job = NoteTitleJob(
        conversation_id=uuid4(),
        resource_id=uuid4(),
        user_id=uuid4(),
    )
    with patch(
        "app.workers.studio.run_note_title_job",
        new=AsyncMock(),
    ) as run_job:
        await dispatch_studio_job(job)

    run_job.assert_awaited_once_with(job)
