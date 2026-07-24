"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all Analytics dashboard actions
in the RAGMate backend. It maps incoming HTTP REST requests directly to the
underlying business logic executors defined inside the analytics handler modules.

From top to bottom, the file performs the following tasks:
1. Imports: Loads standard logging controllers, FastAPI routing modules, and JWT
   authentication guards.
2. Routing Initialization: Declares the APIRouter for 'analytics' tag groupings.
3. HTTP Routes:
   - GET `/analytics`: Fetches workspace and message metrics summaries, checking
     requester permissions using `Depends(get_current_user)`.
"""

import logging  # Import python logging library
from fastapi import APIRouter, Depends  # FastAPI Router object and Dependency Injection tools
from core.auth import get_current_user  # JWT helper to authenticate requests

# Import analytics logic handlers
from handlers.analytics_handler import handle_get_analytics

# Instantiate a scoped file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router for analytics endpoints, grouping with tags
router = APIRouter(tags=["analytics"])


@router.get("/analytics")
async def get_analytics(current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to fetch a user's analytics metrics report.
    Checks JWT tokens in the request header to verify identity.

    Parameters:
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: A dictionary of analytics statistics (message counts, latency graphs, active agents).

    Exceptions Raised:
        HTTPException(401): Raised if the token is invalid.
        HTTPException(500): Raised if database queries fail.
    """
    user_id = current_user["sub"]  # Extract the subject (user UUID) from the validated JWT dictionary
    return await handle_get_analytics(user_id)  # Route task execution to handlers layer
