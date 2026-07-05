from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class RequiredKnowledge(BaseModel):
    id: str = Field(..., description="Unique identifier (e.g., 'product_catalog')")
    type: str = Field(..., description="Expected type (e.g., 'pdf_document', 'csv_database', 'website_url')")
    name: str = Field(..., description="Human-readable name (e.g., 'Product Catalog')")
    description: str = Field(..., description="Instructions for the client on what to upload")
    is_mandatory: bool = Field(default=True)

class ToolParameter(BaseModel):
    name: str = Field(..., description="Name of the parameter (e.g., 'api_key', 'base_url')")
    type: str = Field(..., description="Type of the parameter (e.g., 'string', 'password')")
    description: str = Field(..., description="Description for the client")
    is_required: bool = Field(default=True)

class RequiredTool(BaseModel):
    id: str = Field(..., description="Unique identifier (e.g., 'order_tracking_api')")
    type: str = Field(..., description="Type of tool (e.g., 'rest_api', 'shopify_integration', 'web_search')")
    name: str = Field(..., description="Name of the tool")
    description: str = Field(..., description="Explanation of what this tool does and what the client needs to provide (e.g., API Key, Base URL)")
    # The frontend will use this to generate the input form for the API tool
    parameters: List[ToolParameter] = Field(default_factory=list, description="List of parameters the client must provide")
    is_mandatory: bool = Field(default=True)

class SubAgentConfig(BaseModel):
    id: str = Field(..., description="Unique identifier (e.g., 'support_agent')")
    role: str = Field(..., description="Role of the agent (e.g., 'Customer Support Specialist')")
    goal: str = Field(..., description="Primary goal of the agent")
    backstory: str = Field(..., description="Agent backstory defining its persona and expertise")
    assigned_tools: List[str] = Field(..., description="List of RequiredTool IDs this agent can use")
    assigned_knowledge: List[str] = Field(..., description="List of RequiredKnowledge IDs this agent can query")
    parent_agent_id: Optional[str] = Field(None, description="If this agent reports to another sub-agent (like a Manager), put that agent's ID here. If it reports directly to the Master Coordinator, leave it null.")
    output_format_instructions: Optional[str] = Field(None, description="Strict Markdown formatting rules for this agent (e.g. output product images ![alt](url) and links [text](url)).")

class AgentBlueprint(BaseModel):
    project_name: str = Field(..., description="A catchy, relevant name for the generated project")
    description: str = Field(..., description="Brief summary of how the agent network will function")
    network_architecture: str = Field(..., description="Type: 'single_agent', 'sequential_crew', 'hierarchical_crew', 'state_machine'")
    required_knowledge: List[RequiredKnowledge] = Field(..., description="Knowledge bases the client must provide")
    required_tools: List[RequiredTool] = Field(..., description="Tools/Integrations the client must configure")
    sub_agents: List[SubAgentConfig] = Field(..., description="The specialized agents that form this network")

class DeployRequest(BaseModel):
    blueprint: AgentBlueprint
    config_data: Dict[str, Any]
    workspace_id: str

class SingleAgentResponse(BaseModel):
    name: str = Field(..., description="A catchy, relevant name for the agent")
    description: str = Field(..., description="Brief summary of what the agent does")
    system_prompt: str = Field(..., description="Detailed system prompt defining the agent's persona, rules, and core instructions")
    output_format_instructions: str = Field(..., description="Strict Markdown or JSON formatting instructions for how the agent should structure its output")
