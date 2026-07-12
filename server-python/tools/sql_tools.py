from typing import List, Any
import logging
from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool, BaseTool
import threading

logger = logging.getLogger(__name__)

# Cache SQLDatabase instances to avoid excessive connection overhead
_db_cache = {}
_db_cache_lock = threading.Lock()

def get_sql_database(connection_string: str) -> SQLDatabase:
    with _db_cache_lock:
        if connection_string not in _db_cache:
            # Setting view_support to True can be useful for Postgres
            db = SQLDatabase.from_uri(connection_string, sample_rows_in_table_info=3)
            _db_cache[connection_string] = db
        return _db_cache[connection_string]

def create_sql_tools(connection_string: str, db_name: str) -> List[BaseTool]:
    """
    Creates LangChain tools to inspect and query the connected database.
    """
    try:
        db = get_sql_database(connection_string)
    except Exception as e:
        logger.error(f"Failed to connect to database {db_name}: {e}")
        return []

    # Dynamically define the tools bounded to this specific database connection
    
    @tool(name=f"list_tables_{db_name.replace(' ', '_')}")
    def list_tables(tool_input: str = "") -> str:
        """List all available tables in the database."""
        try:
            return db.get_usable_table_names()
        except Exception as e:
            return f"Error listing tables: {e}"

    @tool(name=f"get_schema_{db_name.replace(' ', '_')}")
    def get_schema(table_names: str) -> str:
        """
        Get the schema and sample rows for the specified comma-separated tables.
        Example input: 'users, orders'
        """
        try:
            t_names = [t.strip() for t in table_names.split(",") if t.strip()]
            return db.get_table_info(t_names)
        except Exception as e:
            return f"Error getting schema: {e}"

    @tool(name=f"execute_sql_{db_name.replace(' ', '_')}")
    def execute_sql(query: str) -> str:
        """
        Execute a raw SQL query against the database and return the results.
        Only use this for SELECT queries. Do not use for INSERT/UPDATE/DELETE.
        """
        if any(keyword in query.upper() for keyword in ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER"]):
            return "Error: Only SELECT queries are permitted for safety."
        try:
            return db.run(query)
        except Exception as e:
            return f"Error executing query: {e}"

    return [list_tables, get_schema, execute_sql]
