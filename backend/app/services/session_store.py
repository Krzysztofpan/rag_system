from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.query_session import QuerySession


class SessionStore:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(self, *, user_id: UUID) -> QuerySession:
        query_session = QuerySession(user_id=user_id)
        self.session.add(query_session)
        await self.session.commit()
        await self.session.refresh(query_session)
        return query_session

    async def get_session(self, session_id: UUID) -> QuerySession:
        query_session = await self.session.get(QuerySession, session_id)
        if query_session is None:
            raise ValueError(f"Session {session_id} not found")
        return query_session
