from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from core.config import settings


def _normalise_url(url: str) -> str:
    """Ensure the URL uses the correct async driver prefix."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("mysql://"):
        return url.replace("mysql://", "mysql+aiomysql://", 1)
    return url


db_url = _normalise_url(
    settings.DATABASE_URL if settings.DATABASE_URL else f"sqlite+aiosqlite:///{settings.DB_PATH}"
)

engine = create_async_engine(
    db_url,
    echo=settings.DEBUG,
    future=True,
)

async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session
