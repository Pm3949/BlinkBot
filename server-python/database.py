"""
Database Connection Manager.
Responsibility: Establishes and provides raw connections to the PostgreSQL database.
"""
# server-python/database.py
import os
import psycopg2
from psycopg2 import pool
from contextlib import asynccontextmanager
from fastapi.concurrency import run_in_threadpool
from dotenv import load_dotenv

load_dotenv()
# The DATABASE_URL contains all credentials (user, password, host, port, dbname) in a single string
DB_URL = os.getenv("DATABASE_URL")

# Fail-fast: If there's no DB connection string, the app can't function. Better to crash immediately on startup than fail silently later.
if not DB_URL:
    raise ValueError("DATABASE_URL must be set in .env file")

# Initialize a global connection pool
try:
    db_pool = psycopg2.pool.ThreadedConnectionPool(1, 30, DB_URL)
except Exception as e:
    raise RuntimeError(f"Failed to initialize database pool: {e}")

def get_db_connection():
    """
    LEGACY: Returns a PostgreSQL connection object from the pool.
    IMPORTANT: You MUST call release_db_connection(conn) in a `finally` block!
    """
    return db_pool.getconn()

def release_db_connection(conn):
    """
    Returns a connection back to the pool.
    """
    if db_pool:
        db_pool.putconn(conn)

@asynccontextmanager
async def get_db_cursor_async(commit=False, cursor_factory=None):
    """
    Async context manager that borrows a connection from the pool, creates a cursor,
    yields it, handles automatic commit/rollback, and returns the connection to the pool.
    """
    conn = db_pool.getconn()
    cursor = conn.cursor(cursor_factory=cursor_factory) if cursor_factory else conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        db_pool.putconn(conn)

@asynccontextmanager
async def get_db_connection_async():
    """
    Async context manager that yields the raw connection object if you need to manage
    cursors and commits manually.
    """
    conn = db_pool.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        db_pool.putconn(conn)