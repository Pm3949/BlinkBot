import asyncio
import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

async def main():
    api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", api_key=api_key)
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_knowledge_base",
                "description": "Search the internal knowledge base.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    
    llm_with_tools = llm.bind_tools(tools)
    messages = [HumanMessage(content="Search the knowledge base for python tips")]
    
    print("Testing tool call stream:")
    async for chunk in llm_with_tools.astream(messages):
        print(f"Chunk: content='{chunk.content}', tool_calls={chunk.tool_calls}")

if __name__ == "__main__":
    asyncio.run(main())
