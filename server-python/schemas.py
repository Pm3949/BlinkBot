# server-python/schemas.py
from pydantic import BaseModel
from typing import List, Dict, Optional

class ChatRequest(BaseModel):
    agent_id: Optional[str] = None
    message: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = []
    language: Optional[str] = None

class WidgetChatRequest(BaseModel):
    chatbot_id: str
    message: str
    history: Optional[List[Dict[str, str]]] = []
    language: Optional[str] = None

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

from enum import Enum

class NotificationType(str, Enum):
    feedback_new = "feedback_new"
    feedback_in_progress = "feedback_in_progress"
    feedback_resolved = "feedback_resolved"
    feedback_reopened = "feedback_reopened"
    
    document_uploaded = "document_uploaded"
    document_processed_success = "document_processed_success"
    document_processing_failed = "document_processing_failed"
    document_deleted = "document_deleted"
    
    agent_created = "agent_created"
    agent_setting_updated = "agent_setting_updated"
    agent_prompt_updated = "agent_prompt_updated"
    
    team_member_added = "team_member_added"
    system_alert = "system_alert"

class NotificationCreate(BaseModel):
    workspace_id: str
    title: str
    message: str
    type: NotificationType
