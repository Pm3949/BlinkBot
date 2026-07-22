from fastapi import HTTPException
from db import analytics_repository

from utils.logger import get_department_logger

logger = get_department_logger("system")

async def handle_get_analytics(user_id: str):
    logger.info(f"Fetching analytics data for user ID: {user_id}")
    try:
        logger.debug("Retrieving analytics metrics counts...")
        total_agents, total_docs, total_storage_mb, total_widget_msgs = await analytics_repository.get_analytics_metrics(user_id)
        logger.debug(f"Metrics retrieved: agents={total_agents}, docs={total_docs}, storage={total_storage_mb}MB, widget_msgs={total_widget_msgs}")
        
        logger.debug("Retrieving message series charts data...")
        internal_rows, widget_rows = await analytics_repository.get_analytics_series(user_id)
        internal_series = [{"date": str(r[0]), "messages": r[1]} for r in internal_rows]
        widget_series = [{"date": str(r[0]), "messages": r[1]} for r in widget_rows]

        logger.debug("Retrieving top chatbots utilization metrics...")
        bot_rows = await analytics_repository.get_analytics_top_chatbots(user_id)
        top_chatbots = [{"name": r[0] or "Unnamed Chatbot", "messages": r[1]} for r in bot_rows]

        logger.debug("Retrieving recent logs/questions feed...")
        q_rows = await analytics_repository.get_analytics_recent_questions(user_id)
        recent_questions = [{"content": r[0], "created_at": str(r[1]), "agent_name": r[2]} for r in q_rows]

        logger.debug("Retrieving customer feedback satisfaction metrics...")
        up_votes, down_votes, category_distribution = await analytics_repository.get_feedback_stats(user_id)

        logger.info(f"Successfully processed analytics dashboard compilation for user {user_id}")
        return {
            "metrics": {
                "totalAgents": total_agents,
                "totalDocuments": total_docs,
                "storageUsedMB": round(total_storage_mb, 2),
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
        logger.error(f"Failed to fetch analytics for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
