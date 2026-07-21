import logging
from fastapi import APIRouter, Depends
from core.auth import get_current_user

from handlers.analytics_handler import handle_get_analytics

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analytics"])

@router.get("/analytics")
async def get_analytics(current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to generate a comprehensive analytics report for the user.
    Args:
        user_id (str): The user ID.
    Returns: The analytics report metrics.
    """
    user_id = current_user["sub"]
    return await handle_get_analytics(user_id)
