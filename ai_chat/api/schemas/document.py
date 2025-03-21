from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class Document(BaseModel):
    id: int
    dataset_id: int
    name: str
    content: Optional[str] = None
    mime_type: str
    status: str
    error: Optional[str] = None
    created_at: Optional[datetime] = None 