import operator
import os
import asyncio
import json
from typing import TypedDict, Annotated, Sequence, Optional, List, Callable, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.language_models.chat_models import BaseChatModel

class GraphState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    active_agent_id: Optional[str]
    routed_agent_name: Optional[str]

def build_multi_agent_graph(
    master_agent_id: str,
    gateway_name: str,
    sub_agents: List[tuple],
    router_llm: BaseChatModel,
    llm_factory: Callable[[str, str], BaseChatModel], # get_llm(active_agent_id, memory_patch) -> (llm, system_prompt, embed_model, web_search_enabled)
    tools_factory: Callable[[str, str], List[Callable]], # get_tools(active_agent_id, embed_model, web_search_enabled) -> [tools]
):
    """
    Builds a LangGraph state machine representing a Supervisor Agent that routes to specialized Sub-Agents.
    """
    workflow = StateGraph(GraphState)
    
    # 1. Supervisor Node
    async def supervisor_node(state: GraphState):
        if not sub_agents or len(sub_agents) <= 1:
            return {"active_agent_id": master_agent_id, "routed_agent_name": gateway_name}
            
        agent_descriptions_list = []
        for sa in sub_agents:
            is_master = str(sa[0]) == str(master_agent_id)
            role_tag = (
                " [MASTER/GLOBAL - Default fallback for general knowledge & uploaded files]"
                if is_master
                else ""
            )
            agent_descriptions_list.append(
                f"ID: {sa[0]} | Name: {sa[1]}{role_tag} | Description: {sa[2]}"
            )
        agent_descriptions = "\n".join(agent_descriptions_list)
        
        from prompts.routing_prompts import ROUTING_SYSTEM_PROMPT
        routing_prompt = ROUTING_SYSTEM_PROMPT.format(
            agent_descriptions=agent_descriptions,
            message=state['messages'][-1].content
        )
        
        import re
        
        try:
            router_llm_json = router_llm.bind(response_format={"type": "json_object"})
            routing_response = await router_llm_json.ainvoke(routing_prompt)
            content = routing_response.content.strip()
            
            # Clean markdown if any
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            try:
                parsed = json.loads(content)
                chosen_uuid = parsed.get("agent_id", "").strip().lower()
            except json.JSONDecodeError:
                # Fallback to regex
                uuid_match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', content, re.IGNORECASE)
                chosen_uuid = uuid_match.group(0).lower() if uuid_match else content
            
            
            chosen_agent = next((sa for sa in sub_agents if str(sa[0]) == chosen_uuid), None)
            
            if chosen_agent and str(chosen_agent[0]) != str(master_agent_id):
                return {"active_agent_id": chosen_agent[0], "routed_agent_name": chosen_agent[1]}
        except Exception as e:
            print(f"Routing failed: {e}")
            
        return {"active_agent_id": master_agent_id, "routed_agent_name": gateway_name}

    # 2. Agent Execution Node
    async def agent_node(state: GraphState):
        active_agent_id = state.get("active_agent_id") or master_agent_id
        
        # Dynamically fetch LLM and tools for the chosen active agent
        llm, sys_prompt, embed_model, web_search_enabled = await llm_factory(active_agent_id)
        tools = tools_factory(active_agent_id, embed_model, web_search_enabled, llm)
        
        if tools:
            llm_with_tools = llm.bind_tools(tools)
        else:
            llm_with_tools = llm
            
        # We need to construct the prompt with history and system prompt
        # Actually, standard LangGraph passes state["messages"] directly to the LLM.
        # So we just inject the system prompt at the beginning of the messages if it's not there.
        msgs = list(state["messages"])
        if not any(isinstance(m, SystemMessage) for m in msgs):
            msgs.insert(0, SystemMessage(content=sys_prompt))
            
        try:
            response = await llm_with_tools.ainvoke(msgs)
            print("AGENT RESPONSE:", response)
        except Exception as e:
            if "Failed to call a function" in str(e) or "tool" in str(e).lower() or "400" in str(e):
                print(f"Groq API Error caught: {e}. Falling back to standard LLM without tools.")
                response = await llm.ainvoke(msgs)
            else:
                raise e
                
        return {"messages": [response]}

    # 3. Tool Execution Node
    async def tool_node(state: GraphState):
        # We use a custom tool node to dynamically fetch the correct tools for the active agent
        active_agent_id = state.get("active_agent_id") or master_agent_id
        llm, _, embed_model, web_search_enabled = await llm_factory(active_agent_id)
        tools = tools_factory(active_agent_id, embed_model, web_search_enabled, llm)
        
        tool_executor = ToolNode(tools)
        return await tool_executor.ainvoke(state)
        
    def should_continue(state: GraphState):
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
    workflow.set_entry_point("supervisor")
    workflow.add_edge("supervisor", "agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()
