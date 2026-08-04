"""
================================================================================
DYNAMIC DATABASE INSPECTION & SQL INVOCATION SYSTEM (sql_tools.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module compiles external database tools allowing agent networks to inspect schemas,
list structures, and execute read-only queries against linked database connections.

KEY ARCHITECTURAL CONCEPTS:
1. Thread-Safe Connection Caching (`get_sql_database`):
   Creating a connection is expensive. This module caches `SQLDatabase` instances inside a 
   global dictionary (`_db_cache`) protected by a thread lock (`threading.Lock`) to prevent 
   race conditions during concurrent requests.
2. Dynamic Bounded Tool Namespaces (`create_sql_tools`):
   Dynamically generates tools bound to specific connection strings. Tool names are dynamically 
   suffixed with sanitised database names (e.g. `list_tables_my_db`) to prevent naming 
   collisions in multi-agent environments.
3. Read-Only Query Constraints:
   Filters incoming SQL queries to block write commands (`DROP`, `DELETE`, `TRUNCATE`, `UPDATE`, 
   `INSERT`, `ALTER`), enforcing read-only behavior for safety.

BEGINNER DATABASE CONCEPTS:
- SQLDatabase (LangChain): An abstraction layer that inspects database structures, 
  retrieves schemas, and executes raw SQL queries.
- Schema: The structure of a database, including table names, columns, and data types.
- Thread Lock: A synchronization primitive that ensures only one thread executes a block 
  of code at a time, preventing race conditions.
"""

from typing import List, Any
import logging
from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool, BaseTool
import threading

# Initialize standard module logger.
logger = logging.getLogger(__name__)

# Global cache dictionary for SQLDatabase connection objects.
_db_cache = {}
# Thread lock to guarantee thread-safe cache updates.
_db_cache_lock = threading.Lock()


# ==========================================
# CACHED CONNECTION UTILITY
# ==========================================

def get_sql_database(connection_string: str) -> SQLDatabase:
    """
    Retrieves or establishes a cached SQLDatabase connection.

    Purpose:
        Returns a cached SQLDatabase instance for the connection string, 
        initializing a new one if it is not already cached.

    Parameters:
        connection_string (str): The target database connection URI.

    Returns:
        SQLDatabase: The cached or newly initialized database object.

    Side Effects / State Changes:
        - Updates the global connection cache `_db_cache`.
    """
    # Acquire the thread lock before reading or writing to the cache.
    with _db_cache_lock:
        if connection_string not in _db_cache:
            # Initialize a new connection object, fetching 3 sample rows per table.
            db = SQLDatabase.from_uri(connection_string, sample_rows_in_table_info=3)
            # Store the instance in the cache.
            _db_cache[connection_string] = db
        # Return the cached instance.
        return _db_cache[connection_string]


# ==========================================
# PUBLIC SQL TOOL CONSTRUCTORS
# ==========================================

def create_sql_tools(connection_string: str, db_name: str) -> List[BaseTool]:
    """
    Creates LangChain database tools bound to a specific connection.

    Purpose:
        Initializes database connections and returns database inspection tools.

    Parameters:
        connection_string (str): The database connection URI.
        db_name (str): Human-readable name of the target database.

    Returns:
        list of BaseTool: List containing database inspection tools, 
                         or an empty list if the connection fails.
    """
    try:
        # Load the connection instance.
        db = get_sql_database(connection_string)
    except Exception as e:
        # Log connection failures and return an empty list.
        logger.error(f"Failed to connect to database {db_name}: {e}")
        return []

    # Clean the database name for tool naming compatibility.
    clean_db_name = db_name.replace(" ", "_")

    # ------------------------------------------
    # 1. LIST TABLES TOOL
    # ------------------------------------------
    @tool(name=f"list_tables_{clean_db_name}")
    def list_tables(tool_input: str = "") -> str:
        """List all available tables in the database."""
        try:
            # Query and return usable table names.
            return db.get_usable_table_names()
        except Exception as e:
            return f"Error listing tables: {e}"

    # ------------------------------------------
    # 2. GET SCHEMA TOOL
    # ------------------------------------------
    @tool(name=f"get_schema_{clean_db_name}")
    def get_schema(table_names: str) -> str:
        """
        Get the schema and sample rows for the specified comma-separated tables.
        Example input: 'users, orders'
        """
        try:
            # Split comma-separated table names, stripping whitespace.
            t_names = [t.strip() for t in table_names.split(",") if t.strip()]
            # Retrieve schemas and sample rows.
            return db.get_table_info(t_names)
        except Exception as e:
            return f"Error getting schema: {e}"

    # ------------------------------------------
    # 3. EXECUTE SQL QUERY TOOL
    # ------------------------------------------
    @tool(name=f"execute_sql_{clean_db_name}")
    def execute_sql(query: str) -> str:
        """
        Execute a raw SQL query against the database and return the results.
        Only use this for SELECT queries. Do not use for INSERT/UPDATE/DELETE.
        """
        # Read-Only Safety Validation: Block query execution if modifying statements are detected.
        if any(keyword in query.upper() for keyword in ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER"]):
            return "Error: Only SELECT queries are permitted for safety."
        try:
            # Execute the query and return the results.
            res = db.run(query)
            if len(res) > 2000:
                truncated_res = res[:2000]
                return (
                    f"{truncated_res}\n\n"
                    f"[OUTPUT TRUNCATED: The result length was {len(res)} characters, which exceeds the 2,000 character context limit. "
                    "If you need to view more rows, please re-run the query using SQL LIMIT and OFFSET for pagination.]"
                )
            return res
        except Exception as e:
            return f"Error executing query: {e}"

    # Return the assembled tools.
    return [list_tables, get_schema, execute_sql]

