# server-python/database.py
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    raise ValueError("DATABASE_URL must be set in .env file")

def get_db_connection():
    return psycopg2.connect(DB_URL)