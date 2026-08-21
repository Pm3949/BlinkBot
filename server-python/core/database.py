"""
================================================================================
POSTGRESQL DATABASE CONNECTION POOL & TRANSACTION MANAGER (database.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the core database access layer for the RAGMate backend. It sets up 
and manages a PostgreSQL connection pool (`psycopg2.pool.ThreadedConnectionPool`) and 
exposes context managers for transaction handshakes.

KEY ARCHITECTURAL FEATURES:
1. Threaded Connection Pooling:
   Initializing database connections is expensive (network roundtrips, handshakes, 
   memory allocation). The `ThreadedConnectionPool` pre-allocates a set of active 
   connections (min: 1, max: 30) that can be borrowed and returned instantly.
2. Async Context Managers (`get_db_cursor_async` & `get_db_connection_async`):
   Leverages FastAPI's concurrent workflows. By using Python's `asynccontextmanager` decorator,
   this module allows asynchronous functions to borrow a cursor or connection, automatically
   commits transactions on success, rolls back queries on failures, and returns resources to the 
   pool in `finally` blocks to prevent leakages.
3. Fail-Fast Design:
   Checks for the `DATABASE_URL` environment variable during initial execution. If the 
   variable is missing or the connection pool fails to initialize, the application crashes 
   immediately, preventing silent failures.

BEGINNER COMPONENT BREAKDOWN:
- Connection Pool: Think of this as a library of active database connections. Code borrowing 
  connections must return them (`putconn`) when finished so other requests can reuse them.
- Cursor: A cursor is a pointer structure that executes SQL commands and retrieves results.
- Commit vs Rollback: A commit permanently saves changes made during a transaction. 
  A rollback undoes all modifications if any step in the transaction fails, maintaining database integrity.
"""

import os
import psycopg2
from psycopg2 import pool
from contextlib import asynccontextmanager
from fastapi.concurrency import run_in_threadpool
from dotenv import load_dotenv
from utils.logger import get_db_logger

# Load local system environment variables.
load_dotenv()

# Initialize database connection pool logger.
logger = get_db_logger("pool")

# Retrieve the PostgreSQL connection string. Contains credentials, host, port, and database name.
DB_URL = os.getenv("DATABASE_URL")

# Fail-Fast: Verify the connection string exists in configurations.
if not DB_URL:
    raise ValueError("DATABASE_URL must be set in .env file")

# Initialize the global connection pool cache.
try:
    # Read pool limits dynamically from environment, defaulting to min=1, max=10.
    db_pool_min = int(os.getenv("DB_POOL_MIN", "1"))
    db_pool_max = int(os.getenv("DB_POOL_MAX", "10"))
    
    db_pool = psycopg2.pool.ThreadedConnectionPool(db_pool_min, db_pool_max, DB_URL)
    logger.info(f"Database connection pool initialized successfully (min={db_pool_min}, max={db_pool_max})")
except Exception as e:
    # Raise a critical runtime error if the database pool fails to initialize.
    logger.critical(f"Failed to initialize database pool: {e}", exc_info=True)
    raise RuntimeError(f"Failed to initialize database pool: {e}")


# ==========================================
# PUBLIC CONNECTION CONTROLLER FUNCTIONS
# ==========================================

def get_db_connection():
    """
    Retrieves a raw database connection from the pool.

    Purpose:
        Legacy sync accessor. Borrowers must call `release_db_connection` in a `finally` block.

    Parameters:
        None.

    Returns:
        psycopg2.extensions.connection: The borrowed connection object.
    """
    # Fetch a connection from the pool.
    return db_pool.getconn()


def release_db_connection(conn):
    """
    Returns a borrowed connection back to the pool.

    Purpose:
        Legacy sync cleanup utility.

    Parameters:
        conn (psycopg2.extensions.connection): The connection object to return.

    Returns:
        None.

    Side Effects / State Changes:
        - Frees up a connection slot in the connection pool.
    """
    # Verify the pool exists and return the connection.
    if db_pool:
        db_pool.putconn(conn)


def _check_connection_alive(conn):
    """
    Synchronous helper to verify if a connection is alive by running a quick query.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
        return True
    except Exception:
        return False


async def _get_valid_connection():
    """
    Retrieves a connection from the pool, validating its health.
    Discards dead connections and retries up to 3 times.
    """
    for _ in range(3):
        conn = await run_in_threadpool(db_pool.getconn)
        is_alive = await run_in_threadpool(_check_connection_alive, conn)
        if is_alive:
            return conn
        
        logger.warning("Borrowed a dead database connection from the pool. Discarding and retrying...")
        try:
            await run_in_threadpool(db_pool.putconn, conn, close=True)
        except Exception as e:
            logger.debug(f"Error putting dead connection back to pool: {e}")
            
    # Fallback to a standard getconn if retries fail
    return await run_in_threadpool(db_pool.getconn)


@asynccontextmanager
async def get_db_cursor_async(commit: bool = False, cursor_factory=None):
    """
    Asynchronous context manager that yields a database cursor.

    Purpose:
        Simplifies transaction handling. Automatically commits changes on success,
        rolls back modifications on failure, and closes the cursor and returns 
        the connection to the pool upon exit.
        
        Optimized: All blocking psycopg2 methods (pool.getconn, commit, rollback, putconn)
        are delegated to run_in_threadpool to keep the main asyncio event loop non-blocking.
    """
    # Borrow a connection from the pool on a worker thread
    conn = await _get_valid_connection()
    
    # Instantiate the cursor using the custom factory if provided on a worker thread
    if cursor_factory:
        cursor = await run_in_threadpool(conn.cursor, cursor_factory=cursor_factory)
    else:
        cursor = await run_in_threadpool(conn.cursor)

    try:
        # Yield the cursor control block back to the caller.
        yield cursor
        # If the block executed successfully and commit is True, commit the transaction on a worker thread.
        if commit:
            await run_in_threadpool(conn.commit)
        else:
            await run_in_threadpool(conn.rollback)
    except Exception as e:
        # If any exception occurred, roll back on a worker thread if the connection is not closed.
        try:
            await run_in_threadpool(conn.rollback)
        except psycopg2.InterfaceError:
            # Connection is already closed/dead, rollback is not possible
            pass
        logger.warning(f"Transaction rolled back due to error: {type(e).__name__}")
        raise
    finally:
        # Close the cursor and return the connection on a worker thread.
        try:
            await run_in_threadpool(cursor.close)
        except Exception:
            pass
        try:
            await run_in_threadpool(db_pool.putconn, conn)
        except Exception:
            pass


@asynccontextmanager
async def get_db_connection_async():
    """
    Asynchronous context manager that yields a raw connection object.

    Purpose:
        Provides raw connection access for custom cursor configurations
        or manual transaction management.
        
        Optimized: Delegated pool methods to run_in_threadpool to ensure non-blocking loop execution.
    """
    # Borrow a connection from the pool on a worker thread
    conn = await _get_valid_connection()
    try:
        # Yield the raw connection object to the caller.
        query_successful = False
        yield conn
        query_successful = True
    except Exception as e:
        # Roll back on error on a worker thread.
        try:
            await run_in_threadpool(conn.rollback)
        except psycopg2.InterfaceError:
            pass
        logger.warning(f"Raw connection transaction rolled back due to error: {type(e).__name__}")
        raise
    finally:
        # Return the connection on a worker thread.
        try:
            await run_in_threadpool(db_pool.putconn, conn)
        except Exception:
            pass

