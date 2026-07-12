from .base_prompts import BASE_SYSTEM_PROMPT
from .sql_prompts import SQL_SYSTEM_PROMPT
from .coding_prompts import CODING_SYSTEM_PROMPT
from .api_prompts import API_SYSTEM_PROMPT
from .native_prompts import NATIVE_SYSTEM_PROMPT

def get_system_prompt(agent: dict) -> str:
    """
    Dynamically construct the system prompt based on the agent's configured integrations.
    """
    prompt = BASE_SYSTEM_PROMPT + "\\n\\n"
    
    # If the agent has a custom persona defined by the user, we prepend/append it.
    if agent.get("system_prompt"):
        prompt += f"USER DEFINED PERSONA:\\n{agent['system_prompt']}\\n\\n"

    prompt += "### TOOL INSTRUCTIONS ###\\n"
    
    # We check what tools the agent has to append specific instructions
    db_connections = agent.get("db_connections", [])
    if db_connections:
        prompt += SQL_SYSTEM_PROMPT + "\\n"
        
    api_endpoints = agent.get("api_endpoints", [])
    if api_endpoints:
        prompt += API_SYSTEM_PROMPT + "\\n"
        
    native_integrations = agent.get("native_integrations", [])
    if native_integrations:
        prompt += NATIVE_SYSTEM_PROMPT + "\\n"
        
    # Example for code interpreter check (assuming it's a setting in the agent)
    # if agent.get("enable_code_interpreter"):
    #     prompt += CODING_SYSTEM_PROMPT + "\\n"
        
    return prompt
