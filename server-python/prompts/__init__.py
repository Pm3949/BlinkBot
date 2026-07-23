from .base_prompts import BASE_SYSTEM_PROMPT
from .sql_prompts import SQL_SYSTEM_PROMPT
from .coding_prompts import CODING_SYSTEM_PROMPT
from .api_prompts import API_SYSTEM_PROMPT
from .native_prompts import NATIVE_SYSTEM_PROMPT


def get_system_prompt(agent: dict) -> str:
    """
    Dynamically compose the system prompt for an agent based on its configured
    integrations and custom persona.

    The prompt is layered in this order:
      1. BASE_SYSTEM_PROMPT  — always present (universal grounding rules)
      2. USER PERSONA         — optional custom system prompt written by the agent owner
      3. TOOL INSTRUCTIONS    — one block per enabled tool category (SQL, API, Native, Code)
    """
    sections = [BASE_SYSTEM_PROMPT]

    # 2. User-defined persona / custom instructions
    if agent.get("system_prompt"):
        sections.append(
            "═══════════════════════════════════════════════════════════════\n"
            " YOUR PERSONA & CUSTOM INSTRUCTIONS (defined by the agent owner):\n"
            "═══════════════════════════════════════════════════════════════\n"
            + agent["system_prompt"]
        )

    # 3. Tool-specific rule blocks (only injected when the tool is actually configured)
    tool_sections = []

    if agent.get("db_connections"):
        tool_sections.append(SQL_SYSTEM_PROMPT)

    if agent.get("api_endpoints"):
        tool_sections.append(API_SYSTEM_PROMPT)

    if agent.get("native_integrations"):
        tool_sections.append(NATIVE_SYSTEM_PROMPT)

    if agent.get("enable_code_interpreter"):
        tool_sections.append(CODING_SYSTEM_PROMPT)

    if tool_sections:
        sections.extend(tool_sections)

    return "\n\n".join(sections)
