from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Citation(BaseModel):
    """引用文档片段模型"""
    text: str
    document_id: str
    segment_id: str
    similarity: float
    index: int
    page_number: Optional[int] = None  # PDF页码
    bbox_x: Optional[float] = None  # 边界框x坐标
    bbox_y: Optional[float] = None  # 边界框y坐标
    bbox_width: Optional[float] = None  # 边界框宽度
    bbox_height: Optional[float] = None  # 边界框高度

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "text": "这是一段引用文本",
                "document_id": "1",
                "segment_id": "1",
                "similarity": 0.8,
                "index": 1,
                "page_number": 1,
                "bbox_x": 100.0,
                "bbox_y": 200.0,
                "bbox_width": 100.0,
                "bbox_height": 100.0
            }
        }

class MessageBase(BaseModel):
    """消息基础模型"""
    content: str

class MessageCreate(BaseModel):
    """创建消息的请求模型"""
    message: str
    use_rag: bool = False

class Message(BaseModel):
    """消息响应模型"""
    id: int
    conversation_id: int
    role: str
    content: str
    tokens: Optional[int] = None
    citations: List[Citation] = Field(default_factory=list)
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class ConversationBase(BaseModel):
    """对话基础模型"""
    name: str

class ConversationCreate(BaseModel):
    name: str = "新对话"
    workspace_id: Optional[int] = None

class Conversation(BaseModel):
    id: int
    name: str
    workspace_id: Optional[int] = None
    created_at: Optional[str] = None
    messages: List[Message] = []

    class Config:
        from_attributes = True

class Document(BaseModel):
    """文档模型"""
    id: int
    dataset_id: int
    name: str
    content: Optional[str] = None
    mime_type: str
    status: str
    size: str
    version: int
    file_hash: str
    error: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True 