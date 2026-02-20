from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from .config import settings


engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    from . import models  # noqa: F401 - import to register models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Simple migration: add columns that may be missing on existing DBs
        await _migrate(conn)


async def _migrate(conn):
    """Add columns introduced after initial schema creation."""
    import sqlalchemy as sa

    migrations = [
        ("metrics", "source_table", "TEXT"),
        ("metrics", "source_platform", "TEXT"),
        ("analysis_jobs", "current_stage", "INTEGER DEFAULT 1"),
        ("analysis_jobs", "logs", "TEXT"),
    ]
    for table, column, col_type in migrations:
        try:
            await conn.execute(sa.text(
                f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
            ))
        except Exception:
            # Column already exists – ignore
            pass


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
