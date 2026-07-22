import os
import logging
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict
from contextvars import ContextVar

# Context variables to track user ID and client IP address across request execution threads
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")
client_ip_var: ContextVar[str] = ContextVar("client_ip", default="-")

# Dictionary to keep track of active loggers
_loggers: Dict[str, logging.Logger] = {}

class ISTFormatter(logging.Formatter):
    """
    Custom formatter that forces the log timestamps to Indian Standard Time (IST)
    and dynamically appends request user and client IP details when present.
    """
    def formatTime(self, record, datefmt=None):
        # Convert log epoch timestamp to Asia/Kolkata timezone
        dt = datetime.fromtimestamp(record.created, tz=ZoneInfo("Asia/Kolkata"))
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S IST")

    def format(self, record):
        user_id = user_id_var.get("-")
        client_ip = client_ip_var.get("-")
        
        context_parts = []
        if user_id and user_id != "-":
            context_parts.append(f"User: {user_id}")
        if client_ip and client_ip != "-":
            context_parts.append(f"IP: {client_ip}")
            
        record.context_info = f" [{'] ['.join(context_parts)}]" if context_parts else ""
        return super().format(record)

def get_department_logger(department_name: str) -> logging.Logger:
    """
    Returns a configured Logger instance for the specified department.
    Each department logger writes to both:
    1. The main console stream.
    2. A department-specific log file under logs/ directory.
    """
    dept_lower = department_name.strip().lower()
    dept_upper = dept_lower.upper()
    logger_name = f"dept.{dept_upper}"
    
    # Avoid adding duplicate handlers if the logger already exists
    if logger_name in _loggers:
        return _loggers[logger_name]
        
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    # Prevent propagation to the root logger to avoid double logging
    logger.propagate = False
    
    # Define custom IST format including context info
    log_format = "[%(asctime)s] [%(name)s] [%(levelname)s]%(context_info)s: %(message)s"
    formatter = ISTFormatter(fmt=log_format)
    
    # 1. Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 2. Dedicated Department File Handler
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    file_path = os.path.join(logs_dir, f"{dept_lower}.log")
    
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    _loggers[logger_name] = logger
    return logger

def cleanup_department_loggers():
    """
    Closes all active file handlers on all department loggers to unlock files.
    """
    for logger in list(_loggers.values()):
        for handler in list(logger.handlers):
            try:
                handler.close()
                logger.removeHandler(handler)
            except Exception:
                pass
    _loggers.clear()
