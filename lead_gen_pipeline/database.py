# lead_gen_pipeline/database.py
# Version: Gemini-2025-05-26 22:05 EDT

from typing import Dict, Any, Optional, AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select # For SQLAlchemy 1.4+ style selects

try:
    from .config import settings # settings is the source of truth for DB URL
    from .models import Base, Lead # Import your SQLAlchemy models
    from .utils import logger
except ImportError:
    from lead_gen_pipeline.config import settings # type: ignore
    from lead_gen_pipeline.models import Base, Lead # type: ignore
    from lead_gen_pipeline.utils import logger # type: ignore

# Module-level placeholders for engine and session factory
# These are initialized by their respective getter functions to allow for
# easier mocking/patching in tests and to ensure they are created only when needed.
_engine: Optional[AsyncEngine] = None
_async_session_local: Optional[sessionmaker[AsyncSession]] = None # type: ignore

def get_engine() -> AsyncEngine:
    """
    Returns the SQLAlchemy async engine, creating it if it doesn't exist.
    Uses the current `settings.database.DATABASE_URL`.
    """
    global _engine
    if _engine is None:
        db_url = settings.database.DATABASE_URL
        echo_sql = settings.database.ECHO_SQL
        logger.info(f"[DB_FACTORY] Creating new SQLAlchemy async engine for URL: {db_url} (Echo: {echo_sql})")
        
        connect_args = {}
        if "sqlite" in db_url: # Specific arguments for SQLite
            connect_args['check_same_thread'] = False 
            # Consider other SQLite pragmas if needed, e.g., {'foreign_keys': 'ON'} via events

        _engine = create_async_engine(
            db_url, 
            echo=echo_sql,
            connect_args=connect_args,
            # Pool settings can be configured here if needed, e.g., pool_size, max_overflow
            # For SQLite in async, default pool (AsyncAdaptedQueuePool) is generally okay.
        )
    return _engine

def get_async_session_local() -> sessionmaker[AsyncSession]: # type: ignore
    """
    Returns the SQLAlchemy async session factory (sessionmaker),
    creating it if it doesn't exist. Uses the engine from get_engine().
    """
    global _async_session_local
    if _async_session_local is None:
        logger.info("[DB_FACTORY] Creating new AsyncSessionLocal factory.")
        engine_to_use = get_engine() # Ensures engine is initialized
        _async_session_local = sessionmaker(
            bind=engine_to_use,
            class_=AsyncSession, # Use AsyncSession for async operations
            expire_on_commit=False, # Good practice for async sessions
            # Other options like autoflush can be set here if needed
        )
    return _async_session_local # type: ignore

async def init_db() -> None:
    """
    Initializes the database by creating all tables defined in models.py (via Base.metadata).
    This should be called once at application startup.
    """
    engine_to_use = get_engine() 
    async with engine_to_use.begin() as conn: # Begins a transaction
        logger.info("[DB_INIT] Initializing database: creating tables if they do not exist...")
        # This creates tables based on all models that subclass Base
        await conn.run_sync(Base.metadata.create_all)
        # For migrations with Alembic, this would be handled by Alembic's `upgrade head`.
        # For simple cases or initial setup, create_all is fine.
    logger.info("[DB_INIT] Database tables checked/created successfully.")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async generator to provide a database session.
    Ensures the session is closed after use.
    Intended for use as a dependency (e.g., in FastAPI).
    """
    session_factory = get_async_session_local()
    async_session: AsyncSession = session_factory()
    try:
        yield async_session
        # For simple scripts or if auto-commit is desired per operation,
        # commits might happen within the functions using the session.
        # If used in a web request context, commit might be here or per request.
        # await async_session.commit() # Optional: commit here if a single transaction per usage is desired
    except Exception:
        await async_session.rollback() # Rollback on any exception during the session's use
        raise
    finally:
        await async_session.close() # Always close the session

async def save_lead(lead_data: Dict[str, Any], db_session: Optional[AsyncSession] = None) -> Optional[Lead]:
    """
    Saves a lead (represented by a dictionary) to the database.
    If db_session is provided, it uses that session; otherwise, it creates a new one.
    The caller is responsible for committing the transaction if an external session is provided.
    """
    company_name_log = lead_data.get("company_name", lead_data.get("website", "Unknown Lead"))
    logger.debug(f"[SAVE_LEAD] Attempting to save lead data for: {company_name_log}")

    # Create a Lead model instance from the dictionary
    # This assumes lead_data keys match Lead model attributes.
    # Consider using Pydantic model for lead_data validation before this step.
    try:
        lead_to_save = Lead(**lead_data)
    except TypeError as te: # Handles cases where lead_data has unexpected keys for Lead model
        logger.error(f"TypeError creating Lead model from data for '{company_name_log}': {te}. Data: {lead_data}", exc_info=True)
        return None

    # Manage session: use provided or create new
    session_to_use: Optional[AsyncSession] = None
    created_session_locally = False

    if db_session:
        session_to_use = db_session
    else:
        session_factory = get_async_session_local()
        session_to_use = session_factory()
        created_session_locally = True
        logger.debug(f"[SAVE_LEAD] Created new DB session for saving lead: {company_name_log}")

    try:
        session_to_use.add(lead_to_save)
        
        if created_session_locally:
            # If session is local, we manage the transaction (flush, commit, rollback)
            await session_to_use.flush() # Flushes to DB, assigns ID if autoincrement
            await session_to_use.refresh(lead_to_save) # Updates instance with DB state (e.g., defaults)
            await session_to_use.commit() # Commits the transaction
            logger.success(f"[SAVE_LEAD] Lead ID {lead_to_save.id} ('{lead_to_save.company_name}') committed successfully (local session).")
        else:
            # If using an external session, just flush to get ID. Caller handles commit.
            await session_to_use.flush()
            await session_to_use.refresh(lead_to_save)
            logger.info(f"[SAVE_LEAD] Lead ID {lead_to_save.id} ('{lead_to_save.company_name}') added/flushed to provided session. Caller must commit.")
        
        return lead_to_save

    except Exception as e:
        if created_session_locally and session_to_use: # Rollback local session on error
            try:
                await session_to_use.rollback()
                logger.info(f"[SAVE_LEAD] Rollback successful for local session after error saving '{company_name_log}'.")
            except Exception as rb_e: # Log error during rollback itself
                logger.error(f"[SAVE_LEAD] Critical error during rollback for local session: {rb_e}", exc_info=True)
        
        logger.error(f"[SAVE_LEAD] Error saving lead for '{company_name_log}': {e}", exc_info=True)
        return None # Indicate failure
    finally:
        if created_session_locally and session_to_use: # Close locally created session
            try:
                await session_to_use.close()
                logger.debug(f"[SAVE_LEAD] Local DB session closed for: {company_name_log}")
            except Exception as close_e:
                logger.error(f"[SAVE_LEAD] Error closing local DB session: {close_e}", exc_info=True)

# Function for tests to reset module-level engine/session factory if settings change.
# This is more of a utility for complex test setups.
def _reset_db_state_for_testing():
    """Resets the global engine and session factory variables. For testing purposes."""
    global _engine, _async_session_local
    if _engine:
        # Disposing the engine might be necessary if tests change DB URLs dynamically.
        # However, if each test suite/module manages its own engine based on settings at its start,
        # this explicit disposal might not always be needed here.
        # For now, just nullifying the global reference.
        logger.debug("[DB_FACTORY_RESET] Nullifying module-level engine and session factory references for testing.")
    _engine = None
    _async_session_local = None
