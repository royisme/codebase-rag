"""依赖注入帮助方法。"""

from __future__ import annotations

import uuid
from typing import AsyncIterator, Optional

from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from database.models import User
from security.manager import UserManager


class UUIDSQLAlchemyUserDatabase(SQLAlchemyUserDatabase[User, uuid.UUID]):
    """Custom user database that handles UUID type conversion for PostgreSQL."""

    async def get(self, id: uuid.UUID) -> Optional[User]:
        """Override get to ensure UUID type is correctly handled."""
        # Convert string to UUID if needed
        if isinstance(id, str):
            id = uuid.UUID(id)
        statement = select(self.user_table).where(self.user_table.id == id)
        result = await self.session.execute(statement)
        return result.scalars().first()


async def get_user_db(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncIterator[UUIDSQLAlchemyUserDatabase]:
    yield UUIDSQLAlchemyUserDatabase(session, User)


async def get_user_manager(
    user_db: UUIDSQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncIterator[UserManager]:
    yield UserManager(user_db)
