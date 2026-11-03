from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import OperationalError, InterfaceError
from sqlalchemy.orm import DeclarativeBase

from weebit.config import settings
from weebit.exceptions import DatabaseUnavailableProblem

engine = create_async_engine(settings.database_url, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    # Abstract base class for all ORM models.
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    try:
        async with AsyncSessionLocal() as session:
            yield session
    except (OperationalError, InterfaceError, ConnectionRefusedError) as e:
        raise DatabaseUnavailableProblem(detail="Database is unavailable.") from e