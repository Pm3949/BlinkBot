import asyncio
import os
from langchain_groq import ChatGroq
from langchain_core.tools import tool

@tool
def search_knowledge_base(query: str) -> str:
    """Searches the internal knowledge base for company documents."""
    return f"Found document about {query}"

@tool
def search_web(query: str) -> str:
    """Searches the internet for real-time information."""
    return f"Web search results for {query}"

async def main():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("No GROQ API KEY")
        return
    
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", api_key=api_key)
    llm_with_tools = llm.bind_tools([search_knowledge_base, search_web])
    
    from langchain_core.messages import HumanMessage
    messages = [HumanMessage(content="What is the weather in Tokyo today?")]
    
    response = await llm_with_tools.ainvoke(messages)
    print("Response tool calls:", response.tool_calls)

if __name__ == "__main__":
    asyncio.run(main())
