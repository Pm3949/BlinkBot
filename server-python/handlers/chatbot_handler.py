import logging
from fastapi import HTTPException
from database import get_db_connection

logger = logging.getLogger(__name__)

async def handle_get_chatbots(workspace_id: str):
    """
    What it does: Fetches all public widgets deployed in a workspace.
    Args:
        workspace_id (str): The workspace ID.
    Returns: A list of chatbots.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT c.id, c.agent_id, c.name, c.settings, c.message_count, c.api_key, c.allowed_domains, c.created_at,
                   a.workspace_id, a.name as agent_name
            FROM chatbots c
            INNER JOIN agents a ON c.agent_id = a.id
            WHERE a.workspace_id = %s
            ORDER BY c.created_at DESC
            """,
            (workspace_id,)
        )
        rows = cursor.fetchall()
        
        chatbots = []
        for row in rows:
            chatbots.append({
                "id": row[0],
                "agent_id": row[1],
                "name": row[2],
                "settings": row[3],
                "message_count": row[4],
                "api_key": row[5],
                "allowed_domains": row[6],
                "created_at": row[7].isoformat() if row[7] else None,
                "agents": {
                    "workspace_id": row[8],
                    "name": row[9]
                }
            })
            
        return chatbots
    except Exception as e:
        logger.error(f"Error fetching chatbots: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chatbots")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_get_chatbot_by_id(chatbot_id: str):
    """
    What it does: Fetches the configuration for a single widget.
    Args:
        chatbot_id (str): The chatbot ID.
    Returns: The chatbot details.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT c.id, c.agent_id, c.name, c.settings, c.message_count, c.api_key, c.allowed_domains, c.created_at,
                   a.workspace_id, a.name as agent_name
            FROM chatbots c
            INNER JOIN agents a ON c.agent_id = a.id
            WHERE c.id = %s
            """,
            (chatbot_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Chatbot not found")
            
        return {
            "id": row[0],
            "agent_id": row[1],
            "name": row[2],
            "settings": row[3],
            "message_count": row[4],
            "api_key": row[5],
            "allowed_domains": row[6],
            "created_at": row[7].isoformat() if row[7] else None,
            "agents": {
                "workspace_id": row[8],
                "name": row[9]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chatbot: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chatbot")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_create_chatbot(payload: dict):
    """
    What it does: Creates a new public endpoint/widget for an existing Agent.
    Args:
        payload (dict): The chatbot payload.
    Returns: The created chatbot details.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        import json
        settings_json = json.dumps(payload.get("settings", {}))
        
        cursor.execute(
            """
            INSERT INTO chatbots (agent_id, name, settings)
            VALUES (%s, %s, %s::jsonb)
            RETURNING id, agent_id, name, settings, message_count, api_key, allowed_domains, created_at
            """,
            (payload.get("agent_id"), payload.get("name"), settings_json)
        )
        row = cursor.fetchone()
        conn.commit()
        
        return {
            "id": row[0],
            "agent_id": row[1],
            "name": row[2],
            "settings": row[3],
            "message_count": row[4],
            "api_key": row[5],
            "allowed_domains": row[6],
            "created_at": row[7].isoformat() if row[7] else None
        }
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error creating chatbot: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chatbot")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_update_chatbot(chatbot_id: str, payload: dict):
    """
    What it does: Updates widget settings dynamically.
    Args:
        chatbot_id (str): The chatbot ID.
        payload (dict): The fields to update.
    Returns: The updated chatbot details.
    """
    conn = None
    cursor = None
    try:
        if not payload:
            return {}

        conn = get_db_connection()
        cursor = conn.cursor()
        
        import json
        set_clauses = []
        values = []
        
        for key, value in payload.items():
            if value is None:
                continue
            if key in ["name", "api_key", "allowed_domains"]:
                set_clauses.append(f"{key} = %s")
                values.append(value)
            elif key == "settings":
                set_clauses.append("settings = %s::jsonb")
                values.append(json.dumps(value))
                
        if not set_clauses:
            raise HTTPException(status_code=400, detail="No valid fields to update")
            
        values.append(chatbot_id)
        
        query = f"UPDATE chatbots SET {', '.join(set_clauses)} WHERE id = %s RETURNING id, agent_id, name, settings, message_count, api_key, allowed_domains, created_at;"
        
        cursor.execute(query, tuple(values))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Chatbot not found")
            
        conn.commit()
        
        return {
            "id": row[0],
            "agent_id": row[1],
            "name": row[2],
            "settings": row[3],
            "message_count": row[4],
            "api_key": row[5],
            "allowed_domains": row[6],
            "created_at": row[7].isoformat() if row[7] else None
        }
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error updating chatbot: {e}")
        raise HTTPException(status_code=500, detail="Failed to update chatbot")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
