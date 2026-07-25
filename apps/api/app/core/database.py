from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# 1. Create the Async Engine
# echo=True prints all generated SQL to stdout (great for debugging in development)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENV == "development",
    future=True,
)

# 2. Create the Session Factory
# expire_on_commit=False prevents SQLAlchemy from fetching objects again after committing
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# 3. Create the Database Session Dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining a database session.

    Yields a session, and automatically closes it after the request completes.
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
