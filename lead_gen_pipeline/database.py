"""Async SQLAlchemy engine, session factory, and lead-persistence helpers.

The engine and session factory are created lazily through getters so tests can swap the
database URL and reset state between runs.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

try:
    from .config import settings
    from .models import Base, Lead
    from .utils import logger
except ImportError:
    from lead_gen_pipeline.config import settings
    from lead_gen_pipeline.models import Base, Lead
    from lead_gen_pipeline.utils import logger

_engine: AsyncEngine | None = None
_async_session_local: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the async engine, creating it from the current settings on first use."""
    global _engine
    if _engine is None:
        db_url = settings.database.DATABASE_URL
        logger.info(f"Creating async engine for {db_url}")
        connect_args: dict[str, Any] = {}
        if "sqlite" in db_url:
            connect_args["check_same_thread"] = False
        _engine = create_async_engine(
            db_url, echo=settings.database.ECHO_SQL, connect_args=connect_args
        )
    return _engine


def get_async_session_local() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory, creating it on first use."""
    global _async_session_local
    if _async_session_local is None:
        _async_session_local = async_sessionmaker(
            bind=get_engine(), expire_on_commit=False
        )
    return _async_session_local


async def init_db() -> None:
    """Create all tables defined on the models. Safe to call repeatedly."""
    async with get_engine().begin() as conn:
        logger.info("Initializing database (creating tables if needed)")
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session, rolling back on error and always closing it.

    Intended for use as a dependency (for example, in a FastAPI route).
    """
    session = get_async_session_local()()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def save_lead(
    lead_data: dict[str, Any], db_session: AsyncSession | None = None
) -> Lead | None:
    """Persist a lead from a dict of column values.

    With ``db_session`` the lead is flushed and the caller commits. Without one, a local
    session is created, committed, and closed. Returns the saved Lead, or None on error.
    """
    label = lead_data.get("company_name") or lead_data.get("website") or "unknown lead"

    try:
        lead = Lead(**lead_data)
    except TypeError as te:
        logger.error(f"Invalid lead data for '{label}': {te}")
        return None

    session = db_session or get_async_session_local()()
    created_locally = db_session is None

    try:
        session.add(lead)
        await session.flush()
        await session.refresh(lead)
        if created_locally:
            await session.commit()
            logger.success(f"Saved lead id {lead.id} ('{lead.company_name}')")
        else:
            logger.debug(f"Flushed lead id {lead.id}; caller must commit")
        return lead
    except Exception as e:
        if created_locally:
            try:
                await session.rollback()
            except Exception as rb_e:
                logger.error(f"Rollback failed while saving '{label}': {rb_e}")
        logger.error(f"Error saving lead '{label}': {e}")
        return None
    finally:
        if created_locally:
            try:
                await session.close()
            except Exception as close_e:
                logger.error(f"Error closing session for '{label}': {close_e}")


def _reset_db_state_for_testing() -> None:
    """Drop the cached engine and session factory so tests can rebind the DB URL."""
    global _engine, _async_session_local
    _engine = None
    _async_session_local = None
