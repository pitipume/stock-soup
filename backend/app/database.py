from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.config import settings

# NullPool: never reuse connections across asyncio.run() calls.
# Required because Celery forks worker processes — the parent creates the engine
# with event loop A, child processes inherit it but run event loop B, causing
# "Future attached to a different loop" errors if connections are pooled.
# FastAPI is unaffected (it uses a single long-lived event loop).
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    poolclass=NullPool,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
