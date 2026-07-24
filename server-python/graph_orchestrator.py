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
    next_agent: Optional[str]

def build_multi_agent_graph(
    master_agent_id: str,
    gateway_name: str,
    sub_agents: List[tuple],
    router_llm: BaseChatModel,
    llm_factory: Callable[[str], BaseChatModel], # get_llm(active_agent_id) -> (llm, system_prompt, embed_model, web_search_enabled)
    tools_factory: Callable[[str, str, bool, BaseChatModel], List[Callable]], # get_tools(active_agent_id, embed_model, web_search_enabled, llm) -> [tools]
):
    """
    Builds a LangGraph state machine representing a Supervisor Agent that routes to specialized Sub-Agents.
    """
    workflow = StateGraph(GraphState)
    
    # 1. Supervisor Node
    async def supervisor_node(state: GraphState):
        # Enforce loop termination: if the last message in state history is an AIMessage,
        # it means a specialist agent has generated a response. We must yield control to the user.
        if state["messages"]:
            last_msg = state["messages"][-1]
            if getattr(last_msg, "type", None) == "ai" or isinstance(last_msg, AIMessage):
                return {
                    "active_agent_id": master_agent_id,
                    "routed_agent_name": gateway_name,
                    "next_agent": "FINISH"
                }
                
        if not sub_agents or len(sub_agents) <= 1:
            return {
                "active_agent_id": master_agent_id, 
                "routed_agent_name": gateway_name,
                "next_agent": master_agent_id
            }
            
        agent_descriptions_list = []
        for sa in sub_agents:
            is_master = str(sa[0]) == str(master_agent_id)
            role_tag = (
                " [MASTER/GLOBAL - Greeting and default fallback agent]"
                if is_master
                else ""
            )
            agent_descriptions_list.append(
                f"ID: {sa[0]} | Name: {sa[1]}{role_tag} | Description: {sa[2]}"
            )
        agent_descriptions = "\n".join(agent_descriptions_list)
        
        from prompts.routing_prompts import SUPERVISOR_LOOP_PROMPT
        supervisor_prompt = SUPERVISOR_LOOP_PROMPT.format(agent_descriptions=agent_descriptions)
        
        try:
            router_llm_json = router_llm.bind(response_format={"type": "json_object"})
            # Append history messages after System instruction prompt
            messages = [SystemMessage(content=supervisor_prompt)] + list(state["messages"])
            routing_response = await router_llm_json.ainvoke(messages)
            content = routing_response.content.strip()
            
            # Clean markdown code fences
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            parsed = json.loads(content)
            next_step = parsed.get("next", "FINISH").strip()
        except Exception as e:
            print(f"Routing failed: {e}")
            next_step = "FINISH"
            
        chosen_agent = next((sa for sa in sub_agents if str(sa[0]).lower() == next_step.lower()), None)
        
        if chosen_agent:
            # If the chosen agent is the master agent, we still run it, but label it with gateway_name
            name = gateway_name if str(chosen_agent[0]).lower() == master_agent_id.lower() else chosen_agent[1]
            return {
                "active_agent_id": chosen_agent[0], 
                "routed_agent_name": name,
                "next_agent": chosen_agent[0]
            }
            
        if next_step.lower() == master_agent_id.lower():
            return {
                "active_agent_id": master_agent_id,
                "routed_agent_name": gateway_name,
                "next_agent": master_agent_id
            }
            
        return {
            "active_agent_id": master_agent_id, 
            "routed_agent_name": gateway_name,
            "next_agent": "FINISH"
        }

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
            
        msgs = [m for m in state["messages"] if not isinstance(m, SystemMessage)]
        msgs.insert(0, SystemMessage(content=sys_prompt))
            
        try:
            response = None
            async for chunk in llm_with_tools.astream(msgs):
                if response is None:
                    response = chunk
                else:
                    response += chunk
            print("AGENT RESPONSE:", response)
        except Exception as e:
            err_str = str(e).lower()
            if "413" in err_str or "rate_limit" in err_str or "too large" in err_str or "failed to call a function" in err_str or "tool" in err_str or "400" in err_str:
                print(f"API/Rate Limit Error caught: {e}. Retrying with payload truncation...")
                truncated_msgs = []
                for m in msgs:
                    if hasattr(m, "content") and isinstance(m.content, str) and len(m.content) > 2000:
                        truncated_msgs.append(m.__class__(content=m.content[:2000] + "\n...[truncated for token limits]"))
                    else:
                        truncated_msgs.append(m)
                response = None
                async for chunk in llm.astream(truncated_msgs):
                    if response is None:
                        response = chunk
                    else:
                        response += chunk
            else:
                raise e
                
        return {"messages": [response]}

    # 3. Tool Execution Node
    async def tool_node(state: GraphState):
        active_agent_id = state.get("active_agent_id") or master_agent_id
        llm, _, embed_model, web_search_enabled = await llm_factory(active_agent_id)
        tools = tools_factory(active_agent_id, embed_model, web_search_enabled, llm)
        
        tool_executor = ToolNode(tools)
        return await tool_executor.ainvoke(state)
        
    def router_edge(state: GraphState):
        next_agent = state.get("next_agent")
        if not next_agent or next_agent == "FINISH":
            return END
        return "agent"

    def agent_edge(state: GraphState):
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "supervisor"

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges("supervisor", router_edge, {"agent": "agent", END: END})
    workflow.add_conditional_edges("agent", agent_edge, {"tools": "tools", "supervisor": "supervisor"})
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()
