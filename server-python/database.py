"""
Database Connection Manager.
Responsibility: Establishes and provides raw connections to the PostgreSQL database.
"""
# server-python/database.py
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
# The DATABASE_URL contains all credentials (user, password, host, port, dbname) in a single string
DB_URL = os.getenv("DATABASE_URL")

# Fail-fast: If there's no DB connection string, the app can't function. Better to crash immediately on startup than fail silently later.
if not DB_URL:
    raise ValueError("DATABASE_URL must be set in .env file")

def get_db_connection():
    """
    Returns a new PostgreSQL connection object.
    IMPORTANT: Every time this is called, a new connection is opened. 
    It is the caller's responsibility to close the connection in a `finally` block 
    to prevent connection pool exhaustion.
    """
    return psycopg2.connect(DB_URL)