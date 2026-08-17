"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script handles the retrieval and aggregation of dashboard analytics data
for RAGMate users.

From top to bottom, the file works as follows:
1. Imports: Loads the FastAPI exception handling module and the analytics 
   database repository.
2. Department Logging: Initializes a logger specifically for auditing database
   transactions and dashboard statistics rendering.
3. Analytics Handler (`handle_get_analytics`): 
   - Receives the requesting User ID.
   - Makes five concurrent/sequential queries to the database layer to obtain:
     a) Global metrics counts (total agents, total docs, total storage in MB, widget message volume).
     b) Daily historical chart data series for internal chats and external widgets.
     c) The top chatbots ranked by chat usage.
     d) The most recent user questions asked.
     e) Customer feedback satisfaction statistics (upvotes vs downvotes, category splits).
   - Formats raw query data structures (tuples) into standardized nested JSON responses.
   - Outputs the complete structured package, rounding numeric parameters cleanly.
"""

import asyncio
from fastapi import HTTPException  # Import web-server module to raise user-facing HTTP error responses
from db import analytics_repository  # Database access layer handling queries for analytics tables

# Logging modules
from utils.logger import get_department_logger

# Set up a department logger labeled "system" to track analytics metrics auditing
logger = get_department_logger("system")


async def handle_get_analytics(user_id: str):
    """
    Fetches, compiles, and formats all analytics data metrics for a user's dashboard.
    Gathers general usage counts, history chart series, recent questions, and feedback.

    Parameters:
        user_id (str): The unique database UUID identifying the target user.

    Returns:
        dict: A nested dictionary structure containing:
            - "metrics": Summary counts (total agents, documents, storage, widget messages).
            - "internalSeries": Daily message chart metrics for internal app workspace.
            - "widgetSeries": Daily message chart metrics for external embedded widget.
            - "topChatbots": Listing of chatbots sorted by utilization.
            - "recentQuestions": Feed of recent queries entered by clients.
            - "creditStats": Wallet credit balance, breakdown, and historical charts.

    Exceptions Raised:
        HTTPException(500): Raised if any SQL query fails or connection breakdown occurs.
    """
    # Log information indicating retrieval is initiated for this user
    logger.info(f"Fetching analytics data for user ID: {user_id}")
    try:
        # Trigger all database query tasks concurrently using asyncio.gather
        logger.debug("Executing parallel database fetches for analytics components...")
        
        metrics_task = analytics_repository.get_analytics_metrics(user_id)
        series_task = analytics_repository.get_analytics_series(user_id)
        chatbots_task = analytics_repository.get_analytics_top_chatbots(user_id)
        questions_task = analytics_repository.get_analytics_recent_questions(user_id)
        credit_task = analytics_repository.get_credit_analytics(user_id)

        (
            (total_agents, total_docs, total_storage_mb, total_widget_msgs),
            (internal_rows, widget_rows),
            bot_rows,
            q_rows,
            (credit_balance, credit_by_model, credit_series)
        ) = await asyncio.gather(
            metrics_task,
            series_task,
            chatbots_task,
            questions_task,
            credit_task
        )
        
        logger.debug(f"Metrics retrieved: agents={total_agents}, docs={total_docs}, storage={total_storage_mb}MB, widget_msgs={total_widget_msgs}")
        
        # Convert date objects to strings so they are safely JSON-serializable for the API
        internal_series = [{"date": str(r[0]), "messages": r[1]} for r in internal_rows]
        widget_series = [{"date": str(r[0]), "messages": r[1]} for r in widget_rows]

        # Map rows and ensure a fallback name exists if the chatbot is unnamed
        top_chatbots = [{"name": r[0] or "Unnamed Chatbot", "messages": r[1]} for r in bot_rows]

        # Convert datetime parameters to string formatting and decrypt encrypted question content
        from utils.data_vault import secure_unpack
        recent_questions = [{"content": secure_unpack(r[0]), "created_at": str(r[1]), "agent_name": r[2]} for r in q_rows]

        # Log dashboard collection success
        logger.info(f"Successfully processed analytics dashboard compilation for user {user_id}")
        
        # Return structured compiled analytics package
        return {
            "metrics": {
                "totalAgents": total_agents,
                "totalDocuments": total_docs,
                "storageUsedMB": round(total_storage_mb, 2), # Round decimal points to 2 digits
                "totalWidgetMessages": total_widget_msgs,
                "creditBalance": credit_balance,
            },
            "internalSeries": internal_series,
            "widgetSeries": widget_series,
            "topChatbots": top_chatbots,
            "recentQuestions": recent_questions,
            "creditStats": {
                "balance": credit_balance,
                "byModel": credit_by_model,
                "series": credit_series
            }
        }
    except Exception as e:
        # If any queries crash, log the traceback and throw an HTTP 500 error
        logger.error(f"Failed to fetch analytics for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

