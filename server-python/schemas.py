# server-python/schemas.py
from pydantic import BaseModel
from typing import List, Dict, Optional

class ChatRequest(BaseModel):
    agent_id: Optional[str] = None
    message: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = []

# Ye missing tha pichle code mein!
class URLRequest(BaseModel):
    agent_id: str
    url: str