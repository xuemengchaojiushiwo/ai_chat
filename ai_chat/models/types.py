from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

class Message(BaseModel):
    id: int
    conversation_id: int
    content: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

class Conversation(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: datetime
    messages: List[Message] = []

    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    content: str
    role: str

class MessageCreate(MessageBase):
    conversation_id: int

class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationBase(BaseModel):
    title: Optional[str] = None

class ConversationCreate(ConversationBase):
    pass

class ConversationResponse(ConversationBase):
    id: int
    created_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True

class Dataset(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class Document(BaseModel):
    id: int
    name: str
    content: Optional[str] = None
    mime_type: Optional[str] = None
    status: str
    error: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentSegmentCreate(BaseModel):
    id: Optional[int] = None
    document_id: int
    content: str
    embedding: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentSegment(BaseModel):
    id: int
    document_id: int
    content: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: int
    name: str
    content: Optional[str] = None
    mime_type: Optional[str] = None
    status: str
    error: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentSegmentResponse(BaseModel):
    id: int
    document_id: int
    content: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True 