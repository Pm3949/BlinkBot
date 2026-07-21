import logging
from fastapi import HTTPException
from db import chatbot_repository

logger = logging.getLogger(__name__)

async def handle_get_chatbots(workspace_id: str):
    try:
        rows = await chatbot_repository.get_chatbots(workspace_id)
        
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


async def handle_get_chatbot_by_id(chatbot_id: str):
    try:
        row = await chatbot_repository.get_chatbot_by_id(chatbot_id)
        
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


async def handle_create_chatbot(payload: dict):
    try:
        row = await chatbot_repository.create_chatbot(
            payload.get("agent_id"),
            payload.get("name"),
            payload.get("settings", {})
        )
        
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
        logger.error(f"Error creating chatbot: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chatbot")


async def handle_update_chatbot(chatbot_id: str, payload: dict):
    try:
        if not payload:
            return {}
            
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
        
        row = await chatbot_repository.update_chatbot(chatbot_id, set_clauses, values)
        
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
            "created_at": row[7].isoformat() if row[7] else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chatbot: {e}")
        raise HTTPException(status_code=500, detail="Failed to update chatbot")
