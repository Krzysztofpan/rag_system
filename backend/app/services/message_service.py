from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Message

class MessageService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_message(self, message: Message) -> Message:
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message