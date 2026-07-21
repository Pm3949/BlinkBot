import logging
from fastapi import HTTPException
from db import analytics_repository

logger = logging.getLogger(__name__)

async def handle_get_analytics(user_id: str):
    try:
        total_agents, total_docs, total_storage_mb, total_widget_msgs = await analytics_repository.get_analytics_metrics(user_id)
        internal_rows, widget_rows = await analytics_repository.get_analytics_series(user_id)
        
        internal_series = [{"date": str(r[0]), "messages": r[1]} for r in internal_rows]
        widget_series = [{"date": str(r[0]), "messages": r[1]} for r in widget_rows]

        bot_rows = await analytics_repository.get_analytics_top_chatbots(user_id)
        top_chatbots = [{"name": r[0] or "Unnamed Chatbot", "messages": r[1]} for r in bot_rows]

        q_rows = await analytics_repository.get_analytics_recent_questions(user_id)
        recent_questions = [{"content": r[0], "created_at": str(r[1]), "agent_name": r[2]} for r in q_rows]

        up_votes, down_votes, category_distribution = await analytics_repository.get_feedback_stats(user_id)

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
        logger.exception("Failed to fetch analytics")
        raise HTTPException(status_code=500, detail=str(e))
