import asyncio
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

agent_descriptions = """
ID: 1234abcd-1111 | Name: Network Manager | Description: The central router agent for this network.
ID: 1234abcd-2222 | Name: General Assistant | Description: A versatile assistant.
ID: 1234abcd-3333 | Name: Customer Service Coordinator | Description: Understand customer intent, provide initial greetings, and route complex requests to the appropriate specialist agent or handle simple queries directly.
ID: 1234abcd-4444 | Name: Order Tracking Specialist | Description: Provide accurate and up-to-date information regarding customer order statuses and tracking details.
ID: 1234abcd-5555 | Name: Returns & Refunds Agent | Description: Facilitate smooth and compliant return processes for customers, providing clear instructions and processing requests efficiently.
ID: 1234abcd-6666 | Name: Product Recommendation Specialist | Description: Suggest relevant products to customers based on their preferences, browsing history, or specific inquiries, leveraging the product catalog.
"""

from prompts.routing_prompts import ROUTING_SYSTEM_PROMPT

async def test():
    router_llm = ChatGroq(model_name="llama-3.1-8b-instant", api_key=api_key, temperature=0.0)
    router_llm_json = router_llm.bind(response_format={"type": "json_object"})
    
    prompt = ROUTING_SYSTEM_PROMPT.format(agent_descriptions=agent_descriptions, message="Product recomendation")
    print("PROMPT:", prompt)
    
    resp1 = router_llm_json.invoke(prompt)
    print("SYNC INVOKE:", resp1.content)
    
    resp2 = await router_llm_json.ainvoke(prompt)
    print("ASYNC AINVOKE:", resp2.content)

asyncio.run(test())
