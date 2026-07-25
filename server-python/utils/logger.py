"""
================================================================================
DEPARTMENTAL LOGGING & DYNAMIC CONTEXT TRACKING SYSTEM (logger.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module provides a unified, thread-safe departmental logging framework for the 
RAGMate application. Instead of writing all application output to a single, chaotic 
system log file, this utility allows different system areas (departments) to maintain 
independent log handlers. 

KEY ARCHITECTURAL FEATURES:
1. Dynamic Context Propagation (ContextVar):
   Uses Python's `contextvars` module to track and log metadata (such as the current 
   User UUID and the client's source IP address) across asynchronous coroutines and 
   execution threads without requiring developers to manually pass this data through 
   every single function parameter.
2. Timezone Standardization (IST):
   Forced timestamp output formatted to Indian Standard Time (IST / Asia/Kolkata) 
   by overriding the standard logging library time formatter.
3. Multi-Destination Handlers:
   Dynamically configures loggers to write messages to two locations simultaneously:
     - The terminal console stream (stdout) for container orchestration platforms (like Docker/Kubernetes).
     - Department-specific log files under the local directory path `./logs/{department}.log`.
4. Logger Lifecycle & Resource Disposal:
   Implements safety mechanisms to close, flush, and release file locks on all active 
   file handlers during application shutdown, ensuring files are not left locked.

BEGINNER COMPONENT BREAKDOWN:
- ContextVar: Think of this as a special "thread-local" global variable that is safe 
  to use in asynchronous programs. When FastAPI processes concurrent requests, 
  each client request runs in its own context. `ContextVar` keeps track of which 
  user belongs to which output log line.
- Logger Registry: A global dictionary cache (_loggers) tracking which department 
  loggers have already been created so that we do not accidentally create duplicate 
  file handlers or write duplicate log rows.
"""

import os
import logging
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict
from contextvars import ContextVar

# ==========================================
# THREAD-SAFE CONTEXT VARIABLES
# ==========================================

# ContextVar tracks user ID across concurrent request executions.
# The default value is "-" representing an anonymous or unauthenticated request.
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")

# ContextVar tracks client IP address across request executions.
# The default value is "-" representing requests made from internal loops or unknown paths.
client_ip_var: ContextVar[str] = ContextVar("client_ip", default="-")


# ==========================================
# GLOBAL REGISTRY CACHE
# ==========================================

# Dict caching already initialized Loggers.
# The key is the fully qualified logger name (e.g. 'dept.BILLING'), and the value is the Logger instance.
_loggers: Dict[str, logging.Logger] = {}


# ==========================================
# FORMATTING CLASSES
# ==========================================

class ISTFormatter(logging.Formatter):
    """
    Custom log formatter that forces logs to Indian Standard Time (IST)
    and appends user session and IP metadata to log records.

    Inherits:
        logging.Formatter: The standard formatter class from Python's logging library.
    """

    def formatTime(self, record: logging.LogRecord, datefmt: str = None) -> str:
        """
        Translates a log entry's creation timestamp to Indian Standard Time (IST).

        Purpose:
            Overrides the standard formatTime method to ignore local system/server time settings
            and force time output to Asia/Kolkata.

        Parameters:
            record (logging.LogRecord): The system object containing metadata of the log event.
            datefmt (str, optional): A format string specifying the date/time layout.
                                     Defaults to None, which triggers standard ISO formatting.

        Returns:
            str: A formatted string representation of the timestamp (e.g., '2026-07-25 20:08:00 IST').

        Side Effects:
            - None. Purely reads data.

        Errors / Exceptions:
            - May raise ZoneInfoNotFoundError if the database of timezones is missing or corrupt.
        """
        # Convert the epoch timestamp (record.created) to a datetime object localized to Asia/Kolkata.
        dt = datetime.fromtimestamp(record.created, tz=ZoneInfo("Asia/Kolkata"))
        
        # If the caller provided a specific format string, use standard strftime formatting.
        if datefmt:
            return dt.strftime(datefmt)
            
        # Default fallback format appending standard timezone indicators.
        return dt.strftime("%Y-%m-%d %H:%M:%S IST")

    def format(self, record: logging.LogRecord) -> str:
        """
        Formats the output string of a log record, injecting current context variables.

        Purpose:
            Fetches active user details and client IP properties from thread-local ContextVars,
            assembles them into a bracketed metadata string, and appends it to the formatted log.

        Parameters:
            record (logging.LogRecord): The system record object representing the log message.

        Returns:
            str: The final formatted log string with metadata injected.

        Side Effects:
            - Modifies the LogRecord object dynamically by writing a new attribute `context_info` to it.

        Errors / Exceptions:
            - None. If context vars are empty, fallback strings are used.
        """
        # Fetch the current value of the user_id ContextVar. Defaults to "-" if not set.
        user_id = user_id_var.get("-")
        
        # Fetch the current value of the client_ip ContextVar. Defaults to "-" if not set.
        client_ip = client_ip_var.get("-")
        
        # Initialize an empty list to assemble active metadata properties.
        context_parts = []
        
        # If a valid user ID is set (not None and not "-"), add it to the metadata parts list.
        if user_id and user_id != "-":
            context_parts.append(f"User: {user_id}")
            
        # If a valid client IP is set (not None and not "-"), add it to the parts list.
        if client_ip and client_ip != "-":
            context_parts.append(f"IP: {client_ip}")
            
        # If we collected metadata parts, format them inside brackets: e.g. " [User: 123] [IP: 192.168.1.1]".
        # Otherwise, leave it as an empty string to avoid adding extra brackets to the log output.
        record.context_info = f" [{'] ['.join(context_parts)}]" if context_parts else ""
        
        # Call the parent Formatter's format method to assemble the final log string.
        return super().format(record)


# ==========================================
# PUBLIC CONTROLLER FUNCTIONS
# ==========================================

def get_department_logger(department_name: str) -> logging.Logger:
    """
    Retrieves or creates a configured Logger instance for a department.

    Purpose:
        Configures loggers to write messages to stdout and a department-specific
        log file under the `./logs/` directory. Saves loggers in a cache registry
        to prevent creating duplicate handlers.

    Parameters:
        department_name (str): The name of the department (e.g. 'billing', 'chat', 'auth').

    Returns:
        logging.Logger: The configured logger instance.

    Side Effects / State Changes:
        - Creates a `./logs` directory on disk if it does not exist.
        - Appends new handlers to the target Logger.
        - Adds the initialized Logger to the global registry cache.

    Errors / Exceptions:
        - Raises OSError if log directory creation or log file writing permissions are denied.
    """
    # Clean the input name: remove leading/trailing spaces and convert to lowercase.
    dept_lower = department_name.strip().lower()
    
    # Create an uppercase variant for logger naming normalization.
    dept_upper = dept_lower.upper()
    
    # Establish a unique logger name prefixed with 'dept.' (e.g. 'dept.BILLING').
    logger_name = f"dept.{dept_upper}"
    
    # Check if the logger has already been configured and cached in our registry.
    if logger_name in _loggers:
        # Return the existing instance directly to avoid duplicate handler registrations.
        return _loggers[logger_name]
        
    # Request a raw logger instance from the standard logging library.
    logger = logging.getLogger(logger_name)
    
    # Set the minimum logging severity level to DEBUG.
    logger.setLevel(logging.DEBUG)
    
    # Prevent logger propagation.
    # Propagation sends log records to parent loggers (like the root logger).
    # Setting this to False avoids printing duplicate log lines.
    logger.propagate = False
    
    # Define the log formatting template.
    # Note the custom key `%(context_info)s`, which matches the property we append in `ISTFormatter.format`.
    log_format = "[%(asctime)s] [%(name)s] [%(levelname)s]%(context_info)s: %(message)s"
    
    # Initialize the custom timezone-aware formatter.
    formatter = ISTFormatter(fmt=log_format)
    
    # ------------------------------------------
    # 1. Terminal Console Stream Handler Setup
    # ------------------------------------------
    
    # Initialize standard stream handler (defaulting to sys.stderr/sys.stdout).
    console_handler = logging.StreamHandler()
    
    # Set debug level threshold for console outputs.
    console_handler.setLevel(logging.DEBUG)
    
    # Bind the timezone formatter to the handler.
    console_handler.setFormatter(formatter)
    
    # Attach the handler to the logger.
    logger.addHandler(console_handler)
    
    # ------------------------------------------
    # 2. File Handler Setup
    # ------------------------------------------
    
    # Define directory name for logs.
    logs_dir = "logs"
    
    # Safely create the target directory if it does not exist.
    os.makedirs(logs_dir, exist_ok=True)
    
    # Construct the absolute path to the log file (e.g., 'logs/billing.log').
    file_path = os.path.join(logs_dir, f"{dept_lower}.log")
    
    # Initialize file writer handler. Forces UTF-8 encoding.
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    
    # Set the debug level threshold for file logs.
    file_handler.setLevel(logging.DEBUG)
    
    # Bind the timezone formatter to the file handler.
    file_handler.setFormatter(formatter)
    
    # Attach the file handler to the logger.
    logger.addHandler(file_handler)
    
    # Store the logger in the cache registry dictionary.
    _loggers[logger_name] = logger
    
    # Return the fully configured logger.
    return logger


def cleanup_department_loggers():
    """
    Closes all active file and console handlers on registered loggers.

    Purpose:
        Iterates through all cached department loggers, closes their active
        handlers, and clears the logger registry. This unlocks log files during
        application shutdown.

    Parameters:
        None.

    Returns:
        None.

    Side Effects / State Changes:
        - Closes all file descriptor handles for log files on disk.
        - Removes handlers from registered loggers.
        - Clears the global `_loggers` registry cache.

    Errors / Exceptions:
        - None. Catches and ignores handler closing exceptions to ensure cleanup continues.
    """
    # Iterate through all configured logger instances in the cache list.
    for logger in list(_loggers.values()):
        # Iterate through all active handlers attached to this specific logger.
        for handler in list(logger.handlers):
            try:
                # Flush and close the handler's file write descriptor.
                handler.close()
                # Remove the handler from the logger instance.
                logger.removeHandler(handler)
            except Exception:
                # Catch any unexpected errors (such as file access lock errors)
                # and continue cleaning up other handlers.
                pass
                
    # Clear the global logger cache directory dictionary.
    _loggers.clear()

