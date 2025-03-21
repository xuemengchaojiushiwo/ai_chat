from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class Message(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    citations: List[dict] = []
    created_at: Optional[datetime] = None

class MessageCreate(BaseModel):
    message: str
    use_rag: bool = False

class ConversationCreate(BaseModel):
    name: Optional[str] = None
    workspace_id: Optional[int] = None

class Conversation(BaseModel):
    id: int
    name: str
    workspace_id: Optional[int] = None
    created_at: Optional[datetime] = None
    messages: List[Message] = [] 