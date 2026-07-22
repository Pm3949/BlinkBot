from fastapi import HTTPException
from db import chatbot_repository

from utils.logger import get_department_logger

logger = get_department_logger("agent")

async def handle_get_chatbots(workspace_id: str):
    logger.info(f"Retrieving chatbots list for workspace ID: {workspace_id}")
    try:
        logger.debug("Executing chatbot fetch query in database...")
        rows = await chatbot_repository.get_chatbots(workspace_id)
        logger.debug(f"Retrieved {len(rows)} chatbot records.")
        
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
            
        logger.info(f"Successfully processed {len(chatbots)} chatbots.")
        return chatbots
    except Exception as e:
        logger.error(f"Error fetching chatbots for workspace {workspace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch chatbots")


async def handle_get_chatbot_by_id(chatbot_id: str):
    logger.info(f"Fetching chatbot metadata by ID: {chatbot_id}")
    try:
        logger.debug("Executing chatbot search query by ID...")
        row = await chatbot_repository.get_chatbot_by_id(chatbot_id)
        
        if not row:
            logger.warning(f"Chatbot ID {chatbot_id} not found in database.")
            raise HTTPException(status_code=404, detail="Chatbot not found")
            
        logger.info(f"Chatbot ID {chatbot_id} details successfully retrieved.")
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
        logger.error(f"Error fetching chatbot ID {chatbot_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch chatbot")


async def handle_create_chatbot(payload: dict):
    # Mask API key if present in payload
    sanitized_payload = payload.copy()
    if "api_key" in sanitized_payload:
        sanitized_payload["api_key"] = "[MASKED]"
    logger.info(f"Creating a new chatbot with configuration: {sanitized_payload}")
    
    try:
        logger.debug("Executing chatbot database creation query...")
        row = await chatbot_repository.create_chatbot(
            payload.get("agent_id"),
            payload.get("name"),
            payload.get("settings", {})
        )
        
        logger.info(f"Chatbot successfully created. ID: {row[0]}")
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
        logger.error(f"Error creating chatbot: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create chatbot")


async def handle_update_chatbot(chatbot_id: str, payload: dict):
    sanitized_payload = payload.copy()
    if "api_key" in sanitized_payload:
        sanitized_payload["api_key"] = "[MASKED]"
    logger.info(f"Updating chatbot ID: {chatbot_id} with configuration parameters: {sanitized_payload}")
    
    try:
        if not payload:
            logger.warning("Empty payload received for chatbot update. Aborting early.")
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
            logger.warning("No valid attributes to update in payload keys.")
            raise HTTPException(status_code=400, detail="No valid fields to update")
            
        values.append(chatbot_id)
        
        logger.debug(f"Executing chatbot database update query for ID: {chatbot_id}")
        row = await chatbot_repository.update_chatbot(chatbot_id, set_clauses, values)
        
        if not row:
            logger.error(f"Update failed: Chatbot ID {chatbot_id} not found in database.")
            raise HTTPException(status_code=404, detail="Chatbot not found")
            
        logger.info(f"Chatbot ID {chatbot_id} successfully updated.")
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
        logger.error(f"Error updating chatbot ID {chatbot_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update chatbot")
