"""
================================================================================
META-AGENT GENERATOR BLUEPRINT SCHEMAS LAYER (meta_agent_schemas.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module defines the validation structures utilized by the generative Meta-Agent engine. 
During agent configuration creation, the LLM analyzes a natural language prompt and generates 
a highly structured JSON response matching these schemas.

KEY COMPONENT SCHEMAS:
1. Agent Blueprint Structure (`AgentBlueprint`):
   Defines the overall architecture ('single_agent', 'state_machine', etc.), project metadata, 
   required external tools, and the sub-agent network configurations.
2. Sub-Agent Configuration (`SubAgentConfig`):
   Defines individual specialized agents, outlining their roles, goals, backstories, assigned 
   tools/knowledge identifiers, hierarchy relationships (`parent_agent_id`), and output formatting.
3. Ingestion & Requirements (`RequiredKnowledge`, `RequiredTool`):
   Specifies what datasets or tools/parameters (like API keys) the client must configure to activate the blueprint.
4. Deployment Requests (`DeployRequest`):
   Validates the body payload when instantiating a generated blueprint inside a target workspace database.

BEGINNER COMPONENTS BREAKDOWN:
- Field(..., description="..."): Annotates Pydantic fields to provide descriptions for the JSON Schema.
  The ellipses (`...`) indicate that the field is mandatory.
- List[str]: Declares that the field must be a collection containing only strings.
- Optional[T]: Indicates that the field is optional and can default to `None`.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class RequiredKnowledge(BaseModel):
    """
    Data validation schema representing a knowledge base required by the blueprint.
    """
    id: str = Field(..., description="Unique identifier of the resource (e.g. 'product_catalog')")
    type: str = Field(..., description="Ingestion source type (e.g. 'pdf_document', 'website_url')")
    name: str = Field(..., description="Human-readable name of the dataset (e.g. 'Product Catalog')")
    description: str = Field(..., description="Instructions detailing what content the client must provide")
    is_mandatory: bool = Field(default=True) # Toggles if this knowledge block is mandatory for deployment


class ToolParameter(BaseModel):
    """
    Data validation schema representing input parameters required to configure a tool.
    """
    name: str = Field(..., description="Name of the parameter parameter key (e.g., 'api_key')")
    type: str = Field(..., description="Value type constraint (e.g., 'string', 'password')")
    description: str = Field(..., description="Help text explaining the parameter's purpose")
    is_required: bool = Field(default=True) # Toggles if the parameter is required for execution


class RequiredTool(BaseModel):
    """
    Data validation schema representing an external tool required by the blueprint.
    """
    id: str = Field(..., description="Unique identifier for the tool (e.g., 'order_tracking_api')")
    type: str = Field(..., description="Tool category (e.g., 'rest_api', 'web_search')")
    name: str = Field(..., description="Human-readable tool name")
    description: str = Field(..., description="Description detailing the tool's behavior and dependencies")
    # Generates a dynamic input form in the frontend based on the parameters list.
    parameters: List[ToolParameter] = Field(default_factory=list, description="List of parameters the client must provide")
    is_mandatory: bool = Field(default=True) # Toggles if this tool is mandatory for deployment


class SubAgentConfig(BaseModel):
    """
    Data validation schema representing an individual specialized sub-agent configuration.
    """
    id: str = Field(..., description="Unique identifier for the sub-agent (e.g., 'support_agent')")
    role: str = Field(..., description="Role title of the agent (e.g., 'Customer Support Specialist')")
    goal: str = Field(..., description="Core objective the agent aims to achieve")
    backstory: str = Field(..., description="Persona backstory detailing the agent's expertise and rules")
    assigned_tools: List[str] = Field(..., description="List of RequiredTool IDs this agent can use")
    assigned_knowledge: List[str] = Field(..., description="List of RequiredKnowledge IDs this agent can query")
    # Hierarchy connection: set to None if this is a master router or independent agent.
    parent_agent_id: Optional[str] = Field(None, description="ID of the parent manager agent, if hierarchical")
    output_format_instructions: Optional[str] = Field(None, description="Strict formatting rules for LLM outputs (e.g. Markdown image tags)")


class AgentBlueprint(BaseModel):
    """
    Data validation schema representing a complete multi-agent network blueprint.
    """
    project_name: str = Field(..., description="Catchy, relevant name for the generated project")
    description: str = Field(..., description="Summary of how the agent network functions")
    network_architecture: str = Field(..., description="Routing topology type (e.g. 'single_agent', 'state_machine')")
    required_knowledge: List[RequiredKnowledge] = Field(..., description="Knowledge bases required for deployment")
    required_tools: List[RequiredTool] = Field(..., description="Tools/Integrations required for deployment")
    sub_agents: List[SubAgentConfig] = Field(..., description="Specialized agents comprising the network")


class DeployRequest(BaseModel):
    """
    Data validation schema for requests to deploy a generated blueprint.
    """
    blueprint: AgentBlueprint # The agent blueprint configuration
    config_data: Dict[str, Any] # Parameter configurations (e.g. API keys, URLs) satisfying blueprint requirements
    workspace_id: str # UUID of the target workspace to deploy to


class SingleAgentResponse(BaseModel):
    """
    Data validation schema for single-agent blueprint completions.
    """
    name: str = Field(..., description="Name for the single assistant")
    description: str = Field(..., description="Brief summary of the assistant's behavior")
    system_prompt: str = Field(..., description="Persona, context instructions, and rules")
    output_format_instructions: str = Field(..., description="Formatting rules for the output")

