"""
================================================================================
ANALYTICS REPORT CONTROLLER LAYER (analytics.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for compiling personal analytics reports
for a user. It gathers usage statistics, total document uploads, storage consumption,
message transaction summaries, and chat session histories.

DATA FLOW:
- The HTTP request triggers `get_analytics`.
- The user's ID is retrieved from the `Depends(get_current_user)` JWT session verification payload.
- The user ID is passed to `handle_get_analytics` inside the analytics handler layer.
"""

import logging
from utils.logger import get_department_logger
from fastapi import APIRouter, Depends
from core.auth import get_current_user

# Import the core business logic executor for analytics compilation.
from handlers.analytics_handler import handle_get_analytics

# Configure standard module-level logger.
logger = get_department_logger("system")

# Initialize router with tag categories for automated API mapping documentation.
router = APIRouter(tags=["analytics"])


@router.get("/analytics")
async def get_analytics(current_user: dict = Depends(get_current_user)):
    """
    Generates a personal usage and storage analytics report for the authenticated user.

    Purpose:
        Retrieves user metrics (document counts, tokens, messages sent, storage quotas)
        for dashboard stats rendering.

    Parameters:
        current_user (dict): JWT details.

    Returns:
        dict: Compiled metrics payload.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401 Unauthorized if the authentication token is expired or missing.
    """
    # Extract the user's unique identifier from the subject ("sub") claim.
    user_id = current_user["sub"]
    # Delegate query operations to the analytics handler.
    return await handle_get_analytics(user_id)

