# lead_gen_pipeline/database.py
# Version: Gemini-2025-05-26 20:55 EDT

from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker

from lead_gen_pipeline.config import settings # settings is now the source of truth
from lead_gen_pipeline.models import Base, Lead
from lead_gen_pipeline.utils import logger

# These will be initialized by get_engine() and get_async_session_local()
_engine: Optional[AsyncEngine] = None
_async_session_local: Optional[sessionmaker[AsyncSession]] = None

def get_engine() -> AsyncEngine:
    """
    Returns the SQLAlchemy async engine, creating it if it doesn't exist.
    Uses the current `settings.database.DATABASE_URL`.
    """
    global _engine
    if _engine is None:
        db_url = settings.database.DATABASE_URL
        echo_sql = settings.database.ECHO_SQL
        logger.info(f"[DB_FACTORY] Creating new engine for URL: {db_url}")
        _engine = create_async_engine(
            db_url, 
            echo=echo_sql,
            connect_args={'check_same_thread': False} # Important for aiosqlite
        )
    return _engine

def get_async_session_local() -> sessionmaker[AsyncSession]:
    """
    Returns the SQLAlchemy async session factory, creating it if it doesn't exist.
    Uses the engine from get_engine().
    """
    global _async_session_local
    if _async_session_local is None:
        logger.info("[DB_FACTORY] Creating new AsyncSessionLocal factory.")
        engine_to_use = get_engine()
        _async_session_local = sessionmaker(
            bind=engine_to_use,
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _async_session_local

async def init_db() -> None:
    """
    Initializes the database by creating all tables defined in models.py.
    """
    engine_to_use = get_engine() # Get the (potentially patched) engine
    async with engine_to_use.begin() as conn:
        logger.info("[DB_INIT] Initializing database: creating tables if they do not exist...")
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[DB_INIT] Database tables created (or already existed).")

async def get_db() -> AsyncSession:
    """
    Dependency function to get a database session.
    Ensures the session is closed after use.
    """
    session_factory = get_async_session_local()
    async_session = session_factory()
    try:
        yield async_session
    finally:
        await async_session.close()

async def save_lead(lead_data: Dict[str, Any], db_session: Optional[AsyncSession] = None) -> Optional[Lead]:
    """
    Saves a lead to the database.
    """
    logger.debug(f"[SAVE_LEAD] Attempting to save: {lead_data.get('company_name', lead_data.get('website'))}")

    lead_to_save = Lead(
        company_name=lead_data.get("company_name"),
        website=lead_data.get("website"),
        scraped_from_url=lead_data.get("scraped_from_url", "N/A"),
        canonical_url=lead_data.get("canonical_url"),
        description=lead_data.get("description"),
        phone_numbers=lead_data.get("phone_numbers"),
        emails=lead_data.get("emails"),
        addresses=lead_data.get("addresses"),
        social_media_links=lead_data.get("social_media_links")
    )

    session_to_use: Optional[AsyncSession] = None
    created_session_locally = False
    try:
        if db_session:
            session_to_use = db_session
        else:
            session_factory = get_async_session_local()
            session_to_use = session_factory()
            created_session_locally = True
            logger.debug(f"[SAVE_LEAD] Created new DB session: {session_to_use.bind}")


        session_to_use.add(lead_to_save)
        await session_to_use.flush() # Get ID before commit
        await session_to_use.refresh(lead_to_save) # Get all DB-generated values
        logger.info(f"[SAVE_LEAD] Lead '{lead_to_save.company_name}' (ID: {lead_to_save.id}) added/flushed in session.")

        if created_session_locally: # Only commit if session was created by this function
            await session_to_use.commit()
            logger.success(f"[SAVE_LEAD] Lead ID {lead_to_save.id} committed successfully (local session).")
        
        return lead_to_save

    except Exception as e:
        if session_to_use and created_session_locally: # Rollback local session on error
            try:
                await session_to_use.rollback()
                logger.info("[SAVE_LEAD] Rollback successful for local session after error.")
            except Exception as rb_e:
                logger.error(f"[SAVE_LEAD] Error during rollback for local session: {rb_e}", exc_info=True)
        
        # If db_session was passed, the caller is responsible for rollback on its own session.
        # We still log the error from this function's perspective.
        logger.error(f"[SAVE_LEAD] Error saving lead for URL '{lead_data.get('scraped_from_url')}': {e}", exc_info=True)
        return None
    finally:
        if session_to_use and created_session_locally: # Close locally created session
            try:
                await session_to_use.close()
                logger.debug("[SAVE_LEAD] Local DB session closed.")
            except Exception as close_e:
                logger.error(f"[SAVE_LEAD] Error closing local DB session: {close_e}", exc_info=True)

# Function to allow tests to reset the module-level engine and session factory
def _reset_db_state_for_testing():
    global _engine, _async_session_local
    if _engine:
        # Note: Disposing engine here might be problematic if it's shared.
        # For testing, it's better if each test setup creates its own engine.
        # This function is more for ensuring a clean slate if the module is re-imported
        # or if settings are changed between test runs in a single session.
        logger.debug("[DB_FACTORY_RESET] Resetting module-level engine and session factory.")
    _engine = None
    _async_session_local = None

