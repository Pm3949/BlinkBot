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
            - "feedbackStats": Satisfaction parameters (up/down votes and category distribution).

    Exceptions Raised:
        HTTPException(500): Raised if any SQL query fails or connection breakdown occurs.
    """
    # Log information indicating retrieval is initiated for this user
    logger.info(f"Fetching analytics data for user ID: {user_id}")
    try:
        # 1. Fetch raw total counters (agents count, documents count, storage size, widget volume)
        logger.debug("Retrieving analytics metrics counts...")
        total_agents, total_docs, total_storage_mb, total_widget_msgs = await analytics_repository.get_analytics_metrics(user_id)
        logger.debug(f"Metrics retrieved: agents={total_agents}, docs={total_docs}, storage={total_storage_mb}MB, widget_msgs={total_widget_msgs}")
        
        # 2. Fetch chart history lists (daily chat trends for app chat vs external widget chat)
        logger.debug("Retrieving message series charts data...")
        internal_rows, widget_rows = await analytics_repository.get_analytics_series(user_id)
        
        # Convert date objects to strings so they are safely JSON-serializable for the API
        internal_series = [{"date": str(r[0]), "messages": r[1]} for r in internal_rows]
        widget_series = [{"date": str(r[0]), "messages": r[1]} for r in widget_rows]

        # 3. Fetch chatbot utilization list (which widgets are utilized the most)
        logger.debug("Retrieving top chatbots utilization metrics...")
        bot_rows = await analytics_repository.get_analytics_top_chatbots(user_id)
        # Map rows and ensure a fallback name exists if the chatbot is unnamed
        top_chatbots = [{"name": r[0] or "Unnamed Chatbot", "messages": r[1]} for r in bot_rows]

        # 4. Fetch recent logs/questions feed (real-time stream of what users are asking)
        logger.debug("Retrieving recent logs/questions feed...")
        q_rows = await analytics_repository.get_analytics_recent_questions(user_id)
        # Convert datetime parameters to string formatting
        recent_questions = [{"content": r[0], "created_at": str(r[1]), "agent_name": r[2]} for r in q_rows]

        # 5. Fetch feedback statistics (useful to measure satisfaction levels and upvote/downvote ratio)
        logger.debug("Retrieving customer feedback satisfaction metrics...")
        up_votes, down_votes, category_distribution = await analytics_repository.get_feedback_stats(user_id)

        # Log dashboard collection success
        logger.info(f"Successfully processed analytics dashboard compilation for user {user_id}")
        
        # Return structured compiled analytics package
        return {
            "metrics": {
                "totalAgents": total_agents,
                "totalDocuments": total_docs,
                "storageUsedMB": round(total_storage_mb, 2), # Round decimal points to 2 digits
                "totalWidgetMessages": total_widget_msgs,
            },
            "internalSeries": internal_series,
            "widgetSeries": widget_series,
            "topChatbots": top_chatbots,
            "recentQuestions": recent_questions,
            "feedbackStats": {
                "upVotes": up_votes,
                "downVotes": down_votes,
                "categoryDistribution": category_distribution,
            }
        }
    except Exception as e:
        # If any queries crash, log the traceback and throw an HTTP 500 error
        logger.error(f"Failed to fetch analytics for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
