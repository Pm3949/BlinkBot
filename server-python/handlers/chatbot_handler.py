"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the backend business logic handler for managing 
Web Widget Chatbots in RAGMate.

From top to bottom, the file performs the following tasks:
1. Imports: Loads FastAPI exception handlers and the database repository methods
   for chatbot configurations.
2. Logging: Initializes a department logger named "agent" to track chatbot configuration edits.
3. Chatbots Listing Handlers:
   - `handle_get_chatbots`: Fetches all widget chatbots active in a workspace,
     formatting nested agent workspace parameters and converting timestamps.
   - `handle_get_chatbot_by_id`: Fetches configuration metadata for a single chatbot client by ID.
4. Creation Handler:
   - `handle_create_chatbot`: Creates a new chatbot entry in the DB, masking API tokens in output logs.
5. Update Handler:
   - `handle_update_chatbot`: Generates dynamic SQL `SET` queries dynamically based on 
     the properties updated in the payload (converting settings dictionaries into postgres JSONB).
"""

from fastapi import HTTPException  # Import web exceptions to raise clean HTTP error status codes
from db import chatbot_repository  # Database access layer handling chatbot table interactions

# Logging modules
from utils.logger import get_department_logger

# Scope a department logger specifically to "agent" context for logging actions
logger = get_department_logger("agent")


async def handle_get_chatbots(workspace_id: str):
    """
    Retrieves the list of all registered widget chatbots inside a given workspace.
    Processes the raw database rows and formats them into clean structured dictionaries.

    Parameters:
        workspace_id (str): The unique database UUID identifying the target workspace.

    Returns:
        list: A list of dictionaries representing chatbot configurations.

    Exceptions Raised:
        HTTPException(500): Raised if any SQL query crashes.
    """
    # Log information indicating retrieval is initiated
    logger.info(f"Retrieving chatbots list for workspace ID: {workspace_id}")
    try:
        # Fetch raw rows from the database repository
        logger.debug("Executing chatbot fetch query in database...")
        rows = await chatbot_repository.get_chatbots(workspace_id)
        logger.debug(f"Retrieved {len(rows)} chatbot records.")
        
        # Loop through rows and construct clean dictionaries
        chatbots = []
        for row in rows:
            chatbots.append({
                "id": row[0],                                                # Chatbot client UUID
                "agent_id": row[1],                                          # Linked AI Agent UUID
                "name": row[2],                                              # Chatbot Display Name
                "settings": row[3],                                          # Settings configuration dictionary (themes, position, avatar)
                "message_count": row[4],                                    # Total messages processed by this widget
                "api_key": row[5],                                           # Public developer connection API key
                "allowed_domains": row[6],                                   # CORS domains allowed to embed this widget (comma-separated)
                "created_at": row[7].isoformat() if row[7] else None,        # Registration timestamp format string
                "agents": {                                                  # Nested dictionary mapping the underlying agent details
                    "workspace_id": row[8],
                    "name": row[9]
                }
            })
            
        # Log successful mapping
        logger.info(f"Successfully processed {len(chatbots)} chatbots.")
        return chatbots
    except Exception as e:
        # Catch errors, print traceback, and raise 500 status response to the client
        logger.error(f"Error fetching chatbots for workspace {workspace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch chatbots")


async def handle_get_chatbot_by_id(chatbot_id: str):
    """
    Fetches the configuration metadata parameters for a specific chatbot client by its ID.

    Parameters:
        chatbot_id (str): The unique database UUID of the target chatbot.

    Returns:
        dict: The structured configuration details for the chatbot.

    Exceptions Raised:
        HTTPException(404): Raised if the chatbot ID is not found.
        HTTPException(500): Raised if database queries fail.
    """
    # Log search request
    logger.info(f"Fetching chatbot metadata by ID: {chatbot_id}")
    try:
        # Query database row matching chatbot_id
        logger.debug("Executing chatbot search query by ID...")
        row = await chatbot_repository.get_chatbot_by_id(chatbot_id)
        
        # Raise 404 error if no record matches in the database
        if not row:
            logger.warning(f"Chatbot ID {chatbot_id} not found in database.")
            raise HTTPException(status_code=404, detail="Chatbot not found")
            
        # Log retrieval success
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
    """
    Registers a new web chatbot client configurations in the database.

    Parameters:
        payload (dict): Payload dictionary containing:
            - 'agent_id' (str): Underlying AI Agent UUID.
            - 'name' (str): Custom label/title for the chatbot client.
            - 'settings' (dict, optional): Custom styling configs.

    Returns:
        dict: The newly registered chatbot data structure.

    Exceptions Raised:
        HTTPException(500): Raised if SQL database insert crashes.
    """
    # Sanitize payload parameter for secure logging prints
    sanitized_payload = payload.copy()
    if "api_key" in sanitized_payload:
        sanitized_payload["api_key"] = "[MASKED]"
    logger.info(f"Creating a new chatbot with configuration: {sanitized_payload}")
    
    try:
        # Call database repository method to write a chatbot row
        logger.debug("Executing chatbot database creation query...")
        row = await chatbot_repository.create_chatbot(
            payload.get("agent_id"),
            payload.get("name"),
            payload.get("settings", {})
        )
        
        # Log success and return
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
    """
    Updates configuration parameters dynamically for an existing chatbot.
    Compiles dynamically formulated SQL clauses depending on properties sent in the payload.

    Parameters:
        chatbot_id (str): The unique database UUID identifying the target chatbot.
        payload (dict): A dictionary of fields and values to update.

    Returns:
        dict: The updated chatbot details.

    Exceptions Raised:
        HTTPException(400): Raised if no valid update fields are supplied.
        HTTPException(404): Raised if the chatbot ID is not found.
        HTTPException(500): Raised if dynamic updates fail.
    """
    # Sanitize variables for logging
    sanitized_payload = payload.copy()
    if "api_key" in sanitized_payload:
        sanitized_payload["api_key"] = "[MASKED]"
    logger.info(f"Updating chatbot ID: {chatbot_id} with configuration parameters: {sanitized_payload}")
    
    try:
        # Abort if the payload is empty
        if not payload:
            logger.warning("Empty payload received for chatbot update. Aborting early.")
            return {}
            
        import json
        set_clauses = []
        values = []
        
        # Build SQL update query dynamically based on fields provided in payload
        for key, value in payload.items():
            if value is None:
                continue
            if key in ["name", "api_key", "allowed_domains"]:
                # Append basic placeholders
                set_clauses.append(f"{key} = %s")
                values.append(value)
            elif key == "settings":
                # Convert settings dictionary into postgres JSONB format
                set_clauses.append("settings = %s::jsonb")
                values.append(json.dumps(value))
                
        # If no matching properties were registered for updates
        if not set_clauses:
            logger.warning("No valid attributes to update in payload keys.")
            raise HTTPException(status_code=400, detail="No valid fields to update")
            
        # Append target ID to values array for WHERE clause
        values.append(chatbot_id)
        
        # Execute query statement in database repository
        logger.debug(f"Executing chatbot database update query for ID: {chatbot_id}")
        row = await chatbot_repository.update_chatbot(chatbot_id, set_clauses, values)
        
        # Raise 404 if no record was found matching chatbot_id
        if not row:
            logger.error(f"Update failed: Chatbot ID {chatbot_id} not found in database.")
            raise HTTPException(status_code=404, detail="Chatbot not found")
            
        # Log success and return updated row details
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
