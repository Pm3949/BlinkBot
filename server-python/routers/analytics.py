"""
Analytics Router.
Responsibility: Gathers telemetry and usage statistics for a specific user to display
on their frontend Dashboard. Queries span across agents, documents, and chat histories 
to provide a bird's-eye view of their resource consumption.
"""
import logging
from fastapi import APIRouter, HTTPException
from database import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analytics"])

@router.get("/analytics/{user_id}")
async def get_analytics(user_id: str):
    """
    Generates a comprehensive analytics report for the user.
    Broken down into:
    1. Top Level Metrics (Totals)
    2. Internal Chat Time Series (For charts)
    3. External Widget Time Series (For charts)
    4. Top Performing Chatbots
    5. Recent raw questions from users
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # ==========================================
        # 1. TOP LEVEL METRICS
        # ==========================================
        
        # Total Agents
        cursor.execute("SELECT COUNT(*) FROM agents WHERE user_id = %s", (user_id,))
        total_agents = cursor.fetchone()[0] or 0

        # Total Documents & Storage
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

        # Total API/Widget Messages (External usage)
        cursor.execute(
            """
            SELECT COALESCE(SUM(message_count), 0) FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE a.user_id = %s
        """,
            (user_id,),
        )
        total_widget_msgs = cursor.fetchone()[0] or 0

        # ==========================================
        # 2. TIME SERIES: INTERNAL DASHBOARD CHATS
        # ==========================================
        # Groups messages by day over the last 30 days to render a line chart.
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

        # ==========================================
        # 3. TIME SERIES: PUBLIC WIDGET CHATS
        # ==========================================
        # Tracks how many times customers interacted with embedded widgets per day.
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

        # ==========================================
        # 4. TOP PERFORMING CHATBOTS
        # ==========================================
        # Finds which widget deployments are getting the most traffic.
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

        # ==========================================
        # 5. RECENT RAW QUESTIONS
        # ==========================================
        # Gives the user a live feed of exactly what their customers are asking.
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
