from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.background_tasks.upload_background import summarize_document_and_update_title
from app.container import create_document_service, create_indexing_service
from app.db.session import get_session_factory
from app.lib.tracing import conversation_tracing
from app.lib.upload_temp import upload_file_from_path
from app.services.parser.base import ParseQualityError


class FileIngestService:
    async def ingest(
        self,
        *,
        conversation_id: UUID,
        document_id: UUID,
        user_id: UUID,
        path: str,
        filename: str,
        content_type: str | None,
    ) -> None:
        tmp = Path(path)
        try:
            with conversation_tracing(
                conversation_id,
                user_id=user_id,
                tags=["ingest"],
                extra_metadata={"document_id": document_id},
            ):
                upload = upload_file_from_path(
                    tmp,
                    filename=filename,
                    content_type=content_type,
                )
                try:
                    session_factory = get_session_factory()
                    async with session_factory() as session:
                        indexing = create_indexing_service(session)
                        result = await indexing.ingest(
                            upload,
                            conversation_id=conversation_id,
                            document_id=document_id,
                        )
                    await summarize_document_and_update_title(
                        result.parsed_content,
                        conversation_id,
                        document_id,
                        user_id,
                    )
                finally:
                    await upload.close()
        except ParseQualityError:
            return
        except Exception as exc:
            await self._mark_failed(document_id, str(exc))
            raise
        finally:
            tmp.unlink(missing_ok=True)

    async def _mark_failed(self, document_id: UUID, message: str) -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            document_service = create_document_service(session)
            await document_service.mark_failed(document_id, message)
