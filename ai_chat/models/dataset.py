from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from ..database import Base


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    # 关系
    documents = relationship(
        "Document",
        back_populates="dataset",
        cascade="all, delete-orphan"
    )

class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    workspace = relationship(
        "ai_chat.models.workspace.Workspace",
        back_populates="conversations"
    )

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    content = Column(Text, nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    created_at = Column(DateTime, default=datetime.utcnow)
    citations = Column(JSON, nullable=True)  # 新增 citations 列

    # 关联
    conversation = relationship("Conversation", back_populates="messages") 