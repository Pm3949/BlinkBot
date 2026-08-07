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
    # Pre-allocates a minimum of 1 connection and caps active concurrent connections at 30.
    db_pool = psycopg2.pool.ThreadedConnectionPool(1, 30, DB_URL)
    logger.info("Database connection pool initialized successfully (min=1, max=30)")
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


@asynccontextmanager
async def get_db_cursor_async(commit: bool = False, cursor_factory=None):
    """
    Asynchronous context manager that yields a database cursor.

    Purpose:
        Simplifies transaction handling. Automatically commits changes on success,
        rolls back modifications on failure, and closes the cursor and returns 
        the connection to the pool upon exit.

    Parameters:
        commit (bool): If True, commits the transaction on successful block completion.
                       Defaults to False.
        cursor_factory (type, optional): Custom cursor class (e.g. DictCursor).
                                         Defaults to None.

    Yields:
        psycopg2.extensions.cursor: The cursor object.

    Side Effects / State Changes:
        - Modifies row records if insert/update/delete SQL queries are run and committed.
        - Borrows and returns connection pool resources.

    Errors / Exceptions:
        - Automatically rolls back the transaction and re-raises any database exceptions.
    """
    # Borrow a connection from the pool.
    conn = db_pool.getconn()
    
    # Instantiate the cursor using the custom factory if provided.
    cursor = conn.cursor(cursor_factory=cursor_factory) if cursor_factory else conn.cursor()
    try:
        # Yield the cursor control block back to the caller.
        yield cursor
        # If the block executed successfully and commit is True, commit the transaction.
        if commit:
            conn.commit()
    except Exception as e:
        # If any exception occurred during block execution, roll back the transaction.
        conn.rollback()
        logger.warning(f"Transaction rolled back due to error: {type(e).__name__}")
        # Re-raise the exception.
        raise
    finally:
        # Close the cursor.
        cursor.close()
        # Return the connection to the pool.
        db_pool.putconn(conn)


@asynccontextmanager
async def get_db_connection_async():
    """
    Asynchronous context manager that yields a raw connection object.

    Purpose:
        Provides raw connection access for custom cursor configurations
        or manual transaction management.

    Yields:
        psycopg2.extensions.connection: The borrowed connection object.

    Side Effects / State Changes:
        - Borrows and returns connection pool resources.

    Errors / Exceptions:
        - Automatically rolls back and re-raises exceptions if the block fails.
    """
    # Borrow a connection from the pool.
    conn = db_pool.getconn()
    try:
        # Yield the raw connection object to the caller.
        yield conn
    except Exception as e:
        # Roll back on error.
        conn.rollback()
        logger.warning(f"Raw connection transaction rolled back due to error: {type(e).__name__}")
        raise
    finally:
        # Return the connection.
        db_pool.putconn(conn)