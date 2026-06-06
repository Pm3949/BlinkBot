# server-python/schemas.py
from pydantic import BaseModel
from typing import List, Dict, Optional

class ChatRequest(BaseModel):
    agent_id: Optional[str] = None
    message: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = []

class WidgetChatRequest(BaseModel):
    chatbot_id: str
    message: str
    history: Optional[List[Dict[str, str]]] = []

# Ye missing tha pichle code mein!
class URLRequest(BaseModel):
    agent_id: str
    url: str

class CheckoutRequest(BaseModel):
    user_id: str
    plan_tier: str
    billing_cycle: str
    agents_limit: int = 1
    agent_messages_limit: int = 500
    storage_mb_limit: int = 100
    chatbots_limit: int = 1
    chatbot_messages_limit: int = 500

class RazorpayVerifyRequest(BaseModel):
    user_id: str
    plan_tier: str
    billing_cycle: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    agents_limit: int = 1
    agent_messages_limit: int = 500
    storage_mb_limit: int = 100
    chatbots_limit: int = 1
    chatbot_messages_limit: int = 500

class InviteRequest(BaseModel):
    email: str
    role: str
    workspace_id: str
    workspace_name: str
    invited_by_name: str
