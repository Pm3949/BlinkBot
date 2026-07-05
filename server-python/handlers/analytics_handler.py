import logging
from fastapi import HTTPException
from database import get_db_connection

logger = logging.getLogger(__name__)

async def handle_get_analytics(user_id: str):
    """
    What it does: Generates a comprehensive analytics report for the user.
    Args:
        user_id (str): The user ID.
    Returns: A dictionary with top level metrics, internal chat series, widget series, top chatbots, and recent questions.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM agents WHERE user_id = %s", (user_id,))
        total_agents = cursor.fetchone()[0] or 0

        cursor.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(file_size_bytes), 0) 
            FROM documents d JOIN agents a ON d.agent_id = a.id WHERE a.user_id = %s
            """,
            (user_id,),
        )
        doc_stats = cursor.fetchone()
        total_docs = doc_stats[0] or 0
        total_storage_mb = (doc_stats[1] or 0) / (1024 * 1024)

        cursor.execute(
            """
            SELECT COALESCE(SUM(message_count), 0) FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE a.user_id = %s
            """,
            (user_id,),
        )
        total_widget_msgs = cursor.fetchone()[0] or 0

        cursor.execute(
            """
            SELECT date_trunc('day', m.created_at)::date AS day, count(*) 
            FROM chat_messages m
            JOIN chat_sessions s ON m.session_id = s.id
            JOIN agents a ON s.agent_id = a.id
            WHERE a.user_id = %s AND m.role = 'user' 
            AND m.created_at >= current_date - interval '30 days'
            GROUP BY day ORDER BY day ASC
            """,
            (user_id,),
        )
        internal_series = [
            {"date": str(r[0]), "messages": r[1]} for r in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT date_trunc('day', l.created_at)::date AS day, count(*) 
            FROM widget_message_logs l
            JOIN chatbots c ON l.chatbot_id = c.id
            JOIN agents a ON c.agent_id = a.id
            WHERE a.user_id = %s 
            AND l.created_at >= current_date - interval '30 days'
            GROUP BY day ORDER BY day ASC
            """,
            (user_id,),
        )
        widget_series = [
            {"date": str(r[0]), "messages": r[1]} for r in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT c.settings->>'name' as name, c.message_count 
            FROM chatbots c JOIN agents a ON c.agent_id = a.id 
            WHERE a.user_id = %s 
            ORDER BY c.message_count DESC LIMIT 5
            """,
            (user_id,),
        )
        top_chatbots = [
            {"name": r[0] or "Unnamed Chatbot", "messages": r[1]}
            for r in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT m.content, m.created_at, a.name as agent_name 
            FROM chat_messages m
            JOIN chat_sessions s ON m.session_id = s.id
            JOIN agents a ON s.agent_id = a.id
            WHERE a.user_id = %s AND m.role = 'user' 
            ORDER BY m.created_at DESC LIMIT 10
            """,
            (user_id,),
        )
        recent_questions = [
            {"content": r[0], "created_at": str(r[1]), "agent_name": r[2]}
            for r in cursor.fetchall()
        ]

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
        }
    except Exception as e:
        logger.exception("Failed to fetch analytics")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
