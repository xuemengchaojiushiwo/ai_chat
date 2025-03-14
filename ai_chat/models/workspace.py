from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class Workgroup(Base):
    __tablename__ = "workgroups"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联工作空间
    workspaces = relationship("ai_chat.models.workspace.Workspace", 
                            back_populates="workgroup", 
                            cascade="all, delete-orphan")

class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    group_id = Column(Integer, ForeignKey("workgroups.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    workgroup = relationship("ai_chat.models.workspace.Workgroup", back_populates="workspaces")
    documents = relationship(
        "ai_chat.models.document.DocumentWorkspace",
        back_populates="workspace",
        cascade="all, delete-orphan"
    )
    # 添加与 Conversation 的关系
    conversations = relationship(
        "ai_chat.models.dataset.Conversation",
        back_populates="workspace",
        cascade="all, delete-orphan"
    ) 