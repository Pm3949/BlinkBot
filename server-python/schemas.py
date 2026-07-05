"""
Data Validation Schemas (Pydantic Models).
Responsibility: Defines the exact structure and types of data expected in API requests.
FastAPI uses these models to automatically validate incoming JSON data. If a client 
sends incorrect data types (e.g., a string instead of an int), FastAPI will automatically 
reject the request with a helpful 422 Error before it ever reaches our route handlers.
"""
# server-python/schemas.py
from pydantic import BaseModel
from typing import List, Dict, Optional
from enum import Enum

# ==========================================
# CHAT & WIDGET SCHEMAS
# ==========================================

class ChatRequest(BaseModel):
    """Schema for a standard internal chat with an agent."""
    agent_id: Optional[str] = None
    message: Optional[str] = None
    # History is a list of dictionaries (e.g., [{"role": "user", "content": "hi"}])
    history: Optional[List[Dict[str, str]]] = []
    language: Optional[str] = None

class WidgetChatRequest(BaseModel):
    """Schema for a chat request coming from an embedded public website widget."""
    chatbot_id: str
    message: str
    history: Optional[List[Dict[str, str]]] = []
    language: Optional[str] = None

class URLRequest(BaseModel):
    """Schema for requesting ingestion of a specific webpage URL by an agent."""
    agent_id: str
    url: str

class ConnectorRequest(BaseModel):
    """Schema for simulating a data connection sync (e.g. Google Drive, Slack) for an agent."""
    agent_id: str
    connector_id: str

# ==========================================
# BILLING & SUBSCRIPTION SCHEMAS
# ==========================================

class CheckoutRequest(BaseModel):
    """Initial request to start a checkout process."""
    plan_tier: str
    billing_cycle: str
    # Default limits for the basic plan
    workspaces_limit: int = 1
    agents_limit: int = 1
    agent_messages_limit: int = 500
    storage_mb_limit: int = 100
    chatbots_limit: int = 1
    chatbot_messages_limit: int = 500

class RazorpayVerifyRequest(BaseModel):
    """Schema for verifying a completed Razorpay transaction webhook/callback."""
    plan_tier: str
    billing_cycle: str
    razorpay_order_id: str
    razorpay_payment_id: str
    # Signature is crucial to verify the payment wasn't spoofed by the client
    razorpay_signature: str
    workspaces_limit: int = 1
    agents_limit: int = 1
    agent_messages_limit: int = 500
    storage_mb_limit: int = 100
    chatbots_limit: int = 1
    chatbot_messages_limit: int = 500

# ==========================================
# WORKSPACE SCHEMAS
# ==========================================

class WorkspaceCreate(BaseModel):
    """Schema to create a new workspace."""
    name: str
    email: str
    user_name: str

class InviteRequest(BaseModel):
    """Schema to invite a new team member to a workspace."""
    email: str
    role: str
    workspace_id: str
    workspace_name: str
    invited_by_name: str

# ==========================================
# NOTIFICATION SCHEMAS
# ==========================================

class NotificationType(str, Enum):
    """
    Enums strict-type the notification types. 
    If a developer tries to create a notification of type 'user_banned', Pydantic will throw an error 
    because it's not in this predefined list.
    """
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
    """Schema to create a new internal app notification."""
    workspace_id: str
    title: str
    message: str
    type: NotificationType

# ==========================================
# AUTHENTICATION SCHEMAS
# ==========================================

class UserRegister(BaseModel):
    email: str
    password: str

class VerifyOTP(BaseModel):
    """Schema for verifying the One-Time Password sent to email during registration."""
    email: str
    otp: str

class UserLogin(BaseModel):
    email: str
    password: str

class ForgotPassword(BaseModel):
    email: str

class ResetPassword(BaseModel):
    """Schema for the final step of password reset containing the secure token."""
    email: str
    token: str
    new_password: str

class Verify2FA(BaseModel):
    """Schema for setting up Two-Factor Authentication."""
    totp_code: str

class Login2FA(BaseModel):
    """Schema for providing the authenticator code during login if 2FA is enabled."""
    user_id: str
    totp_code: str
